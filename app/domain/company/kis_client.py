import httpx

from app.core.config import settings
from app.domain.company.schema import KisStockInfoResponse


class KisApiError(Exception):
    pass

class KisClient:
    STOCK_INFO_PATH=(
        "/uapi/domestic-stock/v1/quotations/search-stock-info"
    )

    STOCK_INFO_TR_ID="CTPF1002R"

    def __init__(self) -> None:
        self.base_url = settings.KIS_BASE_URL

        if not settings.KIS_API_KEY:
            raise KisApiError("KIS_API_KEY가 설정되지 않았습니다.")
        if not settings.KIS_APP_SECRET:
            raise KisApiError("KIS_APP_SECRET이 설정되지 않았습니다.")
        if not settings.KIS_ACCESS_TOKEN:
            raise KisApiError("KIS_ACCESS_TOKEN이 설정되지 않았습니다.")

    async def get_stock_info(
            self, stock_code: str
    ) -> KisStockInfoResponse:
        headers={
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {settings.KIS_ACCESS_TOKEN}",
            "appkey": settings.KIS_API_KEY,
            "appsecret": settings.KIS_APP_SECRET,
            "tr_id": self.STOCK_INFO_TR_ID,
            "custtype":"P"
        }

        params={
            # 국내주식 상품유형코드
            "PRDT_TYPE_CD":"300",
            "PDNO":  stock_code
        }

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0
        ) as client:
            response=await client.get(
                self.STOCK_INFO_PATH,
                headers=headers,
                params=params
            )

        response.raise_for_status()

        result=KisStockInfoResponse.model_validate(response.json())

        if result.rt_cd !="0":
            raise KisApiError(
                f"KIS API 오류: {result.msg_cd} {result.msg1}"
            )
        if result.output is None:
            raise KisApiError("KIS API 응답에 output이 없습니다.")

        return result
    

