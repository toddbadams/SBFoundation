"""EOD bulk ingestion service."""

from __future__ import annotations

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import EOD_DOMAIN

_DIMENSION_DATASETS = {"company-profile-bulk"}


class EodService(BulkPipelineService):
    """Orchestrates daily bulk EOD + company profile bulk ingestion.

    Both datasets are global (ticker_scope: global) — a single API call
    returns data for all symbols. No ticker loop is required.
    Cadence: daily on weekdays.
    """

    def run(self, run: RunContext, date: str | None = None) -> RunContext:
        """Run EOD bulk ingestion.

        Args:
            run: Current run context.
            date: ISO 8601 date string to use as the ``__to__`` query parameter
                for ``eod-bulk-price``. Defaults to today's date when omitted.
        """
        self._logger.log_section(run.run_id, "Processing EOD bulk domain")
        original_today = run.today
        original_force_from_date = self._force_from_date
        if date is not None:
            run.today = date
            self._force_from_date = date  # bypasses the BronzeService dedup gate
            self._logger.info(f"EOD date override: {date}", run_id=run.run_id)
        try:
            recipes = [r for r in self._dataset_service.recipes if r.domain == EOD_DOMAIN]
            if date is not None:
                # company-profile-bulk feeds Gold dimensions and is date-independent;
                # skip it for historical date fetches so only price data is downloaded.
                recipes = [r for r in recipes if r.dataset not in _DIMENSION_DATASETS]
            if not recipes:
                self._logger.warning("No EOD bulk recipes found", run_id=run.run_id)
                return run
            self._logger.info(
                f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} EOD bulk datasets",
                run_id=run.run_id,
            )
            if self._enable_bronze:
                run = self._process_recipe_list(recipes, run)
            run = self._promote_silver(run, EOD_DOMAIN)
            self._logger.info("EOD bulk domain complete", run_id=run.run_id)
        finally:
            run.today = original_today
            self._force_from_date = original_force_from_date
        return run


if __name__ == "__main__":
    from datetime import date, timedelta
    from sbfoundation.api import SBFoundationAPI, RunCommand

    _start = date(2026, 3, 13)
    _end = date(2026, 3, 14)
    _day = _start
    while _day <= _end:
        if _day.weekday() < 5:  # Mon–Fri only
            _eod_date = _day.isoformat()
            print(f"\n===== EOD {_eod_date} =====")
            command = RunCommand(
                domain=EOD_DOMAIN,
                concurrent_requests=1,  # sync mode for debugging
                enable_bronze=True,
                enable_silver=True,
                enable_gold=True,
                eod_date=_eod_date,
            )
            result = SBFoundationAPI(today=date.today().isoformat()).run(command)
            print(
                f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}"
                f"  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
            )
        _day += timedelta(days=1)
