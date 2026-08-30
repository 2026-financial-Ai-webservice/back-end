import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.domain.valuation.dcf import DcfAssumptions, calculate_dcf_fair_price
from app.domain.valuation.metrics import (
    RawValuationMetrics,
    calculate_dividend_yield,
    calculate_raw_metrics,
    normalize_per,
)
from app.domain.valuation.model import ValuationResult
from app.domain.valuation.repository import get_valuation_inputs
from app.domain.valuation.scoring import (
    ScoredValuation,
    ValuationWeights,
    percentile_scores,
    score_candidates,
)
from app.domain.valuation.scripts.run_daily_valuation import (
    refresh_all_valuation_results,
)
from app.domain.valuation.service import run_valuation_for_request
from app.domain.valuation.weights import (
    InvestmentPreferences,
    calculate_weights,
    normalize_weights,
)


def test_calculate_dcf_fair_price_matches_manual_calculation() -> None:
    assumptions = DcfAssumptions(
        forecast_years=2,
        growth_rate=Decimal("0"),
        discount_rate=Decimal("0.10"),
        terminal_growth_rate=Decimal("0"),
    )

    result = calculate_dcf_fair_price(
        average_fcf=Decimal("100"), listed_shares=10, assumptions=assumptions
    )

    expected_enterprise_value = (
        Decimal("100") / Decimal("1.10")
        + Decimal("100") / Decimal("1.10") ** 2
        + (Decimal("100") / Decimal("0.10")) / Decimal("1.10") ** 2
    )
    assert result == expected_enterprise_value / Decimal("10")


@pytest.mark.parametrize(
    ("average_fcf", "listed_shares", "assumptions"),
    [
        (Decimal("0"), 10, DcfAssumptions()),
        (Decimal("-1"), 10, DcfAssumptions()),
        (Decimal("100"), 0, DcfAssumptions()),
        (Decimal("100"), 10, DcfAssumptions(forecast_years=0)),
        (
            Decimal("100"),
            10,
            DcfAssumptions(
                discount_rate=Decimal("0.02"),
                terminal_growth_rate=Decimal("0.02"),
            ),
        ),
    ],
)
def test_calculate_dcf_fair_price_rejects_invalid_inputs(
    average_fcf: Decimal,
    listed_shares: int,
    assumptions: DcfAssumptions,
) -> None:
    assert calculate_dcf_fair_price(
        average_fcf=average_fcf,
        listed_shares=listed_shares,
        assumptions=assumptions,
    ) is None


def test_calculate_raw_metrics_calculates_upside_and_dividend_yield() -> None:
    result = calculate_raw_metrics(
        corp_code="00126380",
        business_year=2025,
        dcf_fair_price=Decimal("15000"),
        current_price=Decimal("10000"),
        per=Decimal("8.5"),
        dps=Decimal("500"),
    )

    assert result == RawValuationMetrics(
        corp_code="00126380",
        business_year=2025,
        dcf_upside=Decimal("0.5"),
        per=Decimal("8.5"),
        dividend_yield=Decimal("0.05"),
    )


def test_metric_normalization_handles_missing_or_invalid_values() -> None:
    assert calculate_dividend_yield(dps=None, current_price=Decimal("10000")) == 0
    assert calculate_dividend_yield(dps=Decimal("0"), current_price=Decimal("10000")) == 0
    assert normalize_per(None) is None
    assert normalize_per(Decimal("0")) is None
    assert normalize_per(Decimal("-1")) is None


def test_percentile_scores_respect_direction_and_ties() -> None:
    values = {
        "A": Decimal("5"),
        "B": Decimal("10"),
        "C": Decimal("10"),
        "D": Decimal("20"),
    }

    lower_is_better = percentile_scores(values, higher_is_better=False)
    higher_is_better = percentile_scores(values, higher_is_better=True)

    assert lower_is_better == {
        "A": Decimal("1"),
        "B": Decimal("0.5"),
        "C": Decimal("0.5"),
        "D": Decimal("0"),
    }
    assert higher_is_better == {
        "A": Decimal("0"),
        "B": Decimal("0.5"),
        "C": Decimal("0.5"),
        "D": Decimal("1"),
    }


def test_score_candidates_calculates_scores_and_competition_ranks() -> None:
    candidates = [
        RawValuationMetrics("A", 2025, Decimal("0.5"), Decimal("5"), Decimal("0.02")),
        RawValuationMetrics("B", 2025, Decimal("0.2"), Decimal("10"), Decimal("0.04")),
        RawValuationMetrics("C", 2025, Decimal("-0.1"), Decimal("20"), Decimal("0.01")),
    ]

    results = score_candidates(
        candidates=candidates,
        weights=ValuationWeights(
            dcf=Decimal("50"), per=Decimal("30"), dividend=Decimal("20")
        ),
    )

    assert [(result.corp_code, result.score, result.rank_position) for result in results] == [
        ("A", Decimal("90.0000"), 1),
        ("B", Decimal("60.0000"), 2),
        ("C", Decimal("0.0000"), 3),
    ]


def test_score_candidates_gives_zero_per_score_when_per_is_missing() -> None:
    [result] = score_candidates(
        candidates=[
            RawValuationMetrics("A", 2025, Decimal("0.1"), None, Decimal("0.01")),
        ],
        weights=ValuationWeights(
            dcf=Decimal("40"), per=Decimal("30"), dividend=Decimal("30")
        ),
    )

    assert result.per == Decimal("0.0000")
    assert result.score == Decimal("70.0000")


def test_scored_valuation_exposes_score_field() -> None:
    result = ScoredValuation(
        corp_code="A",
        business_year=2025,
        dcf=Decimal("10"),
        per=Decimal("20"),
        dividend=Decimal("30"),
        score=Decimal("60"),
        rank_position=1,
    )

    assert result.score == Decimal("60")


def test_valuation_weights_reject_each_negative_component() -> None:
    for values in [
        {"dcf": "-1", "per": "1", "dividend": "1"},
        {"dcf": "1", "per": "-1", "dividend": "1"},
        {"dcf": "1", "per": "1", "dividend": "-1"},
    ]:
        with pytest.raises(ValueError):
            ValuationWeights(**{key: Decimal(value) for key, value in values.items()})


def test_normalize_weights_preserves_total_of_one_hundred() -> None:
    weights = normalize_weights(
        dcf=Decimal("3"), per=Decimal("2"), dividend=Decimal("1")
    )

    assert weights.total == Decimal("100")
    assert weights.dcf > weights.per > weights.dividend


def test_calculate_weights_changes_with_user_preferences() -> None:
    dividend_investor = calculate_weights(
        InvestmentPreferences(
            return_preference="DIVIDEND",
            valuation_preference="CURRENT_ASSET",
            investment_period="UNDER_1_YEAR",
            risk_preference="STABLE",
        )
    )
    growth_investor = calculate_weights(
        InvestmentPreferences(
            return_preference="CAPITAL_GAIN",
            valuation_preference="FUTURE_EARNINGS",
            investment_period="OVER_3_YEARS",
            risk_preference="AGGRESSIVE",
        )
    )

    assert dividend_investor.total == Decimal("100")
    assert growth_investor.total == Decimal("100")
    assert dividend_investor.dividend > growth_investor.dividend
    assert growth_investor.dcf > dividend_investor.dcf


RUN_DB_INTEGRATION_TESTS = os.getenv("RUN_DB_INTEGRATION_TESTS") == "1"
requires_postgres = pytest.mark.skipif(
    not RUN_DB_INTEGRATION_TESTS,
    reason="RUN_DB_INTEGRATION_TESTS=1일 때만 PostgreSQL 통합 테스트를 실행합니다.",
)


@pytest.fixture
async def valuation_db_case():
    """실제 PostgreSQL 트랜잭션에 valuation 입력값을 만들고 종료 후 되돌린다."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    suffix = uuid.uuid4().hex[:7].upper()
    corp_code = f"T{suffix}"

    try:
        await session.execute(
            text(
                """
                INSERT INTO companies (corp_code, corp_name, is_manufacturing)
                VALUES (:corp_code, :corp_name, true)
                """
            ),
            {"corp_code": corp_code, "corp_name": "valuation integration test"},
        )
        await session.execute(
            text(
                """
                INSERT INTO fundamental_screening
                    (corp_code, business_year, passed)
                VALUES (:corp_code, 2025, true)
                """
            ),
            {"corp_code": corp_code},
        )

        for business_year, fcf, dps in [
            (2023, 900_000_000, 300),
            (2024, 1_000_000_000, 400),
            (2025, 1_100_000_000, 500),
        ]:
            await session.execute(
                text(
                    """
                    INSERT INTO financial_ratios
                        (corp_code, business_year, report_code, fcf, dps)
                    VALUES
                        (:corp_code, :business_year, '11011', :fcf, :dps)
                    """
                ),
                {
                    "corp_code": corp_code,
                    "business_year": business_year,
                    "fcf": fcf,
                    "dps": dps,
                },
            )

        await session.execute(
            text(
                """
                INSERT INTO market_data
                    (corp_code, market_date, current_price, listed_shares, per)
                VALUES
                    (:corp_code, :market_date, 10000, 1000000, 8.5)
                """
            ),
            {"corp_code": corp_code, "market_date": date(2026, 8, 28)},
        )
        request_id = await session.scalar(
            text(
                """
                INSERT INTO portfolio_request
                    (seed_money, investment_period, risk_preference,
                     return_preference, valuation_preference)
                VALUES
                    (10000000, 'OVER_3_YEARS', 'AGGRESSIVE',
                     'CAPITAL_GAIN', 'FUTURE_EARNINGS')
                RETURNING request_id
                """
            )
        )
        await session.flush()

        yield session, corp_code, int(request_id)
    finally:
        await session.close()

        if transaction.is_active:
            await transaction.rollback()

        await connection.close()
        await engine.dispose()


@requires_postgres
@pytest.mark.asyncio
async def test_postgres_query_and_save_valuation_results(valuation_db_case) -> None:
    session, corp_code, request_id = valuation_db_case

    inputs = await get_valuation_inputs(session)
    target_input = next(item for item in inputs if item.corp_code == corp_code)

    assert target_input.business_year == 2025
    assert target_input.average_fcf == Decimal("1000000000")
    assert target_input.current_price == Decimal("10000")
    assert target_input.listed_shares == 1_000_000
    assert target_input.per == Decimal("8.5")
    assert target_input.dps == Decimal("500")

    results = await run_valuation_for_request(session, request_id=request_id)
    target_result = next(result for result in results if result.corp_code == corp_code)
    stored_result = await session.scalar(
        select(ValuationResult).where(
            ValuationResult.request_id == request_id,
            ValuationResult.corp_code == corp_code,
        )
    )

    assert target_result.rank_position > 0
    assert target_result.score >= 0
    assert stored_result is not None
    assert stored_result.score == target_result.score


@requires_postgres
@pytest.mark.asyncio
async def test_daily_valuation_batch_replaces_results(valuation_db_case) -> None:
    session, corp_code, request_id = valuation_db_case

    first_count = await refresh_all_valuation_results(session)
    first_result = await session.scalar(
        select(ValuationResult).where(
            ValuationResult.request_id == request_id,
            ValuationResult.corp_code == corp_code,
        )
    )

    assert first_count >= 1
    assert first_result is not None

    second_count = await refresh_all_valuation_results(session)
    result_count = await session.scalar(
        select(text("count(*)")).select_from(ValuationResult).where(
            ValuationResult.request_id == request_id,
            ValuationResult.corp_code == corp_code,
        )
    )

    assert second_count == first_count
    assert result_count == 1

    
