import os
from datetime import datetime

import pytest
from dateutil.relativedelta import relativedelta

from sbfoundation.settings import *
from tests.unit.helpers import make_dataset_recipe


@pytest.mark.parametrize(
    "overrides,expected_error",
    [
        ({"domain": "missing"}, "INVALID DOMAIN"),
        ({"source": "missing"}, "INVALID DATA SOURCE"),
        ({"dataset": "missing"}, "INVALID DATA SET"),
        ({"cadence_mode": "missing"}, "INVALID CADENCE MODE"),
        ({"run_days": ["invalid"]}, "INVALID RUN DAYS"),
    ],
)
def test_invalid_constants_set_error(overrides: dict[str, object], expected_error: str) -> None:
    recipe = make_dataset_recipe(**overrides)
    assert not recipe.isValid()
    assert recipe.error == expected_error


def test_run_days_normalize_and_default() -> None:
    recipe_with_explicit = make_dataset_recipe(run_days=[" MON ", "tues"])
    assert recipe_with_explicit.run_days == ["mon", "tues"]
    assert recipe_with_explicit.isValid()

    recipe_with_blank = make_dataset_recipe(run_days=["   "])
    assert recipe_with_blank.isValid()
    assert recipe_with_blank.run_days == list(DAYS_OF_WEEK)


def test_runs_on_with_default_days() -> None:
    recipe = make_dataset_recipe()
    assert recipe.runs_on("mon")
    assert recipe.runs_on("MON")
    assert recipe.runs_on("")


def test_get_query_vars_substitutes_placeholders(monkeypatch: pytest.MonkeyPatch) -> None:
    recipe = make_dataset_recipe(
        query_vars={
            "ticker": TICKER_PLACEHOLDER,
            "from": FROM_DATE_PLACEHOLDER,
            "from_month": FROM_ONE_MONTH_AGO_PLACEHOLDER,
            "to": TO_DATE_PLACEHOLDER,
            "limit": LIMIT_PLACEHOLDER,
            "period": PERIOD_PLACEHOLDER,
            "keep": "value",
            "none": None,
        }
    )
    monkeypatch.setenv("FMP_API_KEY", "env-key")
    to_date = "2025-02-01"
    expected_from_month = (datetime.fromisoformat(to_date) - relativedelta(months=1)).date().isoformat()
    vars_result = recipe.get_query_vars(from_date="2025-01-01", to_date=to_date, ticker="AAPL")
    assert vars_result["ticker"] == "AAPL"
    assert vars_result["from"] == "2025-01-01"
    assert vars_result["from_month"] == expected_from_month
    assert vars_result["to"] == to_date
    assert vars_result["limit"] == DEFAULT_LIMIT
    assert vars_result["period"] == PERIOD_ANNUAL
    assert vars_result["keep"] == "value"
    assert "none" not in vars_result
    assert vars_result["apikey"] == "env-key"


def test_get_query_vars_uses_explicit_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    recipe = make_dataset_recipe(query_vars={})
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    vars_result = recipe.get_query_vars(api_key="explicit")
    assert vars_result["apikey"] == "explicit"
