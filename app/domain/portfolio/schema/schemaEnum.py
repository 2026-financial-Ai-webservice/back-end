from enum import StrEnum


class InvestmentPeriod(StrEnum):
    UNDER_1_YEAR = "UNDER_1_YEAR"
    ONE_TO_THREE_YEARS = "ONE_TO_THREE_YEARS"
    OVER_3_YEARS = "OVER_3_YEARS"

class RiskPreference(StrEnum):
    STABLE = "STABLE"
    AGGRESSIVE = "AGGRESSIVE"

class ReturnPreference(StrEnum):
    DIVIDEND = "DIVIDEND"
    CAPITAL_GAIN = "CAPITAL_GAIN"

class ValuationPreference(StrEnum):
    CURRENT_ASSET = "CURRENT_ASSET"
    FUTURE_EARNINGS = "FUTURE_EARNINGS"