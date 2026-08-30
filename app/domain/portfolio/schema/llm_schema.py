from pydantic import BaseModel


class CompanyReason(BaseModel):
    corp_code: str
    investment_reason: str

class LlmAnalysisResult(BaseModel):
    valuation_analysis: str
    market_indicator_analysis: str
    allocation_analysis: str
    companies: list[CompanyReason]

# 모든 필드 순차 생성 -> 분석 텍스트 / 기업별 reason을 병렬 2개 호출로 분리
""" LLM 호출 1 - 포트폴리오 전체 분석 """
class PortfolioAnalysisText(BaseModel):
    valuation_analysis: str
    market_indicator_analysis: str
    allocation_analysis: str

"""LLM 호출 2 - 기업별 선정 이유"""
class CompanyReasons(BaseModel):
    companies: list[CompanyReason]