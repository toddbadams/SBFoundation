"""Coverage Dashboard — Home

Landing page showing global health metrics across all datasets,
split into four sections:

  • Global Historical   — global-scope datasets with date-range coverage
  • Global Snapshot     — global-scope datasets that have no date range (point-in-time)
  • Per-Ticker Historical — per-ticker datasets with date-range coverage
  • Per-Ticker Snapshot   — per-ticker datasets that are point-in-time snapshots

Per-ticker coverage is measured against the US_ALL_CAP universe (5,280 tickers).
"""

import pandas as pd
import streamlit as st

from db import get_repo

# US_ALL_CAP universe size — denominator for ticker coverage %
US_ALL_CAP_SIZE = 5_280

st.set_page_config(
    page_title="Coverage Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Data Coverage Dashboard")
st.caption("Operational control plane for Bronze → Silver data coverage.")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

repo = get_repo()


def _load(fn, label: str):
    try:
        return fn()
    except Exception as exc:
        st.error(f"Failed to load {label}: {exc}")
        return None


pth_rows = _load(repo.get_per_ticker_historical_summary, "per-ticker historical")
pts_rows = _load(repo.get_per_ticker_snapshot_summary, "per-ticker snapshot")
gh_rows  = _load(repo.get_global_historical_summary,   "global historical")
gs_rows  = _load(repo.get_global_snapshot_summary,     "global snapshot")

if all(r is None for r in [pth_rows, pts_rows, gh_rows, gs_rows]):
    st.info("Run the pipeline at least once to populate ops.coverage_index.")
    st.stop()

pth = pd.DataFrame(pth_rows or [])
pts = pd.DataFrame(pts_rows or [])
gh  = pd.DataFrame(gh_rows  or [])
gs  = pd.DataFrame(gs_rows  or [])

# ---------------------------------------------------------------------------
# Global metric cards
# ---------------------------------------------------------------------------

total_datasets = (
    len(pth["dataset"].unique()) if not pth.empty else 0
) + (
    len(pts["dataset"].unique()) if not pts.empty else 0
) + (
    len(gh[["dataset", "discriminator"]].drop_duplicates()) if not gh.empty else 0
) + (
    len(gs[["dataset", "discriminator"]].drop_duplicates()) if not gs.empty else 0
)

total_tickers = 0
if not pth.empty:
    total_tickers = max(total_tickers, int(pth["tickers_covered"].max() or 0))
if not pts.empty:
    total_tickers = max(total_tickers, int(pts["tickers_covered"].max() or 0))

avg_hist_cov: float | None = None
hist_cov_vals = []
if not pth.empty:
    hist_cov_vals.extend(pth["avg_coverage_ratio"].dropna().tolist())
if not gh.empty:
    hist_cov_vals.extend(gh["avg_coverage_ratio"].dropna().tolist())
if hist_cov_vals:
    avg_hist_cov = float(sum(hist_cov_vals) / len(hist_cov_vals))

snap_count = (len(pts) if not pts.empty else 0) + (len(gs) if not gs.empty else 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Datasets", f"{total_datasets:,}")
col2.metric("Max Tickers Covered", f"{total_tickers:,} / {US_ALL_CAP_SIZE:,}")
col3.metric(
    "Avg Historical Coverage",
    f"{avg_hist_cov * 100:.1f}%" if avg_hist_cov is not None else "—",
)
col4.metric("Snapshot Dataset Types", f"{snap_count:,}")

st.divider()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_pct(v) -> str:
    return f"{float(v) * 100:.1f}%" if pd.notna(v) else "—"


def _fmt_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d").fillna("—")


def _ticker_cov_pct(n) -> str:
    if pd.isna(n):
        return "—"
    return f"{int(n):,} / {US_ALL_CAP_SIZE:,}  ({int(n) / US_ALL_CAP_SIZE * 100:.1f}%)"


# ---------------------------------------------------------------------------
# Section: Per-Ticker Historical
# ---------------------------------------------------------------------------

st.subheader("Per-Ticker Datasets — Historical")
st.caption(
    f"Datasets that fetch date-range data per ticker. "
    f"Ticker coverage vs US_ALL_CAP ({US_ALL_CAP_SIZE:,} tickers). "
    f"Expected date range: 1990-01-01 → today. Sorted weakest coverage first."
)

if pth.empty:
    st.info("No per-ticker historical data found.")
else:
    disp = pth.copy()
    disp["ticker_coverage"] = disp["tickers_covered"].apply(_ticker_cov_pct)
    disp["avg_coverage"]    = disp["avg_coverage_ratio"].apply(_fmt_pct)
    disp["avg_error_rate"]  = disp["avg_error_rate"].apply(_fmt_pct)
    disp["min_date"]        = _fmt_date(disp["min_date"])
    disp["max_date"]        = _fmt_date(disp["max_date"])
    disp["last_ingested"]   = _fmt_date(disp["last_ingested_at"])

    st.dataframe(
        disp[[
            "domain", "source", "dataset",
            "ticker_coverage", "avg_coverage",
            "min_date", "max_date",
            "avg_error_rate", "last_ingested",
        ]].rename(columns={
            "ticker_coverage": "tickers (vs universe)",
            "avg_coverage":    "avg date coverage",
            "avg_error_rate":  "error rate",
            "last_ingested":   "last ingested",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Section: Per-Ticker Snapshot
# ---------------------------------------------------------------------------

st.subheader("Per-Ticker Datasets — Snapshot")
st.caption(
    f"Datasets fetched as a point-in-time snapshot per ticker (no date range). "
    f"Ticker coverage vs US_ALL_CAP ({US_ALL_CAP_SIZE:,} tickers). Sorted most-covered first."
)

if pts.empty:
    st.info("No per-ticker snapshot data found.")
else:
    disp = pts.copy()
    disp["ticker_coverage"]      = disp["tickers_covered"].apply(_ticker_cov_pct)
    disp["last_snapshot"]        = _fmt_date(disp["last_snapshot_date"])
    disp["avg_age_days"]         = disp["avg_age_days"].apply(
        lambda v: f"{int(v):,}d" if pd.notna(v) else "—"
    )
    disp["avg_error_rate"]       = disp["avg_error_rate"].apply(_fmt_pct)
    disp["last_ingested"]        = _fmt_date(disp["last_ingested_at"])

    st.dataframe(
        disp[[
            "domain", "source", "dataset",
            "ticker_coverage", "last_snapshot", "avg_age_days",
            "avg_error_rate", "last_ingested",
        ]].rename(columns={
            "ticker_coverage": "tickers (vs universe)",
            "last_snapshot":   "most recent update",
            "avg_age_days":    "avg age",
            "avg_error_rate":  "error rate",
            "last_ingested":   "last ingested",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Section: Global Historical
# ---------------------------------------------------------------------------

st.subheader("Global Datasets — Historical")
st.caption(
    "Datasets with a single global endpoint that fetches a date range "
    "(e.g. treasury rates, economic indicators). Expected range: 1990-01-01 → today."
)

if gh.empty:
    st.info("No global historical data found.")
else:
    disp = gh.copy()
    disp["avg_coverage"]   = disp["avg_coverage_ratio"].apply(_fmt_pct)
    disp["avg_error_rate"] = disp["avg_error_rate"].apply(_fmt_pct)
    disp["min_date"]       = _fmt_date(disp["min_date"])
    disp["max_date"]       = _fmt_date(disp["max_date"])
    disp["last_ingested"]  = _fmt_date(disp["last_ingested_at"])

    st.dataframe(
        disp[[
            "domain", "source", "dataset", "discriminator",
            "min_date", "max_date",
            "avg_coverage", "avg_error_rate", "last_ingested",
        ]].rename(columns={
            "avg_coverage":   "date coverage",
            "avg_error_rate": "error rate",
            "last_ingested":  "last ingested",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Section: Global Snapshot
# ---------------------------------------------------------------------------

st.subheader("Global Datasets — Snapshot")
st.caption(
    "Datasets with a single global endpoint that returns a point-in-time snapshot "
    "(e.g. stock list, market sectors). Shows most recent update date."
)

if gs.empty:
    st.info("No global snapshot data found.")
else:
    disp = gs.copy()
    disp["last_snapshot"]  = _fmt_date(disp["last_snapshot_date"])
    disp["avg_age_days"]   = disp["avg_age_days"].apply(
        lambda v: f"{int(v):,}d" if pd.notna(v) else "—"
    )
    disp["avg_error_rate"] = disp["avg_error_rate"].apply(_fmt_pct)
    disp["last_ingested"]  = _fmt_date(disp["last_ingested_at"])

    st.dataframe(
        disp[[
            "domain", "source", "dataset", "discriminator",
            "last_snapshot", "avg_age_days",
            "avg_error_rate", "last_ingested",
        ]].rename(columns={
            "last_snapshot":   "most recent update",
            "avg_age_days":    "avg age",
            "avg_error_rate":  "error rate",
            "last_ingested":   "last ingested",
        }),
        use_container_width=True,
        hide_index=True,
    )
