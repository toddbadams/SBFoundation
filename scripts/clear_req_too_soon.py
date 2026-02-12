"""Remove bronze files and database rows for REQUEST IS TOO SOON errors.

This cleanup script removes legacy "REQUEST IS TOO SOON" artifacts that were
previously saved but are no longer generated after the behavior change.

Usage
-----
    # Dry run - show what would be deleted without making changes
    python scripts/clear_req_too_soon.py --dry-run

    # Actually delete the files and database rows
    python scripts/clear_req_too_soon.py

The script:
1. Queries ops.file_ingestions for rows with bronze_error = 'REQUEST IS TOO SOON'
2. Deletes the corresponding bronze files from the filesystem
3. Deletes the database rows from ops.file_ingestions
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_layer.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from data_layer.infra.logger import LoggerFactory
from folders import Folders


def find_too_soon_records(conn) -> list[dict]:
    """Find all file_ingestions records with REQUEST IS TOO SOON error."""
    sql = """
        SELECT run_id, file_id, domain, source, dataset, discriminator, ticker, bronze_filename
        FROM ops.file_ingestions
        WHERE bronze_error = 'REQUEST IS TOO SOON'
    """
    cursor = conn.execute(sql)
    cols = [desc[0] for desc in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def delete_bronze_file(record: dict, logger: logging.Logger, dry_run: bool) -> bool:
    """Delete the bronze file for a record.

    Returns:
        True if file was deleted (or would be in dry run), False if file not found
    """
    bronze_filename = record.get("bronze_filename")
    if not bronze_filename:
        logger.warning(f"  No bronze_filename for record: {record.get('file_id')}")
        return False

    # The filename in the database is relative, construct the absolute path
    data_root = Folders.data_absolute_path()
    file_path = data_root / bronze_filename

    if file_path.exists():
        logger.info(f"  {'[DRY RUN] ' if dry_run else ''}Deleting file: {file_path}")
        if not dry_run:
            file_path.unlink()
        return True
    else:
        logger.debug(f"  File not found (already deleted?): {file_path}")
        return False


def delete_database_records(conn, records: list[dict], logger: logging.Logger, dry_run: bool) -> int:
    """Delete the database records.

    Returns:
        Number of records deleted
    """
    if not records:
        return 0

    # Build the delete statement using run_id and file_id as the key
    sql = """
        DELETE FROM ops.file_ingestions
        WHERE bronze_error = 'REQUEST IS TOO SOON'
    """

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting {len(records)} database records")
    if not dry_run:
        result = conn.execute(sql)
        return result.rowcount if hasattr(result, "rowcount") else len(records)
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    logger = LoggerFactory().create_logger("ClearReqTooSoon")

    if args.dry_run:
        logger.info("=== DRY RUN MODE - No changes will be made ===")

    bootstrap = DuckDbBootstrap(logger=logger)

    try:
        with bootstrap.transaction() as conn:
            # Find all TOO SOON records
            records = find_too_soon_records(conn)
            logger.info(f"Found {len(records)} REQUEST IS TOO SOON records")

            if not records:
                logger.info("Nothing to clean up.")
                return

            # Delete bronze files
            files_deleted = 0
            files_not_found = 0
            for record in records:
                domain = record.get("domain", "?")
                source = record.get("source", "?")
                dataset = record.get("dataset", "?")
                ticker = record.get("ticker") or "global"
                logger.info(f"Processing: {domain}/{source}/{dataset} ticker={ticker}")

                if delete_bronze_file(record, logger, args.dry_run):
                    files_deleted += 1
                else:
                    files_not_found += 1

            # Delete database records
            rows_deleted = delete_database_records(conn, records, logger, args.dry_run)

            # Summary
            logger.info("=" * 50)
            logger.info(f"Summary:")
            logger.info(f"  Bronze files deleted: {files_deleted}")
            logger.info(f"  Bronze files not found: {files_not_found}")
            logger.info(f"  Database rows deleted: {rows_deleted}")

            if args.dry_run:
                logger.info("=== DRY RUN COMPLETE - Rolling back transaction ===")
                raise Exception("Dry run - rolling back")

    except Exception as e:
        if "Dry run" in str(e):
            pass  # Expected for dry run
        else:
            logger.error(f"Cleanup failed: {e}")
            raise
    finally:
        bootstrap.close()

    if not args.dry_run:
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    main()
