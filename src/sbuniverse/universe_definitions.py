"""
Named universe definitions for SBFoundation ingestion scoping.

Each constant is a UniverseDefinition whose eligibility filters drive:
  1. The nightly Company Screener ingestion (which instruments to fetch).
  2. The universe_member snapshot (reproducible membership per run).
  3. The ingestion pipeline's ticker list (which symbols to pull data for).

Strategy-level selection filters (liquidity gates, factor screens, sector
weights) are intentionally excluded — they belong in the downstream Gold project.

Usage:
    from sbuniverse.universe_definitions import US_LARGE_CAP, UNIVERSE_REGISTRY
"""

from __future__ import annotations

from sbuniverse.universe_definition import UniverseDefinition


# ── US equity universes ───────────────────────────────────────────────────────

US_LARGE_CAP = UniverseDefinition(
    name="us_large_cap",
    description="US large-cap equities: NYSE + NASDAQ, market cap ≥ $10B",
    country="US",
    exchanges=["NYSE", "NASDAQ"],
    market_cap_more_than=10_000_000_000,
    is_actively_trading=True,
    is_etf=False,
    is_fund=False,
)

US_LARGE_MID_CAP = UniverseDefinition(
    name="us_large_mid_cap",
    description="US large & mid-cap equities: NYSE + NASDAQ, market cap ≥ $2B",
    country="US",
    exchanges=["NYSE", "NASDAQ"],
    market_cap_more_than=2_000_000_000,
    is_actively_trading=True,
    is_etf=False,
    is_fund=False,
)

US_MID_CAP = UniverseDefinition(
    name="us_mid_cap",
    description="US mid-cap equities: NYSE + NASDAQ + AMEX, $2B–$10B",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    market_cap_more_than=2_000_000_000,
    market_cap_lower_than=10_000_000_000,
    is_actively_trading=True,
    is_etf=False,
    is_fund=False,
)

US_SMALL_MID_CAP = UniverseDefinition(
    name="us_small_mid_cap",
    description="US small & mid-cap equities: NYSE + NASDAQ + AMEX, $500M–$10B",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    market_cap_more_than=500_000_000,
    market_cap_lower_than=10_000_000_000,
    is_actively_trading=True,
    is_etf=False,
    is_fund=False,
)

US_SMALL_CAP = UniverseDefinition(
    name="us_small_cap",
    description="US small-cap equities: NYSE + NASDAQ + AMEX, $300M–$2B",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    market_cap_more_than=300_000_000,
    market_cap_lower_than=2_000_000_000,
    is_actively_trading=True,
    is_etf=False,
    is_fund=False,
)

US_ALL_CAP = UniverseDefinition(
    name="us_all_cap",
    description="US all-cap equities: NYSE + NASDAQ + AMEX, market cap ≥ $300M",
    country="US",
    exchanges=["NYSE", "NASDAQ", "AMEX"],
    market_cap_more_than=300_000_000,
    is_actively_trading=True,
    is_etf=False,
    is_fund=False,
)


# ── Registry ─────────────────────────────────────────────────────────────────

UNIVERSE_REGISTRY: dict[str, UniverseDefinition] = {
    u.name: u
    for u in [
        US_LARGE_CAP,
        US_LARGE_MID_CAP,
        US_MID_CAP,
        US_SMALL_MID_CAP,
        US_SMALL_CAP,
        US_ALL_CAP,
    ]
}


__all__ = [
    "UniverseDefinition",
    "UNIVERSE_REGISTRY",
    "US_LARGE_CAP",
    "US_LARGE_MID_CAP",
    "US_MID_CAP",
    "US_SMALL_MID_CAP",
    "US_SMALL_CAP",
    "US_ALL_CAP",
]
