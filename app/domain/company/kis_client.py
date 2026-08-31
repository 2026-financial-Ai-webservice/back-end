import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.domain.company.schema import KisStockInfoResponse


class KisApiError(Exception):
    pass


class KisClient:
    STOCK_INFO_PATH = "/uapi/domestic-stock/v1/quotations/search-stock-info"
    STOCK_INFO_TR_ID = "CTPF1002R"
    AUTH_ERROR_CODES = {"EGW00121", "EGW00123"}

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.KIS_APP_KEY:
            raise KisApiError("KIS_APP_KEY가 설정되지 않았습니다.")
        if not settings.KIS_APP_SECRET:
            raise KisApiError("KIS_APP_SECRET이 설정되지 않았습니다.")

        self._client = httpx.AsyncClient(
            base_url=settings.KIS_BASE_URL,
            timeout=10.0,
            transport=transport,
        )
        self._token: str | None = None
        self._token_expires_at = datetime.min.replace(tzinfo=UTC)
        self._token_lock = asyncio.Lock()

    async def __aenter__(self) -> "KisClient":
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

    async def _issue_access_token(self, issued_at: datetime) -> str:
        try:
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
            token = payload.get("access_token")
            if not token:
                raise KisApiError("KIS 토큰 발급 응답에 access_token이 없습니다.")
            expires_in = max(int(payload.get("expires_in", 86400)) - 60, 0)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise KisApiError(f"KIS Access Token 발급에 실패했습니다: {exc}") from exc

        self._token = str(token)
        self._token_expires_at = issued_at + timedelta(seconds=expires_in)
        return self._token

    async def _invalidate_access_token(self, failed_token: str) -> None:
        async with self._token_lock:
            if self._token == failed_token:
                self._token = None
                self._token_expires_at = datetime.min.replace(tzinfo=UTC)

    @classmethod
    def _is_auth_error(
        cls,
        response: httpx.Response,
        payload: dict[str, Any],
    ) -> bool:
        return response.status_code == 401 or payload.get("msg_cd") in cls.AUTH_ERROR_CODES

    async def get_stock_info(self, stock_code: str) -> KisStockInfoResponse:
        params = {"PRDT_TYPE_CD": "300", "PDNO": stock_code}

        for auth_attempt in range(2):
            token = await self._access_token()
            try:
                response = await self._client.get(
                    self.STOCK_INFO_PATH,
                    headers={
                        "content-type": "application/json; charset=utf-8",
                        "authorization": f"Bearer {token}",
                        "appkey": settings.KIS_APP_KEY,
                        "appsecret": settings.KIS_APP_SECRET,
                        "tr_id": self.STOCK_INFO_TR_ID,
                        "custtype": "P",
                    },
                    params=params,
                )
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise KisApiError(f"KIS 종목정보 요청에 실패했습니다: {exc}") from exc

            if self._is_auth_error(response, payload) and auth_attempt == 0:
                await self._invalidate_access_token(token)
                continue

            if response.is_error:
                raise KisApiError(
                    f"KIS HTTP {response.status_code}: "
                    f"{payload.get('msg_cd')} {payload.get('msg1')}"
                )

            result = KisStockInfoResponse.model_validate(payload)
            if result.rt_cd != "0":
                raise KisApiError(f"KIS API 오류: {result.msg_cd} {result.msg1}")
            if result.output is None:
                raise KisApiError("KIS API 응답에 output이 없습니다.")
            return result

        raise KisApiError("KIS 인증 재시도 횟수를 초과했습니다.")

