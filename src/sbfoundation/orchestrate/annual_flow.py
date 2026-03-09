"""Prefect flow for bulk annual fundamental ingestion (Jan–Mar only)."""
from __future__ import annotations

from datetime import date

from prefect import flow, task, get_run_logger

from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.annual import AnnualService
from sbfoundation.settings import ANNUAL_DOMAIN


@task(name="annual-bulk-bronze-silver", retries=1, retry_delay_seconds=60)
def run_annual_pipeline(today: str | None = None) -> dict:
    """Execute annual bulk Bronze + Silver ingestion (gated to Jan–Mar)."""
    logger = get_run_logger()
    today_date = date.fromisoformat(today) if today else date.today()
    if not AnnualService.is_annual_season(today_date):
        logger.info(f"Annual pipeline: outside annual season ({today_date}) — skipped")
        return {"skipped": True, "reason": "outside_annual_season"}
    logger.info(f"Annual pipeline starting for {today_date}")
    command = RunCommand(
        domain=ANNUAL_DOMAIN,
        concurrent_requests=5,
        enable_bronze=True,
        enable_silver=True,
    )
    api = SBFoundationAPI(today=today)
    result = api.run(command)
    return {
        "run_id": result.run_id,
        "bronze_passed": result.bronze_files_passed,
        "bronze_failed": result.bronze_files_failed,
        "silver_rows": result.silver_dto_count,
    }


@flow(
    name="sbfoundation-annual",
    description="Bulk annual fundamental ingestion (Jan–Mar only)",
)
def annual_flow(today: str | None = None) -> dict:
    """Annual bulk flow. Scheduled daily at 08:00 ET; internally gated to Jan–Mar."""
    return run_annual_pipeline(today=today)
