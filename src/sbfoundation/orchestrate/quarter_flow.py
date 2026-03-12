"""Prefect flow for bulk quarterly fundamental ingestion (earnings season only)."""
from __future__ import annotations

from datetime import date

from prefect import flow, task, get_run_logger

from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.quarter import QuarterService
from sbfoundation.settings import QUARTER_DOMAIN


@task(name="quarter-bulk-bronze-silver", retries=1, retry_delay_seconds=60)
def run_quarter_pipeline(today: str | None = None) -> dict:
    """Execute quarterly bulk Bronze + Silver ingestion (gated by earnings season)."""
    logger = get_run_logger()
    today_date = date.fromisoformat(today) if today else date.today()
    if not QuarterService.is_earnings_season(today_date):
        logger.info(f"Quarter pipeline: outside earnings season ({today_date}) — skipped")
        return {"skipped": True, "reason": "outside_earnings_season"}
    logger.info(f"Quarter pipeline starting for {today_date}")
    command = RunCommand(
        domain=QUARTER_DOMAIN,
        concurrent_requests=5,
        enable_bronze=True,
        enable_silver=True,
        enable_gold=True,
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
    name="sbfoundation-quarter",
    description="Bulk quarterly fundamental ingestion (earnings seasons only)",
)
def quarter_flow(today: str | None = None) -> dict:
    """Quarterly bulk flow. Scheduled daily at 08:00 ET; internally gated by earnings season."""
    return run_quarter_pipeline(today=today)
