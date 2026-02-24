"""Tests for RunCommand.validate() — relaxed filter requirements."""
from __future__ import annotations

import pytest

from sbfoundation.api import RunCommand
from sbfoundation.settings import (
    COMPANY_DOMAIN,
    ECONOMICS_DOMAIN,
    FUNDAMENTALS_DOMAIN,
    MARKET_DOMAIN,
    TECHNICALS_DOMAIN,
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


def test_valid_domain_no_filters_does_not_raise() -> None:
    _cmd(COMPANY_DOMAIN).validate()
    _cmd(FUNDAMENTALS_DOMAIN).validate()
    _cmd(TECHNICALS_DOMAIN).validate()
    _cmd(MARKET_DOMAIN).validate()


def test_invalid_domain_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid domain"):
        _cmd("bogus_domain").validate()


def test_market_domain_no_filters_does_not_raise() -> None:
    _cmd(MARKET_DOMAIN).validate()


# ── UniverseDefinition tests ──────────────────────────────────────────────────

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


def test_run_command_accepts_universe_definition() -> None:
    cmd = _cmd(FUNDAMENTALS_DOMAIN, universe_definition=US_LARGE_CAP)
    cmd.validate()
    assert cmd.universe_definition is US_LARGE_CAP


def test_run_command_universe_definition_defaults_to_none() -> None:
    cmd = _cmd(FUNDAMENTALS_DOMAIN)
    assert cmd.universe_definition is None


# ── backfill_to_1990 validation ───────────────────────────────────────────────


def test_backfill_to_1990_invalid_domain_raises() -> None:
    """backfill_to_1990=True on company or market domain must raise ValueError."""
    with pytest.raises(ValueError, match="backfill_to_1990"):
        _cmd(COMPANY_DOMAIN, backfill_to_1990=True).validate()
    with pytest.raises(ValueError, match="backfill_to_1990"):
        _cmd(MARKET_DOMAIN, backfill_to_1990=True).validate()


def test_backfill_to_1990_valid_domain_passes() -> None:
    """backfill_to_1990=True is allowed for fundamentals, technicals, and economics."""
    _cmd(FUNDAMENTALS_DOMAIN, backfill_to_1990=True).validate()
    _cmd(TECHNICALS_DOMAIN, backfill_to_1990=True).validate()
    _cmd(ECONOMICS_DOMAIN, backfill_to_1990=True).validate()


def test_backfill_to_1990_defaults_to_false() -> None:
    """backfill_to_1990 defaults to False and does not affect normal validation."""
    cmd = _cmd(COMPANY_DOMAIN)
    assert cmd.backfill_to_1990 is False
    cmd.validate()  # must not raise


# ── include_delisted validation ───────────────────────────────────────────────


def test_include_delisted_defaults_to_false() -> None:
    cmd = _cmd(TECHNICALS_DOMAIN)
    assert cmd.include_delisted is False


def test_include_delisted_true_passes_validation_for_technicals_and_fundamentals() -> None:
    _cmd(TECHNICALS_DOMAIN, include_delisted=True).validate()
    _cmd(FUNDAMENTALS_DOMAIN, include_delisted=True).validate()
