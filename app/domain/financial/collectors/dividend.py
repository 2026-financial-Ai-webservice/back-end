from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.financial.collectors.dart_client import dart_get
from app.domain.financial.models.financial_ratio import FinancialRatio

REPRT_CODE = "11011"


def _to_num(value: str | None):
    if not value or value == "-":
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


async def collect_dividend(
        session: AsyncSession, api_key: str, dart_corp_code: str, business_year: int
) -> None:
    result = await dart_get("alotMatter.json", {
        "crtfc_key": api_key,
        "corp_code": dart_corp_code,
        "bsns_year": str(business_year),
        "reprt_code": REPRT_CODE,
    })
    if result.get("status") != "000":
        return  # 013(데이터없음) 등은 그냥 스킵 - 배당 안 한 해일 수 있음

    dps = None
    for item in result.get("list", []):
        if item.get("se") == "주당 현금배당금(원)" and item.get("stock_knd") == "보통주":
            dps = _to_num(item.get("thstrm"))
            break

    if dps is None:
        return

    await session.execute(
        update(FinancialRatio)
        .where(
            FinancialRatio.corp_code == dart_corp_code,
            FinancialRatio.business_year == business_year,
            FinancialRatio.report_code == REPRT_CODE,
            )
        .values(dps=dps)
    )
    await session.commit()
