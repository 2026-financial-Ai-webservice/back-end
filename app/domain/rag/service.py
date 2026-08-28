"""투자 성향에 따른 후보 기업 보고서 검색 흐름."""

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.portfolio.schema.schemaEnum import (
    InvestmentPeriod,
    ReturnPreference,
    RiskPreference,
    ValuationPreference,
)
from app.domain.rag.query_templates import build_rag_queries
from app.domain.rag.repository import search_candidate_report_chunks
from app.domain.rag.schema import (
    CompanyRagEvidence,
    PurposeEvidence,
    ReportEvidence,
)
from app.domain.report.embedding import ReportEmbedder


class TextEmbedder(Protocol):
    """검색 문장을 임베딩할 수 있는 객체."""

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        ...

    async def aclose(self) -> None:
        ...


async def retrieve_candidate_evidence(
    session: AsyncSession,
    *,
    corp_codes: Sequence[str],
    investment_period: InvestmentPeriod,
    risk_preference: RiskPreference,
    return_preference: ReturnPreference,
    valuation_preference: ValuationPreference,
    top_k_per_company: int = 3,
    minimum_similarity: float | None = None,
    embedder: TextEmbedder | None = None,
) -> dict[str, CompanyRagEvidence]:
    """후보 기업별로 투자 성향과 관련된 사업보고서 근거를 검색한다.

    반환값은 corp_code를 키로 가지며, 검색 결과가 없는 후보 기업도
    빈 searches 목록과 함께 포함한다.
    """

    normalized_corp_codes = _normalize_corp_codes(corp_codes)

    if not normalized_corp_codes:
        return {}

    queries = build_rag_queries(
        investment_period=investment_period,
        risk_preference=risk_preference,
        return_preference=return_preference,
        valuation_preference=valuation_preference,
    )

    if not queries:
        return {
            corp_code: CompanyRagEvidence(
                corp_code=corp_code,
                searches=[],
            )
            for corp_code in normalized_corp_codes
        }

    owns_embedder = embedder is None
    active_embedder = embedder or ReportEmbedder()

    try:
        query_embeddings = await active_embedder.embed_texts(
            [query["query"] for query in queries]
        )

        if len(query_embeddings) != len(queries):
            raise RuntimeError(
                "검색 쿼리와 임베딩 개수가 일치하지 않습니다: "
                f"queries={len(queries)}, "
                f"embeddings={len(query_embeddings)}"
            )

        result = {
            corp_code: CompanyRagEvidence(
                corp_code=corp_code,
                searches=[],
            )
            for corp_code in normalized_corp_codes
        }

        for query, query_embedding in zip(
            queries,
            query_embeddings,
            strict=True,
        ):
            evidence = await search_candidate_report_chunks(
                session,
                corp_codes=normalized_corp_codes,
                query_embedding=query_embedding,
                top_k_per_company=top_k_per_company,
                minimum_similarity=minimum_similarity,
            )

            _append_search_results(
                result=result,
                corp_codes=normalized_corp_codes,
                purpose=query["purpose"],
                query_text=query["query"],
                evidence=evidence,
            )

        return result

    finally:
        if owns_embedder:
            await active_embedder.aclose()


def _append_search_results(
    *,
    result: dict[str, CompanyRagEvidence],
    corp_codes: Sequence[str],
    purpose: str,
    query_text: str,
    evidence: Sequence[ReportEvidence],
) -> None:
    """한 검색 목적의 결과를 기업별 결과 객체에 추가한다."""

    evidence_by_corp_code: dict[str, list[ReportEvidence]] = {
        corp_code: []
        for corp_code in corp_codes
    }

    for item in evidence:
        if item.corp_code not in evidence_by_corp_code:
            # repository가 후보 밖의 기업을 반환하는 경우를 방어한다.
            continue

        evidence_by_corp_code[item.corp_code].append(item)

    for corp_code in corp_codes:
        company_result = result[corp_code]
        company_evidence = evidence_by_corp_code[corp_code]

        company_evidence.sort(
            key=lambda item: item.similarity,
            reverse=True,
        )

        # 첫 번째 검색 결과에서 기업 기본정보를 채운다.
        if company_evidence:
            first = company_evidence[0]

            if company_result.corp_name is None:
                company_result.corp_name = first.corp_name

            if company_result.stock_code is None:
                company_result.stock_code = first.stock_code

        company_result.searches.append(
            PurposeEvidence(
                purpose=purpose,
                query=query_text,
                chunks=company_evidence,
            )
        )


def _normalize_corp_codes(
    corp_codes: Sequence[str],
) -> list[str]:
    """기업코드의 입력 순서를 유지하며 공백과 중복을 제거한다."""

    normalized: list[str] = []
    seen: set[str] = set()

    for corp_code in corp_codes:
        code = corp_code.strip()

        if not code:
            continue

        if len(code) != 8 or not code.isdigit():
            raise ValueError(
                "corp_code는 숫자로 구성된 8자리 문자열이어야 합니다: "
                f"{corp_code!r}"
            )

        if code in seen:
            continue

        seen.add(code)
        normalized.append(code)

    return normalized