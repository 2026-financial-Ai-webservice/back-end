from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings


class ReportEmbeddingError(RuntimeError):
    pass


class EmbeddableChunk(Protocol):
    content: str


class EmbeddingClient(Protocol):
    class Embeddings(Protocol):
        async def create(
            self,
            **kwargs: object,
        ) -> object:
            ...

    embeddings: Embeddings


class ReportEmbedder:
    def __init__(
        self,
        client: EmbeddingClient | None = None,
        model: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        if client is None and not settings.OPENAI_API_KEY:
            raise ReportEmbeddingError(
                "OPENAI_API_KEY가 설정되지 않았습니다."
            )

        self.client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        self.model = (
            model
            or settings.OPENAI_EMBEDDING_MODEL
        )
        self.batch_size = (
            batch_size
            or settings.OPENAI_EMBEDDING_BATCH_SIZE
        )

        if self.batch_size < 1:
            raise ValueError(
                "OPENAI_EMBEDDING_BATCH_SIZE는 "
                "1 이상이어야 합니다."
            )

    async def embed_chunks(
        self,
        chunks: Sequence[EmbeddableChunk],
    ) -> list[list[float]]:
        """사업보고서 청크를 임베딩한다."""

        texts = [
            self._embedding_text(chunk)
            for chunk in chunks
        ]

        return await self.embed_texts(texts)

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """일반 문자열 목록을 임베딩한다.

        보고서 청크와 RAG 검색 쿼리가 이 메서드를 함께 사용한다.
        """

        if not texts:
            return []

        self._validate_texts(texts)

        embeddings: list[list[float]] = []

        try:
            for start in range(
                0,
                len(texts),
                self.batch_size,
            ):
                batch = list(
                    texts[
                        start : start + self.batch_size
                    ]
                )

                response = (
                    await self.client.embeddings.create(
                        model=self.model,
                        input=batch,
                        dimensions=(
                            settings
                            .OPENAI_EMBEDDING_DIMENSIONS
                        ),
                    )
                )

                ordered = sorted(
                    response.data,
                    key=lambda item: item.index,
                )

                embeddings.extend(
                    item.embedding
                    for item in ordered
                )

        except OpenAIError as exc:
            raise ReportEmbeddingError(
                f"임베딩 생성 실패: {exc}"
            ) from exc

        self._validate_embeddings(
            input_count=len(texts),
            embeddings=embeddings,
        )

        return embeddings

    async def aclose(self) -> None:
        """내부 OpenAI 클라이언트를 종료한다."""

        close = getattr(
            self.client,
            "close",
            None,
        )

        if close is not None:
            await close()

    @staticmethod
    def _embedding_text(
        chunk: EmbeddableChunk,
    ) -> str:
        """보고서 청크에서 임베딩할 문자열을 만든다."""

        return chunk.content

    @staticmethod
    def _validate_texts(
        texts: Sequence[str],
    ) -> None:
        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise TypeError(
                    "임베딩 입력은 문자열이어야 합니다: "
                    f"index={index}, "
                    f"type={type(text).__name__}"
                )

            if not text.strip():
                raise ValueError(
                    "빈 문자열은 임베딩할 수 없습니다: "
                    f"index={index}"
                )

    @staticmethod
    def _validate_embeddings(
        *,
        input_count: int,
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if len(embeddings) != input_count:
            raise ReportEmbeddingError(
                f"텍스트 {input_count}개에 대해 "
                f"임베딩 {len(embeddings)}개가 "
                "반환되었습니다."
            )

        expected_dimensions = (
            settings.OPENAI_EMBEDDING_DIMENSIONS
        )

        for index, embedding in enumerate(embeddings):
            if len(embedding) != expected_dimensions:
                raise ReportEmbeddingError(
                    "임베딩 차원이 올바르지 않습니다: "
                    f"index={index}, "
                    f"expected={expected_dimensions}, "
                    f"actual={len(embedding)}"
                )