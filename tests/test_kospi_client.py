import pytest

from app.domain.company.kospi_client import (
    KospiMasterError,
    parse_kospi_stock_codes,
)


def test_parse_kospi_stock_codes() -> None:
    content = (
        "005930   KR7005930003 삼성전자\n"
        "000660   KR7000660001 SK하이닉스\n"
        "A12345   INVALID 상품\n"
    ).encode("cp949")

    assert parse_kospi_stock_codes(content) == {
        "005930",
        "000660",
    }


def test_parse_kospi_stock_codes_rejects_invalid_encoding() -> None:
    with pytest.raises(KospiMasterError):
        parse_kospi_stock_codes(b"\xff\xff")
