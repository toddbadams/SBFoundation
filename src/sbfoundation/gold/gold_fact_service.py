from __future__ import annotations

import subprocess
from datetime import datetime, timezone

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


class GoldFactService:
    """Builds gold.fact_eod, gold.fact_quarter, gold.fact_annual from Silver + dims.

    Silver sources:
    - silver.fmp_eod_bulk_price        -> fact_eod
    - silver.fmp_income_statement_bulk_quarter + balance_sheet + cashflow -> fact_quarter
    - silver.fmp_income_statement_bulk_annual  + balance_sheet + cashflow
        + key_metrics_bulk_annual (optional) + ratios_bulk_annual (optional) -> fact_annual

    Idempotency: INSERT INTO ... ON CONFLICT DO UPDATE (upsert) so re-runs are safe.
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

    def build(self, gold_build_id: int | None = None, run_id: str | None = None) -> dict[str, int]:
        """Build all three fact tables. Returns row counts."""
        model_version = _git_sha()
        now = datetime.now(timezone.utc).isoformat()
        self._logger.info("GoldFactService: building facts", run_id=run_id)

        with self._bootstrap.gold_transaction() as conn:
            eod_rows = self._build_fact_eod(conn, gold_build_id, model_version, now)
        self._logger.info(f"GoldFactService: fact_eod rows={eod_rows}", run_id=run_id)

        with self._bootstrap.gold_transaction() as conn:
            qtr_rows = self._build_fact_quarter(conn, gold_build_id, model_version, now)
        self._logger.info(f"GoldFactService: fact_quarter rows={qtr_rows}", run_id=run_id)

        with self._bootstrap.gold_transaction() as conn:
            ann_rows = self._build_fact_annual(conn, gold_build_id, model_version, now)
        self._logger.info(f"GoldFactService: fact_annual rows={ann_rows}", run_id=run_id)

        return {"fact_eod": eod_rows, "fact_quarter": qtr_rows, "fact_annual": ann_rows}

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()
        return bool(row and row[0] > 0)

    def _build_fact_eod(
        self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str
    ) -> int:
        if not self._table_exists(conn, "silver", "fmp_eod_bulk_price"):
            self._logger.info("GoldFactService: silver.fmp_eod_bulk_price not found — skipping fact_eod")
            return 0

        conn.execute("""
            INSERT INTO gold.fact_eod (
                instrument_sk, date_sk,
                open, high, low, close, adj_close,
                volume, unadjusted_volume, change, change_pct, vwap,
                gold_build_id, model_version, updated_at
            )
            SELECT
                inst.instrument_sk,
                CAST(strftime(src.date::DATE, '%Y%m%d') AS INTEGER) AS date_sk,
                src.open, src.high, src.low, src.close, src.adj_close,
                src.volume, src.unadjusted_volume, src.change, src.change_pct, src.vwap,
                $1             AS gold_build_id,
                $2             AS model_version,
                $3::TIMESTAMP  AS updated_at
            FROM silver.fmp_eod_bulk_price src
            JOIN gold.dim_instrument inst ON inst.symbol = src.symbol
            WHERE src.date IS NOT NULL
            ON CONFLICT (instrument_sk, date_sk) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low  = EXCLUDED.low,
                close = EXCLUDED.close,
                adj_close = EXCLUDED.adj_close,
                volume = EXCLUDED.volume,
                unadjusted_volume = EXCLUDED.unadjusted_volume,
                change = EXCLUDED.change,
                change_pct = EXCLUDED.change_pct,
                vwap = EXCLUDED.vwap,
                gold_build_id = EXCLUDED.gold_build_id,
                model_version = EXCLUDED.model_version,
                updated_at = EXCLUDED.updated_at
        """, [gold_build_id, model_version, now])

        row = conn.execute("SELECT COUNT(*) FROM gold.fact_eod").fetchone()
        return row[0] if row else 0

    def _build_fact_quarter(
        self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str
    ) -> int:
        inc_exists = self._table_exists(conn, "silver", "fmp_income_statement_bulk_quarter")
        bs_exists  = self._table_exists(conn, "silver", "fmp_balance_sheet_bulk_quarter")
        cf_exists  = self._table_exists(conn, "silver", "fmp_cashflow_bulk_quarter")

        if not inc_exists:
            self._logger.info("GoldFactService: silver quarterly income statement not found — skipping fact_quarter")
            return 0

        bs_select = (
            "bs.total_assets, bs.total_current_assets, bs.total_liabilities, "
            "bs.total_current_liabilities, bs.total_stockholders_equity, "
            "bs.cash_and_cash_equivalents, bs.long_term_debt, bs.total_debt, bs.net_debt, "
            "bs.deferred_revenue, bs.goodwill_and_intangible_assets,"
            if bs_exists else
            "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,"
        )
        cf_select = (
            "cf.operating_cash_flow, cf.capital_expenditure, cf.free_cash_flow, cf.dividends_paid,"
            if cf_exists else
            "NULL, NULL, NULL, NULL,"
        )
        bs_join = (
            "LEFT JOIN silver.fmp_balance_sheet_bulk_quarter bs "
            "ON bs.symbol = inc.symbol AND bs.period = inc.period AND bs.calendar_year = inc.calendar_year"
            if bs_exists else ""
        )
        cf_join = (
            "LEFT JOIN silver.fmp_cashflow_bulk_quarter cf "
            "ON cf.symbol = inc.symbol AND cf.period = inc.period AND cf.calendar_year = inc.calendar_year"
            if cf_exists else ""
        )

        conn.execute(f"""
            INSERT INTO gold.fact_quarter (
                instrument_sk, period, calendar_year, period_date_sk,
                reported_currency,
                revenue, gross_profit, operating_income, net_income, ebitda, eps, eps_diluted,
                research_and_development_expenses, selling_general_and_administrative_expenses,
                interest_expense, income_before_tax, income_tax_expense, depreciation_and_amortization,
                total_assets, total_current_assets, total_liabilities, total_current_liabilities,
                total_stockholders_equity, cash_and_cash_equivalents, long_term_debt, total_debt, net_debt,
                deferred_revenue, goodwill_and_intangible_assets,
                operating_cash_flow, capital_expenditure, free_cash_flow, dividends_paid,
                gold_build_id, model_version, updated_at
            )
            SELECT
                inst.instrument_sk,
                inc.period,
                inc.calendar_year,
                CASE WHEN inc.date IS NOT NULL
                     THEN CAST(strftime(inc.date::DATE, '%Y%m%d') AS INTEGER)
                     ELSE NULL END                         AS period_date_sk,
                inc.reported_currency,
                inc.revenue, inc.gross_profit, inc.operating_income, inc.net_income,
                inc.ebitda, inc.eps, inc.eps_diluted,
                inc.research_and_development_expenses, inc.selling_general_and_administrative_expenses,
                inc.interest_expense, inc.income_before_tax, inc.income_tax_expense,
                inc.depreciation_and_amortization,
                {bs_select}
                {cf_select}
                $1             AS gold_build_id,
                $2             AS model_version,
                $3::TIMESTAMP  AS updated_at
            FROM silver.fmp_income_statement_bulk_quarter inc
            JOIN gold.dim_instrument inst ON inst.symbol = inc.symbol
            {bs_join}
            {cf_join}
            WHERE inc.symbol IS NOT NULL AND inc.calendar_year IS NOT NULL
            ON CONFLICT (instrument_sk, period, calendar_year) DO UPDATE SET
                reported_currency = EXCLUDED.reported_currency,
                revenue = EXCLUDED.revenue,
                gross_profit = EXCLUDED.gross_profit,
                operating_income = EXCLUDED.operating_income,
                net_income = EXCLUDED.net_income,
                ebitda = EXCLUDED.ebitda,
                eps = EXCLUDED.eps,
                eps_diluted = EXCLUDED.eps_diluted,
                research_and_development_expenses = EXCLUDED.research_and_development_expenses,
                selling_general_and_administrative_expenses = EXCLUDED.selling_general_and_administrative_expenses,
                interest_expense = EXCLUDED.interest_expense,
                income_before_tax = EXCLUDED.income_before_tax,
                income_tax_expense = EXCLUDED.income_tax_expense,
                depreciation_and_amortization = EXCLUDED.depreciation_and_amortization,
                total_assets = EXCLUDED.total_assets,
                total_current_assets = EXCLUDED.total_current_assets,
                total_liabilities = EXCLUDED.total_liabilities,
                total_current_liabilities = EXCLUDED.total_current_liabilities,
                total_stockholders_equity = EXCLUDED.total_stockholders_equity,
                cash_and_cash_equivalents = EXCLUDED.cash_and_cash_equivalents,
                long_term_debt = EXCLUDED.long_term_debt,
                total_debt = EXCLUDED.total_debt,
                net_debt = EXCLUDED.net_debt,
                deferred_revenue = EXCLUDED.deferred_revenue,
                goodwill_and_intangible_assets = EXCLUDED.goodwill_and_intangible_assets,
                operating_cash_flow = EXCLUDED.operating_cash_flow,
                capital_expenditure = EXCLUDED.capital_expenditure,
                free_cash_flow = EXCLUDED.free_cash_flow,
                dividends_paid = EXCLUDED.dividends_paid,
                gold_build_id = EXCLUDED.gold_build_id,
                model_version = EXCLUDED.model_version,
                updated_at = EXCLUDED.updated_at
        """, [gold_build_id, model_version, now])

        row = conn.execute("SELECT COUNT(*) FROM gold.fact_quarter").fetchone()
        return row[0] if row else 0

    def _build_fact_annual(
        self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str
    ) -> int:
        if not self._table_exists(conn, "silver", "fmp_income_statement_bulk_annual"):
            self._logger.info("GoldFactService: silver annual income statement not found — skipping fact_annual")
            return 0

        bs_exists  = self._table_exists(conn, "silver", "fmp_balance_sheet_bulk_annual")
        cf_exists  = self._table_exists(conn, "silver", "fmp_cashflow_bulk_annual")
        km_exists  = self._table_exists(conn, "silver", "fmp_key_metrics_bulk_annual")
        rat_exists = self._table_exists(conn, "silver", "fmp_ratios_bulk_annual")

        bs_select = (
            "bs.total_assets, bs.total_current_assets, bs.total_liabilities, "
            "bs.total_current_liabilities, bs.total_stockholders_equity, "
            "bs.cash_and_cash_equivalents, bs.long_term_debt, bs.total_debt, bs.net_debt, "
            "bs.deferred_revenue, bs.goodwill_and_intangible_assets,"
            if bs_exists else
            "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,"
        )
        cf_select = (
            "cf.operating_cash_flow, cf.capital_expenditure, cf.free_cash_flow, cf.dividends_paid,"
            if cf_exists else
            "NULL, NULL, NULL, NULL,"
        )
        km_select = (
            "km.roic, km.invested_capital, km.revenue_per_employee, "
            "km.capex_to_ocf, km.ev_to_ebitda, km.debt_to_equity AS debt_to_equity_km, "
            "km.days_sales_outstanding, km.days_payables_outstanding, km.days_inventory,"
            if km_exists else
            "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,"
        )
        rat_select = (
            "rat.gross_profit_margin, rat.operating_profit_margin, rat.net_profit_margin, "
            "rat.fcf_to_sales_ratio, rat.return_on_assets, rat.return_on_equity, "
            "rat.return_on_capital_employed, rat.effective_tax_rate, rat.debt_ratio, rat.interest_coverage,"
            if rat_exists else
            "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,"
        )

        bs_join = (
            "LEFT JOIN silver.fmp_balance_sheet_bulk_annual bs "
            "ON bs.symbol = inc.symbol AND bs.calendar_year = inc.calendar_year"
            if bs_exists else ""
        )
        cf_join = (
            "LEFT JOIN silver.fmp_cashflow_bulk_annual cf "
            "ON cf.symbol = inc.symbol AND cf.calendar_year = inc.calendar_year"
            if cf_exists else ""
        )
        km_join = (
            "LEFT JOIN silver.fmp_key_metrics_bulk_annual km "
            "ON km.symbol = inc.symbol AND km.calendar_year = inc.calendar_year"
            if km_exists else ""
        )
        rat_join = (
            "LEFT JOIN silver.fmp_ratios_bulk_annual rat "
            "ON rat.symbol = inc.symbol AND rat.calendar_year = inc.calendar_year"
            if rat_exists else ""
        )

        conn.execute(f"""
            INSERT INTO gold.fact_annual (
                instrument_sk, calendar_year, period_date_sk,
                reported_currency,
                revenue, gross_profit, operating_income, net_income, ebitda, eps, eps_diluted,
                research_and_development_expenses, selling_general_and_administrative_expenses,
                interest_expense, income_before_tax, income_tax_expense, depreciation_and_amortization,
                total_assets, total_current_assets, total_liabilities, total_current_liabilities,
                total_stockholders_equity, cash_and_cash_equivalents, long_term_debt, total_debt, net_debt,
                deferred_revenue, goodwill_and_intangible_assets,
                operating_cash_flow, capital_expenditure, free_cash_flow, dividends_paid,
                roic, invested_capital, revenue_per_employee, capex_to_ocf, ev_to_ebitda,
                debt_to_equity_km, days_sales_outstanding, days_payables_outstanding, days_inventory,
                gross_profit_margin, operating_profit_margin, net_profit_margin, fcf_to_sales_ratio,
                return_on_assets, return_on_equity, return_on_capital_employed,
                effective_tax_rate, debt_ratio, interest_coverage,
                gold_build_id, model_version, updated_at
            )
            SELECT
                inst.instrument_sk,
                inc.calendar_year,
                CASE WHEN inc.date IS NOT NULL
                     THEN CAST(strftime(inc.date::DATE, '%Y%m%d') AS INTEGER)
                     ELSE NULL END                         AS period_date_sk,
                inc.reported_currency,
                inc.revenue, inc.gross_profit, inc.operating_income, inc.net_income,
                inc.ebitda, inc.eps, inc.eps_diluted,
                inc.research_and_development_expenses, inc.selling_general_and_administrative_expenses,
                inc.interest_expense, inc.income_before_tax, inc.income_tax_expense,
                inc.depreciation_and_amortization,
                {bs_select}
                {cf_select}
                {km_select}
                {rat_select}
                $1             AS gold_build_id,
                $2             AS model_version,
                $3::TIMESTAMP  AS updated_at
            FROM silver.fmp_income_statement_bulk_annual inc
            JOIN gold.dim_instrument inst ON inst.symbol = inc.symbol
            {bs_join}
            {cf_join}
            {km_join}
            {rat_join}
            WHERE inc.symbol IS NOT NULL AND inc.calendar_year IS NOT NULL
            ON CONFLICT (instrument_sk, calendar_year) DO UPDATE SET
                reported_currency = EXCLUDED.reported_currency,
                revenue = EXCLUDED.revenue,
                gross_profit = EXCLUDED.gross_profit,
                operating_income = EXCLUDED.operating_income,
                net_income = EXCLUDED.net_income,
                ebitda = EXCLUDED.ebitda,
                eps = EXCLUDED.eps,
                eps_diluted = EXCLUDED.eps_diluted,
                research_and_development_expenses = EXCLUDED.research_and_development_expenses,
                selling_general_and_administrative_expenses = EXCLUDED.selling_general_and_administrative_expenses,
                interest_expense = EXCLUDED.interest_expense,
                income_before_tax = EXCLUDED.income_before_tax,
                income_tax_expense = EXCLUDED.income_tax_expense,
                depreciation_and_amortization = EXCLUDED.depreciation_and_amortization,
                total_assets = EXCLUDED.total_assets,
                total_current_assets = EXCLUDED.total_current_assets,
                total_liabilities = EXCLUDED.total_liabilities,
                total_current_liabilities = EXCLUDED.total_current_liabilities,
                total_stockholders_equity = EXCLUDED.total_stockholders_equity,
                cash_and_cash_equivalents = EXCLUDED.cash_and_cash_equivalents,
                long_term_debt = EXCLUDED.long_term_debt,
                total_debt = EXCLUDED.total_debt,
                net_debt = EXCLUDED.net_debt,
                deferred_revenue = EXCLUDED.deferred_revenue,
                goodwill_and_intangible_assets = EXCLUDED.goodwill_and_intangible_assets,
                operating_cash_flow = EXCLUDED.operating_cash_flow,
                capital_expenditure = EXCLUDED.capital_expenditure,
                free_cash_flow = EXCLUDED.free_cash_flow,
                dividends_paid = EXCLUDED.dividends_paid,
                roic = EXCLUDED.roic,
                invested_capital = EXCLUDED.invested_capital,
                revenue_per_employee = EXCLUDED.revenue_per_employee,
                capex_to_ocf = EXCLUDED.capex_to_ocf,
                ev_to_ebitda = EXCLUDED.ev_to_ebitda,
                debt_to_equity_km = EXCLUDED.debt_to_equity_km,
                days_sales_outstanding = EXCLUDED.days_sales_outstanding,
                days_payables_outstanding = EXCLUDED.days_payables_outstanding,
                days_inventory = EXCLUDED.days_inventory,
                gross_profit_margin = EXCLUDED.gross_profit_margin,
                operating_profit_margin = EXCLUDED.operating_profit_margin,
                net_profit_margin = EXCLUDED.net_profit_margin,
                fcf_to_sales_ratio = EXCLUDED.fcf_to_sales_ratio,
                return_on_assets = EXCLUDED.return_on_assets,
                return_on_equity = EXCLUDED.return_on_equity,
                return_on_capital_employed = EXCLUDED.return_on_capital_employed,
                effective_tax_rate = EXCLUDED.effective_tax_rate,
                debt_ratio = EXCLUDED.debt_ratio,
                interest_coverage = EXCLUDED.interest_coverage,
                gold_build_id = EXCLUDED.gold_build_id,
                model_version = EXCLUDED.model_version,
                updated_at = EXCLUDED.updated_at
        """, [gold_build_id, model_version, now])

        row = conn.execute("SELECT COUNT(*) FROM gold.fact_annual").fetchone()
        return row[0] if row else 0
