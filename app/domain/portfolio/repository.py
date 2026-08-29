"""포트폴리오 생성 요청과 LLM 입력 데이터 조회."""

from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.portfolio.schema.portfolioCreateRequest import PortfolioCreateRequest
from app.domain.valuation.model import PortfolioRequest


class PortfolioCompanyDetails(TypedDict):
    company_name: str
    per: float | None
    pbr: float | None
    market_cap: int | None
    roe: float | None
    dcf: float
    dividend_yield: float | None
    business_summary: str


_SELECT_PORTFOLIO_COMPANY_DETAILS = text(
    """
    WITH latest_market_data AS (
        SELECT DISTINCT ON (market.corp_code)
            market.corp_code,
            market.current_price,
            market.market_cap,
            market.per,
            market.pbr
        FROM market_data AS market
        ORDER BY
            market.corp_code,
            market.market_date DESC
    ),
    latest_financial_ratio AS (
        SELECT DISTINCT ON (ratio.corp_code)
            ratio.corp_code,
            ratio.roe,
            ratio.dps
        FROM financial_ratios AS ratio
        WHERE ratio.report_code = '11011'
        ORDER BY
            ratio.corp_code,
            ratio.business_year DESC,
            ratio.financial_ratios_id DESC
    )
    SELECT
        valuation.corp_code,
        company.corp_name AS company_name,
        market.per,
        market.pbr,
        market.market_cap,
        ratio.roe,
        valuation.dcf,
        CASE
            WHEN ratio.dps IS NULL
              OR market.current_price IS NULL
              OR market.current_price <= 0
            THEN NULL
            ELSE ratio.dps / market.current_price * 100
        END AS dividend_yield,
        COALESCE(
            report_summary.content,
            company.industry_category,
            '사업 개요 정보 없음'
        ) AS business_summary
    FROM valuation_result AS valuation
    JOIN companies AS company
      ON company.corp_code = valuation.corp_code
    LEFT JOIN latest_market_data AS market
      ON market.corp_code = valuation.corp_code
    LEFT JOIN latest_financial_ratio AS ratio
      ON ratio.corp_code = valuation.corp_code
    LEFT JOIN LATERAL (
        SELECT chunk.content
        FROM company_reports AS report
        JOIN report_chunks AS chunk
          ON chunk.report_id = report.report_id
        WHERE report.corp_code = valuation.corp_code
        ORDER BY
            report.filing_date DESC,
            report.report_id DESC,
            chunk.chunk_order
        LIMIT 1
    ) AS report_summary ON TRUE
    WHERE valuation.request_id = :request_id
      AND valuation.corp_code IN :corp_codes
    ORDER BY valuation.rank_position, valuation.corp_code
    """
).bindparams(
    bindparam(
        "corp_codes",
        expanding=True,
    )
)


async def create_portfolio_request(
    session: AsyncSession,
    request: PortfolioCreateRequest,
) -> int:
    """포트폴리오 생성 요청을 저장하고 생성된 request_id를 반환한다."""
    portfolio_request = PortfolioRequest(
        seed_money=request.seed_money,
        investment_period=request.investment_period.value,
        risk_preference=request.risk_preference.value,
        return_preference=request.return_preference.value,
        valuation_preference=request.valuation_preference.value,
    )
    session.add(portfolio_request)
    await session.flush()

    return int(portfolio_request.request_id)


async def get_portfolio_company_details(
    session: AsyncSession,
    *,
    request_id: int,
    corp_codes: Sequence[str],
) -> dict[str, PortfolioCompanyDetails]:
    """valuation 후보 기업의 최신 정량 데이터와 보고서 요약을 조회한다."""
    if request_id <= 0:
        raise ValueError(
            "request_id는 1 이상이어야 합니다."
        )

    normalized_codes = _normalize_corp_codes(corp_codes)
    if not normalized_codes:
        return {}

    result = await session.execute(
        _SELECT_PORTFOLIO_COMPANY_DETAILS,
        {
            "request_id": request_id,
            "corp_codes": normalized_codes,
        },
    )

    details: dict[str, PortfolioCompanyDetails] = {}

    for row in result.mappings():
        corp_code = row["corp_code"]
        details[corp_code] = PortfolioCompanyDetails(
            company_name=row["company_name"],
            per=_to_optional_float(row["per"]),
            pbr=_to_optional_float(row["pbr"]),
            market_cap=(
                int(row["market_cap"])
                if row["market_cap"] is not None
                else None
            ),
            roe=_to_optional_float(row["roe"]),
            dcf=float(row["dcf"]),
            dividend_yield=_to_optional_float(
                row["dividend_yield"]
            ),
            business_summary=row["business_summary"],
        )

    return details


def _normalize_corp_codes(
    corp_codes: Sequence[str],
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for corp_code in corp_codes:
        code = corp_code.strip()

        if not code:
            continue

        if len(code) != 8 or not code.isdigit():
            raise ValueError(
                "corp_code는 숫자로 구성된 8자리 문자열이어야 합니다: "
                f"{corp_code!r}"
            )

        if code in seen:
            continue

        seen.add(code)
        normalized.append(code)

    return normalized


def _to_optional_float(value: object) -> float | None:
    if value is None:
        return None

    return float(value)

