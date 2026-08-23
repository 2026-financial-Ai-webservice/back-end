from io import BytesIO
from zipfile import BadZipFile, ZipFile

import httpx

KOSPI_MASTER_URL = (
    "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip"
)


class KospiMasterError(Exception):
    pass


async def download_kospi_stock_codes() -> set[str]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(KOSPI_MASTER_URL)
        response.raise_for_status()

    try:
        with ZipFile(BytesIO(response.content)) as zip_file:
            filenames = zip_file.namelist()
            if not filenames:
                raise KospiMasterError(
                    "KOSPI 마스터 압축 파일이 비어 있습니다."
                )
            master_content = zip_file.read(filenames[0])
    except BadZipFile as exc:
        raise KospiMasterError(
            "KOSPI 마스터 압축 파일을 해석할 수 없습니다."
        ) from exc

    stock_codes = parse_kospi_stock_codes(master_content)
    if not stock_codes:
        raise KospiMasterError(
            "KOSPI 마스터에서 종목코드를 찾지 못했습니다."
        )

    return stock_codes


def parse_kospi_stock_codes(master_content: bytes) -> set[str]:
    try:
        text = master_content.decode("cp949")
    except UnicodeDecodeError as exc:
        raise KospiMasterError(
            "KOSPI 마스터의 문자 인코딩을 해석할 수 없습니다."
        ) from exc

    stock_codes: set[str] = set()

    for line in text.splitlines():
        stock_code = line[:9].strip()
        if len(stock_code) == 6 and stock_code.isdigit():
            stock_codes.add(stock_code)

    return stock_codes
