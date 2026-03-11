-- Migration: 20260312_002
-- Expand gold.fact_quarter with new income statement fields (Pillars 1,4,5,6)
-- and balance sheet fields (Pillars 4,6). All columns are nullable DOUBLE.
-- Note: key metrics and ratios columns are annual-only; no quarter expansion needed.

ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS research_and_development_expenses       DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS selling_general_and_administrative_expenses DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS interest_expense                        DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS income_before_tax                       DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS income_tax_expense                      DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS depreciation_and_amortization           DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS deferred_revenue                        DOUBLE;
ALTER TABLE gold.fact_quarter ADD COLUMN IF NOT EXISTS goodwill_and_intangible_assets          DOUBLE;
