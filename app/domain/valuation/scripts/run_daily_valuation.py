"""장마감 후 일변 재계산 실행"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.domain.valuation.dcf import DcfAssumptions
from app.domain.valuation.repository import (
    get_all_portfolio_request_preferences,
    get_valuation_inputs,
    replace_valuation_results,
)
from app.domain.valuation.scoring import score_candidates
from app.domain.valuation.service import build_raw_candidates
from app.domain.valuation.weights import (
    InvestmentPreferences,
    calculate_weights,
)

logger = logging.getLogger(__name__)


async def refresh_all_valuation_results(
    session: AsyncSession,
) -> int:
    """
    최신 재무·시장 데이터를 사용해 모든 포트폴리오 요청의
    valuation 결과를 다시 계산한다.

    반환값:
        갱신된 portfolio request 개수
    """
    inputs = await get_valuation_inputs(session)

    if not inputs:
        logger.warning(
            "Daily valuation stopped because no valuation inputs were found"
        )
        return 0

    # 사용자와 무관한 원본 지표는 한 번만 계산한다.
    candidates = build_raw_candidates(
        inputs=inputs,
        assumptions=DcfAssumptions(),
    )

    if not candidates:
        logger.warning(
            "Daily valuation stopped because "
            "no valid valuation candidates were produced"
        )
        return 0

    requests = await get_all_portfolio_request_preferences(session)

    if not requests:
        logger.info(
            "Daily valuation skipped because "
            "no portfolio requests were found"
        )
        return 0

    for request in requests:
        preferences = InvestmentPreferences(
            return_preference=request.return_preference,
            valuation_preference=request.valuation_preference,
            investment_period=request.investment_period,
            risk_preference=request.risk_preference,
        )

        weights = calculate_weights(preferences)

        scored_results = score_candidates(
            candidates=candidates,
            weights=weights,
        )

        await replace_valuation_results(
            session,
            request_id=request.request_id,
            results=scored_results,
        )

        logger.info(
            "Valuation refreshed: request_id=%s, result_count=%s",
            request.request_id,
            len(scored_results),
        )

    return len(requests)


async def run_daily_valuation() -> int:
    """
    일별 valuation 배치를 독립적으로 실행한다.

    모든 요청이 성공한 경우에만 commit한다.
    한 요청이라도 실패하면 전체 작업을 rollback한다.
    """
    async with AsyncSessionLocal() as session:
        try:
            updated_request_count = (
                await refresh_all_valuation_results(session)
            )

            if updated_request_count == 0:
                await session.rollback()
                return 0

            await session.commit()

            logger.info(
                "Daily valuation completed: updated_request_count=%s",
                updated_request_count,
            )

            return updated_request_count

        except Exception:
            await session.rollback()

            logger.exception(
                "Daily valuation failed"
            )

            raise


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )

    asyncio.run(run_daily_valuation())


if __name__ == "__main__":
    main()