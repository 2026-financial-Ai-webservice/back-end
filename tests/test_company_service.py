from app.domain.company.service import is_manufacturing, normalize_industry_code


def test_normalize_industry_code() -> None:
    assert normalize_industry_code(" 03120 ") == "03120"
    assert normalize_industry_code(" ") is None
    assert normalize_industry_code(None) is None


def test_is_manufacturing() -> None:
    assert is_manufacturing("03120") is True
    assert is_manufacturing("02110") is False
    assert is_manufacturing(None) is False
