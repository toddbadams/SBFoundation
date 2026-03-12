-- Migration: 20260312_003
-- Remove columns from gold.fact_eod that are absent from the FMP eod-bulk endpoint.
-- The FMP bulk EOD response only returns: symbol, date, open, high, low, close, adjClose, volume.
-- unadjusted_volume, change, change_pct, vwap are never populated and are not needed:
--   unadjusted_volume: redundant with volume (splits do not adjust volume)
--   change / change_pct: derivable as LAG(adj_close) in the feature dev phase
--   vwap: requires intraday tick data; not computable from EOD; not used in any moat pillar

ALTER TABLE gold.fact_eod DROP COLUMN IF EXISTS unadjusted_volume;
ALTER TABLE gold.fact_eod DROP COLUMN IF EXISTS change;
ALTER TABLE gold.fact_eod DROP COLUMN IF EXISTS change_pct;
ALTER TABLE gold.fact_eod DROP COLUMN IF EXISTS vwap;
