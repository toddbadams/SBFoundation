import logging

import duckdb
import pandas as pd

from sbfoundation.run.services.chunk_engine import ChunkEngine
from sbfoundation.run.services.dedupe_engine import DedupeEngine
from sbfoundation.run.services.orchestration_ticker_chunk_service import OrchestrationTickerChunkService

from tests.unit.helpers import make_run_context, make_dataset_recipe


def test_chunk_engine_groups_by_year() -> None:
    engine = ChunkEngine(strategy="year")
    df = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-12-31", "2026-01-01"],
            "value": [1, 2, 3],
        }
    )
    chunks = list(engine.chunk(df, row_date_col="date"))
    assert len(chunks) == 2
    year_keys = {chunk.key: len(chunk.df) for chunk in chunks}
    assert year_keys["2025"] == 2
    assert year_keys["2026"] == 1


def test_dedupe_engine_filters_duplicates_without_duckdb() -> None:
    engine = DedupeEngine(use_duckdb_engine=False)
    conn = duckdb.connect()
    df_candidate = pd.DataFrame(
        [
            {"id": 1, "value": "first"},
            {"id": 1, "value": "second"},
            {"id": 2, "value": "third"},
        ]
    )
    deduped = engine.dedupe_against_table(conn, df_candidate=df_candidate, key_cols=["id"], target_table="dummy", table_exists=True)
    assert len(deduped) == 2
    assert deduped.iloc[0]["value"] == "second"
    assert deduped.iloc[1]["value"] == "third"
    conn.close()


def test_orchestration_service_process_triggers_chunks_and_promotions() -> None:
    recipes = [make_dataset_recipe(), make_dataset_recipe(), make_dataset_recipe()]
    ctx = make_run_context()
    chunk_sizes: list[int] = []
    promotions: list[str] = []

    def process_chunk(chunk, summary):
        chunk_sizes.append(len(chunk))
        summary.bronze_files_passed = len(chunk)
        summary.silver_dto_count = len(chunk)
        return summary

    def promote_silver(summary):
        promotions.append("silver")
        return summary

    service = OrchestrationTickerChunkService(
        chunk_size=2,
        logger=logging.getLogger("test"),
        process_chunk=process_chunk,
        promote_silver=promote_silver,
        silver_enabled=True,
    )

    result = service.process(recipes, ctx)
    assert chunk_sizes == [2, 1]
    assert promotions == ["silver", "silver"]
    assert result is ctx
