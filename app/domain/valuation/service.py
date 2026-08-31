"""
Valuation 전체 계산을 연결한다.

repository에서 입력값 조회
→ DCF 적정주가 계산
→ metrics에서 원본 지표 계산
→ scoring에서 점수·순위 계산
→ repository를 통해 DB 저장
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.valuation.dcf import (
    DcfAssumptions,
    calculate_dcf_fair_price,
)
from app.domain.valuation.metrics import (
    RawValuationMetrics,
    calculate_raw_metrics,
)
from app.domain.valuation.repository import (
    ValuationInput,
    get_portfolio_request_preferences_by_id,
    get_valuation_inputs,
    replace_valuation_results,
)
from app.domain.valuation.scoring import (
    ScoredValuation,
    score_candidates,
)
from app.domain.valuation.weights import (
    InvestmentPreferences,
    calculate_weights,
)

logger = logging.getLogger(__name__)


async def run_valuation_for_request(
    session: AsyncSession,
    *,
    request_id: int,
) -> list[ScoredValuation]:
    """
    특정 portfolio request 한 건에 대해 valuation을 실행한다.
    """
    if request_id <= 0:
        raise ValueError(
            "request_id must be greater than zero"
        )

    try:
        request = (
            await get_portfolio_request_preferences_by_id(
                session,
                request_id=request_id,
            )
        )

        if request is None:
            raise ValueError(
                "Portfolio request not found: "
                f"request_id={request_id}"
            )

        preferences = InvestmentPreferences(
            return_preference=request.return_preference,
            valuation_preference=request.valuation_preference,
            investment_period=request.investment_period,
            risk_preference=request.risk_preference,
        )

        weights = calculate_weights(preferences)

        inputs = await get_valuation_inputs(session)

        candidates = build_raw_candidates(
            inputs=inputs,
            assumptions=DcfAssumptions(),
        )

        if not candidates:
            raise RuntimeError(
                "No valid valuation candidates were found"
            )

        scored_results = score_candidates(
            candidates=candidates,
            weights=weights,
        )

        await replace_valuation_results(
            session,
            request_id=request_id,
            results=scored_results,
        )

        logger.info(
            "Valuation completed: "
            "request_id=%s, result_count=%s",
            request_id,
            len(scored_results),
        )

        return scored_results

    except Exception:
        await session.rollback()

        logger.exception(
            "Valuation failed: request_id=%s",
            request_id,
        )

        raise


def build_raw_candidates(
    *,
    inputs: list[ValuationInput],
    assumptions: DcfAssumptions,
) -> list[RawValuationMetrics]:
    """
    DB 조회 결과를 valuation 원본 지표 목록으로 변환한다.

    계산이 불가능한 기업은 제외한다.
    """
    candidates: list[RawValuationMetrics] = []

    for item in inputs:
        candidate = build_raw_candidate(
            item=item,
            assumptions=assumptions,
        )

        if candidate is not None:
            candidates.append(candidate)

    return candidates


def build_raw_candidate(
    *,
    item: ValuationInput,
    assumptions: DcfAssumptions,
) -> RawValuationMetrics | None:
    """
    기업 한 곳의 DCF 적정주가와 원본 valuation 지표를 계산한다.
    """
    dcf_fair_price = calculate_dcf_fair_price(
        average_fcf=item.average_fcf,
        listed_shares=item.listed_shares,
        assumptions=assumptions,
    )

    if dcf_fair_price is None:
        logger.warning(
            "Company excluded because DCF could not be calculated: "
            "corp_code=%s",
            item.corp_code,
        )
        return None

    metrics = calculate_raw_metrics(
        corp_code=item.corp_code,
        business_year=item.business_year,
        dcf_fair_price=dcf_fair_price,
        current_price=item.current_price,
        per=item.per,
        dps=item.dps,
    )

    if metrics is None:
        logger.warning(
            "Company excluded because valuation metrics "
            "could not be calculated: corp_code=%s",
            item.corp_code,
        )

    return metrics