from __future__ import annotations

from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from tests.unit.helpers import make_bronze_result


def test_from_bronze_captures_bronze_metadata() -> None:
    result = make_bronze_result()
    ingestion = DatasetInjestion.from_bronze(result=result)

    assert ingestion.run_id == result.request.run_id
    assert ingestion.domain == result.request.recipe.domain
    assert ingestion.ticker == result.request.ticker
    assert ingestion.bronze_rows == len(result.content)
    assert ingestion.bronze_can_promote == result.canPromoteToSilverWith(allows_empty_content=result.request.allows_empty_content)


def test_to_dict_includes_required_fields() -> None:
    result = make_bronze_result()
    ingestion = DatasetInjestion.from_bronze(result=result)
    payload = ingestion.to_dict()
    assert payload["run_id"] == ingestion.run_id
    assert "bronze_payload_hash" in payload
