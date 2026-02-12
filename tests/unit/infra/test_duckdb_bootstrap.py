from __future__ import annotations

import pytest

from data_layer.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap


class _FakeConnection:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.closed = False

    def execute(self, sql: str, *args: object, **kwargs: object) -> "_FakeConnection":
        self.commands.append(sql.strip())
        return self

    def fetchall(self) -> list[object]:
        return []

    def close(self) -> None:
        self.closed = True


def test_schema_initialization_runs_only_once(patch_folders) -> None:
    """Schema initialization should run exactly once per bootstrap instance."""
    conn = _FakeConnection()
    bootstrap = DuckDbBootstrap(conn=conn)

    # First connect should initialize
    bootstrap.connect()
    init_commands_1 = len([c for c in conn.commands if 'CREATE' in c.upper()])

    # Second connect should not re-initialize
    bootstrap.connect()
    init_commands_2 = len([c for c in conn.commands if 'CREATE' in c.upper()])

    assert init_commands_1 > 0, "First connect should create schemas/tables"
    assert init_commands_2 == init_commands_1, "Second connect should not create anything new"


def test_transaction_commits_and_rolls_back(patch_folders) -> None:
    conn = _FakeConnection()
    bootstrap = DuckDbBootstrap(conn=conn)

    with bootstrap.transaction() as tx:
        tx.execute("SELECT 1")
    assert any(cmd.startswith("BEGIN") for cmd in conn.commands)
    assert any("COMMIT" in cmd for cmd in conn.commands)

    conn.commands.clear()
    with pytest.raises(ValueError):
        with bootstrap.transaction() as tx:
            tx.execute("SELECT 2")
            raise ValueError("fail")
    assert any("ROLLBACK" in cmd for cmd in conn.commands)

    with bootstrap.ops_transaction() as tx:
        assert tx is conn
    with bootstrap.silver_transaction() as tx:
        assert tx is conn
    with bootstrap.gold_transaction() as tx:
        assert tx is conn
