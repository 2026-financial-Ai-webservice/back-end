import asyncio
import logging

from app.core.database import engine
from batch.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


async def main() -> None:
    scheduler = create_scheduler()
    scheduler.start()

    jobs = scheduler.get_jobs()

    for job in jobs:
        logging.info(
            "배치 등록 완료: %s, 다음 실행=%s",
            job.name,
            job.next_run_time,
        )

    try:
        # 프로세스가 종료되지 않도록 계속 대기
        await asyncio.Event().wait()

    finally:
        scheduler.shutdown(wait=False)
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("배치 worker를 종료합니다.")