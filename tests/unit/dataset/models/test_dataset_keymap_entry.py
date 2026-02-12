from __future__ import annotations

import pytest

from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.dataset.models.dataset_keymap import DatasetKeymap
from sbfoundation.dataset.models.dataset_keymap_entry import DatasetKeymapEntry


def _identity_with_ticker(ticker: str | None) -> DatasetIdentity:
    return DatasetIdentity(domain="company", source="fmp", dataset="company-profile", ticker=ticker or "", discriminator="")


def test_keymap_entry_global_scope_checks_ticker() -> None:
    entry = DatasetKeymapEntry(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker_scope="global",
        silver_schema="schema",
        silver_table="table",
        key_cols=("ticker",),
    )
    assert entry.matches_identity(_identity_with_ticker(""))
    assert not entry.matches_identity(_identity_with_ticker("AAPL"))


def test_keymap_entry_per_ticker_scope_requires_ticker() -> None:
    entry = DatasetKeymapEntry(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker_scope="per_ticker",
        silver_schema="schema",
        silver_table="table",
        key_cols=("ticker",),
    )
    assert entry.matches_identity(_identity_with_ticker("AAPL"))
    assert not entry.matches_identity(_identity_with_ticker(""))


def test_dataset_keymap_require_raises_when_missing() -> None:
    entry = DatasetKeymapEntry(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker_scope="global",
        silver_schema="schema",
        silver_table="table",
        key_cols=("ticker",),
    )
    keymap = DatasetKeymap(version=1, entries=(entry,))
    missing_identity = DatasetIdentity(domain="company", source="fmp", dataset="other", discriminator="", ticker="")
    with pytest.raises(KeyError):
        keymap.require(missing_identity)
