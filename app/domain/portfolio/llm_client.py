from openai import AsyncOpenAI
from app.core.config import settings

from app.domain.portfolio.schema.llm_schema import LlmAnalysisResult

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
async def generate_portfolio_analysis(prompt: str) -> LlmAnalysisResult:
    response = await _client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 한국 주식 시장에 정통한 투자 애널리스트입니다. "
                           "주어진 정량 데이터와 사업 개요를 바탕으로 객관적인 투자 분석을 작성합니다.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format=LlmAnalysisResult,
    )
    return response.choices[0].message.parsed
