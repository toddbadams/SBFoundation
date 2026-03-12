from __future__ import annotations

import datetime
import html as _html_mod
import pathlib
from typing import TYPE_CHECKING, Any

import duckdb

from sbfoundation.folders import Folders
from sbfoundation.maintenance import DuckDbBootstrap

if TYPE_CHECKING:
    from sbfoundation.api import RunCommand


# ── Icons ─────────────────────────────────────────────────────────────────────
_PASS = "✅"
_FAIL = "❌"

_MAX_TICKER_LIST = 50  # max tickers to display inline before truncating

# ── Domain → service label ────────────────────────────────────────────────────
_DOMAIN_SERVICE_LABEL: dict[str, str] = {
    "eod": "EOD",
    "quarter": "Quarter",
    "annual": "Annual",
    "month": "Month",
}

# ── Theme CSS (copied from geopolitical-portfolio-monitor/src/theme.css) ──────
_THEME_CSS = """\
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');
:root {
  --bg-base:      #080c14; --bg-surface:   #0d1117; --bg-elevated:  #161b22; --bg-overlay:   #1a2332;
  --border-subtle: #1a2332; --border-muted:  #21262d; --border-base:   #30363d;
  --text-primary:   #f0f6fc; --text-secondary: #c9d1d9; --text-muted:     #8b949e;
  --text-faint:     #6e7681; --text-dim:       #484f58; --text-ghost:     #30363d;
  --accent:       #58a6ff; --accent-light: #79c0ff;
  --sev-critical-bg:#3a0000; --sev-critical-border:#ef233c; --sev-critical-text:#ef233c;
  --sev-high-bg:#2a1000; --sev-high-border:#e76f51; --sev-high-text:#e76f51;
  --sev-medium-bg:#2a2000; --sev-medium-border:#e9c46a; --sev-medium-text:#e9c46a;
  --sev-low-bg:#0a2e1a; --sev-low-border:#2d6a4f; --sev-low-text:#95d5b2;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
  --radius-sm: 4px; --radius-md: 6px; --radius-lg: 8px; --radius-xl: 12px;
}
*, *::before, *::after { box-sizing: border-box; }
html, body { height: 100%; margin: 0; padding: 0; }
body {
  background: var(--bg-base); color: var(--text-secondary);
  font-family: var(--font-mono); font-size: 13px; line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
code { color: var(--accent); font-family: var(--font-mono); }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-surface); }
::-webkit-scrollbar-thumb { background: var(--border-base); border-radius: 3px; }
"""

# ── Report-specific CSS ────────────────────────────────────────────────────────
_REPORT_CSS = """\
.report-body { max-width: 1500px; margin: 0 auto; padding: 28px 36px 60px; }

.report-header {
  display: flex; align-items: baseline; justify-content: space-between;
  border-bottom: 1px solid var(--border-base); padding-bottom: 14px; margin-bottom: 28px;
}
.report-title { font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0; }
.report-meta  { font-size: 11px; color: var(--text-muted); }

h2 {
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px;
  color: var(--accent); margin: 32px 0 10px;
  border-bottom: 1px solid var(--border-muted); padding-bottom: 5px;
}
h3 {
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;
  color: var(--text-muted); margin: 22px 0 8px;
}

hr.section-divider {
  border: none; border-top: 1px solid var(--border-muted); margin: 36px 0;
}

/* ── Data table ── */
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 4px; }
.data-table th {
  background: var(--bg-elevated); color: var(--text-muted);
  text-align: left; padding: 6px 12px;
  border-bottom: 1px solid var(--border-base);
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;
  white-space: nowrap;
}
.data-table th.num { text-align: right; }
.data-table th.ctr { text-align: center; }
.data-table td {
  padding: 5px 12px; border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}
.data-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.data-table td.ctr { text-align: center; }
.data-table tbody tr:hover td { background: var(--bg-elevated); }
.data-table tr.total-row td {
  background: var(--bg-overlay); color: var(--text-primary);
  font-weight: 700; border-top: 1px solid var(--border-base);
  border-bottom: none;
}

/* ── Run command props table ── */
.props-table { border-collapse: collapse; font-size: 12px; margin-bottom: 4px; }
.props-table td { padding: 4px 16px 4px 0; vertical-align: top; }
.props-table td.prop-key {
  color: var(--text-muted); white-space: nowrap; min-width: 200px;
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px;
}
.props-table td.prop-val { color: var(--text-primary); }

/* ── Status / pass-fail ── */
.pass { color: var(--sev-low-text); }
.fail { color: var(--sev-critical-text); }

/* ── Badges ── */
.service-badge {
  display: inline-block; background: var(--bg-overlay);
  color: var(--accent-light); padding: 2px 10px;
  border-radius: var(--radius-sm); border: 1px solid var(--border-base);
  font-size: 11px;
}
.run-id { color: var(--accent); }

/* ── Error block ── */
.error-cell { color: var(--sev-high-text); max-width: 480px; }

/* ── Empty / info messages ── */
.empty-msg { color: var(--text-faint); font-style: italic; font-size: 12px; padding: 6px 0 10px; }

/* ── Ticker list ── */
.ticker-list { color: var(--text-secondary); font-size: 11px; line-height: 1.8; }
.ticker-list code { font-size: 11px; }
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _n(value: Any) -> int:
    """Coerce None / falsy to 0."""
    return int(value) if value else 0


def _fmt(n: int) -> str:
    return f"{n:,}"


def _fmt_date(d: Any) -> str:
    return str(d) if d else "—"


def _pct(n: int, total: int) -> str:
    return f"{n / total * 100:.0f}%" if total > 0 else "—"


def _esc(s: Any) -> str:
    """HTML-escape a value for safe embedding."""
    return _html_mod.escape(str(s)) if s is not None else ""


def _parse_gold_row_counts(s: str | None) -> int:
    """Sum all values in a row_counts string like "{'dim_instrument': 100, 'fact_eod': 5000}"."""
    if not s:
        return 0
    try:
        import ast
        d = ast.literal_eval(s)
        if isinstance(d, dict):
            return sum(int(v) for v in d.values() if isinstance(v, (int, float)))
    except Exception:
        pass
    return 0


def _pass_icon(condition: bool) -> str:
    cls = "pass" if condition else "fail"
    icon = _PASS if condition else _FAIL
    return f'<span class="{cls}">{icon}</span>'


def _th(text: str, align: str = "l") -> str:
    cls = ' class="num"' if align == "r" else (' class="ctr"' if align == "c" else "")
    return f"<th{cls}>{_esc(text)}</th>"


def _td(content: str, align: str = "l", extra_class: str = "") -> str:
    """Build a <td>. `content` is treated as already-safe HTML."""
    cls_parts = []
    if align == "r":
        cls_parts.append("num")
    elif align == "c":
        cls_parts.append("ctr")
    if extra_class:
        cls_parts.append(extra_class)
    cls = f' class="{" ".join(cls_parts)}"' if cls_parts else ""
    return f"<td{cls}>{content}</td>"


def _html_table(
    headers: list[str],
    rows: list[list[str]],
    alignments: list[str] | None = None,
    has_total_row: bool = False,
) -> str:
    """Build an HTML <table>. Cell values are raw HTML (caller must escape user data)."""
    if alignments is None:
        alignments = ["l"] * len(headers)
    head = "<thead><tr>" + "".join(_th(h, a) for h, a in zip(headers, alignments)) + "</tr></thead>"
    body_parts: list[str] = []
    for i, row in enumerate(rows):
        is_total = has_total_row and i == len(rows) - 1
        cls = ' class="total-row"' if is_total else ""
        cells = "".join(_td(str(c), a) for c, a in zip(row, alignments))
        body_parts.append(f"<tr{cls}>{cells}</tr>")
    return f'<table class="data-table">{head}<tbody>{"".join(body_parts)}</tbody></table>'


class RunStatsReporter:
    """Generates per-run and all-runs HTML statistics reports from ops.file_ingestions.

    Writes a persistent report file to the logs folder: {run_id}_report.html.
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

    def write_report(
        self,
        run_id: str,
        universe_tickers: list[str] | None = None,
        run_command: RunCommand | None = None,
    ) -> pathlib.Path:
        """Assemble all report sections into a self-contained HTML file and write it to the logs folder."""
        generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        with self._bootstrap.read_connection() as conn:
            domain_rows = self._query_domain_summary(conn, run_id)
            dataset_rows = self._query_dataset_breakdown(conn, run_id)
            silver_rows = self._query_silver_promotion(conn, run_id)
            gold_promo_rows = self._query_gold_promotion(conn, run_id)
            bronze_errors = self._query_bronze_errors(conn, run_id)
            silver_errors = self._query_silver_errors(conn, run_id)
            run_history = self._query_run_history(conn)
            silver_sizes = self._query_silver_table_sizes(conn)
            gold_sizes = self._query_gold_table_sizes(conn)
            gold_rows_per_run = self._query_gold_rows_per_run(conn)

        body_parts: list[str] = []

        # Run Command section (before Bronze Ingestion)
        if run_command is not None:
            body_parts.append(self._format_run_command(run_command))
            body_parts.append('<hr class="section-divider">')

        body_parts.append(
            self._format_current_run(
                run_id, domain_rows, dataset_rows, silver_rows, gold_promo_rows,
                bronze_errors, silver_errors,
            )
        )
        body_parts.append('<hr class="section-divider">')
        body_parts.append(self._format_history(run_history, silver_sizes, gold_sizes, gold_rows_per_run))

        if universe_tickers:
            with self._bootstrap.read_connection() as conn:
                presence_rows = self._query_universe_presence(conn, universe_tickers)
                dataset_cov_rows = self._query_universe_dataset_coverage(conn, universe_tickers)
            body_parts.append('<hr class="section-divider">')
            body_parts.append(self._format_universe_coverage(universe_tickers, presence_rows, dataset_cov_rows))

        doc = self._build_html_doc(run_id, generated_at, "\n".join(body_parts))

        logs_dir = Folders.logs_absolute_path()
        logs_dir.mkdir(parents=True, exist_ok=True)
        report_path = logs_dir / f"{run_id}_report.html"
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
            "SUM(COALESCE(bronze_rows, 0)) AS rows_ingested, "
            "SUM(COALESCE(silver_rows_created, 0) + COALESCE(silver_rows_updated, 0)) AS silver_rows "
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
            "SUM(COALESCE(bronze_rows, 0)) AS rows_ingested, "
            "SUM(COALESCE(silver_rows_created, 0) + COALESCE(silver_rows_updated, 0)) AS silver_rows "
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

    def _query_gold_promotion(
        self, conn: duckdb.DuckDBPyConnection, run_id: str
    ) -> list[dict[str, Any]]:
        try:
            sql = (
                "SELECT gold_build_id, model_version, started_at, finished_at, "
                "status, tables_built, row_counts, error_message "
                "FROM ops.gold_build "
                "WHERE run_id = ? "
                "ORDER BY gold_build_id"
            )
            cursor = conn.execute(sql, [run_id])
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception:
            return []

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
            "SUM(COALESCE(silver_rows_created, 0)) AS silver_rows_created, "
            "SUM(COALESCE(silver_rows_created, 0) + COALESCE(silver_rows_updated, 0)) AS silver_rows_total "
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
        try:
            cursor = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'silver' ORDER BY table_name"
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

    def _query_gold_table_sizes(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[tuple[str, int]]:
        try:
            cursor = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'gold' ORDER BY table_name"
            )
            table_names = [row[0] for row in cursor.fetchall()]
        except Exception:
            return []
        results: list[tuple[str, int]] = []
        for name in table_names:
            try:
                row = conn.execute(f'SELECT COUNT(*) FROM gold."{name}"').fetchone()
                results.append((name, _n(row[0]) if row else 0))
            except Exception:
                results.append((name, 0))
        return results

    def _query_gold_rows_per_run(
        self, conn: duckdb.DuckDBPyConnection
    ) -> dict[str, int]:
        """Return {run_id: total_gold_rows} by summing all values in ops.gold_build.row_counts."""
        try:
            cursor = conn.execute("SELECT run_id, row_counts FROM ops.gold_build")
            result: dict[str, int] = {}
            for run_id, row_counts_str in cursor.fetchall():
                result[run_id] = result.get(run_id, 0) + _parse_gold_row_counts(row_counts_str)
            return result
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Query helpers — universe coverage
    # ------------------------------------------------------------------

    def _query_universe_presence(
        self, conn: duckdb.DuckDBPyConnection, universe_tickers: list[str]
    ) -> list[dict[str, Any]]:
        sql = """
            WITH universe AS (SELECT unnest(?) AS ticker),
            bronze_tickers AS (
                SELECT DISTINCT ticker FROM ops.file_ingestions
                WHERE bronze_error IS NULL AND bronze_rows > 0
                  AND ticker IS NOT NULL AND ticker <> ''
            ),
            silver_tickers AS (
                SELECT DISTINCT ticker FROM ops.file_ingestions
                WHERE silver_rows_created > 0 AND ticker IS NOT NULL AND ticker <> ''
            )
            SELECT u.ticker,
                   (bt.ticker IS NOT NULL) AS in_bronze,
                   (st.ticker IS NOT NULL) AS in_silver
            FROM universe u
            LEFT JOIN bronze_tickers bt ON bt.ticker = u.ticker
            LEFT JOIN silver_tickers  st ON st.ticker = u.ticker
            ORDER BY u.ticker
        """
        cursor = conn.execute(sql, [universe_tickers])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _query_universe_dataset_coverage(
        self, conn: duckdb.DuckDBPyConnection, universe_tickers: list[str]
    ) -> list[dict[str, Any]]:
        sql = """
            WITH universe AS (SELECT unnest(?) AS ticker),
            per_ticker_datasets AS (
                SELECT DISTINCT domain, dataset, COALESCE(discriminator, '') AS discriminator
                FROM ops.file_ingestions
                WHERE silver_rows_created > 0 AND ticker IS NOT NULL AND ticker <> ''
            )
            SELECT ptd.domain, ptd.dataset, ptd.discriminator,
                   COUNT(DISTINCT u.ticker) AS universe_count,
                   COUNT(DISTINCT CASE WHEN fi.silver_rows_created > 0 THEN u.ticker END) AS tickers_with_silver,
                   MIN(CASE WHEN fi.silver_rows_created > 0 THEN fi.silver_from_date END) AS earliest_date,
                   MAX(CASE WHEN fi.silver_rows_created > 0 THEN fi.silver_to_date  END) AS latest_date
            FROM per_ticker_datasets ptd
            CROSS JOIN universe u
            LEFT JOIN ops.file_ingestions fi
                ON fi.ticker = u.ticker AND fi.dataset = ptd.dataset
               AND COALESCE(fi.discriminator, '') = ptd.discriminator
               AND fi.silver_rows_created > 0
            GROUP BY ptd.domain, ptd.dataset, ptd.discriminator
            ORDER BY ptd.domain, ptd.dataset, ptd.discriminator
        """
        cursor = conn.execute(sql, [universe_tickers])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # HTML document builder
    # ------------------------------------------------------------------

    def _build_html_doc(self, run_id: str, generated_at: str, body_html: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SBFoundation Run Report — {_esc(run_id)}</title>
<style>
{_THEME_CSS}
{_REPORT_CSS}
</style>
</head>
<body>
<div class="report-body">

<div class="report-header">
  <h1 class="report-title">SBFoundation Run Report</h1>
  <div class="report-meta">
    <span class="run-id">{_esc(run_id)}</span>
    &nbsp;·&nbsp; {_esc(generated_at)}
  </div>
</div>

{body_html}

</div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    def _format_run_command(self, cmd: RunCommand) -> str:
        service_label = _DOMAIN_SERVICE_LABEL.get(cmd.domain, _esc(cmd.domain).upper())
        parts: list[str] = [
            f'<h2>Run Command &nbsp;<span class="service-badge">{_esc(service_label)} Service</span></h2>'
        ]
        props: list[tuple[str, str]] = [
            ("domain", _esc(cmd.domain)),
            ("service", f'<span class="service-badge">{_esc(service_label)}</span>'),
            ("concurrent_requests", _esc(str(cmd.concurrent_requests))),
            ("enable_bronze", _esc(str(cmd.enable_bronze))),
            ("enable_silver", _esc(str(cmd.enable_silver))),
            ("enable_gold", _esc(str(cmd.enable_gold))),
            ("ticker_limit", _esc(str(cmd.ticker_limit)) if cmd.ticker_limit else "—"),
            ("ticker_recipe_chunk_size", _esc(str(cmd.ticker_recipe_chunk_size)) if cmd.ticker_recipe_chunk_size else "—"),
            ("force_from_date", _esc(cmd.force_from_date) if cmd.force_from_date else "—"),
            ("year", _esc(str(cmd.year)) if cmd.year is not None else "—"),
            ("eod_date", _esc(cmd.eod_date) if cmd.eod_date else "—"),
            ("quarter_year", _esc(str(cmd.quarter_year)) if cmd.quarter_year is not None else "—"),
            ("quarter_period", _esc(cmd.quarter_period) if cmd.quarter_period else "—"),
        ]
        rows_html = "".join(
            f'<tr><td class="prop-key">{k}</td><td class="prop-val">{v}</td></tr>'
            for k, v in props
        )
        parts.append(f'<table class="props-table"><tbody>{rows_html}</tbody></table>')
        return "\n".join(parts)

    def _format_current_run(
        self,
        run_id: str,
        domain_rows: list[dict[str, Any]],
        dataset_rows: list[dict[str, Any]],
        silver_rows: list[dict[str, Any]],
        gold_promo_rows: list[dict[str, Any]],
        bronze_errors: list[dict[str, Any]],
        silver_errors: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = []

        # ── Bronze Ingestion ──
        parts.append(f'<h2>Bronze Ingestion — <code>{_esc(run_id)}</code></h2>')
        if domain_rows:
            total_files   = sum(_n(r["files_total"])   for r in domain_rows)
            total_passed  = sum(_n(r["files_passed"])  for r in domain_rows)
            total_failed  = sum(_n(r["files_failed"])  for r in domain_rows)
            total_bronze  = sum(_n(r["rows_ingested"]) for r in domain_rows)
            total_silver  = sum(_n(r["silver_rows"])   for r in domain_rows)
            table_rows: list[list[str]] = []
            for r in domain_rows:
                b_rows = _n(r["rows_ingested"])
                s_rows = _n(r["silver_rows"])
                ok = _n(r["files_failed"]) == 0 and b_rows == s_rows
                table_rows.append([
                    _esc(r["domain"]),
                    _fmt(_n(r["files_total"])),
                    _fmt(_n(r["files_passed"])),
                    _fmt(_n(r["files_failed"])),
                    _fmt(b_rows),
                    _fmt(s_rows),
                    _pass_icon(ok),
                ])
            table_rows.append([
                "<strong>Total</strong>",
                f"<strong>{_fmt(total_files)}</strong>",
                f"<strong>{_fmt(total_passed)}</strong>",
                f"<strong>{_fmt(total_failed)}</strong>",
                f"<strong>{_fmt(total_bronze)}</strong>",
                f"<strong>{_fmt(total_silver)}</strong>",
                _pass_icon(total_failed == 0 and total_bronze == total_silver),
            ])
            parts.append(_html_table(
                ["Domain", "Files", "Passed", "Failed", "Bronze Rows", "Silver Rows", "Pass"],
                table_rows,
                ["l", "r", "r", "r", "r", "r", "c"],
                has_total_row=True,
            ))
        else:
            parts.append('<p class="empty-msg">No bronze files for this run.</p>')

        # ── By Dataset ──
        parts.append("<h3>By Dataset</h3>")
        if dataset_rows:
            table_rows = []
            for r in dataset_rows:
                b_rows = _n(r["rows_ingested"])
                s_rows = _n(r["silver_rows"])
                ok = _n(r["files_failed"]) == 0 and b_rows == s_rows
                table_rows.append([
                    _esc(r["domain"]),
                    _esc(r["dataset"]),
                    _fmt(_n(r["files_total"])),
                    _fmt(_n(r["files_passed"])),
                    _fmt(_n(r["files_failed"])),
                    _fmt(b_rows),
                    _fmt(s_rows),
                    _pass_icon(ok),
                ])
            parts.append(_html_table(
                ["Domain", "Dataset", "Files", "Passed", "Failed", "Bronze Rows", "Silver Rows", "Pass"],
                table_rows,
                ["l", "l", "r", "r", "r", "r", "r", "c"],
            ))
        else:
            parts.append('<p class="empty-msg">No dataset data for this run.</p>')

        # ── Silver Promotion ──
        parts.append("<h2>Silver Promotion</h2>")
        if silver_rows:
            table_rows = []
            for r in silver_rows:
                ok = _n(r["rows_failed"]) == 0
                table_rows.append([
                    _esc(r["silver_tablename"]),
                    _fmt(_n(r["rows_created"])),
                    _fmt(_n(r["rows_updated"])),
                    _fmt(_n(r["rows_failed"])),
                    _esc(_fmt_date(r["coverage_from"])),
                    _esc(_fmt_date(r["coverage_to"])),
                    _pass_icon(ok),
                ])
            parts.append(_html_table(
                ["Table", "Created", "Updated", "Failed", "Coverage From", "Coverage To", "Pass"],
                table_rows,
                ["l", "r", "r", "r", "l", "l", "c"],
            ))
        else:
            parts.append('<p class="empty-msg">No Silver promotion in this run.</p>')

        # ── Gold Promotion ──
        parts.append("<h2>Gold Promotion</h2>")
        if gold_promo_rows:
            table_rows = []
            for r in gold_promo_rows:
                tables = r.get("tables_built")
                tables_str = ", ".join(tables) if isinstance(tables, list) else (str(tables) if tables else "—")
                status = r.get("status") or "—"
                ok = status == "complete" and not r.get("error_message")
                started = str(r["started_at"])[:19] if r.get("started_at") else "—"
                finished = str(r["finished_at"])[:19] if r.get("finished_at") else "—"
                err = r.get("error_message") or ""
                err_html = f'<span class="error-cell">{_esc(err[:120])}{"…" if len(err) > 120 else ""}</span>' if err else "—"
                table_rows.append([
                    _esc(str(r.get("gold_build_id", "—"))),
                    f'<code>{_esc(str(r.get("model_version", "—"))[:12])}</code>',
                    _esc(started),
                    _esc(finished),
                    _esc(status),
                    _esc(tables_str),
                    err_html,
                    _pass_icon(ok),
                ])
            parts.append(_html_table(
                ["Build ID", "Model Ver", "Started", "Finished", "Status", "Tables Built", "Error", "Pass"],
                table_rows,
                ["r", "l", "l", "l", "l", "l", "l", "c"],
            ))
        else:
            parts.append('<p class="empty-msg">No Gold promotion in this run.</p>')

        # ── Errors ──
        total_bronze_errors = sum(_n(r["files_failed"]) for r in domain_rows)
        total_silver_errors = len(silver_errors)

        parts.append("<h2>Errors</h2>")
        if total_bronze_errors == 0 and total_silver_errors == 0:
            parts.append('<p class="empty-msg">No errors.</p>')
        else:
            if bronze_errors:
                parts.append(f"<h3>Bronze Errors ({_fmt(total_bronze_errors)})</h3>")
                err_rows = [
                    [
                        _esc(r["domain"]),
                        _esc(r["dataset"]),
                        _esc(r["ticker"]),
                        f'<span class="error-cell">{_esc(str(r["bronze_error"])[:200])}</span>',
                    ]
                    for r in bronze_errors
                ]
                parts.append(_html_table(
                    ["Domain", "Dataset", "Ticker", "Error"],
                    err_rows,
                    ["l", "l", "l", "l"],
                ))
                if total_bronze_errors > 20:
                    parts.append(f'<p class="empty-msg">… {_fmt(total_bronze_errors - 20)} more bronze errors not shown.</p>')

            if silver_errors:
                parts.append(f"<h3>Silver Errors ({_fmt(total_silver_errors)})</h3>")
                err_rows = [
                    [
                        _esc(r["domain"]),
                        _esc(r["dataset"]),
                        _esc(r["ticker"]),
                        f'<span class="error-cell">{_esc(str(r["silver_errors"])[:200])}</span>',
                    ]
                    for r in silver_errors
                ]
                parts.append(_html_table(
                    ["Domain", "Dataset", "Ticker", "Error"],
                    err_rows,
                    ["l", "l", "l", "l"],
                ))

        return "\n".join(parts)

    def _format_history(
        self,
        run_rows: list[dict[str, Any]],
        silver_sizes: list[tuple[str, int]],
        gold_sizes: list[tuple[str, int]],
        gold_rows_per_run: dict[str, int] | None = None,
    ) -> str:
        parts: list[str] = []
        gold_rows_per_run = gold_rows_per_run or {}

        # ── Run History ──
        n_runs = len(run_rows)
        parts.append(f"<h2>Run History — {_fmt(n_runs)} total</h2>")
        if run_rows:
            table_rows: list[list[str]] = []
            for r in run_rows:
                bronze  = _n(r["rows_ingested"])
                silver  = _n(r["silver_rows_created"])
                gold    = gold_rows_per_run.get(r["run_id"], 0)
                failed  = _n(r["files_failed"])
                ok = silver == bronze and gold >= silver
                table_rows.append([
                    f'<code class="run-id">{_esc(r["run_id"])}</code>',
                    _esc(str(r["started_at"])[:19] if r["started_at"] else "—"),
                    _fmt(_n(r["files_total"])),
                    _fmt(_n(r["files_passed"])),
                    _fmt(failed),
                    _fmt(bronze),
                    _fmt(silver),
                    _fmt(gold),
                    _pass_icon(ok),
                ])
            parts.append(_html_table(
                ["Run ID", "Started At", "Files", "Passed", "Failed", "Bronze Rows", "Silver Created", "Gold Created", "Pass"],
                table_rows,
                ["l", "l", "r", "r", "r", "r", "r", "r", "c"],
            ))
        else:
            parts.append('<p class="empty-msg">No runs recorded yet.</p>')

        # ── Accumulated Silver Table Sizes ──
        parts.append("<h2>Accumulated Silver Table Sizes</h2>")
        if silver_sizes:
            total_silver = sum(count for _, count in silver_sizes)
            size_rows = [[_esc(name), _fmt(count)] for name, count in silver_sizes]
            size_rows.append(["<strong>Total</strong>", f"<strong>{_fmt(total_silver)}</strong>"])
            parts.append(_html_table(["Table", "Total Rows"], size_rows, ["l", "r"], has_total_row=True))
        else:
            parts.append('<p class="empty-msg">No Silver tables found.</p>')

        # ── Accumulated Gold Table Sizes ──
        parts.append("<h2>Accumulated Gold Table Sizes</h2>")
        if gold_sizes:
            total_gold = sum(count for _, count in gold_sizes)
            size_rows = [[_esc(name), _fmt(count)] for name, count in gold_sizes]
            size_rows.append(["<strong>Total</strong>", f"<strong>{_fmt(total_gold)}</strong>"])
            parts.append(_html_table(["Table", "Total Rows"], size_rows, ["l", "r"], has_total_row=True))
        else:
            parts.append('<p class="empty-msg">No Gold tables found.</p>')

        return "\n".join(parts)

    def _format_universe_coverage(
        self,
        universe_tickers: list[str],
        presence_rows: list[dict[str, Any]],
        dataset_rows: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = ["<h2>Universe Coverage</h2>"]

        n_universe    = len(universe_tickers)
        n_bronze      = sum(1 for r in presence_rows if r["in_bronze"])
        n_silver      = sum(1 for r in presence_rows if r["in_silver"])
        n_bronze_only = sum(1 for r in presence_rows if r["in_bronze"] and not r["in_silver"])
        n_not_ingested = sum(1 for r in presence_rows if not r["in_bronze"])

        parts.append(_html_table(
            ["", "Tickers", "% of Universe"],
            [
                ["Universe", _fmt(n_universe), "100%"],
                ["In bronze (≥1 successful ingest)", _fmt(n_bronze), _pct(n_bronze, n_universe)],
                ["In silver (≥1 promoted row)", _fmt(n_silver), _pct(n_silver, n_universe)],
                ["In bronze only (not yet in silver)", _fmt(n_bronze_only), _pct(n_bronze_only, n_universe)],
                ["Not yet ingested", _fmt(n_not_ingested), _pct(n_not_ingested, n_universe)],
            ],
            ["l", "r", "r"],
        ))

        not_ingested = sorted(r["ticker"] for r in presence_rows if not r["in_bronze"])
        if not_ingested:
            parts.append(f"<h3>Not Yet Ingested — {_fmt(len(not_ingested))} tickers</h3>")
            shown = not_ingested[:_MAX_TICKER_LIST]
            ticker_html = ", ".join(f"<code>{_esc(t)}</code>" for t in shown)
            if len(not_ingested) > _MAX_TICKER_LIST:
                ticker_html += f' <em class="empty-msg">… and {_fmt(len(not_ingested) - _MAX_TICKER_LIST)} more not shown.</em>'
            parts.append(f'<p class="ticker-list">{ticker_html}</p>')

        bronze_only = sorted(r["ticker"] for r in presence_rows if r["in_bronze"] and not r["in_silver"])
        if bronze_only:
            parts.append(f"<h3>In Bronze Only — {_fmt(len(bronze_only))} tickers</h3>")
            shown = bronze_only[:_MAX_TICKER_LIST]
            ticker_html = ", ".join(f"<code>{_esc(t)}</code>" for t in shown)
            if len(bronze_only) > _MAX_TICKER_LIST:
                ticker_html += f' <em class="empty-msg">… and {_fmt(len(bronze_only) - _MAX_TICKER_LIST)} more not shown.</em>'
            parts.append(f'<p class="ticker-list">{ticker_html}</p>')

        if dataset_rows:
            parts.append("<h3>Coverage by Dataset</h3>")
            table_rows: list[list[str]] = []
            for r in dataset_rows:
                disc  = r["discriminator"] or ""
                label = _esc(r["dataset"] + (f"/{disc}" if disc else ""))
                n_have = _n(r["tickers_with_silver"])
                n_univ = _n(r["universe_count"])
                n_miss = n_univ - n_have
                table_rows.append([
                    _esc(r["domain"]),
                    label,
                    _fmt(n_have),
                    _fmt(n_miss),
                    _pct(n_miss, n_univ),
                    _esc(_fmt_date(r["earliest_date"])),
                    _esc(_fmt_date(r["latest_date"])),
                ])
            parts.append(_html_table(
                ["Domain", "Dataset", "Have Data", "Missing", "Miss %", "Earliest", "Latest"],
                table_rows,
                ["l", "l", "r", "r", "r", "l", "l"],
            ))
        elif n_universe > 0:
            parts.append('<p class="empty-msg">No per-ticker silver data found for any universe ticker.</p>')

        return "\n".join(parts)
