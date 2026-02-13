from datetime import timedelta

from tests.unit.helpers import make_run_context, make_bronze_result


def test_run_context_bronze_counters_and_status() -> None:
    ctx = make_run_context()
    result = make_bronze_result()
    ctx.result_bronze_pass(result)
    ctx.result_bronze_error(result, e="FAILED")
    ctx.silver_dto_count = 1
    assert ctx.bronze_files_passed == 1
    assert ctx.bronze_files_failed == 1
    assert ctx.resolve_status() == "partial"


def test_run_context_resolve_status_success() -> None:
    ctx = make_run_context()
    ctx.silver_dto_count = 2
    assert ctx.resolve_status() == "success"


def test_run_context_formatted_elapsed_time_multiple_units() -> None:
    ctx = make_run_context()
    ctx.finished_at = ctx.started_at + timedelta(minutes=1, seconds=30)
    assert ctx.formatted_elapsed_time == "1m 30s"
