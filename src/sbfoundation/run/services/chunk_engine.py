from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterator

import pandas as pd


@dataclass(frozen=True)
class Chunk:
    key: str
    df: pd.DataFrame


class ChunkEngine:
    def __init__(self, *, strategy: str) -> None:
        self._strategy = (strategy or "none").strip().lower()

    def chunk(self, df: pd.DataFrame, *, row_date_col: str) -> Iterator[Chunk]:
        if df.empty or self._strategy == "none":
            yield Chunk(key="all", df=df)
            return

        if row_date_col not in df.columns:
            yield Chunk(key="all", df=df)
            return

        dates = pd.to_datetime(df[row_date_col], errors="coerce")
        if self._strategy == "year":
            groups = dates.dt.year
        elif self._strategy == "month":
            groups = dates.dt.to_period("M").astype(str)
        else:
            yield Chunk(key="all", df=df)
            return

        for key, subset in df.groupby(groups, dropna=False):
            label = str(key) if key is not None else "unknown"
            yield Chunk(key=label, df=subset)
