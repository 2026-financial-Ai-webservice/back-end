from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.marketdata.collectors.kis_client import KisApiError, KisMarketDataClient
from app.domain.marketdata.repository import (
    MarketDataValues,
    get_listed_companies,
    upsert_market_data,
)

logger = logging.getLogger(__name__)
SEOUL = ZoneInfo("Asia/Seoul")

SAVE_BATCH_SIZE = 20

def _to_int(value: Any) -> int | None:
    text = str(value or "").strip().replace(",", "")
    return int(text) if text else None


def _to_decimal(value: Any) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise KisApiError(f"숫자로 변환할 수 없는 KIS 응답입니다: {value!r}") from exc


def map_price_output(
    corp_code: str, market_date: date, output: dict[str, Any]
) -> MarketDataValues:
    return {
        "corp_code": corp_code,
        "market_date": market_date,
        "current_price": _to_int(output.get("stck_prpr")),
        "listed_shares": _to_int(output.get("lstn_stcn")),
        "market_cap": _to_int(output.get("hts_avls")),
        "per": _to_decimal(output.get("per")),
        "pbr": _to_decimal(output.get("pbr")),
        "eps": _to_decimal(output.get("eps")),
        "bps": _to_decimal(output.get("bps")),
    }

async def collect_market_data(
    session: AsyncSession,
    target_date: date | None = None,
    client: KisMarketDataClient | None = None,
) -> int:
    target_date = target_date or datetime.now(SEOUL).date()
    owns_client = client is None
    client = client or KisMarketDataClient()

    try:
        if not await client.is_market_open_day(target_date):
            logger.info("%s은 휴장일이므로 수집을 건너뜁니다.", target_date)
            return 0

        companies = await get_listed_companies(session)

        logger.info(
            "시장 데이터 수집 시작: 전체 %d종목",
            len(companies),
        )

        pending_rows: list[MarketDataValues] = []
        saved_count = 0
        failed_count = 0

        for index, company in enumerate(companies, start=1):
            try:
                output = await client.get_price(
                    company["stock_code"]
                )

                pending_rows.append(
                    map_price_output(
                        company["corp_code"],
                        target_date,
                        output,
                    )
                )

            except (httpx.HTTPError, KisApiError, ValueError) as exc:
                failed_count += 1

                logger.error(
                    "%s(%s) 수집 실패: %s",
                    company["corp_code"],
                    company["stock_code"],
                    exc,
                )

            # 20건이 모이면 DB에 중간 저장
            if len(pending_rows) >= SAVE_BATCH_SIZE:
                await upsert_market_data(
                    session,
                    pending_rows,
                )
                await session.commit()

                saved_count += len(pending_rows)
                pending_rows.clear()

                logger.info(
                    "진행률: %d/%d종목 처리, %d건 저장, %d건 실패",
                    index,
                    len(companies),
                    saved_count,
                    failed_count,
                )

            if index < len(companies):
                await asyncio.sleep(
                    settings.MARKET_DATA_REQUEST_INTERVAL_SECONDS
                )

        # 마지막에 20건 미만으로 남은 데이터 저장
        if pending_rows:
            await upsert_market_data(
                session,
                pending_rows,
            )
            await session.commit()

            saved_count += len(pending_rows)

        logger.info(
            "%s 시장 데이터 수집 완료: %d건 저장, %d건 실패",
            target_date,
            saved_count,
            failed_count,
        )

        return saved_count

    except Exception:
        await session.rollback()
        logger.exception("시장 데이터 배치 실행 실패")
        raise

    finally:
        if owns_client:
            await client.aclose()