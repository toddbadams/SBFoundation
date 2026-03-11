"""E2E test fixtures: in-memory DuckDB + fake FMP server serving JSON fixture files."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Generator

import duckdb
import pytest

from sbfoundation.maintenance.duckdb_bootstrap import DuckDbBootstrap

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fmp"


# ---------------------------------------------------------------------------
# mem_duck — isolated in-memory DuckDB with full schema
# ---------------------------------------------------------------------------

@pytest.fixture
def mem_duck() -> Generator[DuckDbBootstrap, None, None]:
    """Provide a fresh in-memory DuckDB with ops/silver/gold schemas initialised."""
    conn = duckdb.connect(":memory:")
    bootstrap = DuckDbBootstrap(conn=conn)
    bootstrap.connect()  # initialises schemas
    yield bootstrap
    bootstrap.close()
    conn.close()


# ---------------------------------------------------------------------------
# fmp_server — FastAPI server serving fixture files by path
# ---------------------------------------------------------------------------

@pytest.fixture
def fmp_server():
    """Start a local FastAPI server that serves JSON fixtures by path.

    Routes are registered dynamically from the fixtures directory.
    Any request path that matches a JSON file under fixtures/fmp/ returns it;
    unmatched paths return [].
    """
    from tests.e2e.fake_api import FakeApiServer

    server = FakeApiServer()

    def _handle_fixture(path: str):
        """Return fixture data for given path, or empty list."""
        # Normalise: strip leading slash
        rel = path.lstrip("/")
        candidate = FIXTURES_DIR / (rel + ".json")
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
        return []

    # Register a catch-all route that serves fixture files
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @server.app.api_route("/{full_path:path}", methods=["GET"])
    async def serve_fixture(full_path: str, request: Request):
        api_key = request.query_params.get("apikey", "")
        if api_key != server.api_key:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        data = _handle_fixture(full_path)
        return JSONResponse(data)

    port = server.start()
    yield server
    server.stop()
