"""투자 성향을 사업보고서 검색 쿼리로 변환하는 템플릿."""

from typing import TypedDict

from app.domain.portfolio.schema.schemaEnum import (
    InvestmentPeriod,
    ReturnPreference,
    RiskPreference,
    ValuationPreference,
)


class RagSearchQuery(TypedDict):
    """한 가지 정성 평가 목적에 사용할 검색 쿼리."""

    purpose: str
    query: str


RAG_QUERY_TEMPLATES: dict[str, tuple[RagSearchQuery, ...]] = {
    RiskPreference.STABLE.value: (
        {
            "purpose": "financial_stability",
            "query": (
                "안정적인 영업현금흐름, 건전한 재무구조, 충분한 유동성과 "
                "부채 상환 능력을 설명하는 내용"
            ),
        },
        {
            "purpose": "business_risk",
            "query": (
                "실적과 재무 안정성에 영향을 미칠 수 있는 시장, 원재료, "
                "환율, 부채 및 주요 사업 위험을 설명하는 내용"
            ),
        },
    ),
    RiskPreference.AGGRESSIVE.value: (
        {
            "purpose": "growth",
            "query": (
                "신규 사업, 연구개발, 설비투자, 시장 확대를 통한 높은 매출과 "
                "이익 성장 가능성을 설명하는 내용"
            ),
        },
    ),
    ReturnPreference.DIVIDEND.value: (
        {
            "purpose": "shareholder_return",
            "query": (
                "배당 정책, 배당 지속 가능성, 배당 실적 및 "
                "주주환원 계획을 설명하는 내용"
            ),
        },
    ),
    ReturnPreference.CAPITAL_GAIN.value: (
        {
            "purpose": "capital_growth",
            "query": (
                "매출 성장, 신규 수주, 시장 확대 및 "
                "기업가치 상승을 이끌 미래 성장동력"
            ),
        },
    ),
    ValuationPreference.CURRENT_ASSET.value: (
        {
            "purpose": "asset_value",
            "query": (
                "현금성 자산, 유형자산, 투자자산, 순자산 및 "
                "보유 자산가치를 설명하는 내용"
            ),
        },
    ),
    ValuationPreference.FUTURE_EARNINGS.value: (
        {
            "purpose": "future_earnings",
            "query": (
                "향후 매출과 이익 성장, 수주잔고, 신규 사업과 "
                "중장기 사업 전망을 설명하는 내용"
            ),
        },
    ),
    InvestmentPeriod.UNDER_1_YEAR.value: (
        {
            "purpose": "short_term_outlook",
            "query": (
                "향후 1년 이내 매출과 이익에 영향을 미칠 "
                "수주, 영업환경 및 단기 사업 전망"
            ),
        },
    ),
    InvestmentPeriod.ONE_TO_THREE_YEARS.value: (
        {
            "purpose": "medium_term_outlook",
            "query": (
                "향후 1년에서 3년 동안의 수주잔고, "
                "설비투자, 사업계획 및 실적 전망"
            ),
        },
    ),
    InvestmentPeriod.OVER_3_YEARS.value: (
        {
            "purpose": "long_term_outlook",
            "query": (
                "3년 이상의 장기 성장전략, 연구개발, "
                "신규 사업 및 지속 가능한 경쟁력"
            ),
        },
    ),
}


def build_rag_queries(
    *,
    investment_period: InvestmentPeriod,
    risk_preference: RiskPreference,
    return_preference: ReturnPreference,
    valuation_preference: ValuationPreference,
) -> list[RagSearchQuery]:
    """투자 성향에 대응하는 사업보고서 검색 쿼리를 반환한다."""

    preferences = (
        investment_period.value,
        risk_preference.value,
        return_preference.value,
        valuation_preference.value,
    )

    queries: list[RagSearchQuery] = []
    seen: set[tuple[str, str]] = set()

    for preference in preferences:
        templates = RAG_QUERY_TEMPLATES[preference]

        for template in templates:
            identity = (
                template["purpose"],
                template["query"],
            )

            if identity in seen:
                continue

            seen.add(identity)

            # 호출부가 결과를 수정해도 전역 템플릿에 영향을 주지 않게 복사한다.
            queries.append(
                {
                    "purpose": template["purpose"],
                    "query": template["query"],
                }
            )

    return queries