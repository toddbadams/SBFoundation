"""Annual bulk ingestion service."""
from __future__ import annotations

import dataclasses
from datetime import date

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import ANNUAL_DOMAIN


class AnnualService(BulkPipelineService):
    """Orchestrates bulk annual fundamental ingestion.

    Only runs during the annual filing window: January through March (FY filings).
    """

    def run(self, run: RunContext, year: int | None = None) -> RunContext:
        self._logger.log_section(run.run_id, "Processing annual bulk domain")
        today = date.fromisoformat(self._today)
        if not self.is_annual_season(today):
            self._logger.info(
                f"Annual bulk: outside annual filing season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == ANNUAL_DOMAIN]
        if not recipes:
            self._logger.warning("No annual bulk recipes found", run_id=run.run_id)
            return run
        if year is not None:
            recipes = [
                dataclasses.replace(r, query_vars={**r.query_vars, "year": year})
                for r in recipes
            ]
            self._logger.info(f"Annual bulk: filtering to year={year}", run_id=run.run_id)
        self._logger.info(
            f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} annual bulk datasets",
            run_id=run.run_id,
        )
        if self._enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, ANNUAL_DOMAIN)
        self._logger.info("Annual bulk domain complete", run_id=run.run_id)
        return run

    @staticmethod
    def is_annual_season(today: date) -> bool:
        """Return True if today falls within the annual filing window (Jan–Mar)."""
        return today.month in (1, 2, 3)


if __name__ == "__main__":
    from sbfoundation.api import SBFoundationAPI, RunCommand

    command = RunCommand(
        domain=ANNUAL_DOMAIN,
        concurrent_requests=1,  # sync mode for debugging
        enable_bronze=True,
        enable_silver=True,
        enable_gold=True,
        year=2024,  # omit to fetch all available years
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}"
        f"  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )
