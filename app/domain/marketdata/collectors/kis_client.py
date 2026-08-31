from __future__ import annotations

import asyncio
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings


class KisApiError(RuntimeError):
    pass


class KisMarketDataClient:
    RATE_LIMIT_CODE = "EGW00201"
    MAX_RATE_LIMIT_RETRIES = 3
    PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
    PRICE_TR_ID = "FHKST01010100"
    HOLIDAY_PATH = "/uapi/domestic-stock/v1/quotations/chk-holiday"
    HOLIDAY_TR_ID = "CTCA0903R"
    AUTH_ERROR_CODES = {"EGW00121", "EGW00123"}

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.KIS_APP_KEY or not settings.KIS_APP_SECRET:
            raise KisApiError("KIS_APP_KEY와 KIS_APP_SECRET을 설정해야 합니다.")
        self._client = httpx.AsyncClient(
            base_url=settings.KIS_BASE_URL,
            timeout=15.0,
            transport=transport,
        )
        self._token: str | None = None
        self._token_expires_at = datetime.min.replace(tzinfo=UTC)
        self._token_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def __aenter__(self) -> KisMarketDataClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _access_token(self) -> str:
        now = datetime.now(UTC)
        async with self._token_lock:
            if self._token and now < self._token_expires_at:
                return self._token
            return await self._issue_access_token(now)

    async def issue_access_token(self) -> str:
        """기존 .env 토큰과 관계없이 새 Access Token을 발급한다."""
        async with self._token_lock:
            return await self._issue_access_token(datetime.now(UTC))

    async def _issue_access_token(self, issued_at: datetime) -> str:
        response = await self._client.post(
            "/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_APP_SECRET,
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        expires_in = max(int(payload.get("expires_in", 86400)) - 60, 0)
        self._token_expires_at = issued_at + timedelta(seconds=expires_in)
        return self._token

    async def _invalidate_access_token(self, failed_token: str) -> None:
        async with self._token_lock:
            if self._token == failed_token:
                self._token = None
                self._token_expires_at = datetime.min.replace(tzinfo=UTC)

    def _is_auth_error(self, response: httpx.Response, payload: dict[str, Any]) -> bool:
        return (
            response.status_code == 401
            or payload.get("msg_cd") in self.AUTH_ERROR_CODES
        )

    async def _get(
        self, path: str, tr_id: str, params: dict[str, str]
    ) -> dict[str, Any]:
        for auth_attempt in range(2):
            for attempt in range(self.MAX_RATE_LIMIT_RETRIES + 1):
                response, token = await self._rate_limited_get(path, tr_id, params)
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise KisApiError(
                        f"KIS HTTP {response.status_code}: {response.text[:500]}"
                    ) from exc

                if self._is_auth_error(response, payload) and auth_attempt == 0:
                    await self._invalidate_access_token(token)
                    break

                if payload.get("msg_cd") == self.RATE_LIMIT_CODE:
                    if attempt == self.MAX_RATE_LIMIT_RETRIES:
                        raise KisApiError(
                            f"KIS API 오류 {self.RATE_LIMIT_CODE}: {payload.get('msg1')}"
                        )
                    await asyncio.sleep(
                        settings.MARKET_DATA_REQUEST_INTERVAL_SECONDS * (attempt + 1)
                    )
                    continue

                if response.is_error:
                    raise KisApiError(
                        f"KIS HTTP {response.status_code}: "
                        f"{payload.get('msg_cd')} {payload.get('msg1')}"
                    )
                if payload.get("rt_cd") != "0":
                    raise KisApiError(
                        f"KIS API 오류 {payload.get('msg_cd')}: {payload.get('msg1')}"
                    )
                return payload

        raise KisApiError("KIS API 재시도 횟수를 초과했습니다.")

    async def _rate_limited_get(
        self, path: str, tr_id: str, params: dict[str, str]
    ) -> tuple[httpx.Response, str]:
        async with self._request_lock:
            elapsed = time.monotonic() - self._last_request_at
            wait_seconds = settings.MARKET_DATA_REQUEST_INTERVAL_SECONDS - elapsed
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            try:
                token = await self._access_token()
                response = await self._client.get(
                    path,
                    headers={
                        "content-type": "application/json; charset=utf-8",
                        "authorization": f"Bearer {token}",
                        "appkey": settings.KIS_APP_KEY,
                        "appsecret": settings.KIS_APP_SECRET,
                        "tr_id": tr_id,
                        "custtype": "P",
                    },
                    params=params,
                )
                return response, token
            finally:
                self._last_request_at = time.monotonic()

    async def get_price(self, stock_code: str) -> dict[str, Any]:
        payload = await self._get(
            self.PRICE_PATH,
            self.PRICE_TR_ID,
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code},
        )
        output = payload.get("output")
        if not isinstance(output, dict):
            raise KisApiError(f"{stock_code}: 현재가 응답에 output이 없습니다.")
        return output

    async def is_market_open_day(self, target_date: date) -> bool:
        payload = await self._get(
            self.HOLIDAY_PATH,
            self.HOLIDAY_TR_ID,
            {
                "BASS_DT": target_date.strftime("%Y%m%d"),
                "CTX_AREA_FK": "",
                "CTX_AREA_NK": "",
            },
        )
        target = target_date.strftime("%Y%m%d")
        return any(
            row.get("bass_dt") == target and row.get("opnd_yn") == "Y"
            for row in payload.get("output") or []
        )
