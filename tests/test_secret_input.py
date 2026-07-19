"""Tests for model-driven, client-local secret entry."""

import pytest

from aero.core.config import AeroConfig
from aero.toolbox.secret_input import (
    SecretInputRequest,
    credential_request_for,
    request_secret_input_from_context,
    use_secret_input_provider,
)
from aero.toolbox.tools.configuration import configure_cds_key, save_secret_handle


def test_request_secret_input_is_registered_for_model_calls():
    from aero.toolbox.registry import get_registry

    spec = get_registry().get("request_secret_input")

    assert spec is not None
    assert "secret_handle" in spec.description
    saver = get_registry().get("save_secret_handle")
    assert saver is not None


def test_credential_request_is_declared_by_scope_not_the_ui():
    request = credential_request_for("ads")

    assert request["scope"] == "ads"
    assert request["multiline"] is True
    assert request["sensitive"] is True
    assert credential_request_for("earthdata")["multiline"] is False


@pytest.mark.asyncio
async def test_secret_handle_saves_cds_without_exposing_raw_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AERO_SECRETS_PATH", str(tmp_path / "secrets.yaml"))
    AeroConfig.create_default().save(tmp_path / "aero.yaml")
    raw_credential = "url: https://cds.climate.copernicus.eu/api\nkey: secret-cds-value"
    handles = {"one-time-handle": raw_credential}

    async def provider(request):
        assert request.scope == "cds"
        assert request.multiline is True
        return {"status": "submitted", "secret_handle": "one-time-handle"}

    with use_secret_input_provider(provider, handles.pop):
        result = await request_secret_input_from_context(
            SecretInputRequest("cds", "配置 CDS", "url: ...\nkey: ...", True)
        )
        saved = configure_cds_key(credential_handle=result["secret_handle"])

    assert saved["status"] == "success"
    assert raw_credential not in repr(result)
    assert raw_credential not in repr(saved)
    assert AeroConfig.load(tmp_path / "aero.yaml").credentials.cds.key == "secret-cds-value"


def test_generic_secret_handle_dispatches_to_registered_scope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AERO_SECRETS_PATH", str(tmp_path / "secrets.yaml"))
    AeroConfig.create_default().save(tmp_path / "aero.yaml")
    handles = {"one-time-handle": "ads-secret-value"}

    with use_secret_input_provider(lambda _: None, handles.pop):
        saved = save_secret_handle("ads", "one-time-handle")

    assert saved["status"] == "success"
    assert "ads-secret-value" not in repr(saved)
    assert AeroConfig.load(tmp_path / "aero.yaml").credentials.ads.key == "ads-secret-value"


def test_generic_secret_handle_saves_earthdata_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AERO_SECRETS_PATH", str(tmp_path / "secrets.yaml"))
    AeroConfig.create_default().save(tmp_path / "aero.yaml")
    handles = {"one-time-handle": "Bearer earthdata-secret-value"}

    with use_secret_input_provider(lambda _: None, handles.pop):
        saved = save_secret_handle("earthdata", "one-time-handle")

    assert saved["status"] == "success"
    assert "earthdata-secret-value" not in repr(saved)
    assert (
        AeroConfig.load(tmp_path / "aero.yaml").credentials.earthdata.token
        == "earthdata-secret-value"
    )
