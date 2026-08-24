from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date

from app.core.database import AsyncSessionLocal
from app.domain.report.service import collect_annual_reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenDART 사업보고서를 DB에 저장합니다.")
    parser.add_argument(
        "--year",
        type=int,
        default=date.today().year - 1,
        help="수집할 사업연도(기본값: 전년도)",
    )
    parser.add_argument(
        "--corp-code",
        help="특정 회사의 DART 고유번호 8자리. 생략하면 companies 전체를 수집합니다.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    async with AsyncSessionLocal() as session:
        saved_count = await collect_annual_reports(
            session=session,
            business_year=args.year,
            corp_code=args.corp_code,
        )
    print(f"사업보고서 {saved_count}건을 저장했습니다.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
