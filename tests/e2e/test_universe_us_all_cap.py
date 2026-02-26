"""
E2E test: validate US_ALL_CAP universe size against live FMP data.

Run all live tests:
    pytest tests/e2e/test_universe_us_all_cap.py -m fmp_live

Skip when credentials are absent (default CI behaviour) — the test calls
pytest.skip() automatically when FMP_API_KEY is not set.

What it tests
-------------
Calls FMP's company-screener endpoint for each (exchange × sector) combination
within US_ALL_CAP's exchange list, then applies the exchange and market-cap
filters client-side.  The resulting ticker count must fall inside the expected
range to confirm that:
  - the screener endpoint is returning a full US stock universe
  - US_ALL_CAP's exchange / market-cap parameters produce a plausible result
  - no silent data truncation is happening (e.g. the undocumented 1000-row limit)
"""

from __future__ import annotations

import os

import pytest
import requests

from sbfoundation.settings import API_KEY, DATA_SOURCES_CONFIG, FMP_BASE_URL_STABLE, FMP_DATA_SOURCE
from sbfoundation.universe_definitions import US_ALL_CAP

# ── Expected range ────────────────────────────────────────────────────────────
# NYSE + NASDAQ + AMEX stocks with market cap ≥ $300 M.
# Adjust only if the market's composition changes structurally.
_EXPECTED_MIN = 2_500
_EXPECTED_MAX = 2_800

# FMP sector names used by the company-screener endpoint.
# Mirrors silver.fmp_market_sectors values from available-sectors.
_SECTORS = [
    "Basic Materials",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Financial Services",
    "Healthcare",
    "Industrials",
    "Real Estate",
    "Technology",
    "Utilities",
]


def _fmp_api_key() -> str | None:
    env_var = DATA_SOURCES_CONFIG[FMP_DATA_SOURCE][API_KEY]  # "FMP_API_KEY"
    return os.environ.get(env_var)


@pytest.mark.fmp_live
def test_us_all_cap_ticker_count_is_in_expected_range() -> None:
    """US_ALL_CAP should contain 2,500–2,800 tickers from NYSE/NASDAQ/AMEX.

    Queries FMP company-screener by (exchange × sector) to work around the
    undocumented 1000-row-per-response limit.  Results are deduplicated on
    symbol before applying the market-cap filter.
    """
    api_key = _fmp_api_key()
    if not api_key:
        pytest.skip("FMP_API_KEY not set — live API test skipped")

    url = f"{FMP_BASE_URL_STABLE}company-screener"

    # Collect all rows, deduplicated by symbol, across exchange × sector combos.
    all_rows: dict[str, dict] = {}
    for exchange in US_ALL_CAP.exchanges:  # NYSE, NASDAQ, AMEX
        for sector in _SECTORS:
            resp = requests.get(
                url,
                params={"exchange": exchange, "sector": sector, "apikey": api_key},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            assert isinstance(data, list), (
                f"Expected a JSON list from FMP company-screener, got {type(data).__name__}. "
                f"exchange={exchange} sector={sector} snippet: {str(data)[:200]}"
            )

            for row in data:
                symbol = row.get("symbol")
                if symbol:
                    all_rows[symbol] = row

    target_exchanges = set(US_ALL_CAP.exchanges)   # {"NYSE", "NASDAQ", "AMEX"}
    min_cap = US_ALL_CAP.min_market_cap_usd        # 300_000_000
    max_cap = US_ALL_CAP.max_market_cap_usd        # None

    matched = [
        row for row in all_rows.values()
        if (
            row.get("exchangeShortName") in target_exchanges
            and (row.get("marketCap") or 0) >= min_cap
            and (max_cap is None or (row.get("marketCap") or 0) <= max_cap)
        )
    ]

    count = len(matched)
    exchange_breakdown = {
        ex: sum(1 for r in matched if r.get("exchangeShortName") == ex)
        for ex in sorted(target_exchanges)
    }

    assert _EXPECTED_MIN <= count <= _EXPECTED_MAX, (
        f"US_ALL_CAP ticker count {count} is outside expected range "
        f"[{_EXPECTED_MIN}, {_EXPECTED_MAX}].\n"
        f"  Total deduplicated records fetched: {len(all_rows)}\n"
        f"  Matched after exchange+market-cap filter: {count}\n"
        f"  Exchange breakdown: {exchange_breakdown}\n"
        f"  Filters applied: exchanges={sorted(target_exchanges)}, "
        f"min_cap={min_cap:,}, max_cap={max_cap}"
    )
