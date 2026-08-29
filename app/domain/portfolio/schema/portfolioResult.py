import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class CompanyResult(CamelModel):
    company_name: str
    corp_code: str
    allocated_amount: int
    final_score: float
    rank_no: int
    per: float | None
    roe: float | None
    dcf: float | None
    investment_reason: str | None

class PortfolioResultResponse(CamelModel):
    portfolio_result_id: int
    request_id: int
    total_investment: int
    average_dividend_yield: float | None
    average_dcf_upside: float | None
    valuation_analysis: str | None
    market_indicator_analysis: str | None
    allocation_analysis: str | None
    companies: list[CompanyResult]
    share_token: str
    created_at: datetime.datetime
