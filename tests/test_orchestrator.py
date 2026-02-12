from datetime import datetime, timezone

import pytest

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.orchestrator import Orchestrator, OrchestrationSettings
from sbfoundation.settings import *


class DummyOpsService:
    def __init__(self) -> None:
        self.finished_context: RunContext | None = None

    def start_run(
        self,
        *,
        update_ticker_limit: int = 0,
        new_ticker_limit: int = 0,
        enable_update_tickers: bool = True,
        enable_new_tickers: bool = False,
    ) -> RunContext:
        tickers = ["AAPL"] if enable_update_tickers else []
        return RunContext(
            run_id="dummy",
            started_at=datetime.now(timezone.utc),
            tickers=tickers,
            update_tickers=tickers if enable_update_tickers else [],
            new_tickers=[] if not enable_new_tickers else [],
            today="2026-01-01",
        )

    def finish_run(self, summary: RunContext) -> None:
        summary.finished_at = datetime.now(timezone.utc)
        self.finished_context = summary

    def close(self) -> None:
        pass


def _make_recipe(name: str, is_ticker_based: bool, domain: str = COMPANY_DOMAIN) -> DatasetRecipe:
    return DatasetRecipe(
        domain=domain,
        source=FMP_DATA_SOURCE,
        dataset=COMPANY_INFO_DATASET,
        data_source_path=f"/{name}",
        query_vars={},
        date_key="date",
        cadence_mode=INTERVAL_CADENCE_MODE,
        min_age_days=0,
        is_ticker_based=is_ticker_based,
        help_url="https://example.com/docs",
    )


def test_orchestrator_processes_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create recipes for the company domain (non-ticker and ticker)
    non_ticker_recipes = [_make_recipe("non-1", False, COMPANY_DOMAIN), _make_recipe("non-2", False, COMPANY_DOMAIN)]
    ticker_recipes = [_make_recipe(f"ticker-{i}", True, COMPANY_DOMAIN) for i in range(12)]
    all_recipes = non_ticker_recipes + ticker_recipes

    # Mock the recipes property to return all recipes
    monkeypatch.setattr(DatasetService, "recipes", property(lambda self: all_recipes))

    registered_batches: list[list[DatasetRecipe]] = []

    class DummyBronzeService:
        def __init__(self, *args, **kwargs) -> None:
            self._last_batch: list[DatasetRecipe] = []

        def register_recipes(self, recipes: list[DatasetRecipe]) -> "DummyBronzeService":
            self._last_batch = list(recipes)
            registered_batches.append(self._last_batch)
            return self

        def process(self, run_summary: RunContext) -> RunContext:
            run_summary.bronze_files_passed += len(self._last_batch)
            return run_summary

        def close(self) -> None:
            pass

    monkeypatch.setattr("sbfoundation.orchestrator.BronzeService", DummyBronzeService)

    silver_calls: list[int] = []

    def fake_silver(self, summary: RunContext) -> RunContext:
        silver_calls.append(summary.bronze_files_passed)
        summary.silver_dto_count += 1
        return summary

    monkeypatch.setattr(Orchestrator, "_promote_silver", fake_silver)

    switches = OrchestrationSettings(
        enable_instrument=True,
        enable_economics=True,
        enable_company=True,
        enable_fundamentals=True,
        enable_technicals=True,
        enable_bronze=True,
        enable_silver=True,
        enable_non_ticker_run=True,
        enable_ticker_run=True,
        enable_update_tickers=True,
        enable_new_tickers=False,
        non_ticker_recipe_limit=99,
        ticker_recipe_limit=99,
        update_ticker_limit=10,
        new_ticker_limit=0,
        fmp_plan=FMP_BASIC_PLAN,
    )
    orchestrator = Orchestrator(switches=switches, today="2026-01-01", ops_service=DummyOpsService())
    result = orchestrator.run()

    # Company domain: 2 non-ticker recipes, then 12 ticker recipes in chunks of 10
    assert len(registered_batches) == 3
    assert all(not recipe.is_ticker_based for recipe in registered_batches[0])
    assert len(registered_batches[0]) == 2
    assert len(registered_batches[1]) == 10
    assert len(registered_batches[2]) == 2
    assert all(recipe.is_ticker_based for recipe in registered_batches[1] + registered_batches[2])
    # Silver calls: after non-ticker (2), after chunk 1 (12), after chunk 2 (14)
    assert silver_calls == [2, 12, 14]
    assert result.bronze_files_passed == 14


def test_silver_runs_without_bronze(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create a recipe for company domain so that domain gets processed
    test_recipes = [_make_recipe("test", False, COMPANY_DOMAIN)]
    monkeypatch.setattr(DatasetService, "recipes", property(lambda self: test_recipes))

    switches = OrchestrationSettings(
        enable_instrument=True,
        enable_economics=True,
        enable_company=True,
        enable_fundamentals=True,
        enable_technicals=True,
        enable_bronze=False,
        enable_silver=True,
        enable_non_ticker_run=True,
        enable_ticker_run=False,
        enable_update_tickers=True,
        enable_new_tickers=False,
        non_ticker_recipe_limit=99,
        ticker_recipe_limit=99,
        update_ticker_limit=5,
        new_ticker_limit=0,
        fmp_plan=FMP_BASIC_PLAN,
    )

    silver_called: list[RunContext] = []

    def fake_silver(self, summary: RunContext) -> RunContext:
        silver_called.append(summary)
        return summary

    def fake_process(self, recipes: list[DatasetRecipe], summary: RunContext) -> RunContext:
        raise AssertionError("Bronze processing should not run when bronze is False")

    monkeypatch.setattr(Orchestrator, "_promote_silver", fake_silver)
    monkeypatch.setattr(Orchestrator, "_process_recipe_list", fake_process)

    orchestrator = Orchestrator(switches=switches, today="2026-01-01", ops_service=DummyOpsService())
    orchestrator.run()

    # Silver should be called once for the company domain (since it has recipes)
    assert len(silver_called) == 1
