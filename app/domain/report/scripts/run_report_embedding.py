from __future__ import annotations

import argparse
import asyncio

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domain.report.embedding import ReportEmbedder
from app.domain.report.repository import (
    get_unembedded_report_chunks,
    save_chunk_embeddings,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DB에 저장된 사업보고서 청크 중 embedding이 없는 행을 임베딩합니다."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=settings.OPENAI_EMBEDDING_BATCH_SIZE,
        help="한 번에 조회하고 커밋할 청크 수",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="이번 실행에서 처리할 최대 청크 수. 생략하면 미처리 청크 전체를 처리합니다.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size는 1 이상이어야 합니다.")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit은 1 이상이어야 합니다.")

    embedder = ReportEmbedder(batch_size=args.batch_size)
    processed = 0
    try:
        async with AsyncSessionLocal() as session:
            while args.limit is None or processed < args.limit:
                fetch_size = args.batch_size
                if args.limit is not None:
                    fetch_size = min(fetch_size, args.limit - processed)

                chunks = await get_unembedded_report_chunks(session, fetch_size)
                if not chunks:
                    break

                try:
                    embeddings = await embedder.embed_chunks(chunks)
                    await save_chunk_embeddings(session, chunks, embeddings)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

                processed += len(chunks)
                print(f"{processed}개 청크 임베딩 완료")
    finally:
        await embedder.aclose()

    print(f"총 {processed}개 청크의 임베딩을 저장했습니다.")


if __name__ == "__main__":
    asyncio.run(main())
