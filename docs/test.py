#!/usr/bin/env python3
import argparse
import os
import pathlib
import shutil
import stat
import sys

# === CONFIGURATION ===
TICKERS = [
    "BBY",
    "BF-B",
    "BKNG",
    "BRO",
    "CB",
    "CHD",
    "CL",
    "CME",
    "CNQ",
    "CRM",
    "D",
    "EBF",
    "EMN",
    "ENB",
    "EPD",
    "ERIE",
    "EVRG",
    "FICO",
    "FTNT",
    "GOOG",
    "HRL",
    "HWM",
    "IDXX",
    "INTU",
    "JNJ",
    "KMB",
    "KMI",
    "KO",
    "KVUE",
    "LRCX",
    "LYB",
    "MAIN",
    "MELI",
    "META",
    "MGA",
    "MKC",
    "MSFT",
    "NEE",
    "NFLX",
    "NICE",
    "NNN",
    "NOW",
    "NVDA",
    "NVO",
    "O",
    "PAYC",
    "PBA",
    "PEP",
    "PG",
    "PRU",
    "PSA",
    "REXR",
    "RMD",
    "ROL",
    "SJM",
    "SNPS",
    "SPOT",
    "SYY",
    "T",
    "V",
    "VZ",
    "WASH",
    "WPC",
    "WST",
    "XOM",
]

TABLES = [
    "BALANCE_SHEET",
    "CASH_FLOW",
    "DIVIDENDS",
    "EARNINGS",
    "INCOME_STATEMENT",
    "INSIDER_TRANSACTIONS",
    "OVERVIEW",
    "TIME_SERIES_MONTHLY_ADJUSTED",
]

DEFAULT_ROOT = pathlib.Path(r"C:\Users\toddb\OneDrive\Projects\development\sb\SBFoundation\data\acquisition")


def _make_writable(path: pathlib.Path):
    """
    Recursively clear read-only flags so shutil.rmtree can delete on Windows.
    """
    try:
        if path.is_dir():
            for root, dirs, files in os.walk(path):
                for name in dirs + files:
                    full = pathlib.Path(root) / name
                    try:
                        os.chmod(full, stat.S_IWRITE)
                    except Exception:
                        pass  # best effort
        else:
            os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass  # best effort


def remove_partition(table_dir: pathlib.Path, ticker: str, dry_run: bool):
    """
    Removes the partition folder named symbol={ticker} inside the table directory.
    """
    partition_name = f"symbol={ticker}"
    target = table_dir / partition_name
    if target.exists():
        if dry_run:
            print(f"[DRY RUN] Would remove: {target}")
            return
        try:
            # attempt to clear read-only flags first
            _make_writable(target)
            shutil.rmtree(target)
            print(f"Removed: {target}")
        except PermissionError as e:
            print(f"[ERROR] Permission denied when removing {target}: {e}")
            print("  -> Try closing any processes using it, run the script as administrator, or manually adjust folder permissions.")
        except Exception as e:
            print(f"[ERROR] Failed to remove {target}: {e}")
    else:
        print(f"(none) No partition found for {ticker} in table {table_dir.name}")


def main():
    parser = argparse.ArgumentParser(description="Remove symbol={ticker} partitions from each table folder.")
    parser.add_argument("--tickers", "-t", nargs="*", default=TICKERS, help="Subset of tickers to process (default: all)")
    parser.add_argument("--tables", "-b", nargs="*", default=TABLES, help="Subset of tables to process (default: all)")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually delete instead of dry run")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt when executing")
    parser.add_argument(
        "--root", "-r", type=pathlib.Path, default=DEFAULT_ROOT, help=f"Root directory containing table folders (default: {DEFAULT_ROOT})"
    )
    args = parser.parse_args()

    to_tickers = args.tickers
    to_tables = args.tables
    dry_run = False  # not args.execute

    print(f"Root: {args.root.resolve()}")
    print(f"Tables: {to_tables}")
    print(f"Tickers: {to_tickers}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")

    if args.execute and not args.yes:
        resp = input("Are you sure you want to delete matching partitions? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    for table in to_tables:
        table_dir = args.root / table
        if not table_dir.exists() or not table_dir.is_dir():
            print(f"Skipping missing table directory: {table_dir}")
            continue
        for ticker in to_tickers:
            remove_partition(table_dir, ticker, dry_run=dry_run)


if __name__ == "__main__":
    main()
