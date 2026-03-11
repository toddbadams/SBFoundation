"""Prefect flow for daily bulk EOD + company profile ingestion."""
from __future__ import annotations

from datetime import date

from prefect import flow, task, get_run_logger

from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.settings import EOD_DOMAIN


@task(name="eod-bulk-bronze-silver", retries=1, retry_delay_seconds=60)
def run_eod_pipeline(today: str | None = None) -> dict:
    """Execute EOD bulk Bronze + Silver ingestion."""
    logger = get_run_logger()
    logger.info(f"EOD pipeline starting for {today or 'today'}")
    command = RunCommand(
        domain=EOD_DOMAIN,
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
    name="sbfoundation-eod",
    description="Daily bulk end-of-day price and company profile ingestion",
)
def eod_flow(today: str | None = None) -> dict:
    """Daily EOD bulk flow. Scheduled weekdays after market close (18:00 ET)."""
    return run_eod_pipeline(today=today)
