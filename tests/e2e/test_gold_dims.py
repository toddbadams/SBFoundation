"""E2E test: Gold dim_instrument and dim_company build from Silver fixtures."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from tests.e2e.conftest import FIXTURES_DIR

pytestmark = pytest.mark.skipif(
    not (FIXTURES_DIR / "v4" / "profile" / "all.json").exists(),
    reason="Company profile bulk fixture not present",
)


def test_gold_dim_instrument_build(mem_duck):
    """Verify dim_instrument builds correctly from in-memory Silver data."""
    from sbfoundation.gold.gold_dim_service import GoldDimService

    # Load fixture
    profile_data = json.loads((FIXTURES_DIR / "v4" / "profile" / "all.json").read_text())

    with mem_duck.gold_transaction() as conn:
        # ------------------------------------------------------------------
        # Silver tables required by GoldDimService
        # ------------------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.fmp_company_profile_bulk (
                symbol VARCHAR, company_name VARCHAR, exchange VARCHAR,
                exchange_short_name VARCHAR, sector VARCHAR, industry VARCHAR,
                country VARCHAR, currency VARCHAR, is_etf BOOLEAN,
                is_actively_trading BOOLEAN, market_cap DOUBLE, price DOUBLE,
                beta DOUBLE, vol_avg INTEGER, description VARCHAR, website VARCHAR,
                ceo VARCHAR, full_time_employees INTEGER, ipo_date DATE,
                bronze_file_id VARCHAR, run_id VARCHAR, ingested_at TIMESTAMP
            )
        """)
        for row in profile_data:
            conn.execute(
                """INSERT INTO silver.fmp_company_profile_bulk VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    row.get("symbol"), row.get("companyName"), row.get("exchange"),
                    row.get("exchangeShortName"), row.get("sector"), row.get("industry"),
                    row.get("country"), row.get("currency"), row.get("isEtf"),
                    row.get("isActivelyTrading"), row.get("mktCap"), row.get("price"),
                    row.get("beta"), None, row.get("description"), row.get("website"),
                    row.get("ceo"), None, row.get("ipoDate"),
                    "test-file-1", "test-run-1", "2026-01-17T00:00:00",
                ],
            )

        # GoldDimService._build_dim_instrument also unions silver.fmp_eod_bulk_price
        conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.fmp_eod_bulk_price (
                symbol VARCHAR, date DATE, open DOUBLE, high DOUBLE, low DOUBLE,
                close DOUBLE, adj_close DOUBLE, volume BIGINT,
                bronze_file_id VARCHAR, run_id VARCHAR, ingested_at TIMESTAMP
            )
        """)

        # ------------------------------------------------------------------
        # Static Gold dimension tables
        # ------------------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold.dim_instrument_type (
                instrument_type_sk SMALLINT PRIMARY KEY,
                instrument_type VARCHAR NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO gold.dim_instrument_type VALUES
            (1,'commodity'),(2,'crypto'),(3,'etf'),(4,'fx'),
            (5,'index'),(6,'stock'),(7,'fund'),(8,'trust')
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold.dim_exchange (
                exchange_sk SMALLINT PRIMARY KEY,
                exchange_code VARCHAR NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO gold.dim_exchange VALUES
            (1,'NASDAQ'),(2,'NYSE'),(3,'AMEX')
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold.dim_sector (
                sector_sk SMALLINT PRIMARY KEY,
                sector VARCHAR NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO gold.dim_sector VALUES
            (1,'Basic Materials'),(2,'Communication Services'),(3,'Consumer Cyclical'),
            (4,'Consumer Defensive'),(5,'Energy'),(6,'Financial Services'),
            (7,'Healthcare'),(8,'Industrials'),(9,'Real Estate'),
            (10,'Technology'),(11,'Utilities'),(12,'Unknown')
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold.dim_industry (
                industry_sk SMALLINT PRIMARY KEY,
                industry VARCHAR NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO gold.dim_industry VALUES
            (1,'Consumer Electronics'),
            (2,'Software\u2014Infrastructure'),
            (3,'Internet Content & Information'),
            (4,'Unknown')
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS gold.dim_country (
                country_sk SMALLINT PRIMARY KEY,
                country_code VARCHAR NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO gold.dim_country VALUES
            (1,'US'),(2,'GB'),(3,'CA')
        """)

        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS gold.instrument_sk_seq START 1;
            CREATE TABLE IF NOT EXISTS gold.dim_instrument (
                instrument_sk INTEGER PRIMARY KEY DEFAULT nextval('gold.instrument_sk_seq'),
                symbol VARCHAR NOT NULL UNIQUE,
                instrument_type_sk SMALLINT,
                exchange_sk SMALLINT,
                sector_sk SMALLINT,
                industry_sk SMALLINT,
                country_sk SMALLINT,
                is_etf BOOLEAN NOT NULL DEFAULT FALSE,
                is_actively_trading BOOLEAN NOT NULL DEFAULT TRUE,
                gold_build_id VARCHAR,
                model_version VARCHAR,
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS gold.company_sk_seq START 1;
            CREATE TABLE IF NOT EXISTS gold.dim_company (
                company_sk INTEGER PRIMARY KEY DEFAULT nextval('gold.company_sk_seq'),
                symbol VARCHAR NOT NULL UNIQUE,
                instrument_sk INTEGER,
                company_name VARCHAR,
                ceo VARCHAR,
                website VARCHAR,
                description VARCHAR,
                full_time_employees INTEGER,
                ipo_date DATE,
                currency VARCHAR,
                country_sk SMALLINT,
                exchange_sk SMALLINT,
                sector_sk SMALLINT,
                industry_sk SMALLINT,
                gold_build_id VARCHAR,
                model_version VARCHAR,
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)

    svc = GoldDimService(bootstrap=mem_duck)
    counts = svc.build(run_id="test-run-1")

    assert counts["dim_instrument"] >= len(profile_data)
    assert counts["dim_company"] >= len(profile_data)
