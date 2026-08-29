"""후보 기업의 사업보고서 청크 벡터 검색."""

from collections.abc import Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, String, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.rag.schema import ReportEvidence

_SEARCH_CANDIDATE_REPORT_CHUNKS = text(
    """
    SELECT
        candidate.corp_code,
        company.corp_name,
        company.stock_code,

        hit.chunk_id,
        hit.report_id,
        hit.report_name,
        hit.filing_date,

        hit.major_section,
        hit.minor_section,
        hit.chunk_order,

        hit.content,
        hit.similarity
    FROM unnest(
        CAST(:corp_codes AS VARCHAR[])
    ) AS candidate(corp_code)

    JOIN companies AS company
      ON company.corp_code = candidate.corp_code

    CROSS JOIN LATERAL (
        SELECT
            chunk.chunk_id,
            chunk.report_id,
            report.report_name,
            report.filing_date,

            chunk.major_section,
            chunk.minor_section,
            chunk.chunk_order,

            chunk.content,

            1 - (
                chunk.embedding
                <=> :query_embedding
            ) AS similarity

        FROM report_chunks AS chunk

        JOIN company_reports AS report
          ON report.report_id = chunk.report_id

        WHERE report.corp_code = candidate.corp_code
          AND chunk.embedding IS NOT NULL

        ORDER BY
            chunk.embedding
            <=> :query_embedding

        LIMIT :top_k_per_company
    ) AS hit

    ORDER BY
        candidate.corp_code,
        hit.similarity DESC,
        hit.chunk_id
    """
).bindparams(
    bindparam(
        "corp_codes",
        type_=ARRAY(String(8)),
    ),
    bindparam(
        "query_embedding",
        type_=Vector(settings.OPENAI_EMBEDDING_DIMENSIONS),
    ),
    bindparam(
        "top_k_per_company",
    ),
)


async def search_candidate_report_chunks(
    session: AsyncSession,
    *,
    corp_codes: Sequence[str],
    query_embedding: Sequence[float],
    top_k_per_company: int = 3,
    minimum_similarity: float | None = None,
) -> list[ReportEvidence]:
    """후보 기업별로 유사도가 높은 보고서 청크를 조회한다.

    각 기업에 대해 최대 ``top_k_per_company``개의 청크를 반환한다.
    후보 기업에 보고서 또는 임베딩된 청크가 없으면 해당 기업은 결과에
    포함되지 않는다.
    """

    normalized_corp_codes = _normalize_corp_codes(corp_codes)

    if not normalized_corp_codes:
        return []

    _validate_query_embedding(query_embedding)
    _validate_top_k(top_k_per_company)
    _validate_minimum_similarity(minimum_similarity)

    result = await session.execute(
        _SEARCH_CANDIDATE_REPORT_CHUNKS,
        {
            "corp_codes": normalized_corp_codes,
            "query_embedding": list(query_embedding),
            "top_k_per_company": top_k_per_company,
        },
    )

    rows = result.mappings().all()

    evidence = [
        ReportEvidence.model_validate(row)
        for row in rows
    ]

    if minimum_similarity is None:
        return evidence

    return [
        item
        for item in evidence
        if item.similarity >= minimum_similarity
    ]


def _normalize_corp_codes(
    corp_codes: Sequence[str],
) -> list[str]:
    """기업코드를 정리하고 입력 순서를 유지하면서 중복을 제거한다."""

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


def _validate_query_embedding(
    query_embedding: Sequence[float],
) -> None:
    expected_dimensions = settings.OPENAI_EMBEDDING_DIMENSIONS

    if len(query_embedding) != expected_dimensions:
        raise ValueError(
            "검색 임베딩 차원이 올바르지 않습니다: "
            f"expected={expected_dimensions}, "
            f"actual={len(query_embedding)}"
        )


def _validate_top_k(
    top_k_per_company: int,
) -> None:
    if not 1 <= top_k_per_company <= 20:
        raise ValueError(
            "top_k_per_company은 1 이상 20 이하여야 합니다."
        )


def _validate_minimum_similarity(
    minimum_similarity: float | None,
) -> None:
    if minimum_similarity is None:
        return

    if not -1.0 <= minimum_similarity <= 1.0:
        raise ValueError(
            "minimum_similarity는 -1.0 이상 1.0 이하여야 합니다."
        )