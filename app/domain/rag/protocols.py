from collections.abc import Sequence
from typing import Protocol


class TextEmbedder(Protocol):
    """검색 문장을 임베딩할 수 있는 객체."""

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        ...

    async def aclose(self) -> None:
        ...
