"""Shared DuckDB connection for the coverage dashboard.

Uses @st.cache_resource so a single DuckDbBootstrap + DuckDbOpsRepo instance
is reused across all Streamlit pages and reruns for the lifetime of the server
process.  Call get_repo() from any page to obtain the shared repo.
"""

from __future__ import annotations

import streamlit as st

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo


@st.cache_resource
def get_repo() -> DuckDbOpsRepo:
    """Return a cached DuckDbOpsRepo backed by a persistent DuckDB connection."""
    bootstrap = DuckDbBootstrap()
    return DuckDbOpsRepo(bootstrap=bootstrap)
