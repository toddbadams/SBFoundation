"""
Migration script: remove gold columns from ops.file_ingestions and drop the gold schema.

Run from the repo root:
    python scripts/remove_gold.py

The script is idempotent - safe to run more than once.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import duckdb

from sbfoundation.folders import Folders
from sbfoundation.settings import DUCKDB_FILENAME

GOLD_COLUMNS = [
    "gold_object_type",
    "gold_tablename",
    "gold_errors",
    "gold_rows_created",
    "gold_rows_updated",
    "gold_rows_failed",
    "gold_from_date",
    "gold_to_date",
    "gold_injest_start_time",
    "gold_injest_end_time",
    "gold_can_promote",
]


def run() -> None:
    db_path = Folders.duckdb_absolute_path() / DUCKDB_FILENAME
    print(f"Connecting to: {db_path}")

    if not db_path.exists():
        print("Database file not found - nothing to migrate.")
        return

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("BEGIN")

        # 1. Drop gold columns from ops.file_ingestions
        existing_cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'ops' AND table_name = 'file_ingestions'"
            ).fetchall()
        }
        dropped = []
        for col in GOLD_COLUMNS:
            if col in existing_cols:
                conn.execute(f"ALTER TABLE ops.file_ingestions DROP COLUMN {col}")
                dropped.append(col)
        if dropped:
            print(f"Dropped {len(dropped)} column(s) from ops.file_ingestions: {', '.join(dropped)}")
        else:
            print("No gold columns found in ops.file_ingestions (already clean).")

        # 2. Drop ops.gold_builds table if it exists
        gold_builds_exists = conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'ops' AND table_name = 'gold_builds'"
        ).fetchone()
        if gold_builds_exists and gold_builds_exists[0] > 0:
            conn.execute("DROP TABLE ops.gold_builds")
            print("Dropped table: ops.gold_builds")
        else:
            print("Table ops.gold_builds does not exist (already clean).")

        # 3. Drop gold schema (CASCADE drops any remaining tables)
        gold_schema_exists = conn.execute(
            "SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'gold'"
        ).fetchone()
        if gold_schema_exists and gold_schema_exists[0] > 0:
            conn.execute("DROP SCHEMA gold CASCADE")
            print("Dropped schema: gold (CASCADE)")
        else:
            print("Schema 'gold' does not exist (already clean).")

        conn.execute("COMMIT")
        print("Migration complete.")
    except Exception as exc:
        conn.execute("ROLLBACK")
        print(f"Migration failed (rolled back): {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
