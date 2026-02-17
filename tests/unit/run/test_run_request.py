from tests.unit.helpers import make_dataset_recipe, make_run_request


def test_run_request_can_run_success() -> None:
    request = make_run_request()
    assert request.canRun()


def test_run_request_rejects_invalid_recipe() -> None:
    bad_recipe = make_dataset_recipe(domain="missing")
    request = make_run_request(recipe=bad_recipe)
    assert not request.canRun()
    assert request.error == "INVALID RUN RECIPE"


def test_run_request_rejects_invalid_ticker() -> None:
    request = make_run_request(overrides={"ticker": "WAYTOOLONGFOR"})
    assert not request.canRun()
    assert request.error == "INVALID TICKER"


def test_run_request_rejects_invalid_dto_type() -> None:
    request = make_run_request(overrides={"dto_type": str})
    assert not request.canRun()
    assert request.error == "INVALID DTO TYPE"


def test_run_request_rejects_too_soon() -> None:
    request = make_run_request(
        overrides={
            "from_date": "2026-01-27",
            "injestion_date": "2026-01-27",
            "min_age_days": 2,
        }
    )
    assert not request.canRun()
    assert request.error == "REQUEST IS TOO SOON"


def test_run_request_has_instrument_sk_property() -> None:
    """Test that RunRequest accepts and stores instrument_sk."""
    request = make_run_request(overrides={"instrument_sk": 42})
    assert request.instrument_sk == 42


def test_run_request_instrument_sk_defaults_to_none() -> None:
    """Test that instrument_sk defaults to None."""
    request = make_run_request()
    assert request.instrument_sk is None
