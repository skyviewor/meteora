"""Official Aerolytica account authentication and platform API access."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from aero.core.config import load_user_secrets, save_user_secrets

DEFAULT_PLATFORM_API_URL = "https://api.aerolytica.skyviewor.team"
DEFAULT_RELAY_LLM_URL = "https://llm.aerolytica.skyviewor.team/v1"
_REFRESH_SKEW_SECONDS = 60


class OfficialAccountError(RuntimeError):
    """A user-facing official-account error."""


class OfficialLoginRequiredError(OfficialAccountError):
    """The saved official session cannot be used or refreshed."""


@dataclass(frozen=True)
class OfficialSessionData:
    access_token: str = ""
    refresh_token: str = ""
    access_expires_at: float = 0.0
    refresh_expires_at: float = 0.0
    user_id: str = ""
    email: str = ""

    @property
    def is_logged_in(self) -> bool:
        return bool(self.access_token and self.refresh_token)


def platform_api_url() -> str:
    return os.environ.get("AERO_OFFICIAL_API_URL", DEFAULT_PLATFORM_API_URL).rstrip("/")


def relay_llm_url() -> str:
    return os.environ.get("AERO_OFFICIAL_LLM_URL", DEFAULT_RELAY_LLM_URL).rstrip("/")


def load_official_session() -> OfficialSessionData:
    data = load_user_secrets().get("official_account")
    if not isinstance(data, dict):
        return OfficialSessionData()
    return OfficialSessionData(
        access_token=str(data.get("access_token") or ""),
        refresh_token=str(data.get("refresh_token") or ""),
        access_expires_at=float(data.get("access_expires_at") or 0.0),
        refresh_expires_at=float(data.get("refresh_expires_at") or 0.0),
        user_id=str(data.get("user_id") or ""),
        email=str(data.get("email") or ""),
    )


def save_official_session(session: OfficialSessionData) -> None:
    secrets = load_user_secrets()
    secrets["official_account"] = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "access_expires_at": session.access_expires_at,
        "refresh_expires_at": session.refresh_expires_at,
        "user_id": session.user_id,
        "email": session.email,
    }
    save_user_secrets(secrets)


def clear_official_session() -> None:
    secrets = load_user_secrets()
    secrets.pop("official_account", None)
    save_user_secrets(secrets)


def _session_from_tokens(
    payload: dict[str, Any],
    previous: OfficialSessionData | None = None,
) -> OfficialSessionData:
    now = time.time()
    prior = previous or OfficialSessionData()
    access_token = str(payload.get("access_token") or "")
    refresh_token = str(payload.get("refresh_token") or "")
    if not access_token or not refresh_token:
        raise OfficialAccountError("官方账户服务返回了不完整的登录凭证。")
    return OfficialSessionData(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=float(
            payload.get("expires_at") or now + float(payload.get("expires_in") or 0)
        ),
        refresh_expires_at=float(
            payload.get("refresh_expires_at")
            or now + float(payload.get("refresh_expires_in") or 0)
        ),
        user_id=str(payload.get("user_id") or prior.user_id),
        email=str(payload.get("email") or prior.email),
    )


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback
    if not isinstance(payload, dict):
        return fallback
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or payload.get("message") or fallback)
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return str(payload.get("message") or fallback)


class OfficialAccountSession:
    """Shared JWT session for the platform, Relay LLM, and future cloud services."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url or platform_api_url()).rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30)
        self._owns_client = client is None
        self._refresh_lock = asyncio.Lock()
        self._session = load_official_session()
        self._refreshing = False

    @property
    def data(self) -> OfficialSessionData:
        return self._session

    @property
    def state(self) -> str:
        if self._refreshing:
            return "refreshing"
        if not self._session.is_logged_in:
            return "logged_out"
        if self._session.refresh_expires_at and self._session.refresh_expires_at <= time.time():
            return "login_required"
        return "logged_in"

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def login(self, email: str, password: str) -> OfficialSessionData:
        try:
            response = await self._client.post(
                f"{self.base_url}/v1/auth/login",
                json={"email": email.strip(), "password": password},
                headers={"Cache-Control": "no-store"},
            )
        except httpx.HTTPError as exc:
            raise OfficialAccountError("无法连接 Aerolytica 官方账户服务。") from exc
        if response.status_code >= 400:
            raise OfficialAccountError(_error_message(response, "邮箱或密码错误。"))
        self._session = _session_from_tokens(response.json())
        save_official_session(self._session)
        return self._session

    async def access_token(self, *, force_refresh: bool = False) -> str:
        session = self._session
        if not session.is_logged_in:
            raise OfficialLoginRequiredError("请先登录 Aerolytica 官方账户。")
        if (
            not force_refresh
            and session.access_expires_at > time.time() + _REFRESH_SKEW_SECONDS
        ):
            return session.access_token
        return (await self.refresh(force=force_refresh)).access_token

    async def refresh(self, *, force: bool = False) -> OfficialSessionData:
        async with self._refresh_lock:
            current = self._session
            if (
                not force
                and current.access_token
                and current.access_expires_at > time.time() + _REFRESH_SKEW_SECONDS
            ):
                return current
            if not current.refresh_token:
                raise OfficialLoginRequiredError("官方账户登录已失效，请重新登录。")
            if current.refresh_expires_at and current.refresh_expires_at <= time.time():
                clear_official_session()
                self._session = OfficialSessionData()
                raise OfficialLoginRequiredError("官方账户登录已过期，请重新登录。")
            self._refreshing = True
            try:
                response = await self._client.post(
                    f"{self.base_url}/v1/auth/refresh",
                    json={"refresh_token": current.refresh_token},
                    headers={"Cache-Control": "no-store"},
                )
            except httpx.HTTPError as exc:
                raise OfficialAccountError("刷新官方账户登录失败，请检查网络。") from exc
            finally:
                self._refreshing = False
            if response.status_code >= 400:
                clear_official_session()
                self._session = OfficialSessionData()
                raise OfficialLoginRequiredError(
                    _error_message(response, "官方账户登录已失效，请重新登录。")
                )
            self._session = _session_from_tokens(response.json(), current)
            save_official_session(self._session)
            return self._session

    async def request(
        self,
        method: str,
        path: str,
        *,
        retry_unauthorized: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        token = await self.access_token()
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {token}"
        try:
            response = await self._client.request(
                method, f"{self.base_url}{path}", headers=headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise OfficialAccountError("无法连接 Aerolytica 官方账户服务。") from exc
        if response.status_code == 401 and retry_unauthorized:
            token = await self.access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = await self._client.request(
                    method, f"{self.base_url}{path}", headers=headers, **kwargs
                )
            except httpx.HTTPError as exc:
                raise OfficialAccountError("无法连接 Aerolytica 官方账户服务。") from exc
        return response

    async def me(self) -> dict[str, Any]:
        response = await self.request("GET", "/v1/auth/me")
        if response.status_code >= 400:
            raise OfficialAccountError(_error_message(response, "无法读取官方账户信息。"))
        return response.json()

    async def credits(self) -> dict[str, Any]:
        response = await self.request("GET", "/v1/credits")
        if response.status_code >= 400:
            raise OfficialAccountError(_error_message(response, "无法读取账户额度。"))
        return response.json()

    async def logout(self) -> bool:
        refresh_token = self._session.refresh_token
        revoked = False
        try:
            if refresh_token:
                response = await self._client.post(
                    f"{self.base_url}/v1/auth/logout",
                    json={"refresh_token": refresh_token},
                    headers={"Cache-Control": "no-store"},
                )
                revoked = response.status_code < 400
        finally:
            clear_official_session()
            self._session = OfficialSessionData()
        return revoked


class CloudSyncClient:
    """Authentication boundary for future cloud file synchronization."""

    def __init__(self, session: OfficialAccountSession) -> None:
        self.session = session

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self.session.request(method, path, **kwargs)
