"""dcf 적정 주가 계산"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DcfAssumptions:
    forecast_years: int = 5
    growth_rate: Decimal = Decimal("0.03")
    discount_rate: Decimal = Decimal("0.10")
    terminal_growth_rate: Decimal = Decimal("0.02")


def calculate_dcf_fair_price(
    *,
    average_fcf: Decimal,
    listed_shares: int,
    assumptions: DcfAssumptions,
) -> Decimal | None:
    if average_fcf <= 0:
        return None

    if listed_shares <= 0:
        return None

    if assumptions.forecast_years <= 0:
        return None

    if assumptions.discount_rate <= assumptions.terminal_growth_rate:
        return None

    one = Decimal("1")
    projected_fcf = average_fcf
    enterprise_value = Decimal("0")

    for year in range(1, assumptions.forecast_years + 1):
        projected_fcf *= one + assumptions.growth_rate

        present_value = projected_fcf / (
            (one + assumptions.discount_rate) ** year
        )
        enterprise_value += present_value

    terminal_value = (
        projected_fcf
        * (one + assumptions.terminal_growth_rate)
        / (
            assumptions.discount_rate
            - assumptions.terminal_growth_rate
        )
    )

    discounted_terminal_value = terminal_value / (
        (one + assumptions.discount_rate)
        ** assumptions.forecast_years
    )

    enterprise_value += discounted_terminal_value

    return enterprise_value / Decimal(listed_shares)