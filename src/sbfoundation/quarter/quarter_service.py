"""Quarterly bulk ingestion service."""
from __future__ import annotations

import dataclasses
from datetime import date

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import QUARTER_DOMAIN


class QuarterService(BulkPipelineService):
    """Orchestrates bulk quarterly fundamental ingestion.

    Only runs during earnings seasons:
    - Jan 1 - Mar 31  (Q4 prior year filings)
    - Apr 1 - May 31  (Q1 filings)
    - Jul 1 - Aug 31  (Q2 filings)
    - Oct 1 - Nov 30  (Q3 filings)
    """

    def run(
        self,
        run: RunContext,
        year: int | None = None,
        period: str | None = None,
    ) -> RunContext:
        """Run quarterly bulk ingestion.

        Args:
            run: Current run context.
            year: Calendar year to fetch (e.g., 2025). When provided together
                with ``period``, bypasses the earnings-season gate and injects
                ``year`` and ``period`` as additional query parameters.
            period: Fiscal quarter to fetch (e.g., "Q1"). Must be provided
                together with ``year``; ignored when ``year`` is omitted.
        """
        self._logger.log_section(run.run_id, "Processing quarter bulk domain")
        override_active = year is not None and period is not None
        today = date.fromisoformat(self._today)
        if not override_active and not self.is_earnings_season(today):
            self._logger.info(
                f"Quarter bulk: outside earnings season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == QUARTER_DOMAIN]
        if not recipes:
            self._logger.warning("No quarterly bulk recipes found", run_id=run.run_id)
            return run
        if override_active:
            self._logger.info(f"Quarter override: year={year} period={period}", run_id=run.run_id)
            recipes = [
                dataclasses.replace(r, query_vars={**(r.query_vars or {}), "year": year, "period": period})
                for r in recipes
            ]
        original_force_from_date = self._force_from_date
        if override_active:
            self._force_from_date = f"{year}-01-01"  # bypass watermark filter for historical fetch
        try:
            self._logger.info(
                f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} quarterly bulk datasets",
                run_id=run.run_id,
            )
            if self._enable_bronze:
                run = self._process_recipe_list(recipes, run)
            run = self._promote_silver(run, QUARTER_DOMAIN)
            self._logger.info("Quarter bulk domain complete", run_id=run.run_id)
        finally:
            self._force_from_date = original_force_from_date
        return run

    @staticmethod
    def is_earnings_season(today: date) -> bool:
        """Return True if today falls within an earnings filing window."""
        return today.month in (1, 2, 3, 4, 5, 7, 8, 10, 11)


if __name__ == "__main__":
    from sbfoundation.api import SBFoundationAPI, RunCommand

    command = RunCommand(
        domain=QUARTER_DOMAIN,
        concurrent_requests=1,  # sync mode for debugging
        enable_bronze=True,
        enable_silver=True,
        enable_gold=True,
        quarter_year=2025,
        quarter_period="Q1",
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}"
        f"  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )
