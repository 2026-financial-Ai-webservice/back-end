from enum import Enum

class InvestmentPeriod(str, Enum):
    UNDER_1_YEAR = "UNDER_1_YEAR"
    ONE_TO_THREE_YEARS = "ONE_TO_THREE_YEARS"
    OVER_3_YEARS = "OVER_3_YEARS"

class RiskPreference(str, Enum):
    STABLE = "STABLE"
    AGGRESSIVE = "AGGRESSIVE"

class ReturnPreference(str, Enum):
    DIVIDEND = "DIVIDEND"
    CAPITAL_GAIN = "CAPITAL_GAIN"

class ValuationPreference(str, Enum):
    CURRENT_ASSET = "CURRENT_ASSET"
    FUTURE_EARNINGS = "FUTURE_EARNINGS"