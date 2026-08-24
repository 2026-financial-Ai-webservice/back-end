from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.company.model import Company
from app.domain.report.dart_client import Disclosure
from app.domain.report.model import CompanyReport, ReportChunk
from app.domain.report.parser import ParsedChunk


async def get_company_codes(session: AsyncSession, corp_code: str | None = None) -> list[str]:
    statement = select(Company.corp_code).order_by(Company.corp_code)
    if corp_code is not None:
        statement = statement.where(Company.corp_code == corp_code)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def replace_report(
    session: AsyncSession,
    disclosure: Disclosure,
    chunks: list[ParsedChunk],
) -> int:
    statement = pg_insert(CompanyReport).values(
        corp_code=disclosure.corp_code,
        receipt_no=disclosure.receipt_no,
        report_name=disclosure.report_name,
        filing_date=disclosure.filing_date,
        business_year=disclosure.business_year,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[CompanyReport.receipt_no],
        set_={
            "corp_code": statement.excluded.corp_code,
            "report_name": statement.excluded.report_name,
            "filing_date": statement.excluded.filing_date,
            "business_year": statement.excluded.business_year,
        },
    ).returning(CompanyReport.report_id)
    report_id = (await session.execute(statement)).scalar_one()

    await session.execute(delete(ReportChunk).where(ReportChunk.report_id == report_id))
    session.add_all(
        [
            ReportChunk(
                report_id=report_id,
                major_section=chunk.major_section,
                minor_section=chunk.minor_section,
                chunk_order=chunk.chunk_order,
                content=chunk.content,
            )
            for chunk in chunks
        ]
    )
    await session.flush()
    return report_id
