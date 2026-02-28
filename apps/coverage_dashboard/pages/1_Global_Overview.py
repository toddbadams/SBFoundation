"""Page 1 — Global Overview

Dataset Coverage Matrix: a Plotly heatmap of 4 coverage metrics across all
datasets, plus a bar chart of the 20 weakest datasets by avg coverage ratio.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import get_repo

st.set_page_config(page_title="Global Overview", layout="wide")
st.title("Global Overview")
st.caption("Dataset Coverage Matrix — 4 metrics across all datasets.")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

repo = get_repo()

try:
    rows = repo.get_coverage_matrix()
except Exception as exc:
    st.error(f"Failed to load coverage matrix: {exc}")
    st.stop()

if not rows:
    st.warning("ops.coverage_index is empty. Run the pipeline to populate it.")
    st.stop()

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Metric cards
# ---------------------------------------------------------------------------

total_datasets = len(df)
total_tickers = int(df["tickers_covered"].sum())
avg_cov = df["avg_coverage_ratio"].dropna().mean()
pct_fresh = df["pct_updated_7d"].dropna().mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Datasets", f"{total_datasets:,}")
c2.metric("Total Ticker×Dataset Rows", f"{total_tickers:,}")
c3.metric("Avg Coverage", f"{avg_cov * 100:.1f}%" if pd.notna(avg_cov) else "—")
c4.metric("Avg Updated Last 7d", f"{pct_fresh * 100:.1f}%" if pd.notna(pct_fresh) else "—")

st.divider()

# ---------------------------------------------------------------------------
# Heatmap — normalize each metric to [0, 1], higher = better
# ---------------------------------------------------------------------------

st.subheader("Dataset Coverage Matrix")
st.caption(
    "Color: green = strong, red = weak. "
    "Columns: ticker coverage, recent refresh %, median history length, data freshness."
)

# Build normalised matrix (all metrics → [0,1], higher is better)
max_tickers = df["tickers_covered"].max() or 1
max_history = df["median_history_years"].replace(0, pd.NA).dropna().max() or 1
max_age = df["oldest_max_date_age"].dropna().max() or 1

norm = pd.DataFrame(index=df["dataset"])
norm["Ticker Coverage"] = df["tickers_covered"].values / max_tickers
norm["Updated Last 7d"] = df["pct_updated_7d"].fillna(0).values
norm["Median History"] = (df["median_history_years"].fillna(0).values / max_history)
# Freshness: older max_date = worse → invert
norm["Freshness"] = 1.0 - (df["oldest_max_date_age"].fillna(max_age).values / max_age).clip(0, 1)

# Raw label matrix for hover
labels = pd.DataFrame(index=df["dataset"])
labels["Ticker Coverage"] = df["tickers_covered"].apply(lambda v: f"{int(v)} tickers")
labels["Updated Last 7d"] = df["pct_updated_7d"].apply(
    lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
)
labels["Median History"] = df["median_history_years"].apply(
    lambda v: f"{int(v)} yr" if pd.notna(v) and v else "—"
)
labels["Freshness"] = df["oldest_max_date_age"].apply(
    lambda v: f"{int(v)}d ago" if pd.notna(v) else "—"
)

datasets = df["dataset"].tolist()  # weakest first (sorted by query)
metrics = ["Ticker Coverage", "Updated Last 7d", "Median History", "Freshness"]

z = norm[metrics].values.tolist()
text = labels[metrics].values.tolist()

fig_heat = go.Figure(
    go.Heatmap(
        z=z,
        x=metrics,
        y=datasets,
        text=text,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorscale="RdYlGn",
        zmin=0,
        zmax=1,
        showscale=True,
        colorbar={"title": "Score", "thickness": 12},
    )
)
fig_heat.update_layout(
    height=max(400, len(datasets) * 22),
    margin={"l": 180, "r": 40, "t": 20, "b": 60},
    yaxis={"autorange": "reversed"},  # weakest at top
    xaxis={"side": "top"},
)
st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------------------------
# Bar chart — bottom 20 datasets by avg coverage ratio
# ---------------------------------------------------------------------------

st.subheader("20 Weakest Datasets by Coverage")

bottom20 = df.dropna(subset=["avg_coverage_ratio"]).head(20).copy()
bottom20["pct"] = (bottom20["avg_coverage_ratio"] * 100).round(1)

fig_bar = go.Figure(
    go.Bar(
        x=bottom20["pct"],
        y=bottom20["dataset"],
        orientation="h",
        marker=dict(
            color=bottom20["pct"],
            colorscale="RdYlGn",
            cmin=0,
            cmax=100,
            showscale=False,
        ),
        text=bottom20["pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    )
)
fig_bar.update_layout(
    height=max(300, len(bottom20) * 28),
    margin={"l": 200, "r": 60, "t": 20, "b": 40},
    xaxis={"title": "Avg Coverage %", "range": [0, 110]},
    yaxis={"autorange": "reversed"},
)
st.plotly_chart(fig_bar, use_container_width=True)
