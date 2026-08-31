from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.financial.collectors.dart_client import dart_get
from app.domain.financial.models.financial_statement import FinancialStatement

YEARS = [2021, 2022, 2023, 2024, 2025]
REPRT_CODE = "11011"  # 사업보고서
SCOPE_LABEL = {"CFS": "연결", "OFS": "별도"}

async def collect_financial_statements(
        session: AsyncSession, api_key: str, dart_corp_code: str
) -> None:
    for year in YEARS:
        data, used_scope = None, None
        for fs_div in ("CFS", "OFS"):  # 연결 우선, 없으면 별도
            result = await dart_get("fnlttSinglAcntAll.json", {
                "crtfc_key": api_key,
                "corp_code": dart_corp_code,
                "bsns_year": str(year),
                "reprt_code": REPRT_CODE,
                "fs_div": fs_div,
            })
            if result.get("status") == "000":
                data, used_scope = result["list"], fs_div
                break

        if not data:
            continue

        for item in data:
            stmt = pg_insert(FinancialStatement).values(
                corp_code=dart_corp_code,
                business_year=year,
                report_code=REPRT_CODE,
                statement_scope=SCOPE_LABEL[used_scope],
                statement_type=item["sj_div"],
                account_id=item.get("account_id") or None,
                account_name=item["account_nm"],
                current_amount=_to_num(item.get("thstrm_amount")),
                receipt_no=item.get("rcept_no"),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_financial_statement",
                set_={"current_amount": stmt.excluded.current_amount,
                      "receipt_no": stmt.excluded.receipt_no},
            )
            await session.execute(stmt)
        await session.commit()

def _to_num(value: str | None):
    if not value or value == "-":
        return None
    return float(value.replace(",", ""))