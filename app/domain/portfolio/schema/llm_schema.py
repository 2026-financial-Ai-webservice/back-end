from pydantic import BaseModel

class CompanyReason(BaseModel):
    corp_code: str
    investment_reason: str

class LlmAnalysisResult(BaseModel):
    valuation_analysis: str
    market_indicator_analysis: str
    allocation_analysis: str
    companies: list[CompanyReason]