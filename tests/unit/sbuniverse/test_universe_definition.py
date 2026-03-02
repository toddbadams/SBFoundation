"""Unit tests for UniverseDefinition."""

from __future__ import annotations

import json

import pytest

from sbuniverse.universe_definition import UniverseDefinition
from sbuniverse.universe_definitions import US_ALL_CAP, US_LARGE_CAP, UNIVERSE_REGISTRY


class TestToScreenerParams:
    def test_emits_only_non_none_fields(self) -> None:
        ud = UniverseDefinition(
            name="test",
            country="US",
            exchanges=["NYSE"],
            market_cap_more_than=1_000_000_000,
            is_actively_trading=True,
            is_etf=False,
        )
        params = ud.to_screener_params()
        assert "country" in params
        assert params["country"] == "US"
        assert params["marketCapMoreThan"] == 1_000_000_000
        assert params["isActivelyTrading"] is True
        assert params["isEtf"] is False
        # None fields excluded
        assert "marketCapLowerThan" not in params
        assert "sector" not in params

    def test_empty_definition_emits_limit_and_actively_trading(self) -> None:
        ud = UniverseDefinition(name="empty")
        params = ud.to_screener_params()
        # is_actively_trading defaults to True
        assert params["isActivelyTrading"] is True
        assert params["limit"] == 1000
        assert "country" not in params

    def test_exchange_excluded_from_screener_params(self) -> None:
        # Exchange is iterated separately — must not appear in to_screener_params()
        ud = UniverseDefinition(name="test", exchanges=["NASDAQ", "NYSE"])
        params = ud.to_screener_params()
        assert "exchange" not in params
        assert "exchanges" not in params

    def test_all_filter_fields(self) -> None:
        ud = UniverseDefinition(
            name="full",
            country="US",
            exchanges=["NYSE"],
            market_cap_more_than=1e9,
            market_cap_lower_than=1e12,
            price_more_than=5.0,
            price_lower_than=500.0,
            volume_more_than=100_000,
            volume_lower_than=50_000_000,
            beta_more_than=0.5,
            beta_lower_than=2.0,
            dividend_more_than=0.0,
            dividend_lower_than=10.0,
            sector="Technology",
            industry="Software",
            is_etf=False,
            is_fund=False,
            is_actively_trading=True,
            include_all_share_classes=False,
            limit=500,
        )
        params = ud.to_screener_params()
        assert params["marketCapMoreThan"] == 1e9
        assert params["marketCapLowerThan"] == 1e12
        assert params["priceMoreThan"] == 5.0
        assert params["priceLowerThan"] == 500.0
        assert params["volumeMoreThan"] == 100_000
        assert params["volumeLowerThan"] == 50_000_000
        assert params["betaMoreThan"] == 0.5
        assert params["betaLowerThan"] == 2.0
        assert params["dividendMoreThan"] == 0.0
        assert params["dividendLowerThan"] == 10.0
        assert params["sector"] == "Technology"
        assert params["industry"] == "Software"
        assert params["isEtf"] is False
        assert params["isFund"] is False
        assert params["isActivelyTrading"] is True
        assert params["includeAllShareClasses"] is False
        assert params["limit"] == 500


class TestFilterHash:
    def test_hash_is_64_char_hex(self) -> None:
        ud = UniverseDefinition(name="test", country="US", exchanges=["NYSE"])
        h = ud.filter_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_params_same_hash(self) -> None:
        ud1 = UniverseDefinition(name="test", country="US", exchanges=["NYSE", "NASDAQ"], market_cap_more_than=1e9)
        ud2 = UniverseDefinition(name="test", country="US", exchanges=["NASDAQ", "NYSE"], market_cap_more_than=1e9)
        # Exchanges are sorted in hash computation — order should not matter
        assert ud1.filter_hash() == ud2.filter_hash()

    def test_different_params_different_hash(self) -> None:
        ud1 = UniverseDefinition(name="a", country="US", market_cap_more_than=1e9)
        ud2 = UniverseDefinition(name="b", country="US", market_cap_more_than=2e9)
        assert ud1.filter_hash() != ud2.filter_hash()

    def test_name_does_not_affect_hash(self) -> None:
        # Hash is based on filter params, not the name identifier
        ud1 = UniverseDefinition(name="alpha", country="US", exchanges=["NYSE"])
        ud2 = UniverseDefinition(name="beta", country="US", exchanges=["NYSE"])
        assert ud1.filter_hash() == ud2.filter_hash()


class TestBackwardCompatAliases:
    def test_min_market_cap_usd(self) -> None:
        ud = UniverseDefinition(name="test", market_cap_more_than=5e9)
        assert ud.min_market_cap_usd == 5e9

    def test_max_market_cap_usd(self) -> None:
        ud = UniverseDefinition(name="test", market_cap_lower_than=10e9)
        assert ud.max_market_cap_usd == 10e9

    def test_none_when_not_set(self) -> None:
        ud = UniverseDefinition(name="test")
        assert ud.min_market_cap_usd is None
        assert ud.max_market_cap_usd is None


class TestUniverseRegistry:
    def test_all_universes_registered(self) -> None:
        expected = {"us_large_cap", "us_large_mid_cap", "us_mid_cap", "us_small_mid_cap", "us_small_cap", "us_all_cap"}
        assert set(UNIVERSE_REGISTRY.keys()) == expected

    def test_us_large_cap_params(self) -> None:
        ud = US_LARGE_CAP
        assert ud.country == "US"
        assert "NYSE" in ud.exchanges
        assert "NASDAQ" in ud.exchanges
        assert ud.market_cap_more_than == 10_000_000_000
        assert ud.is_etf is False
        assert ud.is_fund is False
        assert ud.is_actively_trading is True

    def test_us_all_cap_no_upper_bound(self) -> None:
        assert US_ALL_CAP.market_cap_lower_than is None

    def test_all_universes_have_name_and_exchanges(self) -> None:
        for name, ud in UNIVERSE_REGISTRY.items():
            assert ud.name == name
            assert len(ud.exchanges) > 0

    def test_shim_import_works(self) -> None:
        # Backward-compat: old import path must still work
        from sbfoundation.universe_definitions import US_LARGE_CAP as compat_ud, UniverseDefinition as CompatUD
        assert compat_ud.name == "us_large_cap"
        assert CompatUD is UniverseDefinition
