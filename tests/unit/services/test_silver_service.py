from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from sbfoundation.dtos.models import BronzeManifestRow
from sbfoundation.dataset.models.dataset_keymap import DatasetKeymap
from sbfoundation.dataset.models.dataset_keymap_entry import DatasetKeymapEntry
from sbfoundation.services.silver.silver_service import SilverService


def _keymap_entry(dataset: str, silver_table: str, ticker_scope: str = "per_ticker") -> DatasetKeymapEntry:
    return DatasetKeymapEntry(
        domain="company",
        source="fmp",
        dataset=dataset,
        discriminator="",
        ticker_scope=ticker_scope,
        silver_schema="silver",
        silver_table=silver_table,
        key_cols=("ticker", "as_of_date"),
    )


def _manifest_row(dataset: str, ticker: str | None = None) -> BronzeManifestRow:
    return BronzeManifestRow(
        bronze_file_id=1,
        run_id="run-123",
        domain="company",
        source="fmp",
        dataset=dataset,
        discriminator="",
        ticker=ticker or "",
        file_path_rel="bronze.json",
        coverage_from_date=date(2026, 1, 1),
        coverage_to_date=date(2026, 1, 2),
        ingested_at=datetime(2026, 1, 27, 12, 0),
    )


def test_resolve_keymap_entry_missing_entry_raises() -> None:
    row = _manifest_row("company-profile", ticker="AAPL")
    keymap = DatasetKeymap(version=1, entries=(_keymap_entry("company-employees", "company-employees"),))
    service = object.__new__(SilverService)

    with pytest.raises(KeyError):
        SilverService._resolve_keymap_entry(service, row, keymap)


def test_resolve_keymap_entry_requires_ticker() -> None:
    entry = _keymap_entry("company-profile", "company-profile")
    row = _manifest_row("company-profile", ticker="")
    keymap = DatasetKeymap(version=1, entries=(entry,))
    service = object.__new__(SilverService)

    with pytest.raises(KeyError):
        SilverService._resolve_keymap_entry(service, row, keymap)


def test_apply_watermark_filters_older_rows() -> None:
    df = pd.DataFrame({"as_of_date": ["2026-01-01", "2026-01-10", "2026-01-12"]})
    filtered = SilverService._apply_watermark(df, "as_of_date", date(2026, 1, 10))
    assert len(filtered) == 1
    assert filtered.iloc[0]["as_of_date"] == "2026-01-12"
