import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.company.dart_client import download_dart_companies
from app.domain.company.kis_client import KisApiError, KisClient
from app.domain.company.kospi_client import download_kospi_stock_codes
from app.domain.company.model import Company

BATCH_SIZE = 1000
KIS_REQUEST_INTERVAL_SECONDS = 0.1
logger = logging.getLogger(__name__)

async def synchronize_dart_companies(
    session: AsyncSession,
) -> dict[str, int]:
    dart_companies = await download_dart_companies()
    kospi_stock_codes = await download_kospi_stock_codes()
    companies = [
        company
        for company in dart_companies
        if company.stock_code in kospi_stock_codes
    ]

    rows = [
        {
            "corp_code": company.corp_code,
            "stock_code": company.stock_code,
            "corp_name": company.corp_name,
        }
        for company in companies
    ]

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]

        statement = insert(Company).values(batch)

        statement = statement.on_conflict_do_update(
            index_elements=[Company.corp_code],
            set_={
                "stock_code": statement.excluded.stock_code,
                "corp_name": statement.excluded.corp_name,
            },
        )

        await session.execute(statement)

    await session.commit()

    industry_result = await synchronize_company_industries(
        session,
        stock_codes=kospi_stock_codes,
    )

    listed_count = sum(
        company.stock_code is not None
        for company in companies
    )

    return {
        "dart_total": len(dart_companies),
        "kospi_master_total": len(kospi_stock_codes),
        "kospi_companies": listed_count,
        **industry_result,
    }


async def synchronize_company_industries(
    session: AsyncSession,
    stock_codes: set[str],
    kis_client: KisClient | None = None,
) -> dict[str, int]:
    if not stock_codes:
        return {
            "industry_updated": 0,
            "industry_failed": 0,
        }

    client = kis_client or KisClient()
    result = await session.execute(
        select(Company).where(Company.stock_code.in_(stock_codes))
    )
    companies = result.scalars().all()

    updated = 0
    failed = 0

    for company in companies:
        try:
            response = await client.get_stock_info(company.stock_code)
            output = response.output
            if output is None:
                raise KisApiError("KIS API 응답에 output이 없습니다.")

            industry_code = normalize_industry_code(
                output.std_idst_clsf_cd
            )
            company.industry_category = (
                output.std_idst_clsf_cd_name.strip()
                if output.std_idst_clsf_cd_name
                else None
            )
            company.industry_code = industry_code
            company.is_manufacturing = is_manufacturing(industry_code)
            updated += 1
        except Exception as exc:
            failed += 1
            logger.warning(
                "KIS 업종정보 조회 실패: stock_code=%s, error=%s",
                company.stock_code,
                exc,
            )
        finally:
            await asyncio.sleep(KIS_REQUEST_INTERVAL_SECONDS)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return {
        "industry_updated": updated,
        "industry_failed": failed,
    }


def normalize_industry_code(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def is_manufacturing(industry_code: str | None) -> bool:
    return bool(
        industry_code
        and industry_code.startswith("03")
    )
