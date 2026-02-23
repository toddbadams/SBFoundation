from __future__ import annotations

import pathlib
import tempfile
from contextlib import contextmanager
from datetime import date, datetime

import duckdb
import pytest

from sbfoundation.ops.services.run_stats_reporter import RunStatsReporter

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

RUN_A = "20260221.aaa111"
RUN_B = "20260220.bbb222"


# ---------------------------------------------------------------------------
# In-memory DuckDB bootstrap stub
# ---------------------------------------------------------------------------

_DDL = """
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE TABLE IF NOT EXISTS ops.file_ingestions (
    run_id VARCHAR,
    file_id VARCHAR,
    domain VARCHAR,
    source VARCHAR,
    dataset VARCHAR,
    discriminator VARCHAR,
    ticker VARCHAR,
    bronze_filename VARCHAR,
    bronze_error VARCHAR,
    bronze_rows INTEGER,
    bronze_from_date DATE,
    bronze_to_date DATE,
    bronze_injest_start_time TIMESTAMP,
    bronze_injest_end_time TIMESTAMP,
    bronze_can_promote BOOLEAN,
    bronze_payload_hash VARCHAR,
    silver_tablename VARCHAR,
    silver_errors VARCHAR,
    silver_rows_created INTEGER,
    silver_rows_updated INTEGER,
    silver_rows_failed INTEGER,
    silver_from_date DATE,
    silver_to_date DATE,
    silver_injest_start_time TIMESTAMP,
    silver_injest_end_time TIMESTAMP,
    silver_can_promote BOOLEAN
);
"""


class _StubBootstrap:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def connect(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    @contextmanager
    def read_connection(self):
        yield self.conn

    def close(self) -> None:
        pass


def _make_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    conn.execute(_DDL)
    return conn


def _insert(conn: duckdb.DuckDBPyConnection, **kwargs) -> None:
    defaults = dict(
        run_id=RUN_A,
        file_id="file-1",
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator=None,
        ticker="AAPL",
        bronze_filename="bronze/company/fmp/company-profile/AAPL/2026-02-21-abc.json",
        bronze_error=None,
        bronze_rows=1,
        bronze_from_date=None,
        bronze_to_date=date(2026, 2, 21),
        bronze_injest_start_time=datetime(2026, 2, 21, 8, 0, 0),
        bronze_injest_end_time=datetime(2026, 2, 21, 8, 0, 1),
        bronze_can_promote=True,
        bronze_payload_hash="abc123",
        silver_tablename="fmp_company_profile",
        silver_errors=None,
        silver_rows_created=1,
        silver_rows_updated=0,
        silver_rows_failed=0,
        silver_from_date=None,
        silver_to_date=date(2026, 2, 21),
        silver_injest_start_time=datetime(2026, 2, 21, 8, 0, 2),
        silver_injest_end_time=datetime(2026, 2, 21, 8, 0, 3),
        silver_can_promote=False,
    )
    defaults.update(kwargs)
    cols = list(defaults.keys())
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO ops.file_ingestions ({', '.join(cols)}) VALUES ({placeholders})",
        list(defaults.values()),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn_two_runs() -> duckdb.DuckDBPyConnection:
    """Two runs seeded: RUN_A (with one bronze error), RUN_B (clean)."""
    conn = _make_conn()

    # RUN_A — company domain, 2 files: 1 passed + 1 errored
    _insert(
        conn,
        run_id=RUN_A,
        file_id="a-1",
        domain="company",
        dataset="company-profile",
        ticker="AAPL",
        bronze_rows=10,
        bronze_injest_start_time=datetime(2026, 2, 21, 8, 0, 0),
        silver_rows_created=10,
    )
    _insert(
        conn,
        run_id=RUN_A,
        file_id="a-2",
        domain="company",
        dataset="company-profile",
        ticker="BKLY",
        bronze_rows=0,
        bronze_error="HTTP 404",
        bronze_can_promote=False,
        bronze_injest_start_time=datetime(2026, 2, 21, 8, 0, 5),
        silver_tablename=None,
        silver_rows_created=0,
    )
    # RUN_A — fundamentals domain, 3 clean files
    for i, ticker in enumerate(["MSFT", "GOOG", "AMZN"]):
        _insert(
            conn,
            run_id=RUN_A,
            file_id=f"a-fund-{i}",
            domain="fundamentals",
            dataset="income-statement",
            ticker=ticker,
            bronze_rows=40,
            bronze_injest_start_time=datetime(2026, 2, 21, 8, 1, i),
            silver_tablename="fmp_income_statement",
            silver_rows_created=40,
            silver_from_date=date(2010, 1, 1),
            silver_to_date=date(2025, 12, 31),
        )

    # RUN_B — single clean company file
    _insert(
        conn,
        run_id=RUN_B,
        file_id="b-1",
        domain="company",
        dataset="company-profile",
        ticker="TSLA",
        bronze_rows=5,
        bronze_injest_start_time=datetime(2026, 2, 20, 7, 0, 0),
        silver_rows_created=5,
    )

    return conn


@pytest.fixture()
def conn_with_silver(conn_two_runs: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    """Adds a silver table with rows so history_report() can count them."""
    conn_two_runs.execute(
        "CREATE TABLE silver.fmp_company_profile (ticker VARCHAR, company_name VARCHAR)"
    )
    for i in range(3):
        conn_two_runs.execute(
            "INSERT INTO silver.fmp_company_profile VALUES (?, ?)", [f"T{i}", f"Company {i}"]
        )
    conn_two_runs.execute(
        "CREATE TABLE silver.fmp_income_statement (ticker VARCHAR, period_end DATE)"
    )
    for i in range(10):
        conn_two_runs.execute(
            "INSERT INTO silver.fmp_income_statement VALUES (?, ?)",
            [f"T{i % 3}", date(2020 + i, 1, 1)],
        )
    return conn_two_runs


@pytest.fixture()
def reporter_two_runs(conn_two_runs: duckdb.DuckDBPyConnection) -> RunStatsReporter:
    return RunStatsReporter(bootstrap=_StubBootstrap(conn_two_runs))  # type: ignore[arg-type]


@pytest.fixture()
def reporter_with_silver(conn_with_silver: duckdb.DuckDBPyConnection) -> RunStatsReporter:
    return RunStatsReporter(bootstrap=_StubBootstrap(conn_with_silver))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# report() tests — current-run section
# ---------------------------------------------------------------------------


class TestReport:
    def test_contains_run_id(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert RUN_A in text

    def test_domain_rows_present(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert "company" in text
        assert "fundamentals" in text

    def test_bronze_totals_correct(self, reporter_two_runs: RunStatsReporter) -> None:
        # RUN_A: company has 2 files (1 pass, 1 fail), fundamentals has 3 (all pass)
        text = reporter_two_runs.report(RUN_A)
        # Total files for company domain = 2; total for fundamentals = 3
        assert "company" in text
        assert "fundamentals" in text

    def test_error_section_shows_failed_ticker(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert "BKLY" in text
        assert "HTTP 404" in text

    def test_clean_run_no_errors(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_B)
        assert "No errors" in text

    def test_silver_section_present(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert "Silver Promotion" in text
        assert "fmp_company_profile" in text
        assert "fmp_income_statement" in text

    def test_silver_coverage_dates(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert "2010-01-01" in text
        assert "2025-12-31" in text

    def test_dataset_breakdown_present(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert "By Dataset" in text
        assert "company-profile" in text
        assert "income-statement" in text

    def test_does_not_include_other_run(self, reporter_two_runs: RunStatsReporter) -> None:
        # RUN_A report must not mention TSLA (which only appears in RUN_B)
        text = reporter_two_runs.report(RUN_A)
        assert "TSLA" not in text

    def test_empty_run_returns_no_bronze_message(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report("nonexistent-run-id")
        assert "No bronze files" in text

    def test_total_row_in_domain_table(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        assert "**Total**" in text

    def test_returns_markdown_table(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.report(RUN_A)
        # Markdown tables use pipe separators
        assert "|" in text
        assert "---" in text


# ---------------------------------------------------------------------------
# history_report() tests — all-runs section
# ---------------------------------------------------------------------------


class TestHistoryReport:
    def test_contains_both_run_ids(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.history_report()
        assert RUN_A in text
        assert RUN_B in text

    def test_run_count_header(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.history_report()
        assert "2 total" in text

    def test_most_recent_run_first(self, reporter_two_runs: RunStatsReporter) -> None:
        text = reporter_two_runs.history_report()
        pos_a = text.index(RUN_A)
        pos_b = text.index(RUN_B)
        # RUN_A started at 2026-02-21, RUN_B at 2026-02-20 — A must appear first
        assert pos_a < pos_b

    def test_silver_sizes_section_present(self, reporter_with_silver: RunStatsReporter) -> None:
        text = reporter_with_silver.history_report()
        assert "Accumulated Silver Table Sizes" in text
        assert "fmp_company_profile" in text
        assert "fmp_income_statement" in text

    def test_silver_row_counts_correct(self, reporter_with_silver: RunStatsReporter) -> None:
        text = reporter_with_silver.history_report()
        # 3 rows in fmp_company_profile, 10 in fmp_income_statement
        assert "3" in text
        assert "10" in text

    def test_no_silver_tables_graceful(self, reporter_two_runs: RunStatsReporter) -> None:
        # conn_two_runs has no silver tables (only schema exists)
        text = reporter_two_runs.history_report()
        assert "No Silver tables found" in text

    def test_empty_database_graceful(self) -> None:
        conn = _make_conn()
        reporter = RunStatsReporter(bootstrap=_StubBootstrap(conn))  # type: ignore[arg-type]
        text = reporter.history_report()
        assert "0 total" in text
        assert "No runs recorded yet" in text

    def test_silver_total_row_present(self, reporter_with_silver: RunStatsReporter) -> None:
        text = reporter_with_silver.history_report()
        assert "**Total**" in text


# ---------------------------------------------------------------------------
# write_report() tests
# ---------------------------------------------------------------------------


class TestWriteReport:
    def test_file_is_created(self, reporter_two_runs: RunStatsReporter, tmp_path: pathlib.Path) -> None:
        # Patch Folders.logs_absolute_path to return tmp_path
        import sbfoundation.ops.services.run_stats_reporter as mod
        import sbfoundation.folders as folders_mod

        original = folders_mod.Folders.logs_absolute_path
        folders_mod.Folders.logs_absolute_path = staticmethod(lambda: tmp_path)  # type: ignore
        try:
            result = reporter_two_runs.write_report(RUN_A)
            assert result.exists()
            assert result.name == f"{RUN_A}_report.md"
        finally:
            folders_mod.Folders.logs_absolute_path = original

    def test_file_content_contains_both_sections(
        self, reporter_with_silver: RunStatsReporter, tmp_path: pathlib.Path
    ) -> None:
        import sbfoundation.folders as folders_mod

        original = folders_mod.Folders.logs_absolute_path
        folders_mod.Folders.logs_absolute_path = staticmethod(lambda: tmp_path)  # type: ignore
        try:
            result = reporter_with_silver.write_report(RUN_A)
            content = result.read_text(encoding="utf-8")
            assert "# SBFoundation Run Report" in content
            assert "## Bronze Ingestion" in content
            assert "## Run History" in content
            assert "## Accumulated Silver Table Sizes" in content
        finally:
            folders_mod.Folders.logs_absolute_path = original

    def test_file_is_utf8_markdown(
        self, reporter_two_runs: RunStatsReporter, tmp_path: pathlib.Path
    ) -> None:
        import sbfoundation.folders as folders_mod

        original = folders_mod.Folders.logs_absolute_path
        folders_mod.Folders.logs_absolute_path = staticmethod(lambda: tmp_path)  # type: ignore
        try:
            result = reporter_two_runs.write_report(RUN_A)
            content = result.read_text(encoding="utf-8")
            assert content.startswith("# SBFoundation Run Report")
        finally:
            folders_mod.Folders.logs_absolute_path = original

    def test_second_write_overwrites(
        self, reporter_two_runs: RunStatsReporter, tmp_path: pathlib.Path
    ) -> None:
        """write_report is idempotent — second call overwrites, does not append."""
        import sbfoundation.folders as folders_mod

        original = folders_mod.Folders.logs_absolute_path
        folders_mod.Folders.logs_absolute_path = staticmethod(lambda: tmp_path)  # type: ignore
        try:
            p1 = reporter_two_runs.write_report(RUN_A)
            size_first = p1.stat().st_size
            p2 = reporter_two_runs.write_report(RUN_A)
            assert p1 == p2
            assert p2.stat().st_size == size_first
        finally:
            folders_mod.Folders.logs_absolute_path = original
