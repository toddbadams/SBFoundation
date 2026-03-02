"""Page 1 — Global Overview

Visualises data coverage across four categories:

  1. Per-Ticker Historical  — heatmap: ticker coverage % × avg date coverage %
  2. Per-Ticker Snapshot    — heatmap: ticker coverage % × freshness (age)
  3. Global Historical      — horizontal bar chart: date coverage % per series
  4. Global Snapshot        — staleness table

Per-ticker coverage denominator: US_ALL_CAP universe (5,280 tickers).
Expected date range for historical datasets: 1990-01-01 → today.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import get_repo

US_ALL_CAP_SIZE = 5_280

st.set_page_config(page_title="Global Overview", layout="wide")
st.title("Global Overview")
st.caption("Data coverage matrix split by scope (global / per-ticker) and type (historical / snapshot).")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

repo = get_repo()


def _safe_load(fn, label: str):
    try:
        return fn()
    except Exception as exc:
        st.error(f"Failed to load {label}: {exc}")
        return []


pth_rows = _safe_load(repo.get_per_ticker_historical_summary, "per-ticker historical")
pts_rows = _safe_load(repo.get_per_ticker_snapshot_summary,   "per-ticker snapshot")
gh_rows  = _safe_load(repo.get_global_historical_summary,     "global historical")
gs_rows  = _safe_load(repo.get_global_snapshot_summary,       "global snapshot")

pth = pd.DataFrame(pth_rows)
pts = pd.DataFrame(pts_rows)
gh  = pd.DataFrame(gh_rows)
gs  = pd.DataFrame(gs_rows)

if pth.empty and pts.empty and gh.empty and gs.empty:
    st.warning("ops.coverage_index is empty. Run the pipeline to populate it.")
    st.stop()

# ---------------------------------------------------------------------------
# Top metric cards
# ---------------------------------------------------------------------------

n_hist_datasets  = len(pth) + (len(gh) if not gh.empty else 0)
n_snap_datasets  = len(pts) + (len(gs) if not gs.empty else 0)
max_tickers_cov  = int(pth["tickers_covered"].max()) if not pth.empty else 0
avg_date_cov     = float(pth["avg_coverage_ratio"].dropna().mean()) if not pth.empty else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Historical Datasets", f"{n_hist_datasets:,}")
c2.metric("Snapshot Datasets",   f"{n_snap_datasets:,}")
c3.metric(
    "Max Tickers Covered",
    f"{max_tickers_cov:,} / {US_ALL_CAP_SIZE:,}  ({max_tickers_cov / US_ALL_CAP_SIZE * 100:.1f}%)"
    if max_tickers_cov else "—",
)
c4.metric(
    "Avg Date Coverage (per-ticker hist.)",
    f"{avg_date_cov * 100:.1f}%" if avg_date_cov is not None else "—",
)

st.divider()


# ---------------------------------------------------------------------------
# Helper: build a two-metric normalised heatmap
# ---------------------------------------------------------------------------

def _heatmap(df: pd.DataFrame, y_col: str, metrics: list[dict]) -> go.Figure:
    """Generic two-column heatmap where each `metrics` entry has:
        label, values (Series, already in [0,1]), text (Series of display strings).
    """
    datasets  = df[y_col].tolist()
    metric_labels = [m["label"] for m in metrics]
    z    = [[float(v) for v in m["values"]] for m in metrics]
    text = [[str(t) for t in m["text"]]    for m in metrics]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=datasets,
            y=metric_labels,
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
    fig.update_layout(
        height=max(200, len(datasets) * 22 + 100),
        margin={"l": 120, "r": 40, "t": 20, "b": 180},
        xaxis={"side": "top", "tickangle": -45},
    )
    return fig


# ---------------------------------------------------------------------------
# Section 1: Per-Ticker Historical
# ---------------------------------------------------------------------------

st.subheader("Per-Ticker Historical Datasets")
st.caption(
    f"Each column is a dataset; rows show ticker coverage % (vs {US_ALL_CAP_SIZE:,}) "
    "and average date coverage % (vs 1990-01-01 → today). "
    "Sorted weakest date coverage first (left)."
)

if pth.empty:
    st.info("No per-ticker historical datasets in coverage index.")
else:
    max_t = US_ALL_CAP_SIZE

    ticker_norm = (pth["tickers_covered"].fillna(0) / max_t).clip(0, 1)
    ticker_text = pth["tickers_covered"].apply(
        lambda v: f"{int(v):,} ({int(v) / max_t * 100:.0f}%)" if pd.notna(v) else "—"
    )

    cov_norm = pth["avg_coverage_ratio"].fillna(0).clip(0, 1)
    cov_text = pth["avg_coverage_ratio"].apply(
        lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
    )

    fig = _heatmap(
        pth,
        y_col="dataset",
        metrics=[
            {"label": "Ticker Coverage",    "values": ticker_norm, "text": ticker_text},
            {"label": "Avg Date Coverage",  "values": cov_norm,    "text": cov_text},
        ],
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Per-Ticker Snapshot
# ---------------------------------------------------------------------------

st.subheader("Per-Ticker Snapshot Datasets")
st.caption(
    f"Each column is a dataset; rows show ticker coverage % (vs {US_ALL_CAP_SIZE:,}) "
    "and freshness (lower avg age = greener). Sorted most tickers covered first (left)."
)

if pts.empty:
    st.info("No per-ticker snapshot datasets in coverage index.")
else:
    max_t   = US_ALL_CAP_SIZE
    max_age = pts["avg_age_days"].dropna().max() or 1

    ticker_norm = (pts["tickers_covered"].fillna(0) / max_t).clip(0, 1)
    ticker_text = pts["tickers_covered"].apply(
        lambda v: f"{int(v):,} ({int(v) / max_t * 100:.0f}%)" if pd.notna(v) else "—"
    )

    # Freshness: older = worse → invert (0 = oldest, 1 = freshest)
    fresh_norm = (1.0 - pts["avg_age_days"].fillna(max_age) / max_age).clip(0, 1)
    fresh_text = pts["avg_age_days"].apply(
        lambda v: f"{int(v)}d ago" if pd.notna(v) else "—"
    )

    fig = _heatmap(
        pts,
        y_col="dataset",
        metrics=[
            {"label": "Ticker Coverage", "values": ticker_norm, "text": ticker_text},
            {"label": "Freshness",       "values": fresh_norm,  "text": fresh_text},
        ],
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Global Historical
# ---------------------------------------------------------------------------

st.subheader("Global Historical Datasets")
st.caption(
    "Single-series global datasets with a date range (e.g. treasury rates, economic indicators). "
    "Bar shows date coverage % vs 1990-01-01 → today."
)

if gh.empty:
    st.info("No global historical datasets in coverage index.")
else:
    gh2 = gh.copy()
    gh2["label"] = gh2.apply(
        lambda r: r["dataset"] + (f" [{r['discriminator']}]" if r["discriminator"] else ""),
        axis=1,
    )
    gh2["pct"] = (gh2["avg_coverage_ratio"].fillna(0) * 100).round(1)

    fig_bar = go.Figure(
        go.Bar(
            x=gh2["pct"],
            y=gh2["label"],
            orientation="h",
            marker=dict(
                color=gh2["pct"],
                colorscale="RdYlGn",
                cmin=0,
                cmax=100,
                showscale=False,
            ),
            text=gh2["pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        )
    )
    fig_bar.update_layout(
        height=max(300, len(gh2) * 28),
        margin={"l": 250, "r": 80, "t": 20, "b": 40},
        xaxis={"title": "Date Coverage %", "range": [0, 115]},
        yaxis={"autorange": "reversed"},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 4: Global Snapshot
# ---------------------------------------------------------------------------

st.subheader("Global Snapshot Datasets")
st.caption(
    "Single-series global datasets that are fetched as point-in-time snapshots "
    "(e.g. stock list, market sectors, commodities list)."
)

if gs.empty:
    st.info("No global snapshot datasets in coverage index.")
else:
    disp = gs.copy()
    disp["last_update"] = pd.to_datetime(disp["last_snapshot_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("—")
    disp["age"]         = disp["avg_age_days"].apply(
        lambda v: f"{int(v):,}d" if pd.notna(v) else "—"
    )
    disp["err_rate"]    = disp["avg_error_rate"].apply(
        lambda v: f"{float(v) * 100:.2f}%" if pd.notna(v) else "—"
    )

    st.dataframe(
        disp[[
            "domain", "source", "dataset", "discriminator",
            "last_update", "age", "total_files", "err_rate",
        ]].rename(columns={
            "last_update": "most recent update",
            "age":         "avg age",
            "total_files": "files",
            "err_rate":    "error rate",
        }),
        use_container_width=True,
        hide_index=True,
    )
