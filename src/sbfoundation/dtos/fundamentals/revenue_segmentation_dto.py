from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from typing import Any
import typing

import pandas as pd

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class RevenueSegmentationDTO(BronzeToSilverDTO):
    """
    DTO for FMP revenue segmentation data (product and geographic).

    The FMP API returns one record per period with a nested 'data' dict mapping
    segment names to revenue values. transform_df_content explodes this into one
    row per segment before schema projection.

    API docs:
    - Product: https://site.financialmodelingprep.com/developer/docs#revenue-product-segmentation
    - Geographic: https://site.financialmodelingprep.com/developer/docs#revenue-geographic-segementation
    """

    KEY_COLS = ["ticker", "date", "segment"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # period
    date: date_type | None = field(default=None, metadata={"api": "date"})

    # segmentation data — populated after exploding the 'data' dict in transform_df_content
    segment: str | None = field(default=None, metadata={"api": "segment"})
    revenue: float | None = field(default=None, metadata={"api": "revenue"})

    @property
    def key_date(self) -> date_type:
        return self.date or date_type.min

    @classmethod
    def transform_df_content(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Explode the nested 'data' dict into one row per segment.

        Each Bronze record looks like:
          {"data": {"Consumer Segment": 4870000000, ...}, "date": "2025-07-31", ...}

        After transform, each row contains flat 'segment' and 'revenue' columns.
        """
        if df.empty or "data" not in df.columns:
            return df
        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            data = row["data"]
            if not isinstance(data, dict):
                continue
            base = {k: v for k, v in row.items() if k != "data"}
            for segment_name, revenue_val in data.items():
                new_row = dict(base)
                new_row["segment"] = segment_name
                new_row["revenue"] = revenue_val
                rows.append(new_row)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "RevenueSegmentationDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
