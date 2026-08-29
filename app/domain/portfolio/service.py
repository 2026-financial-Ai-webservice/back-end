import secrets

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.portfolio.allocation import allocate_portfolio
from app.domain.portfolio.llm_client import generate_portfolio_analysis
from app.domain.portfolio.models import PortfolioResult, PortfolioResultCompany
from app.domain.portfolio.prompt import build_prompt
from app.domain.portfolio.schema.portfolioResult import CompanyResult, PortfolioResultResponse
from app.domain.portfolio.schema.schemaEnum import (
    InvestmentPeriod,
    ReturnPreference,
    RiskPreference,
    ValuationPreference,
)
from app.domain.rag.service import (
    select_company_codes_with_rag
)


async def build_portfolio_result(
        session: AsyncSession,
        request_id: int,
        seed_money: int,
        # investment_period, risk_preference,
        # return_preference, valuation_preference
        user_preferences: dict,
        # {corp_code: score} - 2, 3단계 merge 끝난 상태로 전달받음
        scores: dict[str, float],
        # {corp_code: {company_name, per, pbr, market_cap,
        # roe, dcf, business_summary}}
        company_details: dict[str, dict],
) -> PortfolioResultResponse:
    """allocation(할당 비율) 계산 -> LLM 호출 -> DB 저장 -> 최종 응답 조립"""
    candidate_codes = [
        corp_code
        for corp_code in scores
        if corp_code in company_details
    ]

    selected_codes = await select_company_codes_with_rag(
        session,
        corp_codes=candidate_codes,
        investment_period=InvestmentPeriod(
            user_preferences["investment_period"]
        ),
        risk_preference=RiskPreference(
            user_preferences["risk_preference"]
        ),
        return_preference=ReturnPreference(
            user_preferences["return_preference"]
        ),
        valuation_preference=ValuationPreference(
            user_preferences["valuation_preference"]
        ),
        limit=7,
        top_k_per_company=3,
        minimum_chunk_similarity=0.3,
        minimum_company_score=0.2,
    )

    if not selected_codes:
        raise RuntimeError(
            "RAG 선정 조건을 만족하는 기업이 없습니다."
        )

    selected_scores = {
        code: scores[code]
        for code in selected_codes
    }

    selected_company_details = {
        code: company_details[code]
        for code in selected_codes
    }

    # RAG에서 선정된 기업만 포트폴리오에 포함한다.
    allocations = allocate_portfolio(
        selected_scores,
        seed_money,
    )

    # 순위
    ranked_codes = sorted(
        selected_codes,
        key=lambda code: selected_scores[code],
        reverse=True,
    )

    rank_by_code = {
        code: index + 1
        for index, code in enumerate(ranked_codes)
    }
    # LLM 프롬프트 조립 + 호출
    companies_for_prompt = [
        {
            "corp_code": code,
            "company_name": selected_company_details[code]["company_name"],
            "final_score": selected_scores[code],
            "per": selected_company_details[code]["per"],
            "pbr": selected_company_details[code]["pbr"],
            "market_cap": selected_company_details[code]["market_cap"],
            "roe": selected_company_details[code]["roe"],
            "dcf": selected_company_details[code]["dcf"],
            "allocation_ratio": allocations[code]["ratio"],
            "business_summary": selected_company_details[code]["business_summary"],
        }
        for code in selected_codes
    ]
    prompt_input = {
        "seed_money": seed_money,
        **user_preferences,
    }
    prompt = build_prompt(prompt_input, companies_for_prompt)
    llm_result = await generate_portfolio_analysis(prompt)
    reason_by_code = {c.corp_code: c.investment_reason for c in llm_result.companies}

    # 집계값
    total_investment = sum(a["amount"] for a in allocations.values())
    dividend_values = [
        detail["dividend_yield"]
        for detail in selected_company_details.values()
        if detail.get("dividend_yield") is not None
    ]
    dcf_values = [
        detail["dcf"]
        for detail in selected_company_details.values()
        if detail.get("dcf") is not None
    ]
    average_dividend_yield = (
        round(sum(dividend_values) / len(dividend_values), 2)) if dividend_values else None
    average_dcf_upside = round(sum(dcf_values) / len(dcf_values), 2) if dcf_values else None
    share_token = secrets.token_urlsafe(32)

    # DB 저장 (헤더 -> 생성된 PK로 회사별 저장)
    result_row = (
        await session.execute(
            pg_insert(PortfolioResult)
            .values(
                request_id=request_id,
                total_investment=total_investment,
                average_dividend_yield=average_dividend_yield,
                average_dcf_upside=average_dcf_upside,
                valuation_analysis=llm_result.valuation_analysis,
                market_indicator_analysis=llm_result.market_indicator_analysis,
                allocation_analysis=llm_result.allocation_analysis,
                share_token=share_token,
            )
            .returning(PortfolioResult.portfolio_result_id, PortfolioResult.created_at)
        )
    ).one()

    company_rows = [
        {
            "portfolio_result_id": result_row.portfolio_result_id,
            "corp_code": code,
            "company_name": selected_company_details[code]["company_name"],
            "allocated_amount": allocations[code]["amount"],
            "final_score": selected_scores[code],
            "allocation_ratio": allocations[code]["ratio"],
            "rank_no": rank_by_code[code],
            "per": selected_company_details[code]["per"],
            "roe": selected_company_details[code]["roe"],
            "dcf": selected_company_details[code]["dcf"],
            "investment_reason": reason_by_code.get(code),
        }
        for code in selected_codes
    ]
    await session.execute(pg_insert(PortfolioResultCompany), company_rows)


    # API 응답 조립
    return PortfolioResultResponse(
        portfolio_result_id=result_row.portfolio_result_id,
        request_id=request_id,
        total_investment=total_investment,
        average_dividend_yield=average_dividend_yield,
        average_dcf_upside=average_dcf_upside,
        valuation_analysis=llm_result.valuation_analysis,
        market_indicator_analysis=llm_result.market_indicator_analysis,
        allocation_analysis=llm_result.allocation_analysis,
        companies=[
            CompanyResult(
                company_name=selected_company_details[code]["company_name"],
                corp_code=code,
                allocated_amount=allocations[code]["amount"],
                final_score=selected_scores[code],
                rank_no=rank_by_code[code],
                per=selected_company_details[code]["per"],
                roe=selected_company_details[code]["roe"],
                dcf=selected_company_details[code]["dcf"],
                investment_reason=reason_by_code.get(code),
            )
            for code in selected_codes
        ],
        share_token=share_token,
        created_at=result_row.created_at,
    )
