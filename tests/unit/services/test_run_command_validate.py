"""Tests for RunCommand.validate()."""
from __future__ import annotations

import pytest

from sbfoundation.api import RunCommand
from sbfoundation.settings import (
    ANNUAL_DOMAIN,
    EOD_DOMAIN,
    QUARTER_DOMAIN,
)
from sbfoundation.universe_definitions import US_LARGE_CAP, US_MID_CAP, UNIVERSE_REGISTRY, UniverseDefinition


def _cmd(domain: str, **kwargs: object) -> RunCommand:
    return RunCommand(
        domain=domain,
        concurrent_requests=1,
        enable_bronze=False,
        enable_silver=False,
        **kwargs,  # type: ignore[arg-type]
    )


def test_all_active_domains_are_valid() -> None:
    _cmd(EOD_DOMAIN).validate()
    _cmd(QUARTER_DOMAIN).validate()
    _cmd(ANNUAL_DOMAIN).validate()


def test_invalid_domain_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid domain"):
        _cmd("bogus_domain").validate()


# ── UniverseDefinition tests (independent of RunCommand) ─────────────────────

def test_universe_definition_fields() -> None:
    assert US_LARGE_CAP.name == "us_large_cap"
    assert US_LARGE_CAP.country == "US"
    assert set(US_LARGE_CAP.exchanges) == {"NYSE", "NASDAQ"}
    assert US_LARGE_CAP.min_market_cap_usd == 10_000_000_000
    assert US_LARGE_CAP.max_market_cap_usd is None


def test_universe_definition_mid_cap_bounds() -> None:
    assert US_MID_CAP.min_market_cap_usd == 2_000_000_000
    assert US_MID_CAP.max_market_cap_usd == 10_000_000_000


def test_universe_registry_contains_all_definitions() -> None:
    assert set(UNIVERSE_REGISTRY.keys()) == {
        "us_large_mid_cap", "us_large_cap", "us_mid_cap",
        "us_small_mid_cap", "us_small_cap", "us_all_cap",
    }


def test_universe_definition_is_frozen() -> None:
    with pytest.raises((AttributeError, TypeError)):
        US_LARGE_CAP.name = "mutated"  # type: ignore[misc]
