from __future__ import annotations

from datetime import date, datetime, timedelta

from requests.structures import CaseInsensitiveDict

from sbfoundation.dtos.dto_registry import DTO_REGISTRY
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.dtos.run_result import RunResult
from sbfoundation.settings import (
    BASE_URL,
    CADENCES,
    COMPANY_DOMAIN,
    COMPANY_INFO_DATASET,
    DATA_SOURCES_CONFIG,
    DEFAULT_LIMIT,
    FMP_DATA_SOURCE,
)


def make_dataset_recipe(**overrides: object) -> DatasetRecipe:
    base = {
        "domain": COMPANY_DOMAIN,
        "source": FMP_DATA_SOURCE,
        "dataset": COMPANY_INFO_DATASET,
        "data_source_path": "/tmp",
        "query_vars": {"constant": "value"},
        "date_key": "date",
        "cadence_mode": CADENCES[0],
        "min_age_days": 0,
        "is_ticker_based": True,
        "help_url": "https://help",
    }
    base.update(overrides)
    return DatasetRecipe(**base)


def make_run_request(*, recipe: DatasetRecipe | None = None, overrides: dict[str, object] | None = None) -> RunRequest:
    recipe = recipe or make_dataset_recipe()
    today = date(2026, 1, 27)
    from_day = today - timedelta(days=1)
    base = {
        "recipe": recipe,
        "injestion_date": today.isoformat(),
        "run_id": "run-123",
        "ticker": "AAPL",
        "dto_type": DTO_REGISTRY[recipe.dataset],
        "data_source_path": recipe.data_source_path,
        "url": f"{DATA_SOURCES_CONFIG[recipe.source][BASE_URL]}{recipe.data_source_path}",
        "query_vars": recipe.get_query_vars(from_date=from_day.isoformat(), ticker="AAPL", to_date=today.isoformat()),
        "date_key": recipe.date_key,
        "allows_empty_content": False,
        "from_date": from_day.isoformat(),
        "to_date": today.isoformat(),
        "limit": DEFAULT_LIMIT,
        "cadence_mode": recipe.cadence_mode,
        "min_age_days": recipe.min_age_days,
        "release_day": None,
        "error": None,
        "file_id": recipe.create_file_id(),
    }
    if overrides:
        base.update(overrides)
    return RunRequest(**base)


def make_run_result(*, request: RunRequest | None = None, overrides: dict[str, object] | None = None) -> RunResult:
    request = request or make_run_request()
    base = {
        "request": request,
        "now": datetime(2026, 1, 27, 12, 0),
        "elapsed_microseconds": 1000,
        "headers": CaseInsensitiveDict({"content-type": "application/json"}),
        "status_code": 200,
        "reason": "OK",
        "content": [{"date": "2026-01-26"}],
        "hash": "hash",
        "first_date": request.from_date,
        "last_date": request.to_date,
    }
    if overrides:
        base.update(overrides)
    return RunResult(**base)


def make_run_context(**overrides: object) -> RunContext:
    start = datetime(2026, 1, 27, 9, 0)
    base = {
        "run_id": "run-123",
        "started_at": start,
        "tickers": ["AAPL"],
        "today": start.date().isoformat(),
        "finished_at": start + timedelta(seconds=90),
        "bronze_files_passed": 0,
        "bronze_files_failed": 0,
        "silver_dto_count": 0,
        "silver_failed_count": 0,
        "throttle_wait_count": 0,
        "throttle_sleep_seconds": 0.0,
        "throttle_max_queue_depth": 0,
        "status": None,
        "bronze_injest_items": [],
        "silver_injest_items": [],
    }
    if overrides:
        base.update(overrides)
    return RunContext(**base)
