-- Migration: 20260312_004
-- Rename fact_eod placeholder feature columns to _f suffix (mandatory per CLAUDE.md §5.2).
-- These columns have been NULL since creation — renaming preserves all data.

ALTER TABLE gold.fact_eod RENAME COLUMN momentum_1m    TO momentum_1m_f;
ALTER TABLE gold.fact_eod RENAME COLUMN momentum_3m    TO momentum_3m_f;
ALTER TABLE gold.fact_eod RENAME COLUMN momentum_6m    TO momentum_6m_f;
ALTER TABLE gold.fact_eod RENAME COLUMN momentum_12m   TO momentum_12m_f;
ALTER TABLE gold.fact_eod RENAME COLUMN volatility_30d TO volatility_30d_f;
