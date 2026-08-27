from pydantic import BaseModel, Field

from app.domain.portfolio.schema.schemaEnum import (
    InvestmentPeriod,
    ReturnPreference,
    RiskPreference,
    ValuationPreference
)


class PortfolioCreateRequest(BaseModel):
    seed_money: int = Field(gt=0, alias="seedMoney")
    investment_period: InvestmentPeriod = Field(alias="investmentPeriod")
    risk_preference: RiskPreference = Field(alias="riskPreference")
    return_preference: ReturnPreference = Field(alias="returnPreference")
    valuation_preference: ValuationPreference = Field(alias="valuationPreference")
    model_config = {"populate_by_name": True}