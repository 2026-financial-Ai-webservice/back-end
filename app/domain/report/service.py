from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.report.dart_client import DartReportClient, DartReportError
from app.domain.report.parser import extract_document, parse_report_chunks
from app.domain.report.repository import get_company_codes, replace_report

logger = logging.getLogger(__name__)


async def collect_annual_reports(
    session: AsyncSession,
    business_year: int | None = None,
    corp_code: str | None = None,
    client: DartReportClient | None = None,
) -> int:
    """수동 호출 시 사업보고서를 수집한다. 스케줄러에서는 호출하지 않는다."""
    business_year = business_year or date.today().year - 1
    owns_client = client is None
    client = client or DartReportClient()
    saved = 0
    try:
        company_codes = await get_company_codes(session, corp_code)
        for index, company_code in enumerate(company_codes):
            try:
                reports = await client.list_annual_reports(company_code, business_year)
                for report in reports:
                    archive = await client.download_document(report.receipt_no)
                    chunks = parse_report_chunks(extract_document(archive))
                    if not chunks:
                        raise DartReportError(f"{report.receipt_no}: 추출된 본문이 없습니다.")
                    await replace_report(session, report, chunks)
                    await session.commit()
                    saved += 1
            except (httpx.HTTPError, DartReportError, ValueError) as exc:
                await session.rollback()
                logger.error("%s 사업보고서 수집 실패: %s", company_code, exc)
            if index < len(company_codes) - 1:
                await asyncio.sleep(settings.MARKET_DATA_REQUEST_INTERVAL_SECONDS)
        return saved
    finally:
        if owns_client:
            await client.aclose()
