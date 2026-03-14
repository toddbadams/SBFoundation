from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Final

import duckdb

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


# FMP market risk premium country name → ISO 3166-1 alpha-2 code
_COUNTRY_TO_ISO: Final[dict[str, str]] = {
    "United States": "US", "Canada": "CA", "United Kingdom": "GB",
    "Germany": "DE", "France": "FR", "Japan": "JP", "China": "CN",
    "Hong Kong": "HK", "Singapore": "SG", "India": "IN",
    "South Korea": "KR", "Taiwan": "TW", "Brazil": "BR", "Mexico": "MX",
    "Italy": "IT", "Spain": "ES", "Netherlands": "NL", "Sweden": "SE",
    "Switzerland": "CH", "Norway": "NO", "Denmark": "DK", "Finland": "FI",
    "Belgium": "BE", "Austria": "AT", "Australia": "AU", "New Zealand": "NZ",
    "Israel": "IL", "South Africa": "ZA", "Russia": "RU", "Poland": "PL",
    "Czech Republic": "CZ", "Hungary": "HU", "Greece": "GR", "Turkey": "TR",
    "Indonesia": "ID", "Malaysia": "MY", "Thailand": "TH", "Philippines": "PH",
    "Argentina": "AR", "Chile": "CL", "Colombia": "CO", "Peru": "PE",
    "United Arab Emirates": "AE", "Saudi Arabia": "SA", "Egypt": "EG",
    "Nigeria": "NG", "Ireland": "IE", "Portugal": "PT", "Luxembourg": "LU",
    "Iceland": "IS", "Cyprus": "CY", "Malta": "MT", "Pakistan": "PK",
    "Bangladesh": "BD", "Vietnam": "VN", "Ukraine": "UA", "Romania": "RO",
    "Bulgaria": "BG", "Serbia": "RS", "Croatia": "HR", "Slovenia": "SI",
    "Slovakia": "SK", "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT",
    "Kazakhstan": "KZ", "Kenya": "KE", "Ghana": "GH", "Morocco": "MA",
    "Algeria": "DZ", "Tunisia": "TN", "Sri Lanka": "LK", "Myanmar": "MM",
    "Cambodia": "KH",
}

# (raw column in 'rolled' CTE, output _f column in fact_moat_annual, inverted)
# inverted=True → lower raw value = better score (scale is flipped to [0,1])
_FEATS: Final[list[tuple[str, str, bool]]] = [
    ("roic_raw",                 "roic_f",                          False),
    ("roic_spread_raw",          "roic_spread_f",                   False),
    ("roic_spread_5y_mean_raw",  "roic_spread_5y_mean_f",           False),
    ("roic_spread_trend_raw",    "roic_spread_trend_f",             False),
    ("gross_margin_raw",         "gross_margin_f",                  False),
    ("operating_margin_raw",     "operating_margin_f",              False),
    ("fcf_margin_raw",           "fcf_margin_f",                    False),
    ("margin_volatility_raw",    "margin_volatility_f",             True),
    ("recession_resilience_raw", "revenue_recession_resilience_f",  False),
    ("revenue_growth_raw",       "revenue_growth_f",                False),
    ("deferred_rev_pct_raw",     "deferred_rev_pct_f",              False),
    ("sm_pct_raw",               "sm_pct_f",                        True),
    ("cogs_ratio_raw",           "cogs_ratio_f",                    True),
    ("sga_ratio_raw",            "sga_ratio_f",                     True),
    ("asset_turnover_raw",       "asset_turnover_f",                False),
    ("rev_per_employee_raw",     "rev_per_employee_f",              False),
    ("rd_pct_raw",               "rd_pct_f",                        False),
    ("intangibles_pct_raw",      "intangibles_pct_f",               False),
    ("incremental_roic_raw",     "incremental_roic_f",              False),
]


def _country_case_sql() -> str:
    """CASE expression mapping FMP country name to ISO code."""
    clauses = "\n".join(
        f"            WHEN '{name}' THEN '{code}'"
        for name, code in _COUNTRY_TO_ISO.items()
    )
    return f"CASE mrp.country\n{clauses}\n            ELSE NULL\n        END"


def _stats_cols_sql() -> str:
    """SQL columns for one stats CTE (ind or sec): p01, p99, mean, std per feature."""
    parts = []
    for raw, _, _ in _FEATS:
        parts.extend([
            f"        QUANTILE_CONT({raw}, 0.01) AS {raw}_p01",
            f"        QUANTILE_CONT({raw}, 0.99) AS {raw}_p99",
            f"        AVG({raw})                 AS {raw}_mean",
            f"        STDDEV({raw})              AS {raw}_std",
        ])
    return ",\n".join(parts)


def _norm_expr(raw: str, inverted: bool) -> str:
    """SQL CASE expression that winsorizes + z-scores + scales raw to [0,1].

    Uses industry stats (ind.) when peer_n >= 10, sector stats (sec.) as fallback,
    0.5 (neutral) when neither has enough peers or raw is NULL.

    For inverted features the z-score is negated so lower → higher score.
    """
    sign = "-" if inverted else ""
    return f"""
        CASE
            WHEN r.{raw} IS NULL THEN NULL
            WHEN ind.peer_n >= 10 THEN
                GREATEST(0.0, LEAST(1.0, (
                    {sign}(GREATEST(COALESCE(ind.{raw}_p01, r.{raw}),
                           LEAST(COALESCE(ind.{raw}_p99, r.{raw}), r.{raw}))
                     - COALESCE(ind.{raw}_mean, r.{raw}))
                    / NULLIF(ind.{raw}_std, 0.0) + 3.0
                ) / 6.0))
            WHEN sec.peer_n >= 5 THEN
                GREATEST(0.0, LEAST(1.0, (
                    {sign}(GREATEST(COALESCE(sec.{raw}_p01, r.{raw}),
                           LEAST(COALESCE(sec.{raw}_p99, r.{raw}), r.{raw}))
                     - COALESCE(sec.{raw}_mean, r.{raw}))
                    / NULLIF(sec.{raw}_std, 0.0) + 3.0
                ) / 6.0))
            ELSE 0.5
        END"""


def _null_safe_avg(*cols: str) -> str:
    """Average of cols, treating NULL as 0.5 (neutral) and ignoring columns that are
    entirely NULL by counting only non-NULL contributions."""
    n = len(cols)
    sum_parts = " + ".join(f"COALESCE({c}, 0.5)" for c in cols)
    return f"({sum_parts}) / {n}.0"


class MoatFeatureService:
    """Computes all six moat pillar sub-scores and the composite moat_score_s.

    All feature computations, winsorization, z-score normalization, and MERGE
    writes are performed entirely in DuckDB SQL.  Python is only used to:
      - check which Silver tables are available
      - assemble the SQL string (conditional CTEs for optional tables)
      - execute the statement and return the row count

    Reads from:
      gold.fact_annual, gold.dim_instrument, gold.dim_company, gold.dim_country
      silver.fred_dgs10 (rf), silver.fred_usrecm (recession flags)
      silver.fmp_market_risk_premium (ERP by country)
      silver.fmp_company_profile_bulk (beta)

    Writes to: gold.fact_moat_annual (UPSERT on instrument_sk, calendar_year)
    """

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap(logger=self._logger)
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def build(self, gold_build_id: int | None = None, run_id: str | None = None) -> int:
        """Compute moat features and upsert into gold.fact_moat_annual. Returns row count."""
        model_version = _git_sha()
        now = datetime.now(timezone.utc).isoformat()
        self._logger.info("MoatFeatureService: building fact_moat_annual", run_id=run_id)

        with self._bootstrap.gold_transaction() as conn:
            if not self._gold_tables_exist(conn):
                self._logger.info(
                    "MoatFeatureService: required Gold tables missing — skipping", run_id=run_id
                )
                return 0
            flags = self._silver_flags(conn)
            self._logger.info(f"MoatFeatureService: silver flags={flags}", run_id=run_id)
            sql = self._build_moat_sql(flags, gold_build_id, model_version, now)
            conn.execute(sql)
            row = conn.execute("SELECT COUNT(*) FROM gold.fact_moat_annual").fetchone()
            count = row[0] if row else 0

        self._logger.info(f"MoatFeatureService: fact_moat_annual rows={count}", run_id=run_id)
        return count

    # ------------------------------------------------------------------
    # Existence checks
    # ------------------------------------------------------------------

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()
        return bool(row and row[0] > 0)

    def _gold_tables_exist(self, conn: duckdb.DuckDBPyConnection) -> bool:
        required = [
            ("gold", "fact_annual"),
            ("gold", "dim_instrument"),
            ("gold", "dim_company"),
            ("gold", "fact_moat_annual"),
        ]
        return all(self._table_exists(conn, s, t) for s, t in required)

    def _silver_flags(self, conn: duckdb.DuckDBPyConnection) -> dict[str, bool]:
        tables = ["fred_dgs10", "fred_usrecm", "fmp_market_risk_premium", "fmp_company_profile_bulk"]
        return {t: self._table_exists(conn, "silver", t) for t in tables}

    # ------------------------------------------------------------------
    # SQL assembly
    # ------------------------------------------------------------------

    def _build_moat_sql(
        self,
        flags: dict[str, bool],
        gold_build_id: int | None,
        model_version: str,
        now: str,
    ) -> str:
        gid = "NULL" if gold_build_id is None else str(gold_build_id)
        mv = model_version.replace("'", "''")

        rf_cte = self._rf_cte(flags["fred_dgs10"])
        rec_cte = self._recession_cte(flags["fred_usrecm"])
        erp_cte = self._erp_cte(flags["fmp_market_risk_premium"])
        beta_cte = self._beta_cte(flags["fmp_company_profile_bulk"])
        stats_cols = _stats_cols_sql()

        norm_cols = ",\n".join(
            f"        {_norm_expr(raw, inv).strip()} AS {out}"
            for raw, out, inv in _FEATS
        )

        return f"""
INSERT INTO gold.fact_moat_annual (
    instrument_sk, calendar_year, industry_peer_n, benchmark_level,
    roic_f, wacc_f, roic_spread_f, roic_spread_5y_mean_f, roic_spread_trend_f, profitability_s,
    gross_margin_f, operating_margin_f, fcf_margin_f, margin_volatility_f,
    revenue_recession_resilience_f, stability_s,
    revenue_growth_f, gross_margin_vs_industry_f, operating_margin_vs_industry_f, competitive_s,
    deferred_rev_pct_f, sm_pct_f, lock_in_s,
    cogs_ratio_f, sga_ratio_f, asset_turnover_f, rev_per_employee_f, cost_advantage_s,
    rd_pct_f, intangibles_pct_f, incremental_roic_f, reinvestment_s,
    moat_score_s, gold_build_id, model_version, updated_at
)
WITH
-- ── Step 1: risk-free rate (DGS10 annual average) ─────────────────────────────
rf_by_year AS (
{rf_cte}
),

-- ── Step 2: recession calendar years ──────────────────────────────────────────
recession_by_year AS (
{rec_cte}
),

-- ── Step 3: ERP by ISO country code (from FMP market risk premium table) ──────
{erp_cte},

-- ── Step 4: beta from company profile ─────────────────────────────────────────
beta_src AS (
{beta_cte}
),

-- ── Step 5: base join ─────────────────────────────────────────────────────────
base AS (
    SELECT
        fa.instrument_sk,
        fa.calendar_year,
        di.symbol,
        di.sector_sk,
        di.industry_sk,
        dc.country_code,
        fa.revenue,
        fa.gross_profit,
        fa.operating_income,
        fa.free_cash_flow,
        COALESCE(fa.research_and_development_expenses,            0.0) AS rd,
        COALESCE(fa.selling_general_and_administrative_expenses,  0.0) AS sga,
        COALESCE(fa.interest_expense,    0.0) AS interest_expense,
        fa.income_before_tax,
        COALESCE(fa.income_tax_expense,  0.0) AS income_tax_expense,
        COALESCE(fa.total_assets,        0.0) AS total_assets,
        COALESCE(fa.total_debt,          0.0) AS total_debt,
        COALESCE(fa.total_stockholders_equity, 0.0) AS total_equity,
        COALESCE(fa.deferred_revenue,    0.0) AS deferred_revenue,
        COALESCE(fa.goodwill_and_intangible_assets, 0.0) AS intangibles,
        fa.roic,
        fa.invested_capital,
        COALESCE(comp.full_time_employees::DOUBLE, 0.0) AS employees,
        COALESCE(bs.beta,  1.0) AS beta,
        COALESCE(erp.erp,  (SELECT erp FROM us_erp LIMIT 1), 0.055) AS erp,
        COALESCE(rf.rf,    0.04) AS rf
    FROM gold.fact_annual fa
    JOIN  gold.dim_instrument di   ON di.instrument_sk  = fa.instrument_sk
    LEFT JOIN gold.dim_company    comp ON comp.instrument_sk = fa.instrument_sk
    LEFT JOIN gold.dim_country    dc   ON dc.country_sk      = comp.country_sk
    LEFT JOIN beta_src            bs   ON bs.symbol           = di.symbol
    LEFT JOIN erp_by_code         erp  ON erp.country_code    = dc.country_code
    LEFT JOIN rf_by_year          rf   ON rf.calendar_year    = fa.calendar_year
    WHERE fa.revenue IS NOT NULL AND fa.revenue > 0
),

-- ── Step 6: raw feature ratios and WACC ───────────────────────────────────────
raw AS (
    SELECT
        instrument_sk, calendar_year, sector_sk, industry_sk,
        revenue,
        -- WACC (capped [0.04, 0.25] for sanity)
        GREATEST(0.04, LEAST(0.25,
            CASE
                WHEN total_debt + total_equity <= 0 THEN 0.08
                ELSE
                    total_equity / NULLIF(total_debt + total_equity, 0)
                    * GREATEST(0.04, rf + GREATEST(0.0, beta) * erp)
                    + total_debt / NULLIF(total_debt + total_equity, 0)
                    * GREATEST(0.02, LEAST(0.30,
                        CASE WHEN total_debt > 0 AND interest_expense > 0
                             THEN interest_expense / total_debt
                             ELSE 0.05 END))
                    * (1.0 - GREATEST(0.0, LEAST(0.5,
                        CASE WHEN income_before_tax > 0
                             THEN income_tax_expense / income_before_tax
                             ELSE 0.21 END)))
            END
        )) AS wacc_raw,
        COALESCE(roic, 0.0)                                             AS roic_raw,
        -- Pillar 2
        gross_profit     / NULLIF(revenue, 0)                          AS gross_margin_raw,
        operating_income / NULLIF(revenue, 0)                          AS operating_margin_raw,
        COALESCE(free_cash_flow, 0.0) / NULLIF(revenue, 0)            AS fcf_margin_raw,
        -- Pillar 4
        deferred_revenue / NULLIF(revenue, 0)                          AS deferred_rev_pct_raw,
        GREATEST(0.0, sga - rd) / NULLIF(revenue, 0)                  AS sm_pct_raw,
        -- Pillar 5
        GREATEST(0.0, revenue - gross_profit) / NULLIF(revenue, 0)    AS cogs_ratio_raw,
        sga / NULLIF(revenue, 0)                                       AS sga_ratio_raw,
        revenue / NULLIF(total_assets, 0)                              AS asset_turnover_raw,
        CASE WHEN employees > 0 THEN revenue / employees ELSE NULL END AS rev_per_employee_raw,
        -- Pillar 6
        rd / NULLIF(revenue, 0)                                        AS rd_pct_raw,
        intangibles / NULLIF(total_assets, 0)                          AS intangibles_pct_raw,
        COALESCE(roic, 0.0)                                            AS roic_for_incr,
        invested_capital                                                AS ic
    FROM base
),

-- ── Step 7: rolling window features (LAG / rolling stats) ─────────────────────
rolled_base AS (
    SELECT
        r.*,
        r.roic_raw - r.wacc_raw                                    AS roic_spread_raw,
        -- 5Y rolling mean of spread
        AVG(r.roic_raw - r.wacc_raw) OVER (
            PARTITION BY r.instrument_sk ORDER BY r.calendar_year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        )                                                          AS roic_spread_5y_mean_raw,
        -- 5Y slope of spread (linear approx: (current − 4Y-ago) / 4)
        ((r.roic_raw - r.wacc_raw) - LAG(r.roic_raw - r.wacc_raw, 4) OVER (
            PARTITION BY r.instrument_sk ORDER BY r.calendar_year
        )) / 4.0                                                   AS roic_spread_trend_raw,
        -- 5Y stddev of operating margin (inverted: lower = more stable)
        STDDEV(r.operating_margin_raw) OVER (
            PARTITION BY r.instrument_sk ORDER BY r.calendar_year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        )                                                          AS margin_volatility_raw,
        -- YoY revenue growth
        r.revenue / NULLIF(LAG(r.revenue, 1) OVER (
            PARTITION BY r.instrument_sk ORDER BY r.calendar_year
        ), 0) - 1                                                  AS revenue_growth_raw,
        -- Incremental ROIC: Δ(NOPAT) / Δ(IC) over 3Y
        CASE
            WHEN r.ic IS NOT NULL
             AND LAG(r.ic, 3) OVER (PARTITION BY r.instrument_sk ORDER BY r.calendar_year) IS NOT NULL
             AND ABS(r.ic - LAG(r.ic, 3) OVER (PARTITION BY r.instrument_sk ORDER BY r.calendar_year)) > 0
            THEN (r.roic_for_incr * r.ic
                  - LAG(r.roic_for_incr * r.ic, 3) OVER (
                        PARTITION BY r.instrument_sk ORDER BY r.calendar_year))
                 / NULLIF(ABS(r.ic - LAG(r.ic, 3) OVER (
                        PARTITION BY r.instrument_sk ORDER BY r.calendar_year)), 0)
            ELSE NULL
        END                                                        AS incremental_roic_raw
    FROM raw r
),

-- Step 7b: recession resilience (requires joining recession_by_year)
rolled AS (
    SELECT
        rb.*,
        -- avg YoY revenue growth in recession years, trailing 10Y window
        AVG(CASE WHEN rec.calendar_year IS NOT NULL
                 THEN rb.revenue_growth_raw ELSE NULL END) OVER (
            PARTITION BY rb.instrument_sk ORDER BY rb.calendar_year
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS recession_resilience_raw
    FROM rolled_base rb
    LEFT JOIN recession_by_year rec ON rec.calendar_year = rb.calendar_year
),

-- ── Step 8: industry and sector aggregate stats for normalization ──────────────
ind_stats AS (
    SELECT
        industry_sk,
        calendar_year,
        COUNT(*) AS peer_n,
{stats_cols}
    FROM rolled
    WHERE industry_sk IS NOT NULL
    GROUP BY industry_sk, calendar_year
),

sec_stats AS (
    SELECT
        sector_sk,
        calendar_year,
        COUNT(*) AS peer_n,
{stats_cols}
    FROM rolled
    WHERE sector_sk IS NOT NULL
    GROUP BY sector_sk, calendar_year
),

-- ── Step 9: normalised _f features ────────────────────────────────────────────
normalized AS (
    SELECT
        r.instrument_sk,
        r.calendar_year,
        r.wacc_raw                              AS wacc_f,   -- raw %, not normalised
        COALESCE(ind.peer_n, 0)::INTEGER        AS industry_peer_n,
        CASE WHEN COALESCE(ind.peer_n, 0) >= 10 THEN 'industry' ELSE 'sector' END AS benchmark_level,
        -- Percentile-rank features for Pillar 3 (use window functions directly)
        PERCENT_RANK() OVER (
            PARTITION BY r.industry_sk, r.calendar_year ORDER BY r.gross_margin_raw
        )                                       AS gross_margin_vs_industry_f,
        PERCENT_RANK() OVER (
            PARTITION BY r.industry_sk, r.calendar_year ORDER BY r.operating_margin_raw
        )                                       AS operating_margin_vs_industry_f,
        -- Z-score normalised features (winsorise → z-score → scale [0,1])
{norm_cols}
    FROM rolled r
    LEFT JOIN ind_stats ind ON ind.industry_sk  = r.industry_sk
                            AND ind.calendar_year = r.calendar_year
    LEFT JOIN sec_stats sec ON sec.sector_sk     = r.sector_sk
                            AND sec.calendar_year = r.calendar_year
),

-- ── Step 10: pillar sub-scores and composite moat score ───────────────────────
scored AS (
    SELECT
        n.*,
        -- Pillar 1 (30%): profitability
        {_null_safe_avg("n.roic_f", "n.roic_spread_f", "n.roic_spread_5y_mean_f", "n.roic_spread_trend_f")}
            AS profitability_s,
        -- Pillar 2 (25%): stability
        {_null_safe_avg("n.gross_margin_f", "n.operating_margin_f", "n.fcf_margin_f", "n.margin_volatility_f", "n.revenue_recession_resilience_f")}
            AS stability_s,
        -- Pillar 3 (15%): competitive position
        {_null_safe_avg("n.revenue_growth_f", "n.gross_margin_vs_industry_f", "n.operating_margin_vs_industry_f")}
            AS competitive_s,
        -- Pillar 4 (10%): lock-in
        {_null_safe_avg("n.deferred_rev_pct_f", "n.sm_pct_f")}
            AS lock_in_s,
        -- Pillar 5 (15%): cost advantage
        {_null_safe_avg("n.cogs_ratio_f", "n.sga_ratio_f", "n.asset_turnover_f", "n.rev_per_employee_f")}
            AS cost_advantage_s,
        -- Pillar 6 (5%): reinvestment
        {_null_safe_avg("n.rd_pct_f", "n.intangibles_pct_f", "n.incremental_roic_f")}
            AS reinvestment_s
    FROM normalized n
)

SELECT
    s.instrument_sk,
    s.calendar_year,
    s.industry_peer_n,
    s.benchmark_level,
    -- Pillar 1
    s.roic_f, s.wacc_f, s.roic_spread_f, s.roic_spread_5y_mean_f, s.roic_spread_trend_f,
    s.profitability_s,
    -- Pillar 2
    s.gross_margin_f, s.operating_margin_f, s.fcf_margin_f, s.margin_volatility_f,
    s.revenue_recession_resilience_f, s.stability_s,
    -- Pillar 3
    s.revenue_growth_f, s.gross_margin_vs_industry_f, s.operating_margin_vs_industry_f,
    s.competitive_s,
    -- Pillar 4
    s.deferred_rev_pct_f, s.sm_pct_f, s.lock_in_s,
    -- Pillar 5
    s.cogs_ratio_f, s.sga_ratio_f, s.asset_turnover_f, s.rev_per_employee_f,
    s.cost_advantage_s,
    -- Pillar 6
    s.rd_pct_f, s.intangibles_pct_f, s.incremental_roic_f, s.reinvestment_s,
    -- Composite (weighted average of sub-scores)
    0.30 * COALESCE(s.profitability_s, 0.5)
    + 0.25 * COALESCE(s.stability_s,    0.5)
    + 0.15 * COALESCE(s.competitive_s,  0.5)
    + 0.10 * COALESCE(s.lock_in_s,      0.5)
    + 0.15 * COALESCE(s.cost_advantage_s,0.5)
    + 0.05 * COALESCE(s.reinvestment_s, 0.5) AS moat_score_s,
    {gid}    AS gold_build_id,
    '{mv}'  AS model_version,
    now()   AS updated_at
FROM scored s
ON CONFLICT (instrument_sk, calendar_year) DO UPDATE SET
    industry_peer_n                = EXCLUDED.industry_peer_n,
    benchmark_level                = EXCLUDED.benchmark_level,
    roic_f                         = EXCLUDED.roic_f,
    wacc_f                         = EXCLUDED.wacc_f,
    roic_spread_f                  = EXCLUDED.roic_spread_f,
    roic_spread_5y_mean_f          = EXCLUDED.roic_spread_5y_mean_f,
    roic_spread_trend_f            = EXCLUDED.roic_spread_trend_f,
    profitability_s                = EXCLUDED.profitability_s,
    gross_margin_f                 = EXCLUDED.gross_margin_f,
    operating_margin_f             = EXCLUDED.operating_margin_f,
    fcf_margin_f                   = EXCLUDED.fcf_margin_f,
    margin_volatility_f            = EXCLUDED.margin_volatility_f,
    revenue_recession_resilience_f = EXCLUDED.revenue_recession_resilience_f,
    stability_s                    = EXCLUDED.stability_s,
    revenue_growth_f               = EXCLUDED.revenue_growth_f,
    gross_margin_vs_industry_f     = EXCLUDED.gross_margin_vs_industry_f,
    operating_margin_vs_industry_f = EXCLUDED.operating_margin_vs_industry_f,
    competitive_s                  = EXCLUDED.competitive_s,
    deferred_rev_pct_f             = EXCLUDED.deferred_rev_pct_f,
    sm_pct_f                       = EXCLUDED.sm_pct_f,
    lock_in_s                      = EXCLUDED.lock_in_s,
    cogs_ratio_f                   = EXCLUDED.cogs_ratio_f,
    sga_ratio_f                    = EXCLUDED.sga_ratio_f,
    asset_turnover_f               = EXCLUDED.asset_turnover_f,
    rev_per_employee_f             = EXCLUDED.rev_per_employee_f,
    cost_advantage_s               = EXCLUDED.cost_advantage_s,
    rd_pct_f                       = EXCLUDED.rd_pct_f,
    intangibles_pct_f              = EXCLUDED.intangibles_pct_f,
    incremental_roic_f             = EXCLUDED.incremental_roic_f,
    reinvestment_s                 = EXCLUDED.reinvestment_s,
    moat_score_s                   = EXCLUDED.moat_score_s,
    gold_build_id                  = EXCLUDED.gold_build_id,
    model_version                  = EXCLUDED.model_version,
    updated_at                     = EXCLUDED.updated_at
"""

    # ------------------------------------------------------------------
    # CTE builders (return the body of each CTE, not the name+AS)
    # ------------------------------------------------------------------

    def _rf_cte(self, available: bool) -> str:
        if available:
            return """    SELECT
        EXTRACT('year' FROM date)::INTEGER AS calendar_year,
        AVG(CASE WHEN rate BETWEEN 0 AND 20 THEN rate ELSE NULL END) / 100.0 AS rf
    FROM silver.fred_dgs10
    WHERE rate IS NOT NULL
    GROUP BY 1"""
        return "    SELECT NULL::INTEGER AS calendar_year, 0.04 AS rf WHERE FALSE"

    def _recession_cte(self, available: bool) -> str:
        if available:
            return """    SELECT DISTINCT EXTRACT('year' FROM date)::INTEGER AS calendar_year
    FROM silver.fred_usrecm
    WHERE recession_flag = 1"""
        return "    SELECT NULL::INTEGER AS calendar_year WHERE FALSE"

    def _erp_cte(self, available: bool) -> str:
        case_sql = _country_case_sql()
        if available:
            body = f"""erp_by_code AS (
    SELECT
        {case_sql} AS country_code,
        mrp.total_equity_risk_premium / 100.0 AS erp
    FROM silver.fmp_market_risk_premium mrp
    WHERE mrp.total_equity_risk_premium IS NOT NULL
),
us_erp AS (
    SELECT erp FROM erp_by_code WHERE country_code = 'US' LIMIT 1
)"""
        else:
            body = """erp_by_code AS (
    SELECT NULL::VARCHAR AS country_code, 0.055 AS erp WHERE FALSE
),
us_erp AS (
    SELECT 0.055 AS erp
)"""
        return body

    def _beta_cte(self, available: bool) -> str:
        if available:
            return """    SELECT DISTINCT ON (symbol) symbol, beta::DOUBLE AS beta
    FROM silver.fmp_company_profile_bulk
    WHERE beta IS NOT NULL AND beta::DOUBLE > 0
    ORDER BY symbol, ingested_at DESC"""
        return "    SELECT NULL::VARCHAR AS symbol, 1.0 AS beta WHERE FALSE"
