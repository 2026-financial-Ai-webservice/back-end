from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.portfolio import service as portfolio_service
from app.domain.portfolio.schema.llm_schema import CompanyReason, LlmAnalysisResult


class InsertResult:
    def __init__(self, row):
        self.row = row

    def one(self):
        return self.row


@pytest.mark.asyncio
async def test_build_portfolio_result_uses_only_rag_selected_companies(
    monkeypatch,
):
    selected_codes = ["00000003", "00000001"]
    captured: dict[str, object] = {}

    async def fake_select_company_codes_with_rag(*args, **kwargs):
        captured["rag_candidates"] = kwargs["corp_codes"]
        return selected_codes

    def fake_allocate_portfolio(scores, seed_money):
        captured["allocation_scores"] = scores
        captured["seed_money"] = seed_money
        return {
            "00000003": {"ratio": 60.0, "amount": 600_000},
            "00000001": {"ratio": 40.0, "amount": 400_000},
        }

    def fake_build_prompt(user_input, companies):
        captured["prompt_input"] = user_input
        captured["prompt_companies"] = companies
        return "portfolio prompt"

    async def fake_generate_portfolio_analysis(prompt):
        captured["prompt"] = prompt
        return LlmAnalysisResult(
            valuation_analysis="valuation",
            market_indicator_analysis="market",
            allocation_analysis="allocation",
            companies=[
                CompanyReason(
                    corp_code=code,
                    investment_reason=f"reason-{code}",
                )
                for code in selected_codes
            ],
        )

    monkeypatch.setattr(
        portfolio_service,
        "select_company_codes_with_rag",
        fake_select_company_codes_with_rag,
    )
    monkeypatch.setattr(
        portfolio_service,
        "allocate_portfolio",
        fake_allocate_portfolio,
    )
    monkeypatch.setattr(
        portfolio_service,
        "build_prompt",
        fake_build_prompt,
    )
    monkeypatch.setattr(
        portfolio_service,
        "generate_portfolio_analysis",
        fake_generate_portfolio_analysis,
    )

    result_row = SimpleNamespace(
        portfolio_result_id=101,
        created_at=datetime(2026, 8, 29, tzinfo=UTC),
    )
    session = AsyncMock()
    session.execute.side_effect = [
        InsertResult(result_row),
        None,
    ]

    scores = {
        "00000001": 80,
        "00000002": 70,
        "00000003": 90,
    }
    company_details = {
        code: {
            "company_name": f"company-{code}",
            "per": 10.0 + index,
            "pbr": 1.0 + index,
            "market_cap": 10_000 + index,
            "roe": 8.0 + index,
            "dcf": 15.0 + index,
            "dividend_yield": 2.0 + index,
            "business_summary": f"summary-{code}",
        }
        for index, code in enumerate(scores)
    }

    result = await portfolio_service.build_portfolio_result(
        session=session,
        request_id=55,
        seed_money=1_000_000,
        user_preferences={
            "investment_period": "OVER_3_YEARS",
            "risk_preference": "STABLE",
            "return_preference": "DIVIDEND",
            "valuation_preference": "CURRENT_ASSET",
        },
        scores=scores,
        company_details=company_details,
    )

    assert captured["rag_candidates"] == list(scores)
    assert captured["allocation_scores"] == {
        "00000003": 90,
        "00000001": 80,
    }
    assert [
        company["corp_code"]
        for company in captured["prompt_companies"]
    ] == selected_codes
    assert [company.corp_code for company in result.companies] == selected_codes
    assert result.total_investment == 1_000_000

    stored_companies = session.execute.await_args_list[1].args[1]
    assert [row["corp_code"] for row in stored_companies] == selected_codes
    session.commit.assert_not_awaited()
