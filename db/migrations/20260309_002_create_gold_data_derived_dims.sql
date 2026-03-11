-- Gold layer: data-derived dimension tables (built from Silver by GoldDimService)
-- SKs are stable auto-increment sequences; natural keys (ticker) never change SK.

CREATE SEQUENCE IF NOT EXISTS gold.instrument_sk_seq START 1;
CREATE SEQUENCE IF NOT EXISTS gold.company_sk_seq START 1;

-- dim_instrument: one row per tradeable instrument
CREATE TABLE IF NOT EXISTS gold.dim_instrument (
    instrument_sk        INTEGER PRIMARY KEY DEFAULT nextval('gold.instrument_sk_seq'),
    symbol               VARCHAR  NOT NULL UNIQUE,
    instrument_type_sk   SMALLINT REFERENCES gold.dim_instrument_type(instrument_type_sk),
    exchange_sk          SMALLINT REFERENCES gold.dim_exchange(exchange_sk),
    sector_sk            SMALLINT REFERENCES gold.dim_sector(sector_sk),
    industry_sk          SMALLINT REFERENCES gold.dim_industry(industry_sk),
    country_sk           SMALLINT REFERENCES gold.dim_country(country_sk),
    is_etf               BOOLEAN  NOT NULL DEFAULT FALSE,
    is_actively_trading  BOOLEAN  NOT NULL DEFAULT TRUE,
    gold_build_id        VARCHAR,
    model_version        VARCHAR,
    updated_at           TIMESTAMP NOT NULL DEFAULT now()
);

-- dim_company: one row per company (may share symbol with dim_instrument 1:1)
CREATE TABLE IF NOT EXISTS gold.dim_company (
    company_sk           INTEGER PRIMARY KEY DEFAULT nextval('gold.company_sk_seq'),
    symbol               VARCHAR  NOT NULL UNIQUE,
    instrument_sk        INTEGER  REFERENCES gold.dim_instrument(instrument_sk),
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
