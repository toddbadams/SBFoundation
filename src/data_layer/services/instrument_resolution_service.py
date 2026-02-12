"""Service for resolving instrument_sk from gold.dim_instrument."""

from __future__ import annotations

import logging

import duckdb

from data_layer.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from data_layer.infra.logger import LoggerFactory


class InstrumentResolutionService:
    """Resolves instrument_sk from gold.dim_instrument by (symbol, instrument_type).

    This service provides a centralized lookup for instrument surrogate keys,
    supporting both single and bulk resolution with caching for performance.

    Usage:
        resolver = InstrumentResolutionService()
        sk = resolver.resolve("AAPL", "equity")  # Returns int or None

        # Bulk resolution for efficiency
        sk_map = resolver.bulk_resolve(["AAPL", "MSFT", "GOOG"], "equity")
        # Returns {"AAPL": 1, "MSFT": 2, "GOOG": 3}

        # Clear cache after dim_instrument changes (e.g., after Gold promotion)
        resolver.clear_cache()
    """

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._cache: dict[tuple[str, str], int] = {}

    def close(self) -> None:
        """Close the database connection if owned by this service."""
        if self._owns_bootstrap:
            self._bootstrap.close()

    def resolve(self, symbol: str, instrument_type: str = "equity") -> int | None:
        """Lookup instrument_sk by (symbol, instrument_type).

        Args:
            symbol: The instrument symbol (e.g., "AAPL")
            instrument_type: The instrument type (default: "equity")

        Returns:
            The instrument_sk if found, None otherwise
        """
        if not symbol:
            return None

        key = (symbol.upper(), instrument_type)
        if key in self._cache:
            return self._cache[key]

        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "gold", "dim_instrument"):
            self._logger.debug("gold.dim_instrument table does not exist yet")
            return None

        try:
            result = conn.execute(
                """
                SELECT instrument_sk
                FROM gold.dim_instrument
                WHERE symbol = ? AND instrument_type = ? AND is_current = TRUE
                """,
                [symbol.upper(), instrument_type],
            ).fetchone()

            if result and result[0] is not None:
                sk = int(result[0])
                self._cache[key] = sk
                return sk

            return None
        except Exception as exc:
            self._logger.warning(f"Failed to resolve instrument_sk for {symbol}: {exc}")
            return None

    def bulk_resolve(
        self, symbols: list[str], instrument_type: str = "equity"
    ) -> dict[str, int]:
        """Bulk lookup instrument_sk for multiple symbols.

        More efficient than individual lookups when resolving many symbols.
        Results are cached for subsequent single lookups.

        Args:
            symbols: List of instrument symbols
            instrument_type: The instrument type (default: "equity")

        Returns:
            Dictionary mapping symbol to instrument_sk (only includes found symbols)
        """
        if not symbols:
            return {}

        # Normalize symbols
        normalized_symbols = [s.upper() for s in symbols if s]

        # Check cache first, collect uncached symbols
        result: dict[str, int] = {}
        uncached_symbols: list[str] = []

        for symbol in normalized_symbols:
            key = (symbol, instrument_type)
            if key in self._cache:
                result[symbol] = self._cache[key]
            else:
                uncached_symbols.append(symbol)

        if not uncached_symbols:
            return result

        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "gold", "dim_instrument"):
            self._logger.debug("gold.dim_instrument table does not exist yet")
            return result

        try:
            # Build parameterized query for uncached symbols
            placeholders = ", ".join(["?"] * len(uncached_symbols))
            params = uncached_symbols + [instrument_type]

            rows = conn.execute(
                f"""
                SELECT symbol, instrument_sk
                FROM gold.dim_instrument
                WHERE symbol IN ({placeholders})
                  AND instrument_type = ?
                  AND is_current = TRUE
                """,
                params,
            ).fetchall()

            for row in rows:
                symbol, sk = row[0], row[1]
                if sk is not None:
                    sk = int(sk)
                    result[symbol] = sk
                    self._cache[(symbol, instrument_type)] = sk

            return result
        except Exception as exc:
            self._logger.warning(f"Failed to bulk resolve instrument_sk: {exc}")
            return result

    def get_tickers_by_exchanges(
        self,
        exchanges: list[str],
        instrument_type: str = "equity",
        limit: int | None = None,
    ) -> list[tuple[str, int]]:
        """Get tickers and instrument_sk values filtered by exchange.

        Queries gold.dim_company_profile joined with gold.dim_instrument
        to find current instruments on the specified exchanges.

        Args:
            exchanges: List of exchange names (e.g., ["NASDAQ", "NYSE"])
            instrument_type: The instrument type (default: "equity")
            limit: Maximum number of results (None for no limit)

        Returns:
            List of (ticker, instrument_sk) tuples for instruments on the exchanges
        """
        if not exchanges:
            return []

        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "gold", "dim_company_profile"):
            self._logger.debug("gold.dim_company_profile table does not exist yet")
            return []

        if not self._table_exists(conn, "gold", "dim_instrument"):
            self._logger.debug("gold.dim_instrument table does not exist yet")
            return []

        try:
            normalized_exchanges = [e.upper() for e in exchanges if e]
            placeholders = ", ".join(["?"] * len(normalized_exchanges))

            sql = f"""
                SELECT cp.ticker, cp.instrument_sk
                FROM gold.dim_company_profile cp
                INNER JOIN gold.dim_instrument di
                    ON cp.instrument_sk = di.instrument_sk
                WHERE cp.is_current = TRUE
                  AND di.is_current = TRUE
                  AND di.instrument_type = ?
                  AND UPPER(cp.exchange) IN ({placeholders})
                ORDER BY cp.ticker
            """

            params = [instrument_type] + normalized_exchanges

            if limit is not None:
                sql += f" LIMIT {limit}"

            rows = conn.execute(sql, params).fetchall()
            return [(row[0], row[1]) for row in rows if row[0] and row[1]]
        except Exception as exc:
            self._logger.warning(f"Failed to get tickers by exchange: {exc}")
            return []

    def clear_cache(self) -> None:
        """Clear the internal cache.

        Call this after Gold promotion to ensure fresh lookups
        when new instruments have been added to dim_instrument.
        """
        self._cache.clear()
        self._logger.debug("Instrument resolution cache cleared")

    def get_cache_size(self) -> int:
        """Return the current number of cached entries."""
        return len(self._cache)

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        """Check if a table exists in the database."""
        result = conn.execute(
            """
            SELECT COUNT(*) > 0
            FROM information_schema.tables
            WHERE table_schema = ? AND table_name = ?
            """,
            [schema, table],
        ).fetchone()
        return bool(result and result[0])
