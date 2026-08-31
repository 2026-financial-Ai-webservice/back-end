from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.portfolio import router as portfolio_router
from app.domain.portfolio.schema.portfolioCreateRequest import PortfolioCreateRequest


@pytest.mark.asyncio
async def test_create_portfolio_orchestrates_valuation_and_portfolio_build(
    monkeypatch,
):
    session = AsyncMock()
    expected_response = object()
    captured: dict[str, object] = {}

    async def fake_create_portfolio_request(active_session, request):
        assert active_session is session
        return 42

    async def fake_run_valuation_for_request(active_session, *, request_id):
        assert active_session is session
        assert request_id == 42
        return [
            SimpleNamespace(
                corp_code="00000001",
                score=Decimal("91.25"),
            ),
            SimpleNamespace(
                corp_code="00000002",
                score=Decimal("82.50"),
            ),
        ]

    async def fake_get_portfolio_company_details(
        active_session,
        *,
        request_id,
        corp_codes,
    ):
        assert active_session is session
        assert request_id == 42
        assert corp_codes == ["00000001", "00000002"]
        return {code: {"company_name": code} for code in corp_codes}

    async def fake_build_portfolio_result(**kwargs):
        captured.update(kwargs)
        return expected_response

    monkeypatch.setattr(
        portfolio_router,
        "create_portfolio_request",
        fake_create_portfolio_request,
    )
    monkeypatch.setattr(
        portfolio_router,
        "run_valuation_for_request",
        fake_run_valuation_for_request,
    )
    monkeypatch.setattr(
        portfolio_router,
        "get_portfolio_company_details",
        fake_get_portfolio_company_details,
    )
    monkeypatch.setattr(
        portfolio_router,
        "build_portfolio_result",
        fake_build_portfolio_result,
    )

    request = PortfolioCreateRequest(
        seedMoney=1_000_000,
        investmentPeriod="OVER_3_YEARS",
        riskPreference="STABLE",
        returnPreference="DIVIDEND",
        valuationPreference="CURRENT_ASSET",
    )

    response = await portfolio_router.create_portfolio(
        request=request,
        session=session,
    )

    assert response is expected_response
    assert captured["request_id"] == 42
    assert captured["seed_money"] == 1_000_000
    assert captured["scores"] == {
        "00000001": 91.25,
        "00000002": 82.5,
    }
    assert captured["user_preferences"] == {
        "investment_period": "OVER_3_YEARS",
        "risk_preference": "STABLE",
        "return_preference": "DIVIDEND",
        "valuation_preference": "CURRENT_ASSET",
    }
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_portfolio_rolls_back_on_failure(
    monkeypatch,
):
    session = AsyncMock()

    async def fail_to_create_request(*args, **kwargs):
        raise RuntimeError("request creation failed")

    monkeypatch.setattr(
        portfolio_router,
        "create_portfolio_request",
        fail_to_create_request,
    )

    request = PortfolioCreateRequest(
        seedMoney=1_000_000,
        investmentPeriod="OVER_3_YEARS",
        riskPreference="STABLE",
        returnPreference="DIVIDEND",
        valuationPreference="CURRENT_ASSET",
    )

    with pytest.raises(RuntimeError, match="request creation failed"):
        await portfolio_router.create_portfolio(
            request=request,
            session=session,
        )

    session.rollback.assert_awaited_once()

