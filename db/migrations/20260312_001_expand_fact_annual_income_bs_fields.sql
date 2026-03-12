-- Migration: 20260312_001
-- Expand gold.fact_annual with new income statement fields (Pillars 1,4,5,6),
-- balance sheet fields (Pillars 4,6), FMP key metrics (Pillar 1), and
-- FMP ratios (Pillars 1,2,3,5). All columns are nullable DOUBLE.

ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS research_and_development_expenses       DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS selling_general_and_administrative_expenses DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS interest_expense                        DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS income_before_tax                       DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS income_tax_expense                      DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS depreciation_and_amortization           DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS deferred_revenue                        DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS goodwill_and_intangible_assets          DOUBLE;

-- From fmp_key_metrics_bulk_annual
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS roic                       DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS invested_capital           DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS capex_to_ocf               DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS ev_to_ebitda               DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS days_sales_outstanding     DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS days_payables_outstanding  DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS days_inventory             DOUBLE;

-- From fmp_ratios_bulk_annual
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS gross_profit_margin        DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS operating_profit_margin    DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS net_profit_margin          DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS effective_tax_rate         DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS debt_ratio                 DOUBLE;
ALTER TABLE gold.fact_annual ADD COLUMN IF NOT EXISTS interest_coverage          DOUBLE;
