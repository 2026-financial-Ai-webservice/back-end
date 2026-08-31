from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import settings
from app.domain.company.kis_client import KisClient


@pytest.fixture(autouse=True)
def kis_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "KIS_APP_KEY", "app-key")
    monkeypatch.setattr(settings, "KIS_APP_SECRET", "app-secret")


def stock_info_payload() -> dict[str, object]:
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리",
        "output": {
            "std_idst_clsf_cd_name": "제조업",
            "std_idst_clsf_cd": "03120",
        },
    }


async def test_issues_and_reuses_access_token() -> None:
    token_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests
        if request.url.path == "/oauth2/tokenP":
            token_requests += 1
            return httpx.Response(
                200,
                json={"access_token": "issued-token", "expires_in": 3600},
            )
        assert request.headers["authorization"] == "Bearer issued-token"
        return httpx.Response(200, json=stock_info_payload())

    async with KisClient(httpx.MockTransport(handler)) as client:
        await client.get_stock_info("005930")
        await client.get_stock_info("000660")

    assert token_requests == 1


async def test_refreshes_access_token_after_authentication_failure() -> None:
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
        return httpx.Response(200, json=stock_info_payload())

    async with KisClient(httpx.MockTransport(handler)) as client:
        await client.get_stock_info("005930")

    assert token_requests == 2


async def test_refreshes_access_token_before_expiration() -> None:
    token_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests
        if request.url.path == "/oauth2/tokenP":
            token_requests += 1
            return httpx.Response(
                200,
                json={"access_token": f"token-{token_requests}", "expires_in": 3600},
            )
        return httpx.Response(200, json=stock_info_payload())

    async with KisClient(httpx.MockTransport(handler)) as client:
        await client.get_stock_info("005930")
        client._token_expires_at = datetime.min.replace(tzinfo=UTC)
        await client.get_stock_info("000660")

    assert token_requests == 2
