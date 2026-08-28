import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domain.marketdata.service import collect_market_data
from app.domain.valuation.scripts.run_daily_valuation import (
    run_daily_valuation,
)


logger = logging.getLogger(__name__)


async def run_market_data_job() -> None:
    logger.info("시장 데이터 배치를 시작합니다.")

    try:
        async with AsyncSessionLocal() as session:
            saved_count = await collect_market_data(session)

        logger.info(
            "시장 데이터 배치가 완료되었습니다: %d건",
            saved_count,
        )

        await run_daily_valuation()
        logger.info("valuation 갱신이 완료되었습니다.")

    except Exception:
        logger.exception("시장 데이터 배치가 실패했습니다.")
        raise

    


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(
        timezone="Asia/Seoul",
    )

    scheduler.add_job(
        run_market_data_job,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=settings.MARKET_DATA_BATCH_HOUR,
            minute=settings.MARKET_DATA_BATCH_MINUTE,
            timezone="Asia/Seoul",
        ),
        id="collect_market_data",
        name="collect_market_data_and_valuation",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )

    return scheduler