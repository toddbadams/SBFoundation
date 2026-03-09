-- Gold layer: fact tables (built from Silver + dims by GoldFactService)

CREATE SEQUENCE IF NOT EXISTS gold.gold_build_seq START 1;

-- ops.gold_build: audit trail for each Gold build
CREATE TABLE IF NOT EXISTS ops.gold_build (
    gold_build_id  INTEGER PRIMARY KEY DEFAULT nextval('gold.gold_build_seq'),
    run_id         VARCHAR   NOT NULL,
    model_version  VARCHAR,
    started_at     TIMESTAMP NOT NULL,
    finished_at    TIMESTAMP,
    status         VARCHAR   NOT NULL DEFAULT 'running',
    error_message  VARCHAR,
    tables_built   VARCHAR[],
    row_counts     VARCHAR
);

-- fact_eod: one row per (instrument_sk, date_sk)
CREATE TABLE IF NOT EXISTS gold.fact_eod (
    instrument_sk     INTEGER  NOT NULL REFERENCES gold.dim_instrument(instrument_sk),
    date_sk           INTEGER  NOT NULL REFERENCES gold.dim_date(date_sk),
    open              DOUBLE,
    high              DOUBLE,
    low               DOUBLE,
    close             DOUBLE,
    adj_close         DOUBLE,
    volume            BIGINT,
    unadjusted_volume BIGINT,
    change            DOUBLE,
    change_pct        DOUBLE,
    vwap              DOUBLE,
    -- Placeholder columns for future feature/signal pipeline
    momentum_1m       DOUBLE,
    momentum_3m       DOUBLE,
    momentum_6m       DOUBLE,
    momentum_12m      DOUBLE,
    volatility_30d    DOUBLE,
    gold_build_id     INTEGER  REFERENCES ops.gold_build(gold_build_id),
    model_version     VARCHAR,
    updated_at        TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_sk, date_sk)
);

-- fact_quarter: one row per (instrument_sk, period, calendar_year)
CREATE TABLE IF NOT EXISTS gold.fact_quarter (
    instrument_sk             INTEGER  NOT NULL REFERENCES gold.dim_instrument(instrument_sk),
    period                    VARCHAR  NOT NULL,
    calendar_year             INTEGER  NOT NULL,
    period_date_sk            INTEGER  REFERENCES gold.dim_date(date_sk),
    reported_currency         VARCHAR,
    revenue                   DOUBLE,
    gross_profit              DOUBLE,
    operating_income          DOUBLE,
    net_income                DOUBLE,
    ebitda                    DOUBLE,
    eps                       DOUBLE,
    eps_diluted               DOUBLE,
    total_assets              DOUBLE,
    total_current_assets      DOUBLE,
    total_liabilities         DOUBLE,
    total_current_liabilities DOUBLE,
    total_stockholders_equity DOUBLE,
    cash_and_cash_equivalents DOUBLE,
    long_term_debt            DOUBLE,
    total_debt                DOUBLE,
    net_debt                  DOUBLE,
    operating_cash_flow       DOUBLE,
    capital_expenditure       DOUBLE,
    free_cash_flow            DOUBLE,
    dividends_paid            DOUBLE,
    gold_build_id             INTEGER  REFERENCES ops.gold_build(gold_build_id),
    model_version             VARCHAR,
    updated_at                TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_sk, period, calendar_year)
);

-- fact_annual: one row per (instrument_sk, calendar_year)
CREATE TABLE IF NOT EXISTS gold.fact_annual (
    instrument_sk             INTEGER  NOT NULL REFERENCES gold.dim_instrument(instrument_sk),
    calendar_year             INTEGER  NOT NULL,
    period_date_sk            INTEGER  REFERENCES gold.dim_date(date_sk),
    reported_currency         VARCHAR,
    revenue                   DOUBLE,
    gross_profit              DOUBLE,
    operating_income          DOUBLE,
    net_income                DOUBLE,
    ebitda                    DOUBLE,
    eps                       DOUBLE,
    eps_diluted               DOUBLE,
    total_assets              DOUBLE,
    total_current_assets      DOUBLE,
    total_liabilities         DOUBLE,
    total_current_liabilities DOUBLE,
    total_stockholders_equity DOUBLE,
    cash_and_cash_equivalents DOUBLE,
    long_term_debt            DOUBLE,
    total_debt                DOUBLE,
    net_debt                  DOUBLE,
    operating_cash_flow       DOUBLE,
    capital_expenditure       DOUBLE,
    free_cash_flow            DOUBLE,
    dividends_paid            DOUBLE,
    gold_build_id             INTEGER  REFERENCES ops.gold_build(gold_build_id),
    model_version             VARCHAR,
    updated_at                TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_sk, calendar_year)
);
