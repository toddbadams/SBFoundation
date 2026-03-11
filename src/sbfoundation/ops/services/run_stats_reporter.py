from __future__ import annotations

import datetime
import pathlib
from contextlib import contextmanager
from typing import Any, Iterator

import duckdb

from sbfoundation.folders import Folders
from sbfoundation.maintenance import DuckDbBootstrap


def _n(value: Any) -> int:
    """Coerce None / falsy to 0."""
    return int(value) if value else 0


def _fmt(n: int) -> str:
    """Format integer with thousands separator."""
    return f"{n:,}"


def _fmt_date(d: Any) -> str:
    return str(d) if d else "—"


def _pct(n: int, total: int) -> str:
    """Format n/total as a percentage string."""
    return f"{n / total * 100:.0f}%" if total > 0 else "—"


def _md_table(headers: list[str], rows: list[list[str]], alignments: list[str] | None = None) -> str:
    """Build a Markdown table string.

    alignments: list of 'l', 'r', or 'c' per column (default all left).
    """
    if alignments is None:
        alignments = ["l"] * len(headers)

    sep_map = {"l": ":---", "r": "---:", "c": ":---:"}

    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(sep_map.get(a, ":---") for a in alignments) + " |"
    data_rows = ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join([header_row, sep_row] + data_rows)


_MAX_TICKER_LIST = 50  # max tickers to display inline before truncating


class RunStatsReporter:
    """Generates per-run and all-runs Markdown statistics reports from ops.file_ingestions.

    Writes a persistent report file to the logs folder: {run_id}_report.md.
    """

    def __init__(self, bootstrap: DuckDbBootstrap | None = None) -> None:
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def report(self, run_id: str) -> str:
        """Return a Markdown string with Bronze + Silver stats for one run_id."""
        with self._bootstrap.read_connection() as conn:
            domain_rows = self._query_domain_summary(conn, run_id)
            dataset_rows = self._query_dataset_breakdown(conn, run_id)
            silver_rows = self._query_silver_promotion(conn, run_id)
            bronze_errors = self._query_bronze_errors(conn, run_id)
            silver_errors = self._query_silver_errors(conn, run_id)

        return self._format_current_run(
            run_id, domain_rows, dataset_rows, silver_rows, bronze_errors, silver_errors
        )

    def history_report(self) -> str:
        """Return a Markdown string with per-run summaries and accumulated Silver table sizes."""
        with self._bootstrap.read_connection() as conn:
            run_rows = self._query_run_history(conn)
            silver_sizes = self._query_silver_table_sizes(conn)

        return self._format_history(run_rows, silver_sizes)

    def universe_coverage_report(self, universe_tickers: list[str]) -> str:
        """Return a Markdown string comparing universe tickers to bronze/silver coverage.

        For each ticker in universe_tickers, shows whether it has been ingested into
        bronze and promoted to silver.  Also breaks down coverage by dataset so missing
        data can be identified at a glance.

        Args:
            universe_tickers: The canonical ticker list for the strategy universe
                              (e.g. the output of UniverseService.get_filtered_tickers()).
        """
        if not universe_tickers:
            return "## Universe Coverage\n\n*No universe tickers provided.*"

        with self._bootstrap.read_connection() as conn:
            presence_rows = self._query_universe_presence(conn, universe_tickers)
            dataset_rows = self._query_universe_dataset_coverage(conn, universe_tickers)

        return self._format_universe_coverage(universe_tickers, presence_rows, dataset_rows)

    def write_report(
        self,
        run_id: str,
        universe_tickers: list[str] | None = None,
    ) -> pathlib.Path:
        """Assemble report sections into a Markdown file and write it to the logs folder.

        Args:
            run_id: The run whose bronze/silver stats are reported.
            universe_tickers: When provided, a Universe Coverage section is appended
                              that compares this ticker list against the accumulated
                              bronze/silver data warehouse.
        """
        current = self.report(run_id)
        history = self.history_report()

        generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        doc = (
            "# SBFoundation Run Report\n\n"
            f"**run\\_id**: `{run_id}`  \n"
            f"**Generated**: {generated_at}\n\n"
            "---\n\n"
            f"{current}\n\n"
            "---\n\n"
            f"{history}\n"
        )

        if universe_tickers:
            coverage = self.universe_coverage_report(universe_tickers)
            doc += f"\n---\n\n{coverage}\n"

        logs_dir = Folders.logs_absolute_path()
        logs_dir.mkdir(parents=True, exist_ok=True)
        report_path = logs_dir / f"{run_id}_report.md"
        report_path.write_text(doc, encoding="utf-8")
        return report_path

    # ------------------------------------------------------------------
    # Query helpers — current-run
    # ------------------------------------------------------------------

    def _query_domain_summary(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT domain, "
            "COUNT(*) AS files_total, "
            "SUM(CASE WHEN bronze_error IS NULL THEN 1 ELSE 0 END) AS files_passed, "
            "SUM(CASE WHEN bronze_error IS NOT NULL THEN 1 ELSE 0 END) AS files_failed, "
            "SUM(COALESCE(bronze_rows, 0)) AS rows_ingested "
            "FROM ops.file_ingestions "
            "WHERE run_id = ? "
            "GROUP BY domain "
            "ORDER BY domain"
        )
        cursor = conn.execute(sql, [run_id])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_dataset_breakdown(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT domain, dataset, "
            "COUNT(*) AS files_total, "
            "SUM(CASE WHEN bronze_error IS NULL THEN 1 ELSE 0 END) AS files_passed, "
            "SUM(CASE WHEN bronze_error IS NOT NULL THEN 1 ELSE 0 END) AS files_failed, "
            "SUM(COALESCE(bronze_rows, 0)) AS rows_ingested "
            "FROM ops.file_ingestions "
            "WHERE run_id = ? "
            "GROUP BY domain, dataset "
            "ORDER BY domain, dataset"
        )
        cursor = conn.execute(sql, [run_id])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_silver_promotion(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT silver_tablename, "
            "SUM(COALESCE(silver_rows_created, 0)) AS rows_created, "
            "SUM(COALESCE(silver_rows_updated, 0)) AS rows_updated, "
            "SUM(COALESCE(silver_rows_failed, 0))  AS rows_failed, "
            "MIN(silver_from_date) AS coverage_from, "
            "MAX(silver_to_date)   AS coverage_to "
            "FROM ops.file_ingestions "
            "WHERE run_id = ? AND silver_tablename IS NOT NULL "
            "GROUP BY silver_tablename "
            "ORDER BY silver_tablename"
        )
        cursor = conn.execute(sql, [run_id])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_bronze_errors(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT domain, dataset, COALESCE(ticker, '—') AS ticker, bronze_error "
            "FROM ops.file_ingestions "
            "WHERE run_id = ? AND bronze_error IS NOT NULL "
            "ORDER BY domain, dataset, ticker "
            "LIMIT 20"
        )
        cursor = conn.execute(sql, [run_id])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_bronze_error_count(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> int:
        row = conn.execute(
            "SELECT COUNT(*) FROM ops.file_ingestions WHERE run_id = ? AND bronze_error IS NOT NULL",
            [run_id],
        ).fetchone()
        return _n(row[0]) if row else 0

    def _query_silver_errors(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT domain, dataset, COALESCE(ticker, '—') AS ticker, silver_errors "
            "FROM ops.file_ingestions "
            "WHERE run_id = ? AND silver_errors IS NOT NULL "
            "ORDER BY domain, dataset, ticker "
            "LIMIT 20"
        )
        cursor = conn.execute(sql, [run_id])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Query helpers — history
    # ------------------------------------------------------------------

    def _query_run_history(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT run_id, "
            "MIN(bronze_injest_start_time) AS started_at, "
            "COUNT(DISTINCT file_id) AS files_total, "
            "SUM(CASE WHEN bronze_error IS NULL THEN 1 ELSE 0 END) AS files_passed, "
            "SUM(CASE WHEN bronze_error IS NOT NULL THEN 1 ELSE 0 END) AS files_failed, "
            "SUM(COALESCE(bronze_rows, 0)) AS rows_ingested, "
            "SUM(COALESCE(silver_rows_created, 0)) AS silver_rows_created "
            "FROM ops.file_ingestions "
            "GROUP BY run_id "
            "ORDER BY started_at DESC"
        )
        cursor = conn.execute(sql)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_silver_table_sizes(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[tuple[str, int]]:
        """Return (table_name, row_count) for every table in the silver schema."""
        try:
            cursor = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'silver' "
                "ORDER BY table_name"
            )
            table_names = [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

        results: list[tuple[str, int]] = []
        for name in table_names:
            try:
                row = conn.execute(f'SELECT COUNT(*) FROM silver."{name}"').fetchone()
                results.append((name, _n(row[0]) if row else 0))
            except Exception:
                results.append((name, 0))
        return results

    # ------------------------------------------------------------------
    # Query helpers — universe coverage
    # ------------------------------------------------------------------

    def _query_universe_presence(
        self, conn: duckdb.DuckDBPyConnection, universe_tickers: list[str]
    ) -> list[dict[str, Any]]:
        """For each universe ticker return whether it appears in bronze and/or silver.

        in_bronze = at least one successful (no error, >0 rows) bronze ingestion.
        in_silver = at least one file_ingestion with silver_rows_created > 0.
        """
        sql = """
            WITH universe AS (SELECT unnest(?) AS ticker),
            bronze_tickers AS (
                SELECT DISTINCT ticker
                FROM ops.file_ingestions
                WHERE bronze_error IS NULL
                  AND bronze_rows > 0
                  AND ticker IS NOT NULL AND ticker <> ''
            ),
            silver_tickers AS (
                SELECT DISTINCT ticker
                FROM ops.file_ingestions
                WHERE silver_rows_created > 0
                  AND ticker IS NOT NULL AND ticker <> ''
            )
            SELECT
                u.ticker,
                (bt.ticker IS NOT NULL) AS in_bronze,
                (st.ticker IS NOT NULL) AS in_silver
            FROM universe u
            LEFT JOIN bronze_tickers bt ON bt.ticker = u.ticker
            LEFT JOIN silver_tickers st ON st.ticker = u.ticker
            ORDER BY u.ticker
        """
        cursor = conn.execute(sql, [universe_tickers])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_universe_dataset_coverage(
        self, conn: duckdb.DuckDBPyConnection, universe_tickers: list[str]
    ) -> list[dict[str, Any]]:
        """Per per-ticker dataset: how many universe tickers have silver data, and date range.

        Only datasets that have at least one silver row for any ticker are included
        (global/non-ticker datasets are excluded because their ticker column is NULL/empty).
        """
        sql = """
            WITH universe AS (SELECT unnest(?) AS ticker),
            per_ticker_datasets AS (
                SELECT DISTINCT domain, dataset, COALESCE(discriminator, '') AS discriminator
                FROM ops.file_ingestions
                WHERE silver_rows_created > 0
                  AND ticker IS NOT NULL AND ticker <> ''
            )
            SELECT
                ptd.domain,
                ptd.dataset,
                ptd.discriminator,
                COUNT(DISTINCT u.ticker) AS universe_count,
                COUNT(DISTINCT CASE WHEN fi.silver_rows_created > 0 THEN u.ticker END)
                    AS tickers_with_silver,
                MIN(CASE WHEN fi.silver_rows_created > 0 THEN fi.silver_from_date END)
                    AS earliest_date,
                MAX(CASE WHEN fi.silver_rows_created > 0 THEN fi.silver_to_date END)
                    AS latest_date
            FROM per_ticker_datasets ptd
            CROSS JOIN universe u
            LEFT JOIN ops.file_ingestions fi
                ON fi.ticker = u.ticker
                AND fi.dataset = ptd.dataset
                AND COALESCE(fi.discriminator, '') = ptd.discriminator
                AND fi.silver_rows_created > 0
            GROUP BY ptd.domain, ptd.dataset, ptd.discriminator
            ORDER BY ptd.domain, ptd.dataset, ptd.discriminator
        """
        cursor = conn.execute(sql, [universe_tickers])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    def _format_current_run(
        self,
        run_id: str,
        domain_rows: list[dict[str, Any]],
        dataset_rows: list[dict[str, Any]],
        silver_rows: list[dict[str, Any]],
        bronze_errors: list[dict[str, Any]],
        silver_errors: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = []

        # --- Bronze domain summary ---
        parts.append(f"## Bronze Ingestion — `{run_id}`\n")
        if domain_rows:
            total_files = sum(_n(r["files_total"]) for r in domain_rows)
            total_passed = sum(_n(r["files_passed"]) for r in domain_rows)
            total_failed = sum(_n(r["files_failed"]) for r in domain_rows)
            total_rows = sum(_n(r["rows_ingested"]) for r in domain_rows)
            parts.append(
                _md_table(
                    ["Domain", "Files", "Passed", "Failed", "Bronze Rows"],
                    [
                        [
                            r["domain"],
                            _fmt(_n(r["files_total"])),
                            _fmt(_n(r["files_passed"])),
                            _fmt(_n(r["files_failed"])),
                            _fmt(_n(r["rows_ingested"])),
                        ]
                        for r in domain_rows
                    ]
                    + [
                        [
                            "**Total**",
                            f"**{_fmt(total_files)}**",
                            f"**{_fmt(total_passed)}**",
                            f"**{_fmt(total_failed)}**",
                            f"**{_fmt(total_rows)}**",
                        ]
                    ],
                    ["l", "r", "r", "r", "r"],
                )
            )
        else:
            parts.append("*No bronze files for this run.*")

        # --- Dataset breakdown ---
        parts.append("\n### By Dataset\n")
        if dataset_rows:
            parts.append(
                _md_table(
                    ["Domain", "Dataset", "Files", "Passed", "Failed", "Bronze Rows"],
                    [
                        [
                            r["domain"],
                            r["dataset"],
                            _fmt(_n(r["files_total"])),
                            _fmt(_n(r["files_passed"])),
                            _fmt(_n(r["files_failed"])),
                            _fmt(_n(r["rows_ingested"])),
                        ]
                        for r in dataset_rows
                    ],
                    ["l", "l", "r", "r", "r", "r"],
                )
            )
        else:
            parts.append("*No dataset data for this run.*")

        # --- Silver promotion ---
        parts.append("\n## Silver Promotion\n")
        if silver_rows:
            parts.append(
                _md_table(
                    ["Table", "Created", "Updated", "Failed", "Coverage From", "Coverage To"],
                    [
                        [
                            r["silver_tablename"],
                            _fmt(_n(r["rows_created"])),
                            _fmt(_n(r["rows_updated"])),
                            _fmt(_n(r["rows_failed"])),
                            _fmt_date(r["coverage_from"]),
                            _fmt_date(r["coverage_to"]),
                        ]
                        for r in silver_rows
                    ],
                    ["l", "r", "r", "r", "l", "l"],
                )
            )
        else:
            parts.append("*No Silver promotion in this run.*")

        # --- Errors ---
        parts.append("\n## Errors\n")

        total_bronze_errors = sum(_n(r["files_failed"]) for r in domain_rows)
        total_silver_errors = len(silver_errors)

        if total_bronze_errors == 0 and total_silver_errors == 0:
            parts.append("*No errors.*")
        else:
            if bronze_errors:
                parts.append(f"### Bronze Errors ({_fmt(total_bronze_errors)})\n")
                parts.append(
                    _md_table(
                        ["Domain", "Dataset", "Ticker", "Error"],
                        [
                            [r["domain"], r["dataset"], r["ticker"], r["bronze_error"]]
                            for r in bronze_errors
                        ],
                        ["l", "l", "l", "l"],
                    )
                )
                if total_bronze_errors > 20:
                    parts.append(
                        f"\n*… {_fmt(total_bronze_errors - 20)} more bronze errors not shown.*"
                    )

            if silver_errors:
                parts.append(f"\n### Silver Errors ({_fmt(total_silver_errors)})\n")
                parts.append(
                    _md_table(
                        ["Domain", "Dataset", "Ticker", "Error"],
                        [
                            [r["domain"], r["dataset"], r["ticker"], r["silver_errors"]]
                            for r in silver_errors
                        ],
                        ["l", "l", "l", "l"],
                    )
                )

        return "\n".join(parts)

    def _format_history(
        self,
        run_rows: list[dict[str, Any]],
        silver_sizes: list[tuple[str, int]],
    ) -> str:
        parts: list[str] = []

        # --- Run history table ---
        n_runs = len(run_rows)
        parts.append(f"## Run History — {_fmt(n_runs)} total\n")
        if run_rows:
            parts.append(
                _md_table(
                    ["Run ID", "Started At", "Files", "Passed", "Failed", "Bronze Rows", "Silver Rows"],
                    [
                        [
                            f"`{r['run_id']}`",
                            str(r["started_at"])[:19] if r["started_at"] else "—",
                            _fmt(_n(r["files_total"])),
                            _fmt(_n(r["files_passed"])),
                            _fmt(_n(r["files_failed"])),
                            _fmt(_n(r["rows_ingested"])),
                            _fmt(_n(r["silver_rows_created"])),
                        ]
                        for r in run_rows
                    ],
                    ["l", "l", "r", "r", "r", "r", "r"],
                )
            )
        else:
            parts.append("*No runs recorded yet.*")

        # --- Accumulated Silver table sizes ---
        parts.append("\n## Accumulated Silver Table Sizes\n")
        if silver_sizes:
            total_silver = sum(count for _, count in silver_sizes)
            parts.append(
                _md_table(
                    ["Table", "Total Rows"],
                    [[name, _fmt(count)] for name, count in silver_sizes]
                    + [["**Total**", f"**{_fmt(total_silver)}**"]],
                    ["l", "r"],
                )
            )
        else:
            parts.append("*No Silver tables found.*")

        return "\n".join(parts)

    def _format_universe_coverage(
        self,
        universe_tickers: list[str],
        presence_rows: list[dict[str, Any]],
        dataset_rows: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = ["## Universe Coverage\n"]

        n_universe = len(universe_tickers)
        n_bronze = sum(1 for r in presence_rows if r["in_bronze"])
        n_silver = sum(1 for r in presence_rows if r["in_silver"])
        n_bronze_only = sum(1 for r in presence_rows if r["in_bronze"] and not r["in_silver"])
        n_not_ingested = sum(1 for r in presence_rows if not r["in_bronze"])

        # --- Presence summary table ---
        parts.append(
            _md_table(
                ["", "Tickers", "% of Universe"],
                [
                    ["Universe", _fmt(n_universe), "100%"],
                    [
                        "In bronze (≥1 successful ingest)",
                        _fmt(n_bronze),
                        _pct(n_bronze, n_universe),
                    ],
                    [
                        "In silver (≥1 promoted row)",
                        _fmt(n_silver),
                        _pct(n_silver, n_universe),
                    ],
                    [
                        "In bronze only (not yet in silver)",
                        _fmt(n_bronze_only),
                        _pct(n_bronze_only, n_universe),
                    ],
                    [
                        "Not yet ingested",
                        _fmt(n_not_ingested),
                        _pct(n_not_ingested, n_universe),
                    ],
                ],
                ["l", "r", "r"],
            )
        )

        # --- Not-yet-ingested ticker list ---
        not_ingested = sorted(r["ticker"] for r in presence_rows if not r["in_bronze"])
        if not_ingested:
            parts.append(f"\n### Not Yet Ingested — {_fmt(len(not_ingested))} tickers\n")
            shown = not_ingested[:_MAX_TICKER_LIST]
            parts.append(", ".join(f"`{t}`" for t in shown))
            if len(not_ingested) > _MAX_TICKER_LIST:
                parts.append(
                    f"\n\n*… and {_fmt(len(not_ingested) - _MAX_TICKER_LIST)} more not shown.*"
                )

        # --- Bronze-only ticker list (pending silver or empty content) ---
        bronze_only = sorted(
            r["ticker"] for r in presence_rows if r["in_bronze"] and not r["in_silver"]
        )
        if bronze_only:
            parts.append(
                f"\n\n### In Bronze Only — {_fmt(len(bronze_only))} tickers\n"
            )
            shown = bronze_only[:_MAX_TICKER_LIST]
            parts.append(", ".join(f"`{t}`" for t in shown))
            if len(bronze_only) > _MAX_TICKER_LIST:
                parts.append(
                    f"\n\n*… and {_fmt(len(bronze_only) - _MAX_TICKER_LIST)} more not shown.*"
                )

        # --- Per-dataset coverage table ---
        if dataset_rows:
            parts.append("\n\n### Coverage by Dataset\n")
            table_rows = []
            for r in dataset_rows:
                disc = r["discriminator"] or ""
                label = r["dataset"] + (f"/{disc}" if disc else "")
                n_have = _n(r["tickers_with_silver"])
                n_univ = _n(r["universe_count"])
                n_miss = n_univ - n_have
                table_rows.append(
                    [
                        r["domain"],
                        label,
                        _fmt(n_have),
                        _fmt(n_miss),
                        _pct(n_miss, n_univ),
                        _fmt_date(r["earliest_date"]),
                        _fmt_date(r["latest_date"]),
                    ]
                )
            parts.append(
                _md_table(
                    ["Domain", "Dataset", "Have Data", "Missing", "Miss %", "Earliest", "Latest"],
                    table_rows,
                    ["l", "l", "r", "r", "r", "l", "l"],
                )
            )
        elif n_universe > 0:
            parts.append(
                "\n\n*No per-ticker silver data found for any universe ticker.*"
            )

        return "\n".join(parts)
