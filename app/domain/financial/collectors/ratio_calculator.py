from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.financial.models.financial_ratio import FinancialRatio
from app.domain.financial.models.financial_statement import FinancialStatement

# 이미 잘 맞는 것들은 그대로 account_name 유지
ACCOUNT_MAP = {
    "total_liabilities": "부채총계",
    "total_equity": "자본총계",
    "cash_and_equivalents": "현금및현금성자산",
}

# 회사마다 라벨이 제각각이라 account_id(고정 XBRL 코드) 기준으로 매칭
ACCOUNT_ID_MAP = {
    "revenue": ["ifrs-full_Revenue"],
    "operating_income": ["dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"],
    "net_income": ["ifrs-full_ProfitLoss", "dart_ProfitLossForStatementOfCashFlows"],
    "operating_cash_flow": [
        "ifrs-full_CashFlowsFromUsedInOperatingActivities",
        "ifrs-full_CashFlowsFromUsedInOperations",
    ],
    "capex": ["ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"],
}

INTEREST_EXPENSE_ACCOUNT_IDS = [
    "ifrs-full_InterestExpense",
    "dart_InterestExpenseFinanceExpense",
    "dart_AdjustmentsForInterestExpenses",
    "ifrs-full_FinanceCosts",
    "ifrs-full_InterestPaidClassifiedAsOperatingActivities",
    "ifrs-full_InterestPaidClassifiedAsFinancingActivities",
]

BORROWING_ACCOUNT_IDS = [
    "ifrs-full_ShorttermBorrowings",
    "dart_LongTermBorrowingsGross",
    "ifrs-full_LongtermBorrowings",
    "ifrs-full_NoncurrentPortionOfNoncurrentLoansReceived",
    "ifrs-full_CurrentPortionOfLongtermBorrowings",
]

DEPRECIATION_ACCOUNT_IDS = [
    "dart_AdjustmentsForDepreciationExpense",
    "ifrs-full_AdjustmentsForDepreciationExpense",
    "dart_DepreciationExpense",
]
AMORTIZATION_ACCOUNT_IDS = [
    "dart_AdjustmentsForAmortisationExpense",
    "ifrs-full_AdjustmentsForAmortisationExpense",
]

async def _fetch_statement_rows(
        session: AsyncSession, dart_corp_code: str, business_year: int, scope: str
):
    result = await session.execute(
        select(FinancialStatement).where(
            FinancialStatement.corp_code == dart_corp_code,
            FinancialStatement.business_year == business_year,
            FinancialStatement.statement_scope == scope,
            )
    )
    return result.scalars().all()


async def calculate_ratios(
        session: AsyncSession, dart_corp_code: str, business_year: int
) -> None:
    rows = await _fetch_statement_rows(session, dart_corp_code, business_year, "연결")
    if not rows:
        rows = await _fetch_statement_rows(session, dart_corp_code, business_year, "별도")
    if not rows:
        return

    acc = {r.account_name: float(r.current_amount or 0) for r in rows if r.statement_type != "SCE"}
    acc_by_id = {
        r.account_id: float(r.current_amount or 0)
        for r in rows
        if r.account_id and r.statement_type != "SCE"
    }

    def pick(ids: list[str]):
        return next((acc_by_id[i] for i in ids if i in acc_by_id), None)

    values = {key: acc.get(name) for key, name in ACCOUNT_MAP.items()}
    values.update({key: pick(ids) for key, ids in ACCOUNT_ID_MAP.items()})

    total_equity = values["total_equity"] or 0
    total_liabilities = values["total_liabilities"] or 0
    net_income = values["net_income"] or 0
    operating_income = values["operating_income"] or 0
    operating_cf = values["operating_cash_flow"] or 0
    capex = values["capex"] or 0
    interest_expense = next(
        (abs(acc_by_id[aid]) for aid in INTEREST_EXPENSE_ACCOUNT_IDS if aid in acc_by_id),
        None,
    )
    total_borrowings = sum(
        acc_by_id.get(aid, 0) or 0 for aid in BORROWING_ACCOUNT_IDS
    ) or None

    dep_ppe = pick(DEPRECIATION_ACCOUNT_IDS)
    amortization = pick(AMORTIZATION_ACCOUNT_IDS)
    depreciation = (
        None
        if dep_ppe is None and amortization is None
        else (dep_ppe or 0) + (amortization or 0)
    )

    fcf = operating_cf - capex if values["operating_cash_flow"] is not None else None
    roe = (net_income / total_equity * 100) if total_equity else None
    debt_ratio = (total_liabilities / total_equity * 100) if total_equity else None
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
        interest_expense=interest_expense,
        depreciation=depreciation,
        cash_and_equivalents=values["cash_and_equivalents"],
        total_borrowings=total_borrowings,
        fcf=fcf,
        roe=roe,
        debt_ratio=debt_ratio,
        interest_coverage=interest_coverage,
        dps=None,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_financial_ratio",
        set_={
            c.name: getattr(stmt.excluded, c.name)
            for c in FinancialRatio.__table__.columns
            if c.name
            not in ("financial_ratios_id", "corp_code", "business_year",
                    "report_code", "created_at", "dps"
                    )
        },
    )
    await session.execute(stmt)
    await session.commit()


