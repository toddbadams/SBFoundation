"""Page 2 — Dataset Drilldown

Per-ticker coverage stats and optional temporal heatmap for a selected dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import get_repo

st.set_page_config(page_title="Dataset Drilldown", layout="wide")
st.title("Dataset Drilldown")

# ---------------------------------------------------------------------------
# Load dataset list
# ---------------------------------------------------------------------------

repo = get_repo()

try:
    datasets = repo.get_distinct_datasets()
except Exception as exc:
    st.error(f"Failed to load datasets: {exc}")
    st.stop()

if not datasets:
    st.warning("ops.coverage_index is empty. Run the pipeline to populate it.")
    st.stop()

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

selected = st.selectbox("Select dataset", datasets, index=0)

try:
    rows = repo.get_coverage_by_dataset(selected)
except Exception as exc:
    st.error(f"Failed to load coverage for {selected!r}: {exc}")
    st.stop()

if not rows:
    st.info(f"No coverage data for dataset {selected!r}.")
    st.stop()

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Summary strip
# ---------------------------------------------------------------------------

ticker_count = len(df)
avg_cov = df["coverage_ratio"].dropna().mean()
avg_err = df["error_rate"].dropna().mean()
last_refreshed = df["last_ingested_at"].dropna().max()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tickers", f"{ticker_count:,}")
c2.metric("Avg Coverage", f"{avg_cov * 100:.1f}%" if pd.notna(avg_cov) else "—")
c3.metric("Avg Error Rate", f"{avg_err * 100:.1f}%" if pd.notna(avg_err) else "—")
c4.metric(
    "Last Refreshed",
    str(pd.Timestamp(last_refreshed).strftime("%Y-%m-%d %H:%M")) if pd.notna(last_refreshed) else "—",
)

st.divider()

# ---------------------------------------------------------------------------
# Histogram — coverage_ratio distribution
# ---------------------------------------------------------------------------

st.subheader("Coverage Ratio Distribution")

cov_vals = df["coverage_ratio"].dropna() * 100

fig_hist = go.Figure(
    go.Histogram(
        x=cov_vals,
        nbinsx=20,
        marker_color="#4C8BF5",
        opacity=0.8,
    )
)
fig_hist.update_layout(
    height=280,
    margin={"l": 50, "r": 20, "t": 20, "b": 40},
    xaxis={"title": "Coverage %", "range": [0, 105]},
    yaxis={"title": "# Tickers"},
    bargap=0.05,
)
st.plotly_chart(fig_hist, use_container_width=True)

# ---------------------------------------------------------------------------
# Sortable data table
# ---------------------------------------------------------------------------

st.subheader("Per-Ticker Detail")

display_df = df[
    ["ticker", "min_date", "max_date", "coverage_ratio", "error_count", "total_files", "last_ingested_at"]
].copy()

display_df["coverage_ratio"] = display_df["coverage_ratio"].apply(
    lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
)
display_df.columns = ["Ticker", "Min Date", "Max Date", "Coverage", "Errors", "Total Files", "Last Ingested"]

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Temporal heatmap (timeseries datasets only)
# ---------------------------------------------------------------------------

is_ts = bool(df["is_timeseries"].dropna().any()) if "is_timeseries" in df.columns else False

if not is_ts:
    st.caption("Snapshot dataset — temporal heatmap not applicable.")
    st.stop()

st.subheader("Temporal Coverage Heatmap")
st.caption(
    "Green cell = dataset has data for that year. "
    "Rows are tickers sorted by coverage_ratio (weakest first). "
    "Sampled to top 50 + bottom 50 tickers when >100."
)

# Build year range
today_year = pd.Timestamp.now().year
years_all = list(range(1990, today_year + 1))

# Parse date columns
df["min_year"] = pd.to_datetime(df["min_date"], errors="coerce").dt.year.astype("Int64")
df["max_year"] = pd.to_datetime(df["max_date"], errors="coerce").dt.year.astype("Int64")

# Sample tickers: weakest + strongest to keep heatmap manageable
df_sorted = df.sort_values("coverage_ratio", ascending=True, na_position="first").reset_index(drop=True)

if len(df_sorted) > 100:
    bottom50 = df_sorted.head(50)
    top50 = df_sorted.tail(50)
    df_heat = pd.concat([bottom50, top50]).drop_duplicates("ticker")
    label_note = f" (sampled: weakest 50 + strongest 50 of {len(df_sorted)} tickers)"
else:
    df_heat = df_sorted
    label_note = ""

tickers_heat = df_heat["ticker"].tolist()

# Build presence matrix: rows=tickers, cols=years
matrix = np.zeros((len(tickers_heat), len(years_all)), dtype=float)
for i, row in enumerate(df_heat.itertuples()):
    min_y = row.min_year if pd.notna(row.min_year) else None
    max_y = row.max_year if pd.notna(row.max_year) else None
    if min_y is not None and max_y is not None:
        for j, yr in enumerate(years_all):
            if min_y <= yr <= max_y:
                matrix[i, j] = 1.0

fig_theat = go.Figure(
    go.Heatmap(
        z=matrix,
        x=years_all,
        y=tickers_heat,
        colorscale=[[0, "#2d2d2d"], [1, "#27ae60"]],
        showscale=False,
        xgap=1,
        ygap=0.5,
    )
)
fig_theat.update_layout(
    height=max(400, len(tickers_heat) * 14),
    margin={"l": 100, "r": 20, "t": 20, "b": 40},
    yaxis={"autorange": "reversed"},
    xaxis={"title": f"Year{label_note}", "tickmode": "linear", "dtick": 5},
)
st.plotly_chart(fig_theat, use_container_width=True)
