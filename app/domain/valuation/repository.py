from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.valuation.model import ValuationResult
from app.domain.valuation.scoring import ScoredValuation


@dataclass(frozen=True, slots=True)
class ValuationInput:
    corp_code: str
    business_year: int
    average_fcf: Decimal
    listed_shares: int
    current_price: Decimal
    per: Decimal | None
    dps: Decimal | None


@dataclass(frozen=True, slots=True)
class PortfolioRequestPreferences:
    request_id: int
    return_preference: str
    valuation_preference: str
    investment_period: str
    risk_preference: str


async def get_valuation_inputs(
    session: AsyncSession,
) -> list[ValuationInput]:
    """
    펀더멘털 스크리닝을 통과한 기업의 valuation 입력값을 조회한다.

    사용 데이터:
        - 최근 3개년 평균 FCF
        - 최신 사업연도 DPS
        - 최신 거래일의 현재주가, PER, 상장주식 수

    제외 조건:
        - 최근 3개년 재무 데이터가 모두 존재하지 않는 기업
        - 최근 3개년 중 FCF가 NULL인 기업
        - 최신 현재주가가 없거나 0 이하인 기업
        - 상장주식 수가 없거나 0 이하인 기업
    """
    query = text(
        """
        WITH ranked_financial_ratios AS (
            SELECT
                fr.corp_code,
                fr.business_year,
                fr.fcf,
                fr.dps,
                ROW_NUMBER() OVER (
                    PARTITION BY fr.corp_code
                    ORDER BY fr.business_year DESC
                ) AS financial_rank
            FROM financial_ratios AS fr
            WHERE fr.report_code = '11011'
        ),

        recent_fcf AS (
            SELECT
                corp_code,
                AVG(fcf) AS average_fcf
            FROM ranked_financial_ratios
            WHERE financial_rank <= 3
            GROUP BY corp_code
            HAVING
                COUNT(*) = 3
                AND COUNT(fcf) = 3
        ),

        latest_financial_ratio AS (
            SELECT
                corp_code,
                business_year,
                dps
            FROM ranked_financial_ratios
            WHERE financial_rank = 1
        ),

        ranked_market_data AS (
            SELECT
                md.corp_code,
                md.current_price,
                md.listed_shares,
                md.per,
                ROW_NUMBER() OVER (
                    PARTITION BY md.corp_code
                    ORDER BY md.market_date DESC
                ) AS market_rank
            FROM market_data AS md
        ),

        latest_market_data AS (
            SELECT
                corp_code,
                current_price,
                listed_shares,
                per
            FROM ranked_market_data
            WHERE market_rank = 1
        )

        SELECT
            c.corp_code,
            lfr.business_year,
            rf.average_fcf,
            lmd.listed_shares,
            lmd.current_price,
            lmd.per,
            lfr.dps
        FROM companies AS c

        INNER JOIN fundamental_screening AS fs
            ON fs.corp_code = c.corp_code
            AND fs.passed IS TRUE

        INNER JOIN recent_fcf AS rf
            ON rf.corp_code = c.corp_code

        INNER JOIN latest_financial_ratio AS lfr
            ON lfr.corp_code = c.corp_code

        INNER JOIN latest_market_data AS lmd
            ON lmd.corp_code = c.corp_code

        WHERE
            rf.average_fcf > 0
            AND lmd.current_price > 0
            AND lmd.listed_shares > 0

        ORDER BY c.corp_code
        """
    )

    result = await session.execute(query)
    rows = result.mappings().all()

    return [
        ValuationInput(
            corp_code=row["corp_code"],
            business_year=row["business_year"],
            average_fcf=to_decimal(row["average_fcf"]),
            listed_shares=int(row["listed_shares"]),
            current_price=to_decimal(row["current_price"]),
            per=to_optional_decimal(row["per"]),
            dps=to_optional_decimal(row["dps"]),
        )
        for row in rows
    ]


async def replace_valuation_results(
    session: AsyncSession,
    *,
    request_id: int,
    results: list[ScoredValuation],
) -> None:
    """
    특정 portfolio request의 기존 valuation 결과를 전부 제거하고
    새 계산 결과로 교체한다.

    commit은 호출하는 service에서 실행한다.
    """
    await session.execute(
        delete(ValuationResult).where(
            ValuationResult.request_id == request_id
        )
    )

    valuation_results = [
        ValuationResult(
            request_id=request_id,
            corp_code=result.corp_code,
            business_year=result.business_year,
            dcf=result.dcf,
            per=result.per,
            dividend=result.dividend,
            score=result.score,
            rank_position=result.rank_position,
        )
        for result in results
    ]

    session.add_all(valuation_results)

    # DB 제약조건 오류를 commit 전에 확인한다.
    await session.flush()


async def get_valuation_results(
    session: AsyncSession,
    *,
    request_id: int,
) -> list[ValuationResult]:
    """
    특정 요청의 valuation 결과를 순위순으로 조회한다.
    """
    query = (
        select(ValuationResult)
        .where(
            ValuationResult.request_id == request_id
        )
        .order_by(
            ValuationResult.rank_position.asc(),
            ValuationResult.corp_code.asc(),
        )
    )

    result = await session.scalars(query)

    return list(result.all())


def to_decimal(value: object) -> Decimal:
    """
    DB에서 가져온 Numeric, Integer 값을 Decimal로 안전하게 변환한다.
    """
    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def to_optional_decimal(
    value: object | None,
) -> Decimal | None:
    if value is None:
        return None

    return to_decimal(value)


async def get_portfolio_request_preferences_by_id(
    session: AsyncSession,
    *,
    request_id: int
) -> list[PortfolioRequestPreferences]:
    query = text(
        """
        SELECT
            request_id,
            return_preference,
            valuation_preference,
            investment_period,
            risk_preference
        FROM portfolio_request
        WHERE request_id = :request_id
        """
    )

    result = await session.execute(
        query,
        {"request_id":request_id})
    
    row = result.mappings().all()
    row = result.mappings().one_or_none()

    if row is None:
        return None
    
    return [
        PortfolioRequestPreferences(
            request_id=row["request_id"],
            return_preference=row["return_preference"],
            valuation_preference=row["valuation_preference"],
            investment_period=row["investment_period"],
            risk_preference=row["risk_preference"],
        )
    ]



async def get_all_portfolio_request_preferences(
    session: AsyncSession,
) -> list[PortfolioRequestPreferences]:
    """
    장 마감 후 갱신을 위해 모든 요청을 조회한다.
    """
    query = text(
        """
        SELECT
            request_id,
            return_preference,
            valuation_preference,
            investment_period,
            risk_preference
        FROM portfolio_request
        ORDER BY request_id
        """
    )

    result = await session.execute(query)
    rows = result.mappings().all()

    return [
        PortfolioRequestPreferences(
            request_id=row["request_id"],
            return_preference=row["return_preference"],
            valuation_preference=row["valuation_preference"],
            investment_period=row["investment_period"],
            risk_preference=row["risk_preference"],
        )
        for row in rows
    ]