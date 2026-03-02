"""
UniverseDefinition — full eligibility-filter spec for FMP Company Screener.

Each UniverseDefinition describes a named set of instruments eligible for
ingestion into SBFoundation. Fields map directly to FMP Company Screener
query parameters; None values are omitted from the request.

Usage:
    from sbuniverse.universe_definition import UniverseDefinition

    ud = UniverseDefinition(
        name="us_large_cap",
        country="US",
        exchanges=["NYSE", "NASDAQ"],
        market_cap_more_than=10_000_000_000,
        is_actively_trading=True,
        is_etf=False,
        is_fund=False,
    )
    params = ud.to_screener_params()   # {"country": "US", "marketCapMoreThan": 10000000000, ...}
    h = ud.filter_hash()               # stable SHA-256 for snapshot versioning
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UniverseDefinition:
    """Ingestion-scoped universe definition.

    All filter fields are optional (None = no filter applied for that param).
    Fields map directly to FMP Company Screener query parameters.

    Eligibility fields (control whether a stock can ever be ingested):
        country, exchanges, is_etf, is_fund, is_actively_trading,
        include_all_share_classes, price_more_than, price_lower_than,
        volume_more_than, volume_lower_than

    Market-cap bounds:
        market_cap_more_than, market_cap_lower_than

    Beta / dividend / sector / industry:
        beta_more_than, beta_lower_than, dividend_more_than, dividend_lower_than,
        sector, industry

    limit:
        Maximum rows returned per exchange call. Default 1000 (FMP cap).
    """

    # --- Identity ---
    name: str
    description: str = ""

    # --- Geography & listing ---
    country: str | None = None
    exchanges: list[str] = field(default_factory=list)
    is_etf: bool | None = None
    is_fund: bool | None = None
    is_actively_trading: bool | None = True
    include_all_share_classes: bool | None = None

    # --- Market cap (USD) ---
    market_cap_more_than: float | None = None
    market_cap_lower_than: float | None = None

    # --- Price ---
    price_more_than: float | None = None
    price_lower_than: float | None = None

    # --- Volume ---
    volume_more_than: float | None = None
    volume_lower_than: float | None = None

    # --- Beta ---
    beta_more_than: float | None = None
    beta_lower_than: float | None = None

    # --- Dividend ---
    dividend_more_than: float | None = None
    dividend_lower_than: float | None = None

    # --- Sector / industry ---
    sector: str | None = None
    industry: str | None = None

    # --- Request limit per exchange call ---
    limit: int = 1000

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def to_screener_params(self) -> dict[str, Any]:
        """Return FMP Company Screener query params for this definition.

        Exchange is intentionally excluded — callers loop over self.exchanges
        and pass exchange individually to stay under the FMP 1000-row cap.
        Non-None fields only.
        """
        mapping: dict[str, Any] = {
            "country": self.country,
            "marketCapMoreThan": self.market_cap_more_than,
            "marketCapLowerThan": self.market_cap_lower_than,
            "sector": self.sector,
            "industry": self.industry,
            "betaMoreThan": self.beta_more_than,
            "betaLowerThan": self.beta_lower_than,
            "priceMoreThan": self.price_more_than,
            "priceLowerThan": self.price_lower_than,
            "dividendMoreThan": self.dividend_more_than,
            "dividendLowerThan": self.dividend_lower_than,
            "volumeMoreThan": self.volume_more_than,
            "volumeLowerThan": self.volume_lower_than,
            "isEtf": self.is_etf,
            "isFund": self.is_fund,
            "isActivelyTrading": self.is_actively_trading,
            "includeAllShareClasses": self.include_all_share_classes,
            "limit": self.limit,
        }
        return {k: v for k, v in mapping.items() if v is not None}

    def filter_hash(self) -> str:
        """Return a stable SHA-256 hex digest of this definition's filter params.

        Computed from the canonical JSON of to_screener_params() plus the
        sorted exchanges list. Used to version universe snapshots.
        """
        payload = {
            "params": self.to_screener_params(),
            "exchanges": sorted(self.exchanges),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    # -------------------------------------------------------------------------
    # Backward-compat aliases (match old UniverseDefinition attribute names)
    # -------------------------------------------------------------------------

    @property
    def min_market_cap_usd(self) -> float | None:
        return self.market_cap_more_than

    @property
    def max_market_cap_usd(self) -> float | None:
        return self.market_cap_lower_than


__all__ = ["UniverseDefinition"]
