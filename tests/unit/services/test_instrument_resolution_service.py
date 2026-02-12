"""Unit tests for InstrumentResolutionService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from data_layer.services.instrument_resolution_service import InstrumentResolutionService


@pytest.fixture
def mock_bootstrap():
    """Create a mock DuckDbBootstrap with a mock connection."""
    bootstrap = MagicMock()
    conn = MagicMock()
    bootstrap.connect.return_value = conn
    return bootstrap, conn


def test_resolve_returns_instrument_sk_when_found(mock_bootstrap):
    """Test that resolve returns instrument_sk when instrument exists."""
    bootstrap, conn = mock_bootstrap

    # Mock table exists check
    conn.execute.return_value.fetchone.side_effect = [
        (True,),  # table exists
        (42,),  # instrument_sk
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.resolve("AAPL", "equity")

    assert result == 42
    # Verify the SQL was called correctly
    calls = conn.execute.call_args_list
    assert len(calls) == 2
    # Second call should contain dim_instrument and AAPL in params
    sql = calls[1][0][0]  # First positional arg (SQL)
    params = calls[1][0][1]  # Second positional arg (params list)
    assert "dim_instrument" in sql
    assert "AAPL" in params


def test_resolve_returns_none_when_not_found(mock_bootstrap):
    """Test that resolve returns None when instrument doesn't exist."""
    bootstrap, conn = mock_bootstrap

    # Mock table exists check and no result
    conn.execute.return_value.fetchone.side_effect = [
        (True,),  # table exists
        (None,),  # no instrument found
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.resolve("UNKNOWN", "equity")

    assert result is None


def test_resolve_returns_none_when_table_does_not_exist(mock_bootstrap):
    """Test that resolve returns None when dim_instrument table doesn't exist."""
    bootstrap, conn = mock_bootstrap

    # Mock table doesn't exist
    conn.execute.return_value.fetchone.return_value = (False,)

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.resolve("AAPL", "equity")

    assert result is None


def test_resolve_caches_results(mock_bootstrap):
    """Test that resolve caches results for subsequent calls."""
    bootstrap, conn = mock_bootstrap

    # Mock table exists and instrument found
    conn.execute.return_value.fetchone.side_effect = [
        (True,),  # table exists
        (42,),  # instrument_sk
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)

    # First call should hit DB
    result1 = service.resolve("AAPL", "equity")
    assert result1 == 42
    assert conn.execute.call_count == 2

    # Second call should use cache
    result2 = service.resolve("AAPL", "equity")
    assert result2 == 42
    assert conn.execute.call_count == 2  # No additional calls


def test_resolve_normalizes_symbol_to_uppercase(mock_bootstrap):
    """Test that resolve normalizes symbols to uppercase."""
    bootstrap, conn = mock_bootstrap

    conn.execute.return_value.fetchone.side_effect = [
        (True,),  # table exists
        (42,),  # instrument_sk
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.resolve("aapl", "equity")  # lowercase

    assert result == 42
    # Verify uppercase was used in query
    calls = conn.execute.call_args_list
    params = calls[1][0][1]  # Second positional arg (params list)
    assert "AAPL" in params


def test_resolve_returns_none_for_empty_symbol(mock_bootstrap):
    """Test that resolve returns None for empty symbol."""
    bootstrap, conn = mock_bootstrap

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.resolve("", "equity")

    assert result is None
    conn.execute.assert_not_called()


def test_bulk_resolve_returns_dict_of_found_instruments(mock_bootstrap):
    """Test that bulk_resolve returns dictionary of found instruments."""
    bootstrap, conn = mock_bootstrap

    # Mock table exists and multiple results
    conn.execute.return_value.fetchone.return_value = (True,)
    conn.execute.return_value.fetchall.return_value = [
        ("AAPL", 1),
        ("MSFT", 2),
        # "UNKNOWN" not in results
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.bulk_resolve(["AAPL", "MSFT", "UNKNOWN"], "equity")

    assert result == {"AAPL": 1, "MSFT": 2}


def test_bulk_resolve_returns_empty_dict_for_empty_list(mock_bootstrap):
    """Test that bulk_resolve returns empty dict for empty input."""
    bootstrap, conn = mock_bootstrap

    service = InstrumentResolutionService(bootstrap=bootstrap)
    result = service.bulk_resolve([], "equity")

    assert result == {}
    conn.execute.assert_not_called()


def test_bulk_resolve_uses_cache(mock_bootstrap):
    """Test that bulk_resolve uses cached values."""
    bootstrap, conn = mock_bootstrap

    service = InstrumentResolutionService(bootstrap=bootstrap)

    # Pre-populate cache directly
    service._cache[("AAPL", "equity")] = 1

    # Setup mock for bulk call (only needs to find MSFT)
    conn.execute.return_value.fetchone.return_value = (True,)  # table exists
    conn.execute.return_value.fetchall.return_value = [
        ("MSFT", 2),
    ]

    # Bulk resolve should only query MSFT (AAPL cached)
    result = service.bulk_resolve(["AAPL", "MSFT"], "equity")

    assert result == {"AAPL": 1, "MSFT": 2}
    # Verify AAPL was NOT in the bulk query params (only MSFT)
    bulk_call = conn.execute.call_args_list[-1]
    params = bulk_call[0][1]  # Second positional arg (params list)
    assert "MSFT" in params
    assert "AAPL" not in params


def test_clear_cache_removes_all_entries(mock_bootstrap):
    """Test that clear_cache removes all cached entries."""
    bootstrap, conn = mock_bootstrap

    # Setup: populate cache
    conn.execute.return_value.fetchone.side_effect = [
        (True,),  # table exists
        (42,),  # instrument_sk
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)
    service.resolve("AAPL", "equity")
    assert service.get_cache_size() == 1

    # Clear cache
    service.clear_cache()
    assert service.get_cache_size() == 0


def test_get_cache_size_returns_correct_count(mock_bootstrap):
    """Test that get_cache_size returns correct count."""
    bootstrap, conn = mock_bootstrap

    conn.execute.return_value.fetchone.side_effect = [
        (True,), (1,),  # AAPL
        (True,), (2,),  # MSFT
    ]

    service = InstrumentResolutionService(bootstrap=bootstrap)
    assert service.get_cache_size() == 0

    service.resolve("AAPL", "equity")
    assert service.get_cache_size() == 1

    service.resolve("MSFT", "equity")
    assert service.get_cache_size() == 2


def test_close_closes_bootstrap_when_owned(mock_bootstrap):
    """Test that close() closes the bootstrap when service owns it."""
    bootstrap, _ = mock_bootstrap

    # Service owns the bootstrap (created internally) - simulate by setting flag
    service = InstrumentResolutionService(bootstrap=bootstrap)
    service._owns_bootstrap = True

    service.close()
    bootstrap.close.assert_called_once()


def test_close_does_not_close_bootstrap_when_not_owned(mock_bootstrap):
    """Test that close() doesn't close the bootstrap when injected."""
    bootstrap, _ = mock_bootstrap

    service = InstrumentResolutionService(bootstrap=bootstrap)
    # bootstrap was injected, so service doesn't own it

    service.close()
    bootstrap.close.assert_not_called()
