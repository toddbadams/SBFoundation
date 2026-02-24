"""
Universe definitions for SBFoundation ingestion scoping.

Each UniverseDefinition captures the ingestion-relevant properties of a named
instrument universe: which exchanges to include, which country, and the
market-cap bounds that gate inclusion.

Strategy-level properties (rebalance_months, min_instruments_per_sector) are
intentionally excluded here — they live in the downstream SBIntelligence
project which extends this definition.

Usage in RunCommand:
    from sbfoundation.universe_definitions import US_LARGE_CAP

    api.run(RunCommand(
        domain="fundamentals",
        enable_bronze=True,
        enable_silver=True,
        concurrent_requests=10,
        universe_definition=US_LARGE_CAP,
    ))
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UniverseDefinition:
    """Ingestion-scoped universe definition.

    Attributes:
        name: Stable identifier used in logging and UNIVERSE_REGISTRY keys.
        country: ISO country code (e.g. "US").
        exchanges: Exchange short names to include (e.g. ["NYSE", "NASDAQ"]).
        min_market_cap_usd: Minimum market capitalisation in USD (inclusive).
        max_market_cap_usd: Maximum market capitalisation in USD (inclusive).
                            None means no upper bound.
    """

    name: str
    country: str
    exchanges: list[str]
    min_market_cap_usd: float
    max_market_cap_usd: float | None


# ── Universe definitions (mirrors SBIntelligence §0.1) ───────────────────────

US_LARGE_MID_CAP = UniverseDefinition(
    name="us_large_mid_cap",
    country="US",
    exchanges=["NYSE", "NASDAQ"],
    min_market_cap_usd=2_000_000_000,   # $2B+
    max_market_cap_usd=None,
)

US_LARGE_CAP = UniverseDefinition(
    name="us_large_cap",
    country="US",
    exchanges=["NYSE", "NASDAQ"],
    min_market_cap_usd=10_000_000_000,  # $10B+
    max_market_cap_usd=None,
)

US_MID_CAP = UniverseDefinition(
    name="us_mid_cap",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    min_market_cap_usd=2_000_000_000,   # $2B–$10B
    max_market_cap_usd=10_000_000_000,
)

US_SMALL_MID_CAP = UniverseDefinition(
    name="us_small_mid_cap",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    min_market_cap_usd=500_000_000,     # $500M–$10B
    max_market_cap_usd=10_000_000_000,
)

US_SMALL_CAP = UniverseDefinition(
    name="us_small_cap",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    min_market_cap_usd=300_000_000,     # $300M–$2B
    max_market_cap_usd=2_000_000_000,
)

US_ALL_CAP = UniverseDefinition(
    name="us_all_cap",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    min_market_cap_usd=300_000_000,     # $300M+ (all cap)
    max_market_cap_usd=None,
)

# ── Registry ─────────────────────────────────────────────────────────────────

UNIVERSE_REGISTRY: dict[str, UniverseDefinition] = {
    u.name: u
    for u in [
        US_LARGE_MID_CAP,
        US_LARGE_CAP,
        US_MID_CAP,
        US_SMALL_MID_CAP,
        US_SMALL_CAP,
        US_ALL_CAP,
    ]
}

__all__ = [
    "UniverseDefinition",
    "UNIVERSE_REGISTRY",
    "US_LARGE_MID_CAP",
    "US_LARGE_CAP",
    "US_MID_CAP",
    "US_SMALL_MID_CAP",
    "US_SMALL_CAP",
    "US_ALL_CAP",
]
