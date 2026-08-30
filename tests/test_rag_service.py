from datetime import date

import pytest

from app.domain.portfolio.schema.schemaEnum import (
    InvestmentPeriod,
    ReturnPreference,
    RiskPreference,
    ValuationPreference,
)
from app.domain.rag import service as rag_service
from app.domain.rag.schema import CompanyRagEvidence, PurposeEvidence, ReportEvidence


def make_evidence(
    corp_code: str,
    similarities: list[float | None],
) -> CompanyRagEvidence:
    searches: list[PurposeEvidence] = []

    for index, similarity in enumerate(similarities, start=1):
        chunks = []
        if similarity is not None:
            chunks.append(
                ReportEvidence(
                    corp_code=corp_code,
                    corp_name=f"company-{corp_code}",
                    stock_code=None,
                    chunk_id=int(corp_code) * 10 + index,
                    report_id=int(corp_code),
                    report_name="사업보고서",
                    filing_date=date(2026, 3, 31),
                    major_section="사업의 내용",
                    minor_section=None,
                    chunk_order=index,
                    content="테스트 보고서 내용",
                    similarity=similarity,
                )
            )

        searches.append(
            PurposeEvidence(
                purpose=f"purpose-{index}",
                query=f"query-{index}",
                chunks=chunks,
            )
        )

    return CompanyRagEvidence(
        corp_code=corp_code,
        searches=searches,
    )


def test_calculate_company_rag_score_averages_best_score_per_purpose():
    evidence = make_evidence(
        "00000001",
        [0.8, 0.4, None],
    )

    score = rag_service.calculate_company_rag_score(evidence)

    assert score == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_select_company_codes_with_rag_returns_top_n_and_filters_low_scores(
    monkeypatch,
):
    evidence_by_company = {
        "00000001": make_evidence("00000001", [0.9, 0.8]),
        "00000002": make_evidence("00000002", [0.7, 0.6]),
        "00000003": make_evidence("00000003", [0.4, None]),
        "00000004": make_evidence("00000004", [None, None]),
    }

    async def fake_retrieve_candidate_evidence(*args, **kwargs):
        return evidence_by_company

    monkeypatch.setattr(
        rag_service,
        "retrieve_candidate_evidence",
        fake_retrieve_candidate_evidence,
    )

    selected_codes = await rag_service.select_company_codes_with_rag(
        object(),
        corp_codes=list(evidence_by_company),
        investment_period=InvestmentPeriod.OVER_3_YEARS,
        risk_preference=RiskPreference.STABLE,
        return_preference=ReturnPreference.DIVIDEND,
        valuation_preference=ValuationPreference.CURRENT_ASSET,
        limit=2,
        minimum_company_score=0.3,
    )

    assert selected_codes == [
        "00000001",
        "00000002",
    ]

