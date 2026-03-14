-- Migration: 20260312_005
-- Create gold.fact_moat_annual: one row per (instrument_sk, calendar_year).
-- All feature columns end in _f; all signal/score columns end in _s.
-- Populated by MoatFeatureService; NULL until first feature run.

CREATE TABLE IF NOT EXISTS gold.fact_moat_annual (
    instrument_sk                    INTEGER  NOT NULL,
    calendar_year                    INTEGER  NOT NULL,
    industry_peer_n                  INTEGER,           -- peer count used for normalization
    benchmark_level                  VARCHAR,           -- 'industry' or 'sector' (fallback)

    -- Pillar 1: Excess Profitability vs Capital Cost
    roic_f                           DOUBLE,            -- ROIC (winsorized, industry z-score → [0,1])
    wacc_f                           DOUBLE,            -- estimated WACC (raw %, not normalized)
    roic_spread_f                    DOUBLE,            -- ROIC − WACC (winsorized, industry z-score → [0,1])
    roic_spread_5y_mean_f            DOUBLE,            -- 5Y rolling mean of spread → [0,1]
    roic_spread_trend_f              DOUBLE,            -- slope of spread over 5Y → [0,1]
    profitability_s                  DOUBLE,            -- composite sub-score [0,1]

    -- Pillar 2: Profit and Cash-Flow Durability
    gross_margin_f                   DOUBLE,
    operating_margin_f               DOUBLE,
    fcf_margin_f                     DOUBLE,
    margin_volatility_f              DOUBLE,            -- StdDev of operating margin 5Y (inverted → [0,1])
    revenue_recession_resilience_f   DOUBLE,            -- avg revenue growth in recession years → [0,1]
    stability_s                      DOUBLE,

    -- Pillar 3: Market Power and Competitive Position
    revenue_growth_f                 DOUBLE,            -- YoY revenue growth (industry z-score → [0,1])
    gross_margin_vs_industry_f       DOUBLE,            -- gross margin percentile within industry [0,1]
    operating_margin_vs_industry_f   DOUBLE,            -- operating margin percentile within industry [0,1]
    competitive_s                    DOUBLE,

    -- Pillar 4: Switching Costs and Customer Lock-In
    deferred_rev_pct_f               DOUBLE,            -- deferred_revenue / revenue → [0,1]
    sm_pct_f                         DOUBLE,            -- (SG&A − R&D) / revenue (inverted → [0,1])
    lock_in_s                        DOUBLE,

    -- Pillar 5: Structural Cost Advantage
    cogs_ratio_f                     DOUBLE,            -- COGS / revenue (inverted → [0,1])
    sga_ratio_f                      DOUBLE,            -- SG&A / revenue (inverted → [0,1])
    asset_turnover_f                 DOUBLE,            -- revenue / total_assets → [0,1]
    rev_per_employee_f               DOUBLE,            -- revenue / headcount → [0,1]
    cost_advantage_s                 DOUBLE,

    -- Pillar 6: Innovation and Intangible Reinvestment
    rd_pct_f                         DOUBLE,            -- R&D / revenue → [0,1]
    intangibles_pct_f                DOUBLE,            -- goodwill_and_intangibles / total_assets → [0,1]
    incremental_roic_f               DOUBLE,            -- ΔNOPAT / ΔIC rolling 3Y → [0,1]
    reinvestment_s                   DOUBLE,

    -- Composite Moat Score (signal — ends in _s)
    moat_score_s                     DOUBLE,            -- weighted composite [0,1]

    gold_build_id                    INTEGER,
    model_version                    VARCHAR,
    updated_at                       TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_sk, calendar_year)
);
