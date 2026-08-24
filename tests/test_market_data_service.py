from datetime import date
from decimal import Decimal

from app.domain.marketdata.service import map_price_output


def test_map_price_output() -> None:
    result = map_price_output(
        "00126380",
        date(2026, 8, 24),
        {
            "stck_prpr": "73500",
            "lstn_stcn": "5969782550",
            "hts_avls": "4387720",
            "per": "14.25",
            "pbr": "1.35",
            "eps": "5158.0000",
            "bps": "54444.0000",
        },
    )

    assert result["corp_code"] == "00126380"
    assert result["current_price"] == 73500
    assert result["listed_shares"] == 5969782550
    assert result["market_cap"] == 4387720
    assert result["per"] == Decimal("14.25")
    assert result["pbr"] == Decimal("1.35")
    assert result["eps"] == Decimal("5158.0000")
    assert result["bps"] == Decimal("54444.0000")


def test_map_price_output_converts_empty_values_to_none() -> None:
    result = map_price_output("00126380", date(2026, 8, 24), {})
    assert result["current_price"] is None
    assert result["per"] is None
