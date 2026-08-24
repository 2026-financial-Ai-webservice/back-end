# OpenDart 기업 목록 다운로드
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import httpx

from app.core.config import settings

DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

class DartAPIError(Exception):
    pass

@dataclass(frozen=True)
class DartCompany:
    corp_code:str
    stock_code:str|None
    corp_name:str


async def download_dart_companies() -> list[DartCompany]:
    if not settings.DART_API_KEY:
        raise DartAPIError("DART_API_KEY가 설정되지 않았습니다.")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                DART_CORP_CODE_URL,
                params={"crtfc_key": settings.DART_API_KEY},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DartAPIError(
            f"OpenDART 기업 목록 요청에 실패했습니다: {exc}"
        ) from exc

    try:
        with ZipFile(BytesIO(response.content)) as zip_file:
            xml_filename = zip_file.namelist()[0]
            xml_content = zip_file.read(xml_filename)
    except (BadZipFile, IndexError) as exc:
        raise DartAPIError(
            parse_dart_error(response.content)
        ) from exc

    root = ElementTree.fromstring(xml_content)
    companies: list[DartCompany] = []

    for item in root.findall("list"):
        corp_code = get_xml_text(item, "corp_code")
        corp_name = get_xml_text(item, "corp_name")
        stock_code = get_xml_text(item, "stock_code") or None

        if not corp_code or not corp_name:
            continue

        companies.append(
            DartCompany(
                corp_code=corp_code,
                stock_code=stock_code,
                corp_name=corp_name,
            )
        )

    return companies


def get_xml_text(
    element: ElementTree.Element,
    tag: str,
) -> str:
    return (element.findtext(tag) or "").strip()


def parse_dart_error(content: bytes) -> str:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return "OpenDART 응답을 해석할 수 없습니다."

    status = root.findtext("status") or "unknown"
    message = root.findtext("message") or "알 수 없는 오류"

    return f"OpenDART 오류: {status} - {message}"
