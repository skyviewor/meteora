"""Aero workspace configuration."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

_DEPRECATED_LLM_MODELS = {
    ("deepseek", "deepseek-chat"): "deepseek-v4-flash",
    ("deepseek", "deepseek-reasoner"): "deepseek-v4-pro",
}


class CDSCredentials(BaseModel):
    url: str = "https://cds.climate.copernicus.eu/api"
    key: str = ""


class ADSCredentials(BaseModel):
    url: str = "https://ads.atmosphere.copernicus.eu/api"
    key: str = ""


class EarthdataCredentials(BaseModel):
    token: str = ""


class Credentials(BaseModel):
    cds: CDSCredentials = CDSCredentials()
    ads: ADSCredentials = ADSCredentials()
    earthdata: EarthdataCredentials = EarthdataCredentials()


class LLMProviderConfig(BaseModel):
    api_key: str = ""
    model: str = ""
    base_url: str = ""


class LLMConfig(BaseModel):
    provider: str = "deepseek"
    model: str = "deepseek-v4-flash"
    reasoning_effort: str = ""
    base_url: str = ""
    supports_vision: bool = False
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict)

    def active_api_key(self) -> str:
        provider_config = self.providers.get(self.provider)
        return provider_config.api_key if provider_config else ""

    def set_active_api_key(self, api_key: str) -> None:
        self.provider_config(self.provider).api_key = api_key

    def provider_config(self, provider: str | None = None) -> LLMProviderConfig:
        provider_id = provider or self.provider
        if provider_id not in self.providers:
            self.providers[provider_id] = LLMProviderConfig()
        return self.providers[provider_id]

    def apply_active_provider_defaults(self) -> None:
        provider_config = self.provider_config(self.provider)
        if self.model:
            provider_config.model = self.model
        if self.base_url:
            provider_config.base_url = self.base_url

    def use_provider_settings(self) -> None:
        provider_config = self.providers.get(self.provider)
        if provider_config is None:
            return
        if provider_config.model:
            self.model = provider_config.model
        if provider_config.base_url:
            self.base_url = provider_config.base_url

    @property
    def api_key(self) -> str:
        return self.active_api_key()

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.set_active_api_key(value)

    def switch_provider(self, provider: str) -> None:
        self.provider = provider
        self.use_provider_settings()

    def migrate_deprecated_models(self) -> None:
        """Replace removed built-in model IDs in project and user profiles."""
        active_key = (self.provider.strip().lower(), self.model.strip().lower())
        self.model = _DEPRECATED_LLM_MODELS.get(active_key, self.model)
        for provider, profile in self.providers.items():
            profile_key = (provider.strip().lower(), profile.model.strip().lower())
            profile.model = _DEPRECATED_LLM_MODELS.get(profile_key, profile.model)


class VisionConfig(BaseModel):
    """Optional visual capability, separate from the required primary model."""

    mode: str = "unconfigured"  # unconfigured | reuse_primary | separate
    provider: str = "bailian"
    model: str = "qwen3.7-plus"
    api_key: str = ""
    base_url: str = ""
    cache_ttl_hours: int = 3


class WebSearchConfig(BaseModel):
    """Credentials and connection settings for the optional web search service."""

    provider: str = "bailian"
    model: str = "qwen-turbo"
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    from_name: str = "Aero"
    default_to: str = ""


class OutputConfig(BaseModel):
    data_dir: str = "data"


class AeroConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm: LLMConfig = LLMConfig()
    credentials: Credentials = Credentials()
    output: OutputConfig = OutputConfig()
    vision: VisionConfig = VisionConfig()
    web_search: WebSearchConfig = WebSearchConfig()
    email: EmailConfig = EmailConfig()
    language: str = "zh"
    mode: str = "execute"  # plan | qa | execute
    max_tool_rounds: int = 999

    @classmethod
    def load(cls, path: Path | str) -> "AeroConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        raw = cls._resolve_env(yaml.safe_load(path.read_text()) or {})
        _remove_secrets_from_config_data(raw)
        config = cls.model_validate(raw)
        config.llm.use_provider_settings()
        return apply_user_secrets(config)

    @classmethod
    def create_default(cls) -> "AeroConfig":
        return apply_user_secrets(cls())

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.llm.apply_active_provider_defaults()
        data = self.model_dump()
        _remove_secrets_from_config_data(data)
        path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    @staticmethod
    def _resolve_env(data: dict) -> dict:
        def resolve_value(value):
            if isinstance(value, str):
                return re.sub(
                    r"\$\{(\w+)\}",
                    lambda match: os.environ.get(match.group(1), match.group(0)),
                    value,
                )
            if isinstance(value, dict):
                return {key: resolve_value(item) for key, item in value.items()}
            if isinstance(value, list):
                return [resolve_value(item) for item in value]
            return value

        return resolve_value(data)


def user_secrets_path() -> Path:
    override = os.environ.get("AERO_SECRETS_PATH")
    return Path(override) if override else Path.home() / ".aero" / "secrets.yaml"


def load_user_secrets() -> dict:
    path = user_secrets_path()
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}
    data = AeroConfig._resolve_env(data)
    return data if isinstance(data, dict) else {}


def save_user_secrets(data: dict) -> None:
    path = user_secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
    path.chmod(0o600)


def apply_user_secrets(config: AeroConfig) -> AeroConfig:
    secrets = load_user_secrets()
    llm = secrets.get("llm")
    if isinstance(llm, dict):
        providers = llm.get("providers")
        if isinstance(providers, dict):
            for provider, values in providers.items():
                if not isinstance(values, dict):
                    continue
                profile = config.llm.provider_config(str(provider))
                profile.api_key = str(values.get("api_key") or profile.api_key)
                profile.model = str(values.get("model") or profile.model)
                profile.base_url = str(values.get("base_url") or profile.base_url)
        active_provider = str(llm.get("active_provider") or "")
        if active_provider and active_provider in config.llm.providers:
            config.llm.switch_provider(active_provider)
        elif not config.llm.active_api_key():
            for provider, values in config.llm.providers.items():
                if values.api_key:
                    config.llm.switch_provider(provider)
                    break

    credentials = secrets.get("credentials")
    if isinstance(credentials, dict):
        for field, target in (("cds", config.credentials.cds), ("ads", config.credentials.ads)):
            values = credentials.get(field)
            if isinstance(values, dict):
                target.url = str(values.get("url") or target.url)
                target.key = str(values.get("key") or target.key)
        earthdata = credentials.get("earthdata")
        if isinstance(earthdata, dict) and earthdata.get("token"):
            config.credentials.earthdata.token = str(earthdata["token"])

    vision = secrets.get("vision")
    legacy_web_search_secret = _is_legacy_web_search_in_vision(vision)
    if isinstance(vision, dict):
        config.vision.api_key = str(vision.get("api_key") or config.vision.api_key)
        config.vision.base_url = str(vision.get("base_url") or config.vision.base_url)
        config.vision.provider = str(vision.get("provider") or config.vision.provider)
        # Older releases accidentally wrote the web-search model (qwen-turbo)
        # into this section. It is not a vision model, so do not let it replace
        # the visual model selected by the project.
        if not legacy_web_search_secret:
            config.vision.model = str(vision.get("model") or config.vision.model)
    # Migrate existing users who stored a key before visual capability modes existed.
    if config.vision.mode == "unconfigured" and config.vision.api_key:
        config.vision.mode = "separate"

    web_search = secrets.get("web_search")
    if isinstance(web_search, dict):
        config.web_search.api_key = str(web_search.get("api_key") or config.web_search.api_key)
        config.web_search.base_url = str(web_search.get("base_url") or config.web_search.base_url)
        config.web_search.provider = str(web_search.get("provider") or config.web_search.provider)
        config.web_search.model = str(web_search.get("model") or config.web_search.model)
    elif legacy_web_search_secret and isinstance(vision, dict):
        # Keep the credential usable after upgrading without preserving the
        # incorrect vision-model override. It will be saved independently the
        # next time the user changes their search settings.
        config.web_search.api_key = str(vision.get("api_key") or config.web_search.api_key)
        config.web_search.base_url = str(vision.get("base_url") or config.web_search.base_url)

    email = secrets.get("email")
    if isinstance(email, dict) and email.get("smtp_password"):
        config.email.smtp_password = str(email["smtp_password"])

    config.llm.migrate_deprecated_models()
    return config


def save_llm_api_key(provider: str, api_key: str) -> None:
    secrets = load_user_secrets()
    llm = secrets.setdefault("llm", {})
    providers = llm.setdefault("providers", {})
    provider_data = providers.setdefault(provider, {})
    provider_data["api_key"] = api_key
    save_user_secrets(secrets)


def save_llm_profile(provider: str, api_key: str, model: str, base_url: str) -> None:
    secrets = load_user_secrets()
    llm = secrets.setdefault("llm", {})
    llm["active_provider"] = provider
    profile = llm.setdefault("providers", {}).setdefault(provider, {})
    profile.update({"api_key": api_key, "model": model, "base_url": base_url})
    save_user_secrets(secrets)


def clear_llm_api_key(provider: str) -> None:
    save_llm_api_key(provider, "")


def save_cds_credentials(url: str, key: str) -> None:
    secrets = load_user_secrets()
    secrets.setdefault("credentials", {})["cds"] = {"url": url, "key": key}
    save_user_secrets(secrets)


def clear_cds_credentials() -> None:
    save_cds_credentials("", "")


def save_ads_credentials(url: str, key: str) -> None:
    secrets = load_user_secrets()
    secrets.setdefault("credentials", {})["ads"] = {"url": url, "key": key}
    save_user_secrets(secrets)


def clear_ads_credentials() -> None:
    save_ads_credentials("", "")


def save_earthdata_token(token: str) -> None:
    secrets = load_user_secrets()
    secrets.setdefault("credentials", {})["earthdata"] = {"token": token}
    save_user_secrets(secrets)


def clear_earthdata_token() -> None:
    save_earthdata_token("")


def save_vision_api_key(
    api_key: str,
    base_url: str = "",
    *,
    provider: str = "",
    model: str = "",
) -> None:
    secrets = load_user_secrets()
    vision = secrets.setdefault("vision", {})
    vision["api_key"] = api_key
    if base_url:
        vision["base_url"] = base_url
    if provider:
        vision["provider"] = provider
    if model:
        vision["model"] = model
    save_user_secrets(secrets)


def save_web_search_api_key(
    api_key: str,
    base_url: str = "",
    *,
    provider: str = "bailian",
    model: str = "qwen-turbo",
) -> None:
    """Save the optional web-search credential without changing vision settings."""
    secrets = load_user_secrets()
    web_search = secrets.setdefault("web_search", {})
    web_search["api_key"] = api_key
    if base_url:
        web_search["base_url"] = base_url
    if provider:
        web_search["provider"] = provider
    if model:
        web_search["model"] = model
    save_user_secrets(secrets)


def vision_is_configured(config: AeroConfig) -> bool:
    if config.vision.mode == "separate":
        return bool(config.vision.model and config.vision.api_key)
    if config.vision.mode == "reuse_primary":
        return bool(config.llm.supports_vision and config.llm.model and config.llm.active_api_key())
    return False


def resolved_vision_config(config: AeroConfig) -> VisionConfig | None:
    if config.vision.mode == "reuse_primary" and vision_is_configured(config):
        return VisionConfig(
            mode="reuse_primary",
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.active_api_key(),
            base_url=config.llm.base_url,
            cache_ttl_hours=config.vision.cache_ttl_hours,
        )
    if config.vision.mode == "separate" and vision_is_configured(config):
        return config.vision
    return None


def save_email_smtp_password(smtp_password: str) -> None:
    secrets = load_user_secrets()
    secrets.setdefault("email", {})["smtp_password"] = smtp_password
    save_user_secrets(secrets)


def clear_email_config() -> None:
    save_email_smtp_password("")


def _remove_secrets_from_config_data(data: dict) -> None:
    credentials = data.get("credentials")
    if isinstance(credentials, dict):
        for field in ("cds", "ads"):
            values = credentials.get(field)
            if isinstance(values, dict):
                values["key"] = ""
        earthdata = credentials.get("earthdata")
        if isinstance(earthdata, dict):
            earthdata["token"] = ""
    llm = data.get("llm")
    if isinstance(llm, dict) and isinstance(llm.get("providers"), dict):
        for profile in llm["providers"].values():
            if isinstance(profile, dict):
                profile["api_key"] = ""
    vision = data.get("vision")
    if isinstance(vision, dict):
        vision["api_key"] = ""
    web_search = data.get("web_search")
    if isinstance(web_search, dict):
        web_search["api_key"] = ""
    email = data.get("email")
    if isinstance(email, dict):
        email["smtp_password"] = ""


def _is_legacy_web_search_in_vision(values: object) -> bool:
    """Identify the short-lived config bug that stored search settings as vision."""
    if not isinstance(values, dict):
        return False
    return (
        str(values.get("provider") or "").strip().lower() == "bailian"
        and str(values.get("model") or "").strip().lower() == "qwen-turbo"
    )
