"""Coverage Dashboard — Home

Landing page showing global health metrics across all datasets.
"""

import pandas as pd
import streamlit as st

from db import get_repo

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

try:
    rows = repo.get_coverage_summary()
except Exception as exc:
    st.error(f"Failed to load coverage index: {exc}")
    st.info("Run the pipeline at least once to populate ops.coverage_index.")
    st.stop()

if not rows:
    st.warning("ops.coverage_index is empty. Run the pipeline to populate it.")
    st.stop()

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Global metric cards
# ---------------------------------------------------------------------------

total_datasets = df["dataset"].nunique()
total_tickers = int(df["tickers_covered"].sum())

timeseries_avg = df["avg_coverage_ratio"].dropna()
avg_coverage = float(timeseries_avg.mean()) if not timeseries_avg.empty else None

datasets_with_errors = int((df["avg_error_rate"].fillna(0) > 0).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Datasets", f"{total_datasets:,}")
col2.metric("Tickers Covered", f"{total_tickers:,}")
col3.metric(
    "Avg Coverage",
    f"{avg_coverage * 100:.1f}%" if avg_coverage is not None else "—",
)
col4.metric("Datasets w/ Errors", datasets_with_errors)

st.divider()

# ---------------------------------------------------------------------------
# Dataset summary table
# ---------------------------------------------------------------------------

st.subheader("Dataset Summary")
st.caption("Sorted weakest coverage first. Use the sidebar pages for drilldowns.")

display = df.copy()
display["avg_coverage"] = display["avg_coverage_ratio"].apply(
    lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
)
display["avg_error_rate"] = display["avg_error_rate"].apply(
    lambda v: f"{v * 100:.2f}%" if pd.notna(v) else "—"
)
display["last_ingested_at"] = pd.to_datetime(display["last_ingested_at"]).dt.strftime("%Y-%m-%d %H:%M")

st.dataframe(
    display[["domain", "source", "dataset", "tickers_covered", "avg_coverage", "avg_error_rate", "last_ingested_at"]].rename(
        columns={
            "tickers_covered": "tickers",
            "avg_coverage": "avg coverage",
            "last_ingested_at": "last ingested",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
