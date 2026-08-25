from app.domain.screening.service import is_fcf_3yr_negative


# fcf가 모두 음수일 경우 True 반환
def test_is_fcf_3yr_negative_all_negative():
    assert is_fcf_3yr_negative([-100.0, -200.0, -50.0]) is True

# 양수가 하나라도 존재하면 False 반환
def test_is_fcf_3yr_negative_one_positive_breaks_streak():
    assert is_fcf_3yr_negative([-100.0, 50.0, -200.0]) is False

# 3개년 미만이면 실격
def test_is_fcf_3yr_negative_insufficient_data():
    assert is_fcf_3yr_negative([-100.0, -200.0]) is True

# fcf가 NULL인 연도가 존재하면 Trueb (TypeError 방지)
def test_is_fcf_3yr_negative_none_value_treated_as_fail():
    assert is_fcf_3yr_negative([-100.0, None, -200.0]) is True