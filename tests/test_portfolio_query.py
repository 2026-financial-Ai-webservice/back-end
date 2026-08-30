from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.domain.portfolio import router as portfolio_router
from app.domain.portfolio import service as portfolio_service


@pytest.mark.asyncio
async def test_retrieve_portfolio_result_maps_and_sorts_companies(
    monkeypatch,
):
    stored_result = SimpleNamespace(
        portfolio_result_id=10,
        request_id=20,
        total_investment=1_000_000,
        average_dividend_yield=2.5,
        average_dcf_upside=12.5,
        valuation_analysis="valuation",
        market_indicator_analysis="market",
        allocation_analysis="allocation",
        share_token="share-token",
        created_at=datetime(2026, 8, 29, tzinfo=UTC),
        companies=[
            SimpleNamespace(
                company_name="second",
                corp_code="00000002",
                allocated_amount=400_000,
                allocation_ratio=0.4,
                final_score=80.0,
                rank_no=2,
                per=12.0,
                roe=8.0,
                dcf=10.0,
                investment_reason="reason-2",
            ),
            SimpleNamespace(
                company_name="first",
                corp_code="00000001",
                allocated_amount=600_000,
                allocation_ratio=0.6,
                final_score=90.0,
                rank_no=1,
                per=10.0,
                roe=9.0,
                dcf=15.0,
                investment_reason="reason-1",
            ),
        ],
    )

    async def fake_get_result(session, *, share_token):
        assert share_token == "share-token"
        return stored_result

    monkeypatch.setattr(
        portfolio_service,
        "get_portfolio_result_by_share_token",
        fake_get_result,
    )

    result = await portfolio_service.retrieve_portfolio_result(
        AsyncMock(),
        share_token="share-token",
    )

    assert result is not None
    assert [company.rank_no for company in result.companies] == [1, 2]
    assert result.share_token == "share-token"


@pytest.mark.asyncio
async def test_get_portfolio_returns_400_when_token_does_not_exist(
    monkeypatch,
):
    async def fake_retrieve_result(session, *, share_token):
        return None

    monkeypatch.setattr(
        portfolio_router,
        "retrieve_portfolio_result",
        fake_retrieve_result,
    )

    with pytest.raises(HTTPException) as exc_info:
        await portfolio_router.get_portfolio(
            share_token="missing-token",
            session=AsyncMock(),
        )

    assert exc_info.value.status_code == 400

