"""EOD bulk ingestion service."""
from __future__ import annotations

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import EOD_DOMAIN


class EodService(BulkPipelineService):
    """Orchestrates daily bulk EOD + company profile bulk ingestion.

    Both datasets are global (ticker_scope: global) — a single API call
    returns data for all symbols. No ticker loop is required.
    Cadence: daily on weekdays.
    """

    def run(self, run: RunContext) -> RunContext:
        self._logger.log_section(run.run_id, "Processing EOD bulk domain")
        recipes = [r for r in self._dataset_service.recipes if r.domain == EOD_DOMAIN]
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
        return run


if __name__ == "__main__":
    from datetime import date
    from sbfoundation.api import SBFoundationAPI, RunCommand

    command = RunCommand(
        domain=EOD_DOMAIN,
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
