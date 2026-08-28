"""백분위, 가중치, 총점, 순위 계산"""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from app.domain.valuation.metrics import RawValuationMetrics

SCORE_PRECISION=Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class ValuationWeights:
    dcf: Decimal
    per: Decimal
    dividend:Decimal

    def __post_init__(self) -> None:
        if self.dcf<0:
            raise ValueError("dcf must not be negative")
        if self.dcf<0:
            raise ValueError("per must not be negative")
        if self.dividend<0:
            raise ValueError("dividend weight must not be negative")
        if self.total<=0:
            raise ValueError(
                "sum of valuation weights must be greater than zero"
            )

    @property
    def total(self) -> Decimal:
        return self.dcf + self.per + self.dividend


@dataclass(frozen=True, slots=True)
class ScoredValuation:
    corp_code:str
    business_year:int

    # 백분위 x 사용자 가중치
    dcf:Decimal
    per: Decimal
    dividend: Decimal

    socre: Decimal
    rank_position: int=0


def percentile_scores(
    values: dict[str, Decimal],
    *,
    higher_is_better: bool
)-> dict[str, Decimal]:
    """
    기업별 원본 값을 0~1 사이의 백분위 점수로 변환한다.
    
    higer_is_better = True: 값이 높을수록 1에 가까워진다.
    higer_is_better = False: 값이 낮을수록 1에 가까워진다.

    동점 기업은 같은 점수를 부여한다.
    
    """
    if not values:
        return {}

    if len(values) ==1:
        corp_code=next(iter(values))
        return {corp_code:Decimal("1")}

    sorted_items=sorted(
        values.items(),
        key=lambda item: item[1],
    )

    result: dict[str,Decimal]={}
    total_count=len(sorted_items)
    index=0

    while index<total_count:
        current_value=sorted_items[index][1]
        group_end=index

        # 같은 값을 가진 기업의 범위를 찾는다.
        while(
            group_end+1 < total_count
            and sorted_items[group_end+1][1] == current_value
        ):
            group_end+=1

        # 동점 그룹이 차지하는 인덱스의 평균값
        average_index=(
            Decimal(index)+ Decimal(group_end)
        )/Decimal("2")

        percentile=average_index/Decimal(total_count -1)

        if not higher_is_better:
            percentile=Decimal("1")-percentile
        for group_index in range(index, group_end+1):
            corp_code= sorted_items[group_index][0]
            result[corp_code]=percentile
        index=group_end+1

    return result

def score_candidates(
    *,
    candidates: list[RawValuationMetrics],
    weights: ValuationWeights,
) -> list[ScoredValuation]:
    """
    전체 후보 기업에 백분위와 사용자 가중치를 적용하고
    총점과 순위를 계산한다.
    """
    if not candidates:
        return []

    dcf_percentiles = percentile_scores(
        {
            candidate.corp_code: candidate.dcf_upside
            for candidate in candidates
        },
        higher_is_better=True,
    )

    per_percentiles = percentile_scores(
        {
            candidate.corp_code: candidate.per
            for candidate in candidates
            if candidate.per is not None
        },
        higher_is_better=False,
    )

    dividend_percentiles = percentile_scores(
        {
            candidate.corp_code: candidate.dividend_yield
            for candidate in candidates
        },
        higher_is_better=True,
    )

    scored_results: list[ScoredValuation] = []

    for candidate in candidates:
        dcf_score = quantize_score(
            dcf_percentiles[candidate.corp_code]
            * weights.dcf
        )

        # 유효한 PER이 없는 기업은 PER 점수를 0으로 처리한다.
        per_score = quantize_score(
            per_percentiles.get(
                candidate.corp_code,
                Decimal("0"),
            )
            * weights.per
        )

        dividend_score = quantize_score(
            dividend_percentiles[candidate.corp_code]
            * weights.dividend
        )

        total_score = quantize_score(
            dcf_score
            + per_score
            + dividend_score
        )

        scored_results.append(
            ScoredValuation(
                corp_code=candidate.corp_code,
                business_year=candidate.business_year,
                dcf=dcf_score,
                per=per_score,
                dividend=dividend_score,
                score=total_score,
            )
        )

    return assign_ranks(scored_results)


def assign_ranks(
    results: list[ScoredValuation],
) -> list[ScoredValuation]:
    """
    총점 내림차순으로 경쟁 순위를 부여한다.

    예:
        90점 → 1위
        80점 → 2위
        80점 → 2위
        70점 → 4위
    """
    sorted_results = sorted(
        results,
        key=lambda result: (
            -result.score,
            result.corp_code,
        ),
    )

    ranked_results: list[ScoredValuation] = []
    previous_score: Decimal | None = None
    previous_rank = 0

    for position, result in enumerate(
        sorted_results,
        start=1,
    ):
        if previous_score is None or result.score != previous_score:
            rank = position
        else:
            rank = previous_rank

        ranked_results.append(
            replace(
                result,
                rank_position=rank,
            )
        )

        previous_score = result.score
        previous_rank = rank

    return ranked_results


def quantize_score(value: Decimal) -> Decimal:
    return value.quantize(
        SCORE_PRECISION,
        rounding=ROUND_HALF_UP,
    )