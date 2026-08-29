from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.portfolio.repository import (
    create_portfolio_request,
    get_portfolio_company_details,
)
from app.domain.portfolio.schema.portfolioCreateRequest import PortfolioCreateRequest
from app.domain.portfolio.schema.portfolioResult import PortfolioResultResponse
from app.domain.portfolio.service import build_portfolio_result, retrieve_portfolio_result
from app.domain.valuation.service import run_valuation_for_request

router = APIRouter(
    prefix="/portfolios",
    tags=["portfolios"],
)


@router.get(
    "/{shareToken}",
    response_model=PortfolioResultResponse,
    status_code=status.HTTP_200_OK,
)
async def get_portfolio(
    share_token: Annotated[
        str,
        Path(
            alias="shareToken",
            min_length=1,
            max_length=64,
        ),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PortfolioResultResponse:
    result = await retrieve_portfolio_result(
        session,
        share_token=share_token,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="포트폴리오를 찾을 수 없습니다.",
        )

    return result


@router.post(
    "",
    response_model=PortfolioResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio(
    request: PortfolioCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PortfolioResultResponse:
    try:
        request_id = await create_portfolio_request(
            session,
            request,
        )

        valuation_results = await run_valuation_for_request(
            session,
            request_id=request_id,
        )

        scores = {
            result.corp_code: float(result.score)
            for result in valuation_results
        }
        company_details = await get_portfolio_company_details(
            session,
            request_id=request_id,
            corp_codes=list(scores),
        )

        user_preferences = {
            "investment_period": request.investment_period.value,
            "risk_preference": request.risk_preference.value,
            "return_preference": request.return_preference.value,
            "valuation_preference": request.valuation_preference.value,
        }

        result= await build_portfolio_result(
            session=session,
            request_id=request_id,
            seed_money=request.seed_money,
            user_preferences=user_preferences,
            scores=scores,
            company_details=company_details,
        )
        await session.commit()
        return result

    except Exception:
        await session.rollback()
        raise
