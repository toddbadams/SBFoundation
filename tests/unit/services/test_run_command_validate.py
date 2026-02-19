"""Tests for RunCommand.validate() — relaxed filter requirements."""
from __future__ import annotations

import pytest

from sbfoundation.api import RunCommand
from sbfoundation.settings import COMPANY_DOMAIN, FUNDAMENTALS_DOMAIN, MARKET_DOMAIN, TECHNICALS_DOMAIN


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


def test_exchange_filter_only() -> None:
    _cmd(COMPANY_DOMAIN, exchanges=["NASDAQ"]).validate()


def test_sector_filter_only() -> None:
    _cmd(COMPANY_DOMAIN, sectors=["Technology"]).validate()


def test_industry_filter_only() -> None:
    _cmd(COMPANY_DOMAIN, industries=["Software-Application"]).validate()


def test_country_filter_only() -> None:
    _cmd(COMPANY_DOMAIN, countries=["US"]).validate()


def test_multiple_filters_combined() -> None:
    _cmd(
        COMPANY_DOMAIN,
        exchanges=["NASDAQ", "NYSE"],
        sectors=["Technology"],
        countries=["US"],
    ).validate()


def test_invalid_domain_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid domain"):
        _cmd("bogus_domain").validate()


def test_market_domain_no_filters_does_not_raise() -> None:
    _cmd(MARKET_DOMAIN).validate()
