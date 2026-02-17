-- Migration: Create ops.instrument_catalog table
-- Date: 2026-02-17
-- Purpose: Create operational instrument catalog to replace broken silver.instrument

-- Create ops.instrument_catalog with operational fields only
CREATE TABLE IF NOT EXISTS ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
);

-- Create indexes for query performance
CREATE INDEX IF NOT EXISTS idx_instrument_catalog_symbol
ON ops.instrument_catalog(symbol);

CREATE INDEX IF NOT EXISTS idx_instrument_catalog_type_active
ON ops.instrument_catalog(instrument_type, is_active);

-- Note: Data will be populated by InstrumentCatalogService during orchestration
-- from Silver instrument list tables (fmp_stock_list, fmp_etf_list, etc.)
