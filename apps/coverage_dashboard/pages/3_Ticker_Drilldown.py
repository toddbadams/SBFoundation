"""Page 3 — Ticker Drilldown

Per-dataset coverage for a single ticker, with a completeness score gauge.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import get_repo

st.set_page_config(page_title="Ticker Drilldown", layout="wide")
st.title("Ticker Drilldown")

# ---------------------------------------------------------------------------
# Load ticker list
# ---------------------------------------------------------------------------

repo = get_repo()

try:
    tickers = repo.get_distinct_tickers()
except Exception as exc:
    st.error(f"Failed to load tickers: {exc}")
    st.stop()

if not tickers:
    st.warning("ops.coverage_index is empty. Run the pipeline to populate it.")
    st.stop()

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

col_sel, col_search = st.columns([3, 1])
with col_sel:
    selected = st.selectbox("Select ticker", tickers, index=0)
with col_search:
    # Manual override if ticker not in dropdown yet
    override = st.text_input("Or type ticker", value="")

ticker = override.strip().upper() if override.strip() else selected

try:
    rows = repo.get_coverage_by_ticker(ticker)
except Exception as exc:
    st.error(f"Failed to load coverage for {ticker!r}: {exc}")
    st.stop()

if not rows:
    st.info(f"No coverage data for ticker {ticker!r}.")
    st.stop()

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Completeness score gauge
# ---------------------------------------------------------------------------
# Score = fraction of datasets that have any data (coverage_ratio > 0 or not NULL)

total_ds = len(df)
datasets_with_data = int((df["coverage_ratio"].fillna(0) > 0).sum())
completeness_pct = (datasets_with_data / total_ds * 100) if total_ds else 0.0
avg_cov = df["coverage_ratio"].dropna().mean()
last_refreshed = df["last_ingested_at"].dropna().max()
total_errors = int(df["error_count"].fillna(0).sum())

left, right = st.columns([1, 2])

with left:
    st.subheader("Completeness Score")
    st.caption(f"Datasets with any data: {datasets_with_data} / {total_ds}")

    gauge_color = (
        "#27ae60" if completeness_pct >= 80
        else "#f39c12" if completeness_pct >= 50
        else "#e74c3c"
    )

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=completeness_pct,
            number={"suffix": "%", "font": {"size": 36}},
            gauge={
                "axis": {"range": [0, 100], "ticksuffix": "%"},
                "bar": {"color": gauge_color},
                "steps": [
                    {"range": [0, 50], "color": "#3d1515"},
                    {"range": [50, 80], "color": "#3d2e0a"},
                    {"range": [80, 100], "color": "#0a2e15"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 2},
                    "thickness": 0.75,
                    "value": 80,
                },
            },
        )
    )
    fig_gauge.update_layout(height=260, margin={"l": 20, "r": 20, "t": 20, "b": 20})
    st.plotly_chart(fig_gauge, use_container_width=True)

with right:
    st.subheader("Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Datasets", f"{total_ds:,}")
    c2.metric("Avg Coverage", f"{avg_cov * 100:.1f}%" if pd.notna(avg_cov) else "—")
    c3.metric("Total Errors", f"{total_errors:,}")
    c4.metric(
        "Last Refreshed",
        str(pd.Timestamp(last_refreshed).strftime("%Y-%m-%d")) if pd.notna(last_refreshed) else "—",
    )

st.divider()

# ---------------------------------------------------------------------------
# Horizontal bar chart — coverage_ratio per dataset
# ---------------------------------------------------------------------------

st.subheader("Coverage by Dataset")

df_bar = df.copy()
df_bar["pct"] = (df_bar["coverage_ratio"].fillna(0) * 100).round(1)
df_bar = df_bar.sort_values("pct", ascending=True)

fig_bar = go.Figure(
    go.Bar(
        x=df_bar["pct"],
        y=df_bar["dataset"],
        orientation="h",
        marker=dict(
            color=df_bar["pct"],
            colorscale="RdYlGn",
            cmin=0,
            cmax=100,
            showscale=False,
        ),
        text=df_bar["pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    )
)
fig_bar.update_layout(
    height=max(300, len(df_bar) * 26),
    margin={"l": 200, "r": 60, "t": 20, "b": 40},
    xaxis={"title": "Coverage %", "range": [0, 115]},
    yaxis={"autorange": "reversed"},
)
st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# Per-dataset detail table
# ---------------------------------------------------------------------------

st.subheader("Per-Dataset Detail")

ts_mask = df["is_timeseries"].fillna(True)

display_df = df[
    ["dataset", "is_timeseries", "min_date", "max_date", "coverage_ratio",
     "error_count", "total_files", "last_ingested_at", "age_days", "last_snapshot_date"]
].copy()

display_df["coverage_ratio"] = display_df["coverage_ratio"].apply(
    lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
)
display_df["is_timeseries"] = display_df["is_timeseries"].apply(
    lambda v: "timeseries" if v else "snapshot"
)
display_df["age_days"] = display_df["age_days"].apply(
    lambda v: f"{int(v)}d" if pd.notna(v) else "—"
)
display_df.columns = [
    "Dataset", "Type", "Min Date", "Max Date", "Coverage",
    "Errors", "Total Files", "Last Ingested", "Age", "Last Snapshot"
]

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Stale snapshots callout
# ---------------------------------------------------------------------------

stale = df[(~ts_mask) & df["age_days"].notna() & (df["age_days"] >= 30)]
if not stale.empty:
    st.warning(
        f"{len(stale)} snapshot dataset(s) for {ticker} not refreshed in ≥30 days: "
        + ", ".join(stale["dataset"].tolist())
    )
