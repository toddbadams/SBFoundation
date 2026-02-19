"""Simple migration runner script to apply SQL migrations to DuckDB.

Usage:
    python scripts/run_migration.py db/migrations/20260217_001_fix_pe_column_types.sql
"""
import sys
from pathlib import Path

import duckdb

from sbfoundation.folders import Folders
from sbfoundation.settings import DUCKDB_FILENAME


def run_migration(migration_file: str) -> None:
    """Run a SQL migration file against the DuckDB database.

    Args:
        migration_file: Path to the SQL migration file
    """
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)

    # Read migration SQL
    with open(migration_path, "r", encoding="utf-8") as f:
        migration_sql = f.read()

    # Connect to database
    duckdb_path = Folders.duckdb_absolute_path() / DUCKDB_FILENAME
    if not duckdb_path.exists():
        print(f"ERROR: Database not found at: {duckdb_path}")
        sys.exit(1)

    print(f"Connecting to database: {duckdb_path}")
    conn = duckdb.connect(str(duckdb_path))

    try:
        print(f"Running migration: {migration_path.name}")
        conn.execute("BEGIN")
        conn.execute(migration_sql)
        conn.execute("COMMIT")
        print("Migration completed successfully")

        # Verify the changes for the pe column migration
        if "fix_pe_column_types" in migration_path.name:
            print("\nVerifying changes:")
            for table in ["fmp_market_sector_pe", "fmp_market_industry_pe"]:
                result = conn.execute(f"SELECT column_name, column_type FROM (DESCRIBE silver.{table}) WHERE column_name = 'pe'").fetchone()
                if result:
                    print(f"  {table}.pe: {result[1]}")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"ERROR: Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_migration.py <migration_file.sql>")
        sys.exit(1)

    run_migration(sys.argv[1])
