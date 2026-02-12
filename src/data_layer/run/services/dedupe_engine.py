from __future__ import annotations

from typing import Iterable

import duckdb
import pandas as pd


class DedupeEngine:
    def __init__(self, *, use_duckdb_engine: bool = True) -> None:
        self._use_duckdb_engine = use_duckdb_engine

    def dedupe_against_table(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        df_candidate: pd.DataFrame,
        key_cols: Iterable[str],
        target_table: str,
        table_exists: bool,
    ) -> pd.DataFrame:
        if df_candidate.empty or not table_exists:
            return df_candidate

        key_cols = tuple(key_cols)
        if not key_cols:
            return df_candidate

        df_candidate = df_candidate.drop_duplicates(subset=list(key_cols), keep="last")

        if not self._use_duckdb_engine:
            return df_candidate

        conn.register("_candidate_rows", df_candidate)
        try:
            key_col = key_cols[0]
            using_cols = ", ".join(f'"{col}"' for col in key_cols)
            sql = (
                "SELECT c.* FROM _candidate_rows c "
                f"LEFT JOIN {target_table} t USING ({using_cols}) "
                f"WHERE t.\"{key_col}\" IS NULL"
            )
            return conn.execute(sql).df()
        finally:
            conn.unregister("_candidate_rows")
