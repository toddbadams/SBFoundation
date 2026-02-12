from __future__ import annotations

import re
from datetime import date

from data_layer.services.universe_service import UniverseService


def test_update_tickers_slice_and_limits() -> None:
    service = UniverseService()
    first_three = service.update_tickers(limit=3)
    # May return empty if no data has been ingested yet
    assert len(first_three) <= 3
    if first_three:
        assert first_three[0] == sorted(service.update_tickers(limit=50))[0]
    total_count = service.update_ticker_count()
    assert service.update_tickers(start=total_count + 1, limit=3) == []


def test_update_tickers_with_non_positive_limit_returns_empty() -> None:
    service = UniverseService()
    assert service.update_tickers(limit=0) == []
    assert service.update_tickers(limit=-1) == []


def test_new_tickers_with_non_positive_limit_returns_empty() -> None:
    service = UniverseService()
    assert service.new_tickers(limit=0) == []
    assert service.new_tickers(limit=-1) == []


def test_run_id_has_expected_format() -> None:
    service = UniverseService()
    run_id = service.run_id()
    assert re.fullmatch(r"\d{6}\.[0-9a-f]{6}", run_id)


def test_next_market_day_skips_weekend() -> None:
    service = UniverseService()
    friday = date(2026, 1, 23)
    next_day = service.next_market_day(friday)
    assert next_day.weekday() == 0  # Monday
    assert next_day > friday
