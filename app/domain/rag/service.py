"""투자 성향에 따른 후보 기업 보고서 검색 흐름."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.portfolio.schema.schemaEnum import (
    InvestmentPeriod,
    ReturnPreference,
    RiskPreference,
    ValuationPreference,
)
from app.domain.rag.embedding_cache import get_cached_query_embeddings
from app.domain.rag.protocols import TextEmbedder
from app.domain.rag.query_templates import build_rag_queries
from app.domain.rag.repository import search_candidate_report_chunks
from app.domain.rag.schema import (
    CompanyRagEvidence,
    PurposeEvidence,
    ReportEvidence,
)
from app.domain.report.embedding import ReportEmbedder


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
        query_texts = [
            query["query"]
            for query in queries
        ]

        (
            query_embeddings,
            cache_hits,
            cache_misses,
        ) = await get_cached_query_embeddings(
            embedder=active_embedder,
            texts=query_texts,
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


def calculate_company_rag_score(
    evidence: CompanyRagEvidence,
) -> float:
    """기업의 검색 목적별 최고 유사도를 평균하여 RAG 점수를 계산한다.

    검색 결과가 없는 목적은 0점으로 처리한다. 따라서 일부 목적에서만
    높은 유사도를 받은 기업보다 여러 투자 목적에서 고르게 근거가 검색된
    기업이 높은 점수를 받는다.
    """
    if not evidence.searches:
        return 0.0

    purpose_scores: list[float] = []

    for search in evidence.searches:
        if not search.chunks:
            purpose_scores.append(0.0)
            continue

        best_similarity = max(
            chunk.similarity
            for chunk in search.chunks
        )

        # 음수 cosine similarity는 선정 점수에서 0으로 처리한다.
        purpose_scores.append(
            max(0.0, best_similarity)
        )

    return sum(purpose_scores) / len(purpose_scores)


#corp_code 리스트 반환
async def select_company_codes_with_rag(
    session: AsyncSession,
    *,
    corp_codes: Sequence[str],
    investment_period: InvestmentPeriod,
    risk_preference: RiskPreference,
    return_preference: ReturnPreference,
    valuation_preference: ValuationPreference,
    limit: int = 5,
    top_k_per_company: int = 3,
    minimum_chunk_similarity: float | None = 0.3,
    minimum_company_score: float = 0.0,
    embedder: TextEmbedder | None = None,
) -> list[str]:
    """사업보고서 RAG 점수가 높은 기업코드를 순서대로 반환한다."""
    if limit < 1:
        raise ValueError(
            "limit은 1 이상이어야 합니다."
        )

    if not 0.0 <= minimum_company_score <= 1.0:
        raise ValueError(
            "minimum_company_score는 "
            "0.0 이상 1.0 이하여야 합니다."
        )

    evidence_by_company = await retrieve_candidate_evidence(
        session,
        corp_codes=corp_codes,
        investment_period=investment_period,
        risk_preference=risk_preference,
        return_preference=return_preference,
        valuation_preference=valuation_preference,
        top_k_per_company=top_k_per_company,
        minimum_similarity=minimum_chunk_similarity,
        embedder=embedder,
    )

    scores = {
        corp_code: calculate_company_rag_score(
            evidence
        )
        for corp_code, evidence
        in evidence_by_company.items()
    }

    eligible_codes = [
        corp_code
        for corp_code, score in scores.items()
        if score >= minimum_company_score
        and any(
            search.chunks
            for search
            in evidence_by_company[corp_code].searches
        )
    ]

    # 점수가 같으면 corp_code 오름차순으로 정렬해 결과를 항상 동일하게 만든다.
    eligible_codes.sort(
        key=lambda corp_code: (
            -scores[corp_code],
            corp_code,
        )
    )

    return eligible_codes[:limit]


 
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


def format_company_evidence(
    evidence: CompanyRagEvidence | None,
    *,
    max_chunks: int = 6,
    max_content_chars: int = 700,
) -> str:
    """기업별 RAG 검색 결과를 LLM 프롬프트용 문자열로 변환한다."""
    if max_chunks < 1:
        raise ValueError("max_chunks는 1 이상이어야 합니다.")

    if max_content_chars < 1:
        raise ValueError(
            "max_content_chars는 1 이상이어야 합니다."
        )

    if evidence is None:
        return "검색된 사업보고서 근거 없음"

    candidates: list[tuple[str, ReportEvidence]] = []
    seen_chunk_ids: set[int] = set()

    for search in evidence.searches:
        for chunk in search.chunks:
            # 여러 검색 목적에서 같은 청크가 검색될 수 있으므로 중복 제거
            if chunk.chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(chunk.chunk_id)
            candidates.append((search.purpose, chunk))

    candidates.sort(
        key=lambda item: item[1].similarity,
        reverse=True,
    )
    selected = candidates[:max_chunks]

    if not selected:
        return "검색된 사업보고서 근거 없음"

    lines: list[str] = []

    for index, (purpose, chunk) in enumerate(
        selected,
        start=1,
    ):
        section = " > ".join(
            value
            for value in (
                chunk.major_section,
                chunk.minor_section,
            )
            if value
        )

        if not section:
            section = "섹션 정보 없음"

        # 불필요한 줄바꿈과 공백을 정리한다.
        content = " ".join(chunk.content.split())

        if len(content) > max_content_chars:
            content = (
                f"{content[:max_content_chars].rstrip()}…"
            )

        lines.append(
            f"[{index}] "
            f"목적={purpose}; "
            f"보고서={chunk.report_name}; "
            f"공시일={chunk.filing_date}; "
            f"섹션={section}; "
            f"유사도={chunk.similarity:.4f}\n"
            f"{content}"
        )

    return "\n".join(lines)
