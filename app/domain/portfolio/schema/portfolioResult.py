import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class CompanyResult(CamelModel):
    company_name: str
    corp_code: str
    allocated_amount: int
    final_score: int
    rank_no: int
    per: float
    roe: float
    dcf: float
    investment_reason: str

class PortfolioResultResponse(CamelModel):
    portfolio_result_id: int
    request_id: int
    total_investment: int
    average_dividend_yield: float
    average_dcf_upside: float
    valuation_analysis: str
    market_indicator_analysis: str
    allocation_analysis: str
    companies: list[CompanyResult]
    share_token: str
    created_at: datetime.datetime