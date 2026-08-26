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
        async def create(self, **kwargs: object) -> object: ...

    embeddings: Embeddings


class ReportEmbedder:
    def __init__(
        self,
        client: EmbeddingClient | None = None,
        model: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        if client is None and not settings.OPENAI_API_KEY:
            raise ReportEmbeddingError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = client or AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        self.batch_size = batch_size or settings.OPENAI_EMBEDDING_BATCH_SIZE
        if self.batch_size < 1:
            raise ValueError("OPENAI_EMBEDDING_BATCH_SIZE는 1 이상이어야 합니다.")

    async def embed_chunks(self, chunks: Sequence[EmbeddableChunk]) -> list[list[float]]:
        if not chunks:
            return []

        texts = [self._embedding_text(chunk) for chunk in chunks]
        embeddings: list[list[float]] = []
        try:
            for start in range(0, len(texts), self.batch_size):
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts[start : start + self.batch_size],
                    dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
                )
                ordered = sorted(response.data, key=lambda item: item.index)
                embeddings.extend(item.embedding for item in ordered)
        except OpenAIError as exc:
            raise ReportEmbeddingError(f"사업보고서 임베딩 생성 실패: {exc}") from exc

        if len(embeddings) != len(chunks):
            raise ReportEmbeddingError(
                f"청크 {len(chunks)}개에 대해 임베딩 {len(embeddings)}개가 반환되었습니다."
            )
        if any(len(embedding) != settings.OPENAI_EMBEDDING_DIMENSIONS for embedding in embeddings):
            raise ReportEmbeddingError(
                f"임베딩 차원은 {settings.OPENAI_EMBEDDING_DIMENSIONS}이어야 합니다."
            )
        return embeddings

    async def aclose(self) -> None:
        close = getattr(self.client, "close", None)
        if close is not None:
            await close()

    @staticmethod
    def _embedding_text(chunk: EmbeddableChunk) -> str:
        return chunk.content
