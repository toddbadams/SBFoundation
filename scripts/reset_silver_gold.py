"""Reset Silver and Gold layer data for debugging.

This maintenance script removes data from the Silver and/or Gold layers,
allowing you to re-run the promotion pipelines from Bronze.

Usage
-----
    # Reset both Silver and Gold layers (full reset)
    python scripts/reset_silver_gold.py

    # Reset only Gold layer (keep Silver data)
    python scripts/reset_silver_gold.py --gold-only

    # Dry run - show what would be done without making changes
    python scripts/reset_silver_gold.py --dry-run

The script:
1. Drops all tables in the gold schema (and silver if not --gold-only)
2. Resets ops.file_ingestions metadata columns for the affected layers
3. Sets bronze_can_promote = TRUE to allow re-promotion
4. Clears ops.gold_builds lineage table
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


def get_schema_tables(conn, schema: str) -> list[str]:
    """Get all table names in a schema."""
    result = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = ?",
        [schema],
    ).fetchall()
    return [row[0] for row in result]


def reset_gold_layer(conn, logger: logging.Logger, dry_run: bool) -> int:
    """Drop all Gold layer tables and reset gold metadata.

    Returns:
        Number of tables dropped
    """
    tables = get_schema_tables(conn, "gold")
    logger.info(f"Found {len(tables)} tables in gold schema")

    for table in tables:
        sql = f'DROP TABLE IF EXISTS gold."{table}"'
        logger.info(f"  {'[DRY RUN] ' if dry_run else ''}Dropping gold.{table}")
        if not dry_run:
            conn.execute(sql)

    # Reset gold columns in file_ingestions
    reset_sql = """
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
            gold_can_promote = NULL,
            silver_can_promote = TRUE
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Resetting gold columns in ops.file_ingestions")
    if not dry_run:
        conn.execute(reset_sql)

    # Clear gold_builds table
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Clearing ops.gold_builds table")
    if not dry_run:
        conn.execute("DELETE FROM ops.gold_builds")

    return len(tables)


def reset_silver_layer(conn, logger: logging.Logger, dry_run: bool) -> int:
    """Drop all Silver layer tables and reset silver metadata.

    Returns:
        Number of tables dropped
    """
    tables = get_schema_tables(conn, "silver")
    logger.info(f"Found {len(tables)} tables in silver schema")

    for table in tables:
        sql = f'DROP TABLE IF EXISTS silver."{table}"'
        logger.info(f"  {'[DRY RUN] ' if dry_run else ''}Dropping silver.{table}")
        if not dry_run:
            conn.execute(sql)

    # Reset silver columns in file_ingestions and set bronze_can_promote = TRUE
    reset_sql = """
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
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Resetting silver columns in ops.file_ingestions")
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Setting bronze_can_promote = TRUE")
    if not dry_run:
        conn.execute(reset_sql)

    return len(tables)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--gold-only",
        action="store_true",
        help="Only reset Gold layer (keep Silver data intact)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    logger = LoggerFactory().create_logger("ResetSilverGold")

    if args.dry_run:
        logger.info("=== DRY RUN MODE - No changes will be made ===")

    bootstrap = DuckDbBootstrap(logger=logger)

    try:
        with bootstrap.transaction() as conn:
            if args.gold_only:
                logger.info("Resetting Gold layer only...")
                gold_count = reset_gold_layer(conn, logger, args.dry_run)
                logger.info(f"Gold layer reset complete. {gold_count} tables dropped.")
            else:
                logger.info("Resetting both Silver and Gold layers...")
                # Reset Gold first (depends on Silver)
                gold_count = reset_gold_layer(conn, logger, args.dry_run)
                silver_count = reset_silver_layer(conn, logger, args.dry_run)
                logger.info(
                    f"Full reset complete. Gold: {gold_count} tables, Silver: {silver_count} tables dropped."
                )

            if args.dry_run:
                logger.info("=== DRY RUN COMPLETE - Rolling back transaction ===")
                raise Exception("Dry run - rolling back")

    except Exception as e:
        if "Dry run" in str(e):
            pass  # Expected for dry run
        else:
            logger.error(f"Reset failed: {e}")
            raise
    finally:
        bootstrap.close()

    if not args.dry_run:
        logger.info("Database is ready for Silver/Gold re-promotion from Bronze.")


if __name__ == "__main__":
    main()
