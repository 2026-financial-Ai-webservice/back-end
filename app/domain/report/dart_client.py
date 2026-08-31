from __future__ import annotations

import asyncio
import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import settings

DART_BASE_URL = "https://opendart.fss.or.kr/api"


class DartReportError(RuntimeError):
    pass


@dataclass(frozen=True)
class Disclosure:
    corp_code: str
    receipt_no: str
    report_name: str
    filing_date: date
    business_year: int


def _business_year(report_name: str, filing_date: date) -> int:
    import re

    match = re.search(r"\((20\d{2})(?:\.|\)|\s)", report_name)
    return int(match.group(1)) if match else filing_date.year - 1


def map_disclosure(row: dict[str, Any]) -> Disclosure:
    filing_date = datetime.strptime(str(row["rcept_dt"]), "%Y%m%d").date()
    report_name = str(row["report_nm"]).strip()
    return Disclosure(
        corp_code=str(row["corp_code"]),
        receipt_no=str(row["rcept_no"]),
        report_name=report_name,
        filing_date=filing_date,
        business_year=_business_year(report_name, filing_date),
    )


class DartReportClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or settings.DART_API_KEY
        if not self.api_key:
            raise DartReportError("DART_API_KEY가 설정되지 않았습니다.")
        self.http = httpx.AsyncClient(
            base_url=DART_BASE_URL, timeout=60.0, transport=transport
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        last_status = ""
        for attempt in range(3):
            response = await self.http.get(endpoint, params={"crtfc_key": self.api_key, **params})
            response.raise_for_status()
            payload = response.json()
            last_status = str(payload.get("status", ""))
            if last_status in {"000", "013"}:
                return payload
            if last_status == "020":
                await asyncio.sleep(2**attempt)
                continue
            raise DartReportError(
                f"OpenDART 오류 {last_status}: {payload.get('message', '알 수 없는 오류')}"
            )
        raise DartReportError(f"OpenDART 요청 제한 재시도 실패: {last_status}")

    async def list_annual_reports(self, corp_code: str, business_year: int) -> list[Disclosure]:
        page_no = 1
        reports: list[Disclosure] = []
        while True:
            payload = await self._get_json(
                "/list.json",
                {
                    "corp_code": corp_code,
                    "bgn_de": f"{business_year + 1}0101",
                    "end_de": f"{business_year + 1}1231",
                    "pblntf_ty": "A",
                    "pblntf_detail_ty": "A001",
                    "sort": "date",
                    "sort_mth": "desc",
                    "page_no": page_no,
                    "page_count": 100,
                },
            )
            if payload.get("status") == "013":
                return []
            reports.extend(map_disclosure(row) for row in payload.get("list", []))
            if page_no >= int(payload.get("total_page", 1)):
                return [report for report in reports if report.business_year == business_year]
            page_no += 1

    async def download_document(self, receipt_no: str) -> bytes:
        response = await self.http.get(
            "/document.xml",
            params={"crtfc_key": self.api_key, "rcept_no": receipt_no},
        )
        response.raise_for_status()
        if not zipfile.is_zipfile(io.BytesIO(response.content)):
            message = response.text.replace("\n", " ").strip()
            raise DartReportError(f"원문 다운로드 실패({receipt_no}): {message[:300]}")
        return response.content
