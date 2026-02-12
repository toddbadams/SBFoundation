# Quantitative Value Feature Pipeline

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/AI_context/PLANS.md` from the repository root. Maintain this document in accordance with that file.

## Purpose / Big Picture

After implementing this plan, the platform will compute a complete set of Quantitative Value features (earnings quality and manipulation, financial distress, value and durability, and financial strength) for each ticker and fiscal quarter. The results will be stored in a new `gold.features` fact table with both raw and normalized values so that screening and scoring can read a single, stable output. You can see it working by running the gold build with the feature step enabled, then querying `gold.features` to confirm that a ticker has non-null rows for the expected feature ids for the most recent quarter.

## Findings

Finding: The prior Quantitative Value spec contained character encoding corruption that obscured operators and punctuation; this plan normalizes all formulas to ASCII so they are safe to implement.

Finding: The financial strength delta rules conflicted between sections (t-4 versus t-1). This plan resolves the conflict by using TTM at t versus TTM shifted 4 quarters for all delta-based financial strength features.

Finding: The financial strength score formula previously read as a multiplication chain; this plan defines it as the sum of the ten binary sub-scores divided by 10.

Finding: The variable name PRICE was reused for EBIT/TEV even though PRICE already denotes log(price) in the distress model; this plan names the value feature `ebit_to_tev` and reserves PRICE for the distress definition.

Finding: Archived calculators in `archive/archive/calculators` define STA and SNOA differently from the current spec; this plan follows the current spec but flags the mismatch for confirmation.

## Questions

Question: Should STA and SNOA follow the archived calculator formulas that use average assets, or should they remain as defined here? This plan assumes the current spec to avoid changing the stated contract.

Question: What weight vectors should be used for NIMTAAVG and EXRETAVG? This plan requires explicit weights in config and will return null when weights are missing.

Question: Are winsorization percentiles of 1% and 99% acceptable defaults for normalization, and should a minimum cross-section size be enforced before z-scoring? This plan uses 1%/99% and requires at least five non-null values per quarter.

Question: Is SPY an acceptable proxy for S&P 500 total return and market cap for EXRETAVG and RSIZE? This plan uses SPY because it is already in the free tier symbol list.

YES, use SPY

Question: Should margin_max_8y be the max of percentile ranks for margin growth and margin stability, or the max of raw values? This plan uses percentile ranks so the metric is scale-neutral.

## Progress

- [x] (2026-01-16 17:31Z) Converted the Quantitative Value spec into ExecPlan format and normalized it to ASCII, adding Findings and Questions sections.
- [ ] (2026-01-16 17:31Z) Implement the Quantitative Value feature pipeline, register `gold.features`, and add validation tests.

## Surprises & Discoveries

- Observation: Archived Beneish, STA, and SNOA calculators exist with test-backed formulas that differ from the current spec.
  Evidence: `archive/archive/calculators/test_beneish_calculators.py`, `archive/archive/calculators/test_sta_calculator.py`, `archive/archive/calculators/test_snoa_calculator.py`.

## Decision Log

- Decision: Use TTM-at-t versus TTM-at-(t-4) for delta-based financial strength features.
  Rationale: The "rolling averages for FS deltas" section defines this explicitly and it aligns with the 32-quarter history rule.
  Date/Author: 2026-01-16 / Codex.

- Decision: Name the EBIT/TEV feature `ebit_to_tev` and keep PRICE for the distress model's log(price) input.
  Rationale: Avoid variable collisions and keep feature ids consistent with the registry list.
  Date/Author: 2026-01-16 / Codex.

- Decision: Use SPY as the S&P 500 proxy for EXRETAVG and RSIZE.
  Rationale: SPY exists in the configured universe and provides a practical benchmark without new data sources.
  Date/Author: 2026-01-16 / Codex.

- Decision: Use normal CDF for manipulation_prob and logistic for distress_prob.
  Rationale: Matches the formulas in the spec and preserves expected probability behavior.
  Date/Author: 2026-01-16 / Codex.

- Decision: Default winsorization percentiles to 1% and 99%, and set norm_value to null when fewer than five non-null values exist for a quarter or when the standard deviation is zero.
  Rationale: Prevents unstable normalization in small or degenerate cross-sections.
  Date/Author: 2026-01-16 / Codex.

- Decision: Keep STA and SNOA formulas as written in this plan pending confirmation.
  Rationale: The current spec is labeled as locked-in; archived formulas will be revisited if the user requests alignment.
  Date/Author: 2026-01-16 / Codex.

## Outcomes & Retrospective

No implementation has been performed yet. This document now contains a complete, self-contained implementation plan and the open questions that must be confirmed for final sign-off.

## Context and Orientation

The repository root is `c:/strawberry`. The data platform ingests data into Bronze, promotes it to Silver, and then loads curated Gold tables using `src/data_layer/orchestrator.py`, `src/data_layer/services/gold/gold_service.py`, and the dataset mapping in `config/dataset_keymap.yaml`. Gold facts are dataclasses under `src/data_layer/facts/...`, such as `src/data_layer/facts/fundamentals/fact_income_statement.py` and `src/data_layer/facts/fundamentals/fact_balance_sheet.py`.

Quantitative Value features do not exist yet. This plan adds a new feature build step that reads existing Gold facts, computes feature values per ticker and fiscal quarter, normalizes them cross-sectionally, and writes a tall feature fact table named `gold.features`. The plan also adds supporting configuration and tests so a novice can reproduce outputs.

A "fiscal quarter end" is the quarter-ending date from quarterly financial statements. "as_of" always refers to that quarter end. "TTM" means trailing twelve months, defined as the rolling sum of the most recent four quarterly values for flow items such as revenue or net income. Balance sheet items use quarter-end values unless a formula explicitly calls for a change, in which case the change is current quarter minus prior quarter. The notation t means the current quarter, t-1 means the prior quarter, and t-4 means the quarter one year earlier.

### Data Sources and Required Inputs

Income statement inputs come from `gold.fact_income_statement`, using quarterly rows with period in `{"Q1", "Q2", "Q3", "Q4"}`. Balance sheet inputs come from `gold.fact_balance_sheet` with the same quarter dates. Cash flow inputs come from `gold.fact_cashflow_statement`. Market cap comes from `gold.fact_market_cap_snapshot`. Enterprise value and share counts come from `gold.fact_enterprise_values`. Daily prices come from `gold.fact_historical_price_eod_dividend_adjusted`. If a required input is missing for a ticker-quarter, the feature is null and the row is marked ineligible.

### Feature Storage Contract

`gold.features` is a tall fact table with grain keys (ticker, as_of_date, feature_id). Store both raw and normalized values along with run metadata. The recommended columns are: ticker, as_of_date, feature_id, raw_value, norm_value, is_eligible, run_id, gold_build_id, model_version. Optionally include company_sk and date_sk if the feature loader can resolve them consistently with other gold facts.

### Null and Eligibility Rules

A feature must return null if any required input is missing or invalid. Invalid means denominators are zero or negative where a ratio is defined (for example total assets, sales, or MTA), or a required historical window is incomplete. The minimum required history is 32 quarters for all features in this plan. There is no imputation; the feature is skipped for that ticker-quarter but other features may still be computed.

### Normalization Contract

Normalization happens cross-sectionally per quarter across all non-null raw values. Apply winsorization by capping values at configured lower and upper percentiles. Then compute z-scores as (value - mean) / standard deviation. If the standard deviation is zero or there are fewer than five non-null values, set norm_value to null for that quarter. Directionality is preserved; the feature definition does not invert signs. Ranking or scoring logic decides whether higher is better.

### Feature Definitions and Rules

All features are quarterly and use the time semantics above. The registry includes the following feature ids grouped by theme: earnings quality and manipulation (scaled_total_accruals, scaled_net_operating_assets, beneish_dsri, beneish_gmi, beneish_aqi, beneish_sgi, beneish_depi, beneish_sgai, beneish_lvgi, beneish_tata, manipulation_logit, manipulation_prob), financial distress (nimtaavg, tlmta, cashmta, exretavg, sigma_3m_ann, rsize, mb, price_log_capped, distress_logit, distress_prob), value and durability (ebit_to_tev, roa_8y_geo, roc_8y, fcfa_8y_on_assets, margin_growth_8y_geo, margin_stability_8y, margin_max_8y), and financial strength (fs_roa, fs_fcfta, fs_accrual, fs_lever, fs_liquid, fs_neqiss, fs_delta_roa, fs_delta_fcfta, fs_delta_margin, fs_delta_turn, financial_strength_score).

#### Earnings Quality and Manipulation

Scaled Total Accruals (scaled_total_accruals):

    STA = (delta_current_assets - delta_cash - delta_current_liabilities + delta_short_term_debt + delta_tax_payables - depreciation_and_amortization_ttm) / total_assets

delta_current_assets is total_current_assets_t minus total_current_assets_{t-1}. delta_cash is cash_and_cash_equivalents_t minus cash_and_cash_equivalents_{t-1}. delta_current_liabilities is total_current_liabilities_t minus total_current_liabilities_{t-1}. delta_short_term_debt is short_term_debt_t minus short_term_debt_{t-1}. delta_tax_payables is tax_payables_t minus tax_payables_{t-1}. depreciation_and_amortization_ttm uses the income statement depreciation_and_amortization rolling sum. total_assets is balance sheet total_assets at t. If any component is missing, STA is null.

Scaled Net Operating Assets (scaled_net_operating_assets):

    operating_assets = total_assets - cash_and_cash_equivalents - short_term_investments
    operating_liabilities = total_liabilities - short_term_debt - long_term_debt
    SNOA = (operating_assets - operating_liabilities) / total_assets

Use quarter-end balance sheet values at t and the same null rules.

Beneish component ratios, using TTM for flow items and quarter-end for balance sheet items. For each ratio, compute the value at t and at t-1, then take the ratio t / (t-1).

    DSRI = (accounts_receivables / sales_ttm) / (accounts_receivables_{t-1} / sales_ttm_{t-1})
    GMI = (gross_margin_ttm_{t-1} / sales_ttm_{t-1}) / (gross_margin_ttm / sales_ttm)
    AQI = (1 - (total_current_assets + property_plant_equipment_net + short_term_investments) / total_assets)
          divided by the same quantity at t-1
    SGI = sales_ttm / sales_ttm_{t-1}
    DEPI = (depreciation_rate_{t-1}) / depreciation_rate_t
           where depreciation_rate = depreciation_and_amortization_ttm / (depreciation_and_amortization_ttm + property_plant_equipment_net)
    SGAI = (selling_general_and_administrative_expenses_ttm / sales_ttm) / (selling_general_and_administrative_expenses_ttm_{t-1} / sales_ttm_{t-1})
    LVGI = (total_liabilities / total_assets) / (total_liabilities_{t-1} / total_assets_{t-1})
    TATA = (net_income_ttm - operating_cash_flow_ttm) / total_assets

Use selling_general_and_administrative_expenses from the income statement; if it is null, use the sum of selling_and_marketing_expenses and general_and_administrative_expenses. sales_ttm uses revenue TTM. gross_margin_ttm is gross_profit TTM.

Manipulation score:

    manipulation_logit = -4.84 + 0.92 * DSRI + 0.528 * GMI + 0.404 * AQI + 0.892 * SGI + 0.115 * DEPI - 0.172 * SGAI + 4.679 * TATA - 0.327 * LVGI
    manipulation_prob = normal_cdf(manipulation_logit)

Implement normal_cdf as 0.5 * (1 + erf(x / sqrt(2))) to avoid extra dependencies.

#### Financial Distress

Define MTA as total_liabilities + market_cap, where market_cap comes from `fact_market_cap_snapshot` at the quarter end (or the closest prior trading day if dates do not align). Use SPY market_cap as the benchmark in RSIZE.

    NIMTA = net_income_ttm / MTA
    NIMTAAVG = weighted_average(NIMTA_t, NIMTA_{t-1}, NIMTA_{t-2}, NIMTA_{t-3})
    TLMTA = total_liabilities / MTA
    CASHMTA = cash_and_cash_equivalents / MTA

EXRETAVG uses quarterly total returns computed from dividend-adjusted close prices at quarter ends:

    quarterly_return = (adj_close_t / adj_close_{t-1}) - 1
    EXRET = log(1 + quarterly_return_stock) - log(1 + quarterly_return_spy)
    EXRETAVG = weighted_average(EXRET_t, EXRET_{t-1}, EXRET_{t-2}, EXRET_{t-3})

Weights for NIMTAAVG and EXRETAVG are required in config. If weights are missing or do not sum to 1, set the feature to null.

SIGMA is annualized volatility of daily log returns over the last 63 trading days ending at the quarter end:

    daily_log_return = log(adj_close_t / adj_close_{t-1})
    sigma_3m_ann = stddev(daily_log_return) * sqrt(252)

RSIZE uses the proxy SPY market cap:

    rsize = log(market_cap / market_cap_spy)

MB uses market to adjusted book value:

    adjusted_book_value = book_value + 0.1 * (market_cap - book_value)
    mb = MTA / adjusted_book_value

book_value uses total_stockholders_equity when available; fall back to total_equity.

PRICE for the distress model is the log of quarter-end price, capped at log(15):

    price_log_capped = min(log(price), log(15))

Use the quarter-end adj_close for price.

Distress score:

    distress_logit = -20.26 * NIMTAAVG + 1.42 * TLMTA - 7.13 * EXRETAVG + 1.41 * sigma_3m_ann - 0.045 * rsize - 2.13 * CASHMTA + 0.075 * mb - 0.058 * price_log_capped - 9.16
    distress_prob = 1 / (1 + exp(-distress_logit))

#### Value and Durability

EBIT to TEV:

    ebit_to_tev = ebit_ttm / enterprise_value

Use ebit from the income statement and enterprise_value from `fact_enterprise_values`.

Eight-year ROA geometric average:

    roa = net_income_ttm / total_assets
    roa_8y_geo = geometric_mean(1 + roa over last 32 quarters) - 1

Eight-year ROC:

    capital = total_assets - total_current_liabilities
    roc = ebit_ttm / capital
    roc_8y = geometric_mean(1 + roc over last 32 quarters) - 1

FCFA over assets:

    fcfa_8y_on_assets = sum(free_cash_flow over last 32 quarters) / total_assets

Margin growth:

    gross_margin = gross_profit_ttm / sales_ttm
    margin_growth_8y_geo = geometric_mean(1 + gross_margin_growth over last 32 quarters) - 1

Define gross_margin_growth as gross_margin_t / gross_margin_{t-1} - 1 and require gross_margin values to be positive. If any required ratio is not positive, set the geometric average to null.

Margin stability:

    margin_stability_8y = mean(gross_margin over last 32 quarters) / stddev(gross_margin over last 32 quarters)

Margin max:

    margin_max_8y = max(percentile_rank(margin_growth_8y_geo), percentile_rank(margin_stability_8y))

Percentile ranks are computed cross-sectionally per quarter before z-scoring.

#### Financial Strength

Base ratios at t use TTM for flows and quarter-end for balance sheet values.

    ROA = net_income_ttm / total_assets
    FCFTA = free_cash_flow_ttm / total_assets
    ACCRUAL = FCFTA - ROA
    LEVER = (long_term_debt_{t-1} / total_assets_{t-1}) - (long_term_debt_t / total_assets_t)
    LIQUID = current_ratio_t - current_ratio_{t-1}
    current_ratio = total_current_assets / total_current_liabilities
    NEQISS = (shares_outstanding_t - shares_outstanding_{t-1}) * price_t

shares_outstanding uses enterprise_values.number_of_shares when available; fall back to income_statement.weighted_average_shs_out or weighted_average_shs_out_dil. price_t uses enterprise_values.stock_price if present, otherwise adj_close.

Binary components:

    fs_roa = 1 if ROA > 0 else 0
    fs_fcfta = 1 if FCFTA > 0 else 0
    fs_accrual = 1 if ACCRUAL > 0 else 0
    fs_lever = 1 if LEVER > 0 else 0
    fs_liquid = 1 if LIQUID > 0 else 0
    fs_neqiss = 1 if NEQISS > 0 else 0

Delta components compare TTM metrics at t versus t-4:

    delta_roa = ROA_t - ROA_{t-4}
    delta_fcfta = FCFTA_t - FCFTA_{t-4}
    delta_margin = gross_margin_t - gross_margin_{t-4}
    delta_turn = turnover_t - turnover_{t-4}
    turnover = sales_ttm / total_assets

Binary delta flags:

    fs_delta_roa = 1 if delta_roa > 0 else 0
    fs_delta_fcfta = 1 if delta_fcfta > 0 else 0
    fs_delta_margin = 1 if delta_margin > 0 else 0
    fs_delta_turn = 1 if delta_turn > 0 else 0

Financial strength score:

    financial_strength_score = (fs_roa + fs_fcfta + fs_accrual + fs_lever + fs_liquid + fs_neqiss + fs_delta_roa + fs_delta_fcfta + fs_delta_margin + fs_delta_turn) / 10

## Plan of Work

Start by adding a feature configuration module that captures the weights for NIMTAAVG and EXRETAVG plus normalization percentiles. Store this configuration in a new YAML file under `config/quant_value_features.yaml` and add a loader in a new module `src/research/features/feature_config.py` so the feature builder can fail loudly or return null when weights are missing.

Next, define a small feature metadata layer so the computed output is traceable. Introduce a `FeatureSpec` dataclass in `src/research/features/feature_spec.py` with fields for feature_id, description, min_history_quarters, direction (higher_is_better or higher_is_worse), and a compute function name. Create `src/research/features/feature_registry.py` that lists every feature id in this plan with its metadata.

Then build a new service `src/research/features/services/quant_value_feature_service.py` that reads Gold facts using DuckDB, constructs a merged quarterly fundamentals frame per ticker, computes TTM series and the formulas above, enforces null and eligibility rules, normalizes results by quarter, and writes to `gold.features`. The service should record ops.gold_manifest rows via `OpsService.start_gold_manifest` and `OpsService.finish_gold_manifest`, and update `ops.gold_watermarks` for `gold.features` so that reruns can incrementally append new quarters.

After the service exists, integrate it into the orchestration flow. Add a new switch on `OrchestrationSwitches` for `features` and call the new service from `_promote_gold` in `src/data_layer/orchestrator.py` after the existing gold load, using the same run summary and logger. Ensure that the run does not fail if the feature build is disabled.

Finally, add tests under `tests/data_platform` to cover at least one feature from each category, including a Beneish ratio, a distress metric, an eight-year metric, and the financial strength score. Use small pandas DataFrames to validate the formulas and null rules. Add a small integration test that builds a temporary DuckDB database and verifies that `gold.features` receives rows with the expected grain keys and schema.

## Concrete Steps

Work in `c:/strawberry` unless noted otherwise. Follow these steps sequentially and update the Progress section after each completed step.

Edit the configuration and feature registry files, then run tests.

    PS C:\sb\SBFoundation> python -m pytest

If the repository does not yet have tests in `tests/data_platform`, create them as described above, then re-run the same command. Expect pytest to discover the new tests and report them as passing.

After implementing the feature service and integration in the orchestrator, run the full data pipeline with a small ticker limit so the run is fast.

    PS C:\sb\SBFoundation> python src/data_layer/orchestrator.py

If the run requires API access, ensure the `FMP_API_KEY` environment variable is set according to `src/settings.py` before running. If API access is not available, run the feature service against existing DuckDB data and skip the Bronze and Silver steps by configuring `OrchestrationSwitches` accordingly.

## Validation and Acceptance

A successful implementation allows a user to compute Quantitative Value features and see them stored in the Gold layer. Run the orchestrator with features enabled and then query the DuckDB file to confirm that `gold.features` exists and has rows for the most recent quarter. A minimal validation query can be run through a short Python script:

    PS C:\sb\SBFoundation> @'
    import duckdb
    from data_layer.infra.duckdb.duckdb_config import DuckDbConfig
    cfg = DuckDbConfig()
    conn = duckdb.connect(str(cfg.duckdb))
    rows = conn.execute("SELECT feature_id, COUNT(*) FROM gold.features GROUP BY feature_id ORDER BY feature_id").fetchall()
    print(rows[:5])
    '@ | python -

Expect a non-empty result set containing known feature ids such as scaled_total_accruals, nimtaavg, ebit_to_tev, and financial_strength_score. If any of these are missing, the feature registry or computation step is incomplete.

## Idempotence and Recovery

The feature build should be safe to rerun. Use grain keys (ticker, as_of_date, feature_id) and a merge/upsert strategy so that reruns update existing rows rather than duplicating them. If a run fails mid-way, rerun the same command after fixing the error; the merge logic should bring `gold.features` back to a consistent state. If a clean rebuild is required, delete the affected quarter from `gold.features` with a scoped DELETE in DuckDB rather than dropping the entire table.

## Artifacts and Notes

Expected `gold.features` schema example:

    ticker: string
    as_of_date: date
    feature_id: string
    raw_value: double
    norm_value: double
    is_eligible: boolean
    run_id: string
    gold_build_id: bigint
    model_version: string

Short example of a successful query:

    [("ebit_to_tev", 100), ("financial_strength_score", 100), ("manipulation_prob", 100)]

## Interfaces and Dependencies

Introduce the following modules and interfaces so the feature system is explicit and testable.

In `src/research/features/feature_spec.py`, define:

    @dataclass(frozen=True)
    class FeatureSpec:
        feature_id: str
        description: str
        min_history_quarters: int
        direction: str  # "higher_is_better" or "higher_is_worse"
        compute_fn: str  # name of a compute method on the feature service

In `src/research/features/feature_config.py`, define a loader:

    def load_quant_value_config(path: Path) -> QuantValueConfig

QuantValueConfig should carry nimta_weights, exret_weights, winsor_lower_pct, winsor_upper_pct, and min_cross_section.

In `src/research/features/quant_value/feature_registry.py`, define:

    QUANT_VALUE_FEATURES: tuple[FeatureSpec, ...]

In `src/data_layer/services/gold/quant_value_feature_service.py`, define:

    class QuantValueFeatureService:
        def __init__(self, config: DuckDbConfig | None = None, logger: logging.Logger | None = None, ops_service: OpsService | None = None) -> None
        def build(self, run_summary: RunContext, as_of: date | None = None) -> RunContext

The build method should read Gold facts, compute raw features, normalize them, and write to `gold.features` with merge semantics on (ticker, as_of_date, feature_id). It should also record a gold manifest row for `gold.features` via OpsService.

Change Note: Replaced the prior narrative spec with a full ExecPlan formatted per `docs/AI_context/PLANS.md`, normalized to ASCII, and added Findings and Questions sections so the plan is executable and self-contained.
