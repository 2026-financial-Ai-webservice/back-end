import secrets

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.portfolio.allocation import allocate_portfolio
from app.domain.portfolio.llm_client import generate_portfolio_analysis
from app.domain.portfolio.models import PortfolioResult, PortfolioResultCompany
from app.domain.portfolio.prompt import build_prompt
from app.domain.portfolio.schema.portfolioResult import CompanyResult, PortfolioResultResponse


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

    # 비율 할당
    allocations = allocate_portfolio(scores, seed_money)

    # 순위
    ranked_codes = sorted(scores, key=scores.get, reverse=True)
    rank_by_code = {code: i + 1 for i, code in enumerate(ranked_codes)}

    # LLM 프롬프트 조립 + 호출
    prompt_input = {"seed_money": seed_money, **user_preferences}
    companies_for_prompt = [
        {
            "corp_code": code,
            "company_name": d["company_name"],
            "final_score": scores[code],
            "per": d["per"],
            "pbr": d["pbr"],
            "market_cap": d["market_cap"],
            "roe": d["roe"],
            "dcf": d["dcf"],
            "allocation_ratio": allocations[code]["ratio"],
            "business_summary": d["business_summary"],
        }
        for code, d in company_details.items()
    ]
    prompt = build_prompt(prompt_input, companies_for_prompt)
    llm_result = await generate_portfolio_analysis(prompt)
    reason_by_code = {c.corp_code: c.investment_reason for c in llm_result.companies}

    # 집계값
    total_investment = sum(a["amount"] for a in allocations.values())
    dividend_values = [d["dividend_yield"] for d in company_details.values()
                       if d.get("dividend_yield") is not None]
    dcf_values = [d["dcf"] for d in company_details.values()
                  if d.get("dcf") is not None]
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
            "company_name": d["company_name"],
            "allocated_amount": allocations[code]["amount"],
            "final_score": scores[code],
            "allocation_ratio": allocations[code]["ratio"],
            "rank_no": rank_by_code[code],
            "per": d["per"],
            "roe": d["roe"],
            "dcf": d["dcf"],
            "investment_reason": reason_by_code.get(code),
        }
        for code, d in company_details.items()
    ]
    await session.execute(pg_insert(PortfolioResultCompany), company_rows)
    await session.commit()

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
                company_name=d["company_name"],
                corp_code=code,
                allocated_amount=allocations[code]["amount"],
                final_score=scores[code],
                rank_no=rank_by_code[code],
                per=d["per"],
                roe=d["roe"],
                dcf=d["dcf"],
                investment_reason=reason_by_code.get(code),
            )
            for code, d in company_details.items()
        ],
        share_token=share_token,
        created_at=result_row.created_at,
    )