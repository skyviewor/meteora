"""Tests for the shared Aerolytica official-account session."""

import asyncio
import stat
import time

import httpx
import pytest

from aero.core.official_account import (
    CloudSyncClient,
    OfficialAccountSession,
    OfficialLoginRequiredError,
    OfficialSessionData,
    clear_official_session,
    load_official_session,
    save_official_session,
)


def _token_payload(*, access: str = "jwt-new", refresh: str = "rfr-new") -> dict:
    return {
        "user_id": "usr_1",
        "email": "user@example.com",
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": 3600,
        "refresh_expires_in": 86400,
        "token_type": "bearer",
    }


@pytest.fixture
def secrets_path(tmp_path, monkeypatch):
    path = tmp_path / "secrets.yaml"
    monkeypatch.setenv("AERO_SECRETS_PATH", str(path))
    return path


@pytest.mark.asyncio
async def test_login_persists_tokens_without_password(secrets_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/auth/login"
        return httpx.Response(200, json=_token_payload(), request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    session = OfficialAccountSession(base_url="https://api.test", client=client)

    result = await session.login("user@example.com", "never-save-this")

    assert result.email == "user@example.com"
    assert load_official_session().access_token == "jwt-new"
    assert "never-save-this" not in secrets_path.read_text()
    assert stat.S_IMODE(secrets_path.stat().st_mode) == 0o600
    await client.aclose()


@pytest.mark.asyncio
async def test_concurrent_refresh_is_coalesced(secrets_path):
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return httpx.Response(200, json=_token_payload(), request=request)

    save_official_session(
        OfficialSessionData(
            access_token="jwt-old",
            refresh_token="rfr-old",
            access_expires_at=time.time() - 1,
            refresh_expires_at=time.time() + 3600,
        )
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    session = OfficialAccountSession(base_url="https://api.test", client=client)

    tokens = await asyncio.gather(*(session.access_token() for _ in range(5)))

    assert tokens == ["jwt-new"] * 5
    assert calls == 1
    assert load_official_session().refresh_token == "rfr-new"
    await client.aclose()


@pytest.mark.asyncio
async def test_authenticated_request_refreshes_once_after_401(secrets_path):
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/v1/auth/refresh":
            return httpx.Response(200, json=_token_payload(), request=request)
        if request.headers["Authorization"] == "Bearer jwt-old":
            return httpx.Response(401, json={"detail": "expired"}, request=request)
        return httpx.Response(200, json={"user_id": "usr_1"}, request=request)

    save_official_session(
        OfficialSessionData(
            access_token="jwt-old",
            refresh_token="rfr-old",
            access_expires_at=time.time() + 3600,
            refresh_expires_at=time.time() + 7200,
        )
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    session = OfficialAccountSession(base_url="https://api.test", client=client)

    response = await session.request("GET", "/v1/auth/me")

    assert response.status_code == 200
    assert paths == ["/v1/auth/me", "/v1/auth/refresh", "/v1/auth/me"]
    await client.aclose()


@pytest.mark.asyncio
async def test_expired_refresh_token_clears_session(secrets_path):
    save_official_session(
        OfficialSessionData(
            access_token="jwt-old",
            refresh_token="rfr-old",
            access_expires_at=time.time() - 2,
            refresh_expires_at=time.time() - 1,
        )
    )
    session = OfficialAccountSession(
        base_url="https://api.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)),
    )

    with pytest.raises(OfficialLoginRequiredError):
        await session.access_token()

    assert not load_official_session().is_logged_in
    clear_official_session()
    await session._client.aclose()


@pytest.mark.asyncio
async def test_cloud_sync_boundary_uses_shared_session():
    class StubSession:
        async def request(self, method, path, **kwargs):
            return method, path, kwargs

    sync = CloudSyncClient(StubSession())
    result = await sync.request("GET", "/v1/files", params={"cursor": "next"})

    assert result == ("GET", "/v1/files", {"params": {"cursor": "next"}})
