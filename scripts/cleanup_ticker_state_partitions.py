"""Remove existing ``TICKER_STATE`` partition folders.

This maintenance script is useful when the schema of ``TICKER_STATE``
changes.  Removing old partitions avoids mixing files with incompatible
schemas when the table is rewritten.

Usage
-----
    python cleanup_ticker_state_partitions.py /path/to/data/root

The ``data_root`` should be the same directory configured for
``ParquetStorageRepository``.  The script removes the entire
``control/TICKER_STATE`` directory if it exists.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def cleanup(data_root: str) -> None:
    root = Path(data_root) / "control" / "TICKER_STATE"
    if not root.exists():
        return
    shutil.rmtree(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_root", help="Root directory used for parquet data")
    args = parser.parse_args()
    cleanup(args.data_root)


if __name__ == "__main__":
    main()
