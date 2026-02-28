from __future__ import annotations

import argparse
import sys
from typing import Any

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo


# ---------------------------------------------------------------------------
# Table formatting (stdlib only — no tabulate dependency)
# ---------------------------------------------------------------------------


def _print_table(headers: list[str], rows: list[list[str]], *, title: str = "") -> None:
    if title:
        print(f"\n{title}")

    if not rows:
        print("  (no results)")
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    sep = "  ".join("-" * w for w in widths)
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print(sep)
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    print(f"\n{len(rows)} row(s)")


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_summary(repo: DuckDbOpsRepo, _args: argparse.Namespace) -> int:
    rows = repo.get_coverage_summary()
    table = [
        [r["domain"], r["dataset"], str(r["tickers_covered"]), _fmt_pct(r["avg_coverage_ratio"]), _fmt_pct(r["avg_error_rate"])]
        for r in rows
    ]
    _print_table(
        ["domain", "dataset", "tickers", "avg_coverage", "avg_error_rate"],
        table,
        title="Dataset Coverage Summary (weakest first)",
    )
    return 0


def _cmd_dataset(repo: DuckDbOpsRepo, args: argparse.Namespace) -> int:
    rows = repo.get_coverage_by_dataset(args.name)
    if not rows:
        print(f"No coverage data for dataset '{args.name}'.")
        return 1
    table = [
        [r["ticker"], _fmt(r["min_date"]), _fmt(r["max_date"]), _fmt_pct(r["coverage_ratio"]), str(r["error_count"]), _fmt(r["last_ingested_at"])]
        for r in rows
    ]
    _print_table(
        ["ticker", "min_date", "max_date", "coverage", "errors", "last_ingested"],
        table,
        title=f"Coverage for dataset: {args.name}",
    )
    return 0


def _cmd_ticker(repo: DuckDbOpsRepo, args: argparse.Namespace) -> int:
    rows = repo.get_coverage_by_ticker(args.symbol)
    if not rows:
        print(f"No coverage data for ticker '{args.symbol}'.")
        return 1
    table = [
        [r["dataset"], "timeseries" if r["is_timeseries"] else "snapshot", _fmt_pct(r["coverage_ratio"]), _fmt(r["last_ingested_at"]), _fmt(r["age_days"])]
        for r in rows
    ]
    _print_table(
        ["dataset", "type", "coverage", "last_ingested", "age_days"],
        table,
        title=f"Coverage for ticker: {args.symbol}",
    )
    return 0


def _cmd_stale(repo: DuckDbOpsRepo, args: argparse.Namespace) -> int:
    rows = repo.get_stale_snapshots(args.days)
    if not rows:
        print(f"No stale snapshots found (threshold: {args.days} days).")
        return 0
    table = [
        [r["dataset"], r["ticker"], _fmt(r["last_snapshot_date"]), str(r["age_days"])]
        for r in rows
    ]
    _print_table(
        ["dataset", "ticker", "last_snapshot", "age_days"],
        table,
        title=f"Stale snapshots (age >= {args.days} days)",
    )
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sbfoundation.coverage",
        description="Query the ops.coverage_index data coverage control plane.",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    sub.add_parser("summary", help="All datasets aggregated, sorted by weakest coverage first.")

    p_dataset = sub.add_parser("dataset", help="All tickers for one dataset.")
    p_dataset.add_argument("name", help="Dataset name (e.g. price-eod)")

    p_ticker = sub.add_parser("ticker", help="All datasets for one ticker.")
    p_ticker.add_argument("symbol", help="Ticker symbol (e.g. AAPL)")

    p_stale = sub.add_parser("stale", help="Snapshot datasets not refreshed recently.")
    p_stale.add_argument("--days", type=int, default=90, help="Minimum age in days (default: 90)")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


_HANDLERS = {
    "summary": _cmd_summary,
    "dataset": _cmd_dataset,
    "ticker": _cmd_ticker,
    "stale": _cmd_stale,
}


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    bootstrap = DuckDbBootstrap()
    try:
        repo = DuckDbOpsRepo(bootstrap=bootstrap)
        handler = _HANDLERS[args.command]
        rc = handler(repo, args)
    finally:
        bootstrap.close()

    sys.exit(rc)
