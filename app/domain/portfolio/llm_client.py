import asyncio
import time

from openai import AsyncOpenAI

from app.core.config import settings
from app.domain.portfolio.cache import _CACHE_TTL_SECONDS, _cache, _make_cache_key
from app.domain.portfolio.schema.llm_schema import (
    CompanyReasons,
    LlmAnalysisResult,
    PortfolioAnalysisText,
)

_client : AsyncOpenAI | None = None

def get_openai_client() -> AsyncOpenAI:
    global _client

    if _client is not None:
        return _client

    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI API KEY가 설정되지 않았습니다."
        )

    _client=AsyncOpenAI(
        api_key= settings.OPENAI_API_KEY
    )

    return _client

async def generate_portfolio_analysis(
        analysis_prompt: str,
        reason_prompt: str
) -> LlmAnalysisResult:
    cache_key = _make_cache_key(analysis_prompt, reason_prompt)
    cached = _cache.get(cache_key)

    if cached is not None:
        result, expires_at = cached
        if time.time() < expires_at:
            print(f"llm_cache hit key={cache_key[:8]}")
            return result

    client = get_openai_client()

    analysis_task = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 한국 주식 시장에 정통한 투자 애널리스트입니다. "
                           "주어진 정량 데이터와 사업 개요를 바탕으로 객관적인 "
                           "투자 분석을 작성합니다.",
            },
            {"role": "user", "content": analysis_prompt},
        ],
        response_format=PortfolioAnalysisText,
    )

    reason_task = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 한국 주식 시장에 정통한 투자 애널리스트입니다. "
                           "주어진 정량 데이터와 사업 개요를 바탕으로 객관적인 "
                           "투자 분석을 작성합니다.",
            },
            {"role": "user", "content": reason_prompt},
        ],
        response_format=CompanyReasons,
    )

    analysis_response, reason_response = await asyncio.gather(
        analysis_task, reason_task,
    )
    analysis = analysis_response.choices[0].message.parsed
    reasons = reason_response.choices[0].message.parsed
    result = LlmAnalysisResult(
        valuation_analysis=analysis.valuation_analysis,
        market_indicator_analysis=analysis.market_indicator_analysis,
        allocation_analysis=analysis.allocation_analysis,
        companies=reasons.companies,
    )

    _cache[cache_key] = (result, time.time() + _CACHE_TTL_SECONDS)
    return result
