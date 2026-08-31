"""DCF 상승여력, 시가배당률 계산"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RawValuationMetrics:
    corp_code:str
    business_year: int

    # (dcf적정주가 - 현재주가)/현재주가
    dcf_upside: Decimal

    # 최신 시장 PER, 유효하지 않으면 None
    per: Decimal|None

    # DPS/현재주가
    dividend_yield: Decimal


def calculate_raw_metrics(
        *,
        corp_code: str,
        business_year: int,
        dcf_fair_price: Decimal,
        current_price: Decimal,
        per: Decimal|None,
        dps: Decimal|None,
) -> RawValuationMetrics|None:
    """
    기업 한 곳의 valuation 원본 지표를 계산
    반환값: 
        RawValuationMetrics: 정상적으로 계산된 원본 지표
        None: 현재 주가 또는 dcf 적정주가가 유효하지 않아 valuation 자체를 계산할 수 없느 경우
    """


    if current_price<=0:
        return None
    if dcf_fair_price<=0:
        return None

    dcf_upside=(
        dcf_fair_price-current_price
    )/current_price

    dividend_yield=calculate_dividend_yield(
        dps=dps,
        current_price=current_price
    )

    valid_per=normalize_per(per)

    return RawValuationMetrics(
        corp_code=corp_code,
        business_year=business_year,
        dcf_upside=dcf_upside,
        per=valid_per,
        dividend_yield=dividend_yield,
    )

def calculate_dividend_yield(
        *,
        dps: Decimal|None,
        current_price: Decimal
)-> Decimal:
    """
    시가배당률을 계산한다.
    DPS가 없거나 0이면 무배당 기업으로 보고 0으로 반환한다.
    """

    if current_price<=0:
        raise ValueError("current price must be graater than zero")

    if dps is None or dps<=0:
        return Decimal("0")

    return dps/current_price

def normalize_per(
        per: Decimal|None
)-> Decimal|None:
    """
    상대평가에 사용할 수 있는 PER만 반환한다.

    per이 0이하이면 적자기업이거나 유효하지 않은 값일 수 있으므로
    per 비ㅛㄱ대상에서 제외하기 위해 None으로 반환
    """
    if per is None or per<=0:
        return None

    return per