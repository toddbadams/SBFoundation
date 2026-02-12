from tests.unit.helpers import make_run_result


def test_run_result_is_valid_bronze_success() -> None:
    result = make_run_result()
    assert result.is_valid_bronze


def test_run_result_invalid_headers_report_error() -> None:
    result = make_run_result(overrides={"headers": None})
    assert not result.is_valid_bronze
    assert result.error == "INVALID HEADERS"


def test_run_result_invalid_content_report_error() -> None:
    result = make_run_result(overrides={"content": "bad"})
    assert not result.is_valid_bronze
    assert result.error == "INVALID CONTENT"


def test_run_result_can_promote_to_silver_when_payload_present() -> None:
    result = make_run_result()
    assert result.canPromoteToSilver


def test_run_result_cannot_promote_with_empty_payload() -> None:
    result = make_run_result(overrides={"content": [], "hash": "hash"})
    assert not result.canPromoteToSilver
    assert not result.canPromoteToSilverWith(allows_empty_content=False)
