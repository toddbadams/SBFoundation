"""Re-promote company-peers data from Bronze to Silver and Gold.

This script fixes the company-peers data after the bug fix that added the
`api` field mapping for the `peer` column (Bronze `symbol` -> Silver `peer`).

Usage
-----
    # Re-promote company-peers with dry run first
    python scripts/repromote_company_peers.py --dry-run

    # Re-promote company-peers (Silver and Gold)
    python scripts/repromote_company_peers.py

    # Re-promote only Silver layer
    python scripts/repromote_company_peers.py --silver-only

The script:
1. Drops the silver.fmp_company_peers table
2. Drops the gold.dim_company_peer table (unless --silver-only)
3. Resets ops.file_ingestions metadata for company-peers files
4. Re-runs Silver promotion from existing Bronze files
5. Re-runs Gold promotion (unless --silver-only)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory
from sbfoundation.services.silver.silver_service import SilverService
from sbfoundation.services.gold.gold_service import GoldService
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.services.instrument_resolution_service import InstrumentResolutionService
from datetime import date


DATASET = "company-peers"
SILVER_TABLE = "fmp_company_peers"
GOLD_TABLE = "dim_company_peer"


def table_exists(conn, schema: str, table: str) -> bool:
    """Check if a table exists in the database."""
    result = conn.execute(
        """
        SELECT COUNT(*) > 0
        FROM information_schema.tables
        WHERE table_schema = ? AND table_name = ?
        """,
        [schema, table],
    ).fetchone()
    return bool(result and result[0])


def reset_company_peers_silver(conn, logger: logging.Logger, dry_run: bool) -> int:
    """Drop the company-peers Silver table and reset metadata.

    Returns:
        Number of rows affected in file_ingestions
    """
    # Drop the Silver table
    if table_exists(conn, "silver", SILVER_TABLE):
        sql = f'DROP TABLE silver."{SILVER_TABLE}"'
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Dropping silver.{SILVER_TABLE}")
        if not dry_run:
            conn.execute(sql)
    else:
        logger.info(f"Silver table silver.{SILVER_TABLE} does not exist, skipping drop")

    # Reset silver columns in file_ingestions for company-peers only
    reset_sql = f"""
        UPDATE ops.file_ingestions
        SET
            silver_tablename = NULL,
            silver_errors = NULL,
            silver_rows_created = NULL,
            silver_rows_updated = NULL,
            silver_rows_failed = NULL,
            silver_from_date = NULL,
            silver_to_date = NULL,
            silver_injest_start_time = NULL,
            silver_injest_end_time = NULL,
            silver_can_promote = NULL,
            bronze_can_promote = TRUE
        WHERE dataset = '{DATASET}'
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Resetting silver metadata for {DATASET} in ops.file_ingestions")

    # Get count of affected rows
    count_result = conn.execute(f"SELECT COUNT(*) FROM ops.file_ingestions WHERE dataset = '{DATASET}'").fetchone()
    affected_rows = count_result[0] if count_result else 0

    if not dry_run:
        conn.execute(reset_sql)

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}{affected_rows} file_ingestions rows will be reset")
    return affected_rows


def reset_company_peers_gold(conn, logger: logging.Logger, dry_run: bool) -> None:
    """Drop the company-peers Gold dimension table and reset metadata."""
    # Drop the Gold table
    if table_exists(conn, "gold", GOLD_TABLE):
        sql = f'DROP TABLE gold."{GOLD_TABLE}"'
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Dropping gold.{GOLD_TABLE}")
        if not dry_run:
            conn.execute(sql)
    else:
        logger.info(f"Gold table gold.{GOLD_TABLE} does not exist, skipping drop")

    # Reset gold columns in file_ingestions for company-peers only
    reset_sql = f"""
        UPDATE ops.file_ingestions
        SET
            gold_object_type = NULL,
            gold_tablename = NULL,
            gold_errors = NULL,
            gold_rows_created = NULL,
            gold_rows_updated = NULL,
            gold_rows_failed = NULL,
            gold_from_date = NULL,
            gold_to_date = NULL,
            gold_injest_start_time = NULL,
            gold_injest_end_time = NULL,
            gold_can_promote = NULL
        WHERE dataset = '{DATASET}'
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Resetting gold metadata for {DATASET} in ops.file_ingestions")
    if not dry_run:
        conn.execute(reset_sql)


def run_silver_promotion(logger: logging.Logger) -> tuple[int, int]:
    """Run Silver promotion for company-peers.

    Returns:
        Tuple of (files_promoted, rows_promoted)
    """
    logger.info("Running Silver promotion for company-peers...")

    ops_service = OpsService()
    keymap_service = DatasetService(today=date.today().isoformat(), plan="basic", logger=logger)
    instrument_resolver = InstrumentResolutionService(logger=logger)

    silver_service = SilverService(
        ops_service=ops_service,
        keymap_service=keymap_service,
        instrument_resolver=instrument_resolver,
    )

    try:
        promoted_ids, promoted_rows = silver_service.promote()
        logger.info(f"Silver promotion complete: {len(promoted_ids)} files, {promoted_rows} rows")
        return len(promoted_ids), promoted_rows
    finally:
        silver_service.close()
        instrument_resolver.close()
        ops_service.close()


def run_gold_promotion(logger: logging.Logger) -> tuple[int, int, int]:
    """Run Gold promotion for company-peers.

    Returns:
        Tuple of (dims_inserted, dims_updated, facts_upserted)
    """
    logger.info("Running Gold promotion...")

    ops_service = OpsService()
    keymap_service = DatasetService(today=date.today().isoformat(), plan="basic", logger=logger)

    gold_service = GoldService(ops_service=ops_service, dataset_service=keymap_service)

    try:
        # Generate a run_id for this promotion
        import uuid
        run_id = f"repromote-{uuid.uuid4().hex[:8]}"

        summary = gold_service.process(run_id=run_id, tickers=set())
        logger.info(
            f"Gold promotion complete: dims_inserted={summary.dims_inserted}, "
            f"dims_updated={summary.dims_updated}, facts_upserted={summary.facts_upserted}"
        )
        return summary.dims_inserted, summary.dims_updated, summary.facts_upserted
    finally:
        gold_service.close()
        ops_service.close()


def verify_fix(conn, logger: logging.Logger) -> bool:
    """Verify that the peer column is now populated correctly."""
    if not table_exists(conn, "silver", SILVER_TABLE):
        logger.warning(f"Cannot verify - silver.{SILVER_TABLE} does not exist")
        return False

    # Check for rows with empty peer column
    result = conn.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN peer IS NULL OR peer = '' THEN 1 ELSE 0 END) as empty_peers
        FROM silver."{SILVER_TABLE}"
    """).fetchone()

    total = result[0] if result else 0
    empty_peers = result[1] if result else 0

    if total == 0:
        logger.warning("No rows found in silver.fmp_company_peers")
        return False

    if empty_peers > 0:
        logger.error(f"VERIFICATION FAILED: {empty_peers}/{total} rows still have empty peer column")
        return False

    logger.info(f"VERIFICATION PASSED: All {total} rows have peer column populated")

    # Show sample data
    sample = conn.execute(f"""
        SELECT ticker, peer, company_name
        FROM silver."{SILVER_TABLE}"
        LIMIT 5
    """).fetchall()

    logger.info("Sample data:")
    for row in sample:
        logger.info(f"  ticker={row[0]}, peer={row[1]}, company_name={row[2]}")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--silver-only",
        action="store_true",
        help="Only re-promote Silver layer (skip Gold)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify the current state without making changes",
    )
    args = parser.parse_args()

    logger = LoggerFactory().create_logger("RepromoteCompanyPeers")

    bootstrap = DuckDbBootstrap(logger=logger)

    try:
        conn = bootstrap.connect()

        if args.verify_only:
            logger.info("=== VERIFICATION ONLY MODE ===")
            verify_fix(conn, logger)
            return

        if args.dry_run:
            logger.info("=== DRY RUN MODE - No changes will be made ===")

        # Step 1: Reset Gold layer (unless silver-only)
        if not args.silver_only:
            logger.info("Step 1: Resetting Gold layer for company-peers...")
            reset_company_peers_gold(conn, logger, args.dry_run)
        else:
            logger.info("Step 1: Skipping Gold reset (--silver-only)")

        # Step 2: Reset Silver layer
        logger.info("Step 2: Resetting Silver layer for company-peers...")
        affected_rows = reset_company_peers_silver(conn, logger, args.dry_run)

        if args.dry_run:
            logger.info("=== DRY RUN COMPLETE ===")
            logger.info(f"Would affect {affected_rows} Bronze files for re-promotion")
            return

        # Commit the reset changes
        conn.commit()
        logger.info("Reset changes committed to database")

        # Step 3: Run Silver promotion
        logger.info("Step 3: Running Silver promotion...")
        files_promoted, rows_promoted = run_silver_promotion(logger)

        if files_promoted == 0:
            logger.warning("No files were promoted to Silver. Check that Bronze files exist.")
            return

        # Step 4: Run Gold promotion (unless silver-only)
        if not args.silver_only:
            logger.info("Step 4: Running Gold promotion...")
            dims_inserted, dims_updated, facts_upserted = run_gold_promotion(logger)
        else:
            logger.info("Step 4: Skipping Gold promotion (--silver-only)")

        # Step 5: Verify the fix
        logger.info("Step 5: Verifying the fix...")
        conn = bootstrap.connect()  # Reconnect to see changes
        success = verify_fix(conn, logger)

        if success:
            logger.info("=== RE-PROMOTION COMPLETE AND VERIFIED ===")
        else:
            logger.error("=== RE-PROMOTION COMPLETE BUT VERIFICATION FAILED ===")

    except Exception as e:
        logger.error(f"Re-promotion failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        bootstrap.close()


if __name__ == "__main__":
    main()
