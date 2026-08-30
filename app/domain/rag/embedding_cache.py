import hashlib
import json
import logging
from collections.abc import Sequence

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import redis_client
from app.domain.rag.protocols import TextEmbedder

logger = logging.getLogger("uvicorn.error")

CACHE_VERSION = "v1"
CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30일


def _build_cache_key(text: str) -> str:
    query_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return (
        f"rag:query-embedding:{CACHE_VERSION}:"
        f"{settings.OPENAI_EMBEDDING_MODEL}:"
        f"{settings.OPENAI_EMBEDDING_DIMENSIONS}:"
        f"{query_hash}"
    )


def _deserialize_embedding(
    value: str,
) -> list[float] | None:
    try:
        embedding = json.loads(value)

        if (
            not isinstance(embedding, list)
            or len(embedding)
            != settings.OPENAI_EMBEDDING_DIMENSIONS
        ):
            return None

        return [
            float(number)
            for number in embedding
        ]

    except (TypeError, ValueError, json.JSONDecodeError):
        return None


async def get_cached_query_embeddings(
    *,
    embedder: TextEmbedder,
    texts: Sequence[str],
) -> tuple[list[list[float]], int, int]:
    """검색문 임베딩을 Redis에서 조회하고 없는 항목만 생성한다.

    반환:
        embeddings, cache_hits, cache_misses
    """
    if not texts:
        return [], 0, 0

    cache_keys = [
        _build_cache_key(text)
        for text in texts
    ]

    try:
        cached_values = await redis_client.mget(
            cache_keys
        )
    except RedisError:
        logger.exception(
            "RAG embedding Redis 조회 실패; "
            "OpenAI 임베딩으로 fallback"
        )

        embeddings = await embedder.embed_texts(texts)
        return embeddings, 0, len(texts)

    embeddings: list[list[float] | None] = [
        None
        for _ in texts
    ]
    missing_indexes: list[int] = []
    missing_texts: list[str] = []

    for index, cached_value in enumerate(cached_values):
        if cached_value is None:
            missing_indexes.append(index)
            missing_texts.append(texts[index])
            continue

        embedding = _deserialize_embedding(
            cached_value
        )

        if embedding is None:
            missing_indexes.append(index)
            missing_texts.append(texts[index])
            continue

        embeddings[index] = embedding

    if missing_texts:
        generated_embeddings = (
            await embedder.embed_texts(
                missing_texts
            )
        )

        try:
            async with redis_client.pipeline(
                transaction=False
            ) as pipeline:
                for index, embedding in zip(
                    missing_indexes,
                    generated_embeddings,
                    strict=True,
                ):
                    embeddings[index] = embedding

                    pipeline.set(
                        cache_keys[index],
                        json.dumps(
                            embedding,
                            separators=(",", ":"),
                        ),
                        ex=CACHE_TTL_SECONDS,
                    )

                await pipeline.execute()
        except RedisError:
            # 캐시 저장 실패가 포트폴리오 생성을 실패시키면 안 된다.
            logger.exception(
                "RAG embedding Redis 저장 실패"
            )

    final_embeddings = [
        embedding
        for embedding in embeddings
        if embedding is not None
    ]

    if len(final_embeddings) != len(texts):
        raise RuntimeError(
            "RAG 검색문 임베딩 개수가 일치하지 않습니다: "
            f"expected={len(texts)}, "
            f"actual={len(final_embeddings)}"
        )

    cache_misses = len(missing_texts)
    cache_hits = len(texts) - cache_misses

    return (
        final_embeddings,
        cache_hits,
        cache_misses,
    )
