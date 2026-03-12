"""CLI entry point: python -m sbfoundation.integrity

Prints a summary of integrity events for recent runs.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from sbfoundation.maintenance import DuckDbBootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description="SBFoundation data integrity report")
    parser.add_argument("--run-id", help="Filter to a specific run_id")
    parser.add_argument("--days", type=int, default=7, help="Show runs from last N days (default: 7)")
    parser.add_argument("--failed-only", action="store_true", help="Show only failed records")
    args = parser.parse_args()

    bootstrap = DuckDbBootstrap()
    try:
        with bootstrap.read_connection() as conn:
            # Check table exists
            exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'ops' AND table_name = 'run_integrity'"
            ).fetchone()
            if not exists or exists[0] == 0:
                print("ops.run_integrity table does not exist — run maintenance first.")
                return

            since = (datetime.utcnow() - timedelta(days=args.days)).isoformat()
            where_clauses = [f"checked_at >= '{since}'"]
            if args.run_id:
                where_clauses.append(f"run_id = '{args.run_id}'")
            if args.failed_only:
                where_clauses.append("status = 'failed'")
            where = " AND ".join(where_clauses)

            rows = conn.execute(f"""
                SELECT run_id, layer, domain, dataset, status,
                       SUM(COALESCE(rows_in, 0)) AS rows_in,
                       SUM(COALESCE(rows_out, 0)) AS rows_out,
                       COUNT(*) AS files,
                       MAX(checked_at) AS last_checked
                FROM ops.run_integrity
                WHERE {where}
                GROUP BY run_id, layer, domain, dataset, status
                ORDER BY last_checked DESC, run_id, layer, dataset
            """).fetchall()

            if not rows:
                print(f"No integrity records found in last {args.days} days.")
                return

            headers = ["run_id", "layer", "domain", "dataset", "status", "rows_in", "rows_out", "files", "last_checked"]
            widths = [max(len(str(row[i])) for row in rows + [tuple(headers)]) for i in range(len(headers))]
            fmt = "  ".join(f"{{:<{w}}}" for w in widths)
            print(fmt.format(*headers))
            print("  ".join("-" * w for w in widths))
            for row in rows:
                print(fmt.format(*[str(v) for v in row]))
    finally:
        bootstrap.close()


if __name__ == "__main__":
    main()
