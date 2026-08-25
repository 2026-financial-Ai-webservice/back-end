from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domain.screening.models.fundamental_screening import FundamentalScreening

async def get_latest_snapshot(session: AsyncSession) -> list[Row]:
    """회사별 가장 최신 연도의 financial_ratios + market_data + companies 스냅샷"""
    query = text("""
        SELECT
            c.corp_code,
            c.is_manufacturing,
            fr.business_year,
            fr.revenue,
            fr.roe,
            fr.debt_ratio,
            fr.interest_coverage,
            md.market_cap
        FROM companies c
        JOIN (
            SELECT DISTINCT ON (corp_code) *
            FROM financial_ratios
            ORDER BY corp_code, business_year DESC
        ) fr ON fr.corp_code = c.corp_code
        LEFT JOIN (
            SELECT DISTINCT ON (corp_code) *
            FROM market_data
            ORDER BY corp_code, market_date DESC
        ) md ON md.corp_code = c.corp_code
    """)

    result = await session.execute(query)
    return result.all()

# 3개년 FCF 헬퍼
async def get_recent_fcf(session, corp_code: str, years: int = 3) -> list[float | None]:
    # financial_ratios에서 corp_code 기준 business_year DESC로 최근 N개 fcf 조회
    query = text("""
        SELECT fcf 
        FROM financial_ratios
        WHERE corp_code = :corp_code
        ORDER BY business_year DESC
        LIMIT :years
    """)

    result = await session.execute(query, {"corp_code": corp_code, "years": years})
    return [row[0] for row in result]

def is_fcf_3yr_negative(fcf_list: list[float | None]) -> bool:
    # 3년 연속 마이너스 실격 조건 -> 3개 다 존재 and 음수인 경우 True
    # 데이터가 3개 미만이면 실격(임시)
    if len(fcf_list) < 3:
        return True

    for fcf in fcf_list:
        if fcf is None:
            return True
        elif fcf >= 0:
            return False
    return True

# 메인 필터링 함수
async def screen_companies(session: AsyncSession) -> None:
    snapshot = await get_latest_snapshot(session)
    for row in snapshot:
        fcfs = await get_recent_fcf(session, row.corp_code)
        fail_reasons = []

        if row.revenue is None or row.revenue < 100_000_000_000:
            fail_reasons.append("매출액이 1000억 미만 또는 데이터 없음")
        if row.market_cap is None or row.market_cap < 2000:
            fail_reasons.append("시가총액 2000억 미만 또는 데이터 없음")
        if row.roe is None or row.roe < 7:
            fail_reasons.append("ROE 7% 미만 또는 데이터 없음")
        if row.debt_ratio is None or row.debt_ratio > 150:
            fail_reasons.append("부채비율 150% 초과 또는 데이터 없음")
        if row.interest_coverage is None or row.interest_coverage < 1:
            fail_reasons.append("이자보상배율 1 미만 또는 데이터 없음")
        if not row.is_manufacturing:
            fail_reasons.append("제조업 아님")
        if is_fcf_3yr_negative(fcfs):
            fail_reasons.append("최근 3개년 FCF 연속 마이너스 또는 데이터 부족")

        passed = len(fail_reasons) == 0

        stmt = pg_insert(FundamentalScreening).values(
            corp_code=row.corp_code,
            business_year=row.business_year,
            passed=passed,
            fail_reasons=", ".join(fail_reasons) if fail_reasons else None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["corp_code"],
            set_={
                "business_year": stmt.excluded.business_year,
                "passed": stmt.excluded.passed,
                "fail_reasons": stmt.excluded.fail_reasons,
                "screened_at": stmt.excluded.screened_at,
            },
        )
        await session.execute(stmt)
    await session.commit()