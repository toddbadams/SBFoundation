"""Quarterly bulk ingestion service."""
from __future__ import annotations

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

    def run(self, run: RunContext) -> RunContext:
        self._logger.log_section(run.run_id, "Processing quarter bulk domain")
        today = date.fromisoformat(self._today)
        if not self.is_earnings_season(today):
            self._logger.info(
                f"Quarter bulk: outside earnings season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == QUARTER_DOMAIN]
        if not recipes:
            self._logger.warning("No quarterly bulk recipes found", run_id=run.run_id)
            return run
        self._logger.info(
            f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} quarterly bulk datasets",
            run_id=run.run_id,
        )
        if self._enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, QUARTER_DOMAIN)
        self._logger.info("Quarter bulk domain complete", run_id=run.run_id)
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
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}"
        f"  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )
