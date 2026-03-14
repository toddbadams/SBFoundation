"""
Moat Score Validation — Phase 4

Run as:  python -m services.moat_score_validation

Prints a series of diagnostic checks to stdout using DuckDB SQL queries.
All queries execute directly against the Gold database — no pandas loading.
Requires gold.fact_moat_annual to be populated by MoatFeatureService.
"""
from __future__ import annotations

import sys

from sbfoundation.maintenance import DuckDbBootstrap


def _divider(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def _run(con, sql: str) -> list:
    try:
        return con.execute(sql).fetchall()
    except Exception as exc:
        print(f"  [QUERY ERROR] {exc}")
        return []


def check_table_exists(con) -> bool:
    _divider("1. Table existence check")
    rows = _run(con, """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema = 'gold' AND table_name = 'fact_moat_annual'
    """)
    if rows:
        print("  ✓  gold.fact_moat_annual exists")
        count = _run(con, "SELECT COUNT(*) FROM gold.fact_moat_annual")[0][0]
        print(f"     total rows: {count:,}")
        return True
    else:
        print("  ✗  gold.fact_moat_annual NOT FOUND — run MoatFeatureService first")
        return False


def check_row_counts(con) -> None:
    _divider("2. Row counts by calendar year")
    rows = _run(con, """
        SELECT calendar_year,
               COUNT(*)                              AS total_instruments,
               SUM(CASE WHEN moat_score_s IS NOT NULL THEN 1 ELSE 0 END) AS with_score,
               AVG(industry_peer_n)::INTEGER         AS avg_peer_n,
               SUM(CASE WHEN benchmark_level = 'sector' THEN 1 ELSE 0 END) AS sector_fallback_n
        FROM gold.fact_moat_annual
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 10
    """)
    print(f"  {'Year':>6}  {'Instruments':>12}  {'With Score':>10}  {'Avg Peers':>10}  {'Sector FB':>10}")
    print(f"  {'-'*6}  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*10}")
    for r in rows:
        print(f"  {r[0]:>6}  {r[1]:>12,}  {r[2]:>10,}  {r[3]:>10}  {r[4]:>10,}")


def check_score_distribution(con) -> None:
    _divider("3. Score column distribution (min / mean / max / null%)")
    cols = [
        "moat_score_s", "profitability_s", "stability_s", "competitive_s",
        "cost_advantage_s", "lock_in_s", "reinvestment_s",
        "roic_f", "wacc_f", "roic_spread_f",
    ]
    total = _run(con, "SELECT COUNT(*) FROM gold.fact_moat_annual")[0][0]
    print(f"  {'Column':<35}  {'Min':>7}  {'Mean':>7}  {'Max':>7}  {'Null%':>7}")
    print(f"  {'-'*35}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*7}")
    for col in cols:
        rows = _run(con, f"""
            SELECT
                MIN({col})::DOUBLE,
                AVG({col})::DOUBLE,
                MAX({col})::DOUBLE,
                100.0 * SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) / NULLIF({total}, 0)
            FROM gold.fact_moat_annual
        """)
        if rows:
            mn, av, mx, np = rows[0]
            mn_s = f"{mn:.3f}" if mn is not None else "NULL"
            av_s = f"{av:.3f}" if av is not None else "NULL"
            mx_s = f"{mx:.3f}" if mx is not None else "NULL"
            np_s = f"{np:.1f}%" if np is not None else "NULL"
            print(f"  {col:<35}  {mn_s:>7}  {av_s:>7}  {mx_s:>7}  {np_s:>7}")


def check_wacc_sanity(con) -> None:
    _divider("4. WACC sanity — instruments with implausible WACC (outside 4%–25%)")
    rows = _run(con, """
        SELECT di.symbol, m.calendar_year, ROUND(m.wacc_f * 100, 2) AS wacc_pct
        FROM gold.fact_moat_annual m
        JOIN gold.dim_instrument di ON di.instrument_sk = m.instrument_sk
        WHERE m.wacc_f IS NOT NULL AND (m.wacc_f < 0.04 OR m.wacc_f > 0.25)
        ORDER BY ABS(m.wacc_f - 0.08) DESC
        LIMIT 20
    """)
    if rows:
        print(f"  {'Symbol':<10}  {'Year':>6}  {'WACC%':>8}")
        for r in rows:
            print(f"  {r[0]:<10}  {r[1]:>6}  {r[2]:>8}")
    else:
        print("  ✓  No implausible WACC values found (all in [4%, 25%] — WACC is clamped by design)")


def check_known_high_moat(con) -> None:
    _divider("5. Known high-moat stocks — latest year scores (AAPL, MSFT, KO, JNJ)")
    rows = _run(con, """
        SELECT di.symbol, m.calendar_year,
               ROUND(m.moat_score_s,    3) AS moat,
               ROUND(m.profitability_s, 3) AS profit,
               ROUND(m.stability_s,     3) AS stability,
               ROUND(m.competitive_s,   3) AS competitive,
               ROUND(m.wacc_f * 100,    2) AS wacc_pct,
               m.benchmark_level
        FROM gold.fact_moat_annual m
        JOIN gold.dim_instrument di ON di.instrument_sk = m.instrument_sk
        WHERE di.symbol IN ('AAPL', 'MSFT', 'KO', 'JNJ', 'V', 'GOOGL')
          AND m.calendar_year = (SELECT MAX(calendar_year) FROM gold.fact_moat_annual)
        ORDER BY m.moat_score_s DESC NULLS LAST
    """)
    if rows:
        print(f"  {'Symbol':<8}  {'Year':>4}  {'Moat':>6}  {'Profit':>6}  {'Stable':>6}  {'Compet':>6}  {'WACC%':>6}  {'Level'}")
        for r in rows:
            print(f"  {r[0]:<8}  {r[1]:>4}  {r[2]:>6}  {r[3]:>6}  {r[4]:>6}  {r[5]:>6}  {r[6]:>6}  {r[7]}")
    else:
        print("  No data for AAPL/MSFT/KO/JNJ — check universe coverage")


def check_quintile_analysis(con) -> None:
    _divider("6. Quintile analysis — top vs bottom moat_score_s quintile (most recent year)")
    rows = _run(con, """
        WITH latest AS (
            SELECT * FROM gold.fact_moat_annual
            WHERE calendar_year = (SELECT MAX(calendar_year) FROM gold.fact_moat_annual)
              AND moat_score_s IS NOT NULL
        ),
        quintiled AS (
            SELECT *,
                NTILE(5) OVER (ORDER BY moat_score_s) AS quintile
            FROM latest
        )
        SELECT
            quintile,
            COUNT(*)                     AS n,
            ROUND(MIN(moat_score_s), 3)  AS min_score,
            ROUND(AVG(moat_score_s), 3)  AS avg_score,
            ROUND(MAX(moat_score_s), 3)  AS max_score,
            ROUND(AVG(profitability_s), 3) AS avg_profit,
            ROUND(AVG(stability_s), 3)   AS avg_stability
        FROM quintiled
        GROUP BY 1
        ORDER BY 1
    """)
    if rows:
        print(f"  {'Q':>2}  {'N':>6}  {'Min':>6}  {'Avg':>6}  {'Max':>6}  {'Profit':>7}  {'Stable':>7}")
        for r in rows:
            print(f"  {r[0]:>2}  {r[1]:>6,}  {r[2]:>6}  {r[3]:>6}  {r[4]:>6}  {r[5]:>7}  {r[6]:>7}")


def check_sector_fallback_rate(con) -> None:
    _divider("7. Sector fallback rate (target: < 20% of rows)")
    rows = _run(con, """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN benchmark_level = 'sector' THEN 1 ELSE 0 END) AS sector_rows,
            ROUND(100.0 * SUM(CASE WHEN benchmark_level = 'sector' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1) AS sector_pct
        FROM gold.fact_moat_annual
    """)
    if rows:
        total, sector, pct = rows[0]
        status = "✓" if (pct or 0) < 20 else "⚠"
        print(f"  {status}  sector fallback: {sector:,} / {total:,} = {pct}%  (target < 20%)")


def check_eod_features(con) -> None:
    _divider("8. EOD feature coverage (gold.fact_eod)")
    rows = _run(con, """
        SELECT
            COUNT(*)                                                    AS total_rows,
            SUM(CASE WHEN momentum_1m_f IS NOT NULL THEN 1 ELSE 0 END) AS with_momentum,
            SUM(CASE WHEN volatility_30d_f IS NOT NULL THEN 1 ELSE 0 END) AS with_volatility,
            ROUND(100.0 * SUM(CASE WHEN momentum_1m_f IS NOT NULL THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1) AS momentum_pct
        FROM gold.fact_eod
    """)
    if rows:
        total, mom, vol, pct = rows[0]
        print(f"  fact_eod total rows : {total:,}")
        print(f"  with momentum_1m_f  : {mom:,}  ({pct}%)")
        print(f"  with volatility_30d : {vol:,}")
        min_rows = _run(con, """
            SELECT COUNT(*) FROM (
                SELECT instrument_sk, COUNT(*) AS n
                FROM gold.fact_eod WHERE momentum_1m_f IS NOT NULL
                GROUP BY 1 HAVING n >= 252
            ) t
        """)
        if min_rows:
            print(f"  instruments ≥ 252 momentum rows: {min_rows[0][0]:,}")
    else:
        print("  gold.fact_eod not found or empty")


def main() -> None:
    print("Moat Score Validation")
    print("=" * 70)

    bootstrap = DuckDbBootstrap()
    con = bootstrap.connect()

    if not check_table_exists(con):
        bootstrap.close()
        sys.exit(1)

    check_row_counts(con)
    check_score_distribution(con)
    check_wacc_sanity(con)
    check_known_high_moat(con)
    check_quintile_analysis(con)
    check_sector_fallback_rate(con)
    check_eod_features(con)

    print("\n" + "=" * 70)
    print("  Validation complete.")
    print("=" * 70 + "\n")
    bootstrap.close()


if __name__ == "__main__":
    main()
