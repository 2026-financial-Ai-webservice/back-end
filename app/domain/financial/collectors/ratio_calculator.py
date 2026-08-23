from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.financial.models.financial_statement import FinancialStatement
from app.domain.financial.models.financial_ratio import FinancialRatio

# account_name은 회사마다 표기가 조금씩 다를 수 있어 실제 수집 후 검증 필요
ACCOUNT_MAP = {
    "revenue": "매출액",
    "operating_income": "영업이익",
    "net_income": "당기순이익",
    "total_liabilities": "부채총계",
    "total_equity": "자본총계",
    "operating_cash_flow": "영업활동으로인한현금흐름",
    "interest_expense": "이자비용",
    "capex": "유형자산의취득",
    "depreciation": "감가상각비",
    "cash_and_equivalents": "현금및현금성자산"
}

BORROWING_ACCOUNTS = ["단기차입금", "장기차입금", "유동성장기부채"]

async def calculate_ratios(
    session: AsyncSession, dart_corp_code: str, business_year: int
) -> None:
    rows = (await session.execute(
        select(FinancialStatement).where(
            FinancialStatement.corp_code == dart_corp_code,
            FinancialStatement.business_year == business_year,
        )
    )).scalars().all()
    if not rows:
        return

    acc = {r.account_name: float(r.current_amount or 0) for r in rows}
    values = {key: acc.get(name) for key, name in ACCOUNT_MAP.items()}

    total_equity = values["total_equity"] or 0
    total_liabilities = values["total_liabilities"] or 0
    net_income = values["net_income"] or 0
    operating_income = values["operating_income"] or 0
    operating_cf = values["operating_cash_flow"] or 0
    capex = values["capex"] or 0
    interest_expense = values["interest_expense"] or 0
    total_borrowings = sum(
        acc.get(name, 0) or 0 for name in BORROWING_ACCOUNTS
    ) or None

    fcf = operating_cf - capex if values["operating_cash_flow"] is not None else None
    roe = (net_income / total_equity * 100) if total_equity else None
    debt_ratio = (total_liabilities / total_equity * 100) if total_equity else None
    # 이자 비용은 표준 계정으로 잘 안 잡혀서(재무제표 주석에 있는 경우가 많음) None 처리 후 나중에 보완
    interest_coverage = (operating_income / interest_expense) if interest_expense else None

    stmt = pg_insert(FinancialRatio).values(
        corp_code=dart_corp_code,
        business_year=business_year,
        report_code="11011",
        revenue=values["revenue"],
        operating_income=values["operating_income"],
        net_income=values["net_income"],
        total_liabilities=values["total_liabilities"],
        total_equity=values["total_equity"],
        operating_cash_flow=values["operating_cash_flow"],
        capex=values["capex"],
        interest_expense=values["interest_expense"],
        depreciation=values["depreciation"],
        cash_and_equivalents=values["cash_and_equivalents"],
        total_borrowings=total_borrowings,
        fcf=fcf,
        roe=roe,
        debt_ratio=debt_ratio,
        interest_coverage=interest_coverage,
        dps=None,  # TODO: alotMatter API 연동 후 채우기
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_financial_ratio",
        set={c.name: getattr(stmt.excluded, c.name)
             for c in FinancialRatio.__table__.columns
             if c.name not in ("financial_ratios_id", "corp_code", "business_year", "report_code", "created_at")},
    )
    await session.execute(stmt)
    await session.commit()