from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import settings
from app.domain.marketdata.collectors.kis_client import KisMarketDataClient


@pytest.fixture(autouse=True)
def kis_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "KIS_APP_KEY", "app-key")
    monkeypatch.setattr(settings, "KIS_APP_SECRET", "app-secret")
    monkeypatch.setattr(settings, "KIS_ACCESS_TOKEN", "legacy-env-token")
    monkeypatch.setattr(settings, "MARKET_DATA_REQUEST_INTERVAL_SECONDS", 0)


async def test_issues_and_reuses_access_token() -> None:
    token_requests = 0
    price_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests, price_requests
        if request.url.path == "/oauth2/tokenP":
            token_requests += 1
            assert request.read().decode().find('"appkey":"app-key"') >= 0
            return httpx.Response(
                200,
                json={"access_token": "issued-token", "expires_in": 3600},
            )

        price_requests += 1
        assert request.headers["authorization"] == "Bearer issued-token"
        return httpx.Response(200, json={"rt_cd": "0", "output": {}})

    async with KisMarketDataClient(httpx.MockTransport(handler)) as client:
        await client.get_price("005930")
        await client.get_price("000660")

    assert token_requests == 1
    assert price_requests == 2


async def test_refreshes_token_after_authentication_failure() -> None:
    issued_tokens = iter(["expired-token", "refreshed-token"])
    token_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests
        if request.url.path == "/oauth2/tokenP":
            token_requests += 1
            return httpx.Response(
                200,
                json={"access_token": next(issued_tokens), "expires_in": 3600},
            )

        if request.headers["authorization"] == "Bearer expired-token":
            return httpx.Response(
                401,
                json={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "expired"},
            )
        return httpx.Response(200, json={"rt_cd": "0", "output": {}})

    async with KisMarketDataClient(httpx.MockTransport(handler)) as client:
        await client.get_price("005930")

    assert token_requests == 2


async def test_refreshes_token_before_expiration() -> None:
    token_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests
        if request.url.path == "/oauth2/tokenP":
            token_requests += 1
            return httpx.Response(
                200,
                json={"access_token": f"token-{token_requests}", "expires_in": 3600},
            )
        return httpx.Response(200, json={"rt_cd": "0", "output": {}})

    async with KisMarketDataClient(httpx.MockTransport(handler)) as client:
        await client.get_price("005930")
        client._token_expires_at = datetime.min.replace(tzinfo=UTC)
        await client.get_price("000660")

    assert token_requests == 2
