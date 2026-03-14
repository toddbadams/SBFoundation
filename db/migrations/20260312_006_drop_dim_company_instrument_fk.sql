-- Migration: 20260312_006
-- Drop FK constraint from dim_company.instrument_sk -> dim_instrument.instrument_sk.
--
-- DuckDB treats UPDATE on a referenced row as delete+insert internally, which fires the
-- FK constraint even when instrument_sk (the PK) is not being modified. This blocks
-- GoldDimService from backfilling sector_sk/country_sk/etc. on dim_instrument rows that
-- are already referenced by dim_company.
--
-- Gold FK integrity is enforced at the application layer (GoldDimService / GoldFactService),
-- consistent with the approach already used for fact tables (see 20260309_003 comment).
--
-- DuckDB does not support ALTER TABLE DROP CONSTRAINT, so we recreate dim_company without
-- the offending REFERENCES clause, preserving all data and column definitions.

CREATE TABLE gold.dim_company_new AS SELECT * FROM gold.dim_company;

DROP TABLE gold.dim_company;

CREATE TABLE gold.dim_company (
    company_sk           INTEGER PRIMARY KEY DEFAULT nextval('gold.company_sk_seq'),
    symbol               VARCHAR  NOT NULL UNIQUE,
    instrument_sk        INTEGER,  -- FK to dim_instrument enforced by application
    company_name         VARCHAR,
    ceo                  VARCHAR,
    website              VARCHAR,
    description          VARCHAR,
    full_time_employees  INTEGER,
    ipo_date             DATE,
    currency             VARCHAR,
    country_sk           SMALLINT REFERENCES gold.dim_country(country_sk),
    exchange_sk          SMALLINT REFERENCES gold.dim_exchange(exchange_sk),
    sector_sk            SMALLINT REFERENCES gold.dim_sector(sector_sk),
    industry_sk          SMALLINT REFERENCES gold.dim_industry(industry_sk),
    gold_build_id        VARCHAR,
    model_version        VARCHAR,
    updated_at           TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO gold.dim_company SELECT * FROM gold.dim_company_new;

DROP TABLE gold.dim_company_new;
