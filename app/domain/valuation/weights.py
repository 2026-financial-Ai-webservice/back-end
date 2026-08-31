from dataclasses import dataclass
from decimal import Decimal

from app.domain.valuation.scoring import ValuationWeights

BASE_DCF_WEIGHT = Decimal("34")
BASE_PER_WEIGHT = Decimal("33")
BASE_DIVIDEND_WEIGHT = Decimal("33")

TARGET_WEIGHT_TOTAL = Decimal("100")


@dataclass(frozen=True, slots=True)
class InvestmentPreferences:
    return_preference: str
    valuation_preference: str
    investment_period: str
    risk_preference: str


def calculate_weights(
    preferences: InvestmentPreferences,
) -> ValuationWeights:
    dcf = BASE_DCF_WEIGHT
    per = BASE_PER_WEIGHT
    dividend = BASE_DIVIDEND_WEIGHT

    # 배당선호도
    if preferences.return_preference == "DIVIDEND":
        dividend += Decimal("15")
        per -= Decimal("7.5")

    elif preferences.return_preference == "CAPITAL_GAIN":
        dividend -= Decimal("15")
        per += Decimal("7.5")

    else:
        raise ValueError(
            "return_preference must be "
            "DIVIDEND or CAPITAL_GAIN"
        )

    # 가치평가지표 선호도
    if preferences.valuation_preference == "CURRENT_ASSET":
        dcf -= Decimal("15")
        per += Decimal("15")

    elif preferences.valuation_preference == "FUTURE_EARNINGS":
        dcf += Decimal("15")
        per -= Decimal("15")

    else:
        raise ValueError(
            "valuation_preference must be "
            "CURRENT_ASSET or FUTURE_EARNINGS"
        )

    # 투자가능기간
    if preferences.investment_period == "UNDER_1_YEAR":
        per += Decimal("10")

    elif preferences.investment_period == "ONE_TO_THREE_YEARS":
        per += Decimal("5")
        dcf += Decimal("5")

    elif preferences.investment_period == "OVER_3_YEARS":
        dcf += Decimal("10")

    else:
        raise ValueError(
            "investment_period must be "
            "UNDER_1_YEAR, ONE_TO_THREE_YEARS, "
            "or OVER_3_YEARS"
        )

    # 위험성향
    if preferences.risk_preference == "STABLE":
        dividend += Decimal("5")
        per += Decimal("5")

    elif preferences.risk_preference == "AGGRESSIVE":
        dcf += Decimal("10")

    else:
        raise ValueError(
            "risk_preference must be "
            "STABLE or AGGRESSIVE"
        )

    return normalize_weights(
        dcf=dcf,
        per=per,
        dividend=dividend,
    )


def normalize_weights(
    *,
    dcf: Decimal,
    per: Decimal,
    dividend: Decimal,
) -> ValuationWeights:
    """
    조정된 가중치 비율을 유지하면서 합계를 100으로 정규화한다.
    """
    if dcf < 0 or per < 0 or dividend < 0:
        raise ValueError(
            "calculated weights must not be negative"
        )

    total = dcf + per + dividend

    if total <= 0:
        raise ValueError(
            "sum of calculated weights must be greater than zero"
        )

    normalized_dcf = (
        dcf / total
    ) * TARGET_WEIGHT_TOTAL

    normalized_per = (
        per / total
    ) * TARGET_WEIGHT_TOTAL

    # 반올림 오차가 생기지 않도록 마지막 값은 나머지로 계산
    normalized_dividend = (
        TARGET_WEIGHT_TOTAL
        - normalized_dcf
        - normalized_per
    )

    return ValuationWeights(
        dcf=normalized_dcf,
        per=normalized_per,
        dividend=normalized_dividend,
    )