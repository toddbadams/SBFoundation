"""Page 4 — Ingestion Diagnostics

Error rates, latency, and hash-change frequency drawn from ops.file_ingestions.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from db import get_repo

st.set_page_config(page_title="Ingestion Diagnostics", layout="wide")
st.title("Ingestion Diagnostics")
st.caption("Error rates, latency, and hash stability drawn from ops.file_ingestions.")

repo = get_repo()

# ---------------------------------------------------------------------------
# Load all diagnostic data sets in parallel (Streamlit evaluates top-to-bottom
# but we declare them together for readability)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_error_rates() -> pd.DataFrame:
    return pd.DataFrame(repo.get_ingestion_error_rates())

@st.cache_data(ttl=300)
def load_latency() -> pd.DataFrame:
    return pd.DataFrame(repo.get_ingestion_latency())

@st.cache_data(ttl=300)
def load_hash_stability() -> pd.DataFrame:
    return pd.DataFrame(repo.get_hash_stability())

@st.cache_data(ttl=300)
def load_recent_errors() -> pd.DataFrame:
    return pd.DataFrame(repo.get_recent_errors(limit=200))


try:
    df_err = load_error_rates()
    df_lat = load_latency()
    df_hash = load_hash_stability()
    df_errs = load_recent_errors()
except Exception as exc:
    st.error(f"Failed to load diagnostics: {exc}")
    st.stop()

if df_err.empty:
    st.warning("ops.file_ingestions is empty. Run the pipeline to populate it.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary KPIs
# ---------------------------------------------------------------------------

total_files = int(df_err["total_files"].sum())
total_errors = int(df_err["error_count"].sum())
overall_error_pct = (total_errors / total_files * 100) if total_files else 0.0
datasets_with_errors = int((df_err["error_count"] > 0).sum())
avg_latency_ms = df_lat["avg_ms"].dropna().mean() if not df_lat.empty else None

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Files", f"{total_files:,}")
c2.metric("Total Errors", f"{total_errors:,}")
c3.metric("Overall Error Rate", f"{overall_error_pct:.2f}%")
c4.metric("Datasets w/ Errors", f"{datasets_with_errors:,}")
c5.metric(
    "Avg Latency",
    f"{avg_latency_ms:.0f} ms" if avg_latency_ms is not None and pd.notna(avg_latency_ms) else "—",
)

st.divider()

tab_errors, tab_latency, tab_hash, tab_log = st.tabs(
    ["Error Rates", "Latency", "Hash Stability", "Error Log"]
)

# ---------------------------------------------------------------------------
# Tab 1 — Error Rates
# ---------------------------------------------------------------------------

with tab_errors:
    st.subheader("Error Rate by Dataset")
    st.caption(
        "Percentage of bronze ingestion files that contain a bronze_error. "
        "Datasets with 0% error rate are hidden."
    )

    df_err_nonzero = df_err[df_err["error_count"] > 0].copy()

    if df_err_nonzero.empty:
        st.success("No errors found in ops.file_ingestions.")
    else:
        df_err_nonzero = df_err_nonzero.sort_values("error_rate_pct", ascending=True)

        fig_err = go.Figure(
            go.Bar(
                x=df_err_nonzero["error_rate_pct"],
                y=df_err_nonzero["dataset"],
                orientation="h",
                marker=dict(
                    color=df_err_nonzero["error_rate_pct"],
                    colorscale="RdYlGn_r",
                    cmin=0,
                    cmax=100,
                    showscale=True,
                    colorbar={"title": "Error %", "thickness": 12},
                ),
                text=df_err_nonzero["error_rate_pct"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside",
                customdata=df_err_nonzero[["total_files", "error_count"]].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Error rate: %{x:.2f}%<br>"
                    "Total files: %{customdata[0]:,}<br>"
                    "Error files: %{customdata[1]:,}<extra></extra>"
                ),
            )
        )
        fig_err.update_layout(
            height=max(300, len(df_err_nonzero) * 28),
            margin={"l": 200, "r": 80, "t": 20, "b": 40},
            xaxis={"title": "Error Rate %", "range": [0, 115]},
            yaxis={"autorange": "reversed"},
        )
        st.plotly_chart(fig_err, use_container_width=True)

    # Full table for reference
    with st.expander("All datasets (including zero-error)"):
        display = df_err[["dataset", "total_files", "error_count", "error_rate_pct", "last_seen"]].copy()
        display["error_rate_pct"] = display["error_rate_pct"].apply(
            lambda v: f"{v:.2f}%" if pd.notna(v) else "0.00%"
        )
        display.columns = ["Dataset", "Total Files", "Errors", "Error Rate", "Last Seen"]
        st.dataframe(display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tab 2 — Latency
# ---------------------------------------------------------------------------

with tab_latency:
    st.subheader("Bronze Ingestion Latency by Dataset")
    st.caption("avg / p95 / max latency in milliseconds per dataset, slowest first.")

    if df_lat.empty:
        st.info("No latency data available (end timestamps missing).")
    else:
        df_lat_sorted = df_lat.sort_values("avg_ms", ascending=True)

        fig_lat = go.Figure()
        fig_lat.add_trace(
            go.Bar(
                name="Avg",
                x=df_lat_sorted["avg_ms"],
                y=df_lat_sorted["dataset"],
                orientation="h",
                marker_color="#4C8BF5",
            )
        )
        fig_lat.add_trace(
            go.Bar(
                name="p95",
                x=df_lat_sorted["p95_ms"],
                y=df_lat_sorted["dataset"],
                orientation="h",
                marker_color="#F5A623",
            )
        )
        fig_lat.add_trace(
            go.Bar(
                name="Max",
                x=df_lat_sorted["max_ms"],
                y=df_lat_sorted["dataset"],
                orientation="h",
                marker_color="#E74C3C",
                opacity=0.5,
            )
        )
        fig_lat.update_layout(
            barmode="overlay",
            height=max(350, len(df_lat_sorted) * 26),
            margin={"l": 200, "r": 60, "t": 20, "b": 40},
            xaxis={"title": "Latency (ms)"},
            yaxis={"autorange": "reversed"},
            legend={"orientation": "h", "y": -0.08},
        )
        st.plotly_chart(fig_lat, use_container_width=True)

        with st.expander("Latency data table"):
            display_lat = df_lat[["dataset", "samples", "avg_ms", "p95_ms", "max_ms"]].copy()
            for col in ["avg_ms", "p95_ms", "max_ms"]:
                display_lat[col] = display_lat[col].apply(
                    lambda v: f"{int(v):,} ms" if pd.notna(v) else "—"
                )
            display_lat.columns = ["Dataset", "Samples", "Avg", "p95", "Max"]
            st.dataframe(display_lat, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tab 3 — Hash Stability
# ---------------------------------------------------------------------------

with tab_hash:
    st.subheader("Payload Hash Stability by Dataset")
    st.caption(
        "hash_change_pct = distinct hashes / total files × 100. "
        "Low % = data rarely changes (stable feeds). High % = data changes frequently."
    )

    if df_hash.empty:
        st.info("No hash data available.")
    else:
        df_hash_sorted = df_hash.sort_values("hash_change_pct", ascending=False)

        fig_hash = go.Figure(
            go.Bar(
                x=df_hash_sorted["dataset"],
                y=df_hash_sorted["hash_change_pct"],
                marker=dict(
                    color=df_hash_sorted["hash_change_pct"],
                    colorscale="RdYlGn_r",
                    cmin=0,
                    cmax=100,
                    showscale=True,
                    colorbar={"title": "Change %", "thickness": 12},
                ),
                text=df_hash_sorted["hash_change_pct"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside",
                customdata=df_hash_sorted[["total_files", "distinct_hashes"]].values,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Hash change: %{y:.1f}%<br>"
                    "Total files: %{customdata[0]:,}<br>"
                    "Distinct hashes: %{customdata[1]:,}<extra></extra>"
                ),
            )
        )
        fig_hash.update_layout(
            height=400,
            margin={"l": 60, "r": 60, "t": 20, "b": 140},
            xaxis={"tickangle": -45},
            yaxis={"title": "Hash Change %", "range": [0, 115]},
        )
        st.plotly_chart(fig_hash, use_container_width=True)

        with st.expander("Hash stability data table"):
            display_hash = df_hash[["dataset", "total_files", "distinct_hashes", "hash_change_pct"]].copy()
            display_hash["hash_change_pct"] = display_hash["hash_change_pct"].apply(
                lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
            )
            display_hash.columns = ["Dataset", "Total Files", "Distinct Hashes", "Change %"]
            st.dataframe(display_hash, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tab 4 — Error Log
# ---------------------------------------------------------------------------

with tab_log:
    st.subheader("Recent Ingestion Errors")
    st.caption("Last 200 bronze files with bronze_error set, newest first.")

    if df_errs.empty:
        st.success("No errors in the error log.")
    else:
        # Dataset filter
        ds_options = ["(all)"] + sorted(df_errs["dataset"].unique().tolist())
        ds_filter = st.selectbox("Filter by dataset", ds_options, index=0)

        df_show = df_errs if ds_filter == "(all)" else df_errs[df_errs["dataset"] == ds_filter]

        # Truncate long error messages for display
        df_display = df_show[["occurred_at", "dataset", "ticker", "error_message", "run_id"]].copy()
        df_display["error_message"] = df_display["error_message"].apply(
            lambda v: str(v)[:120] + "…" if v and len(str(v)) > 120 else v
        )
        df_display.columns = ["Occurred At", "Dataset", "Ticker", "Error", "Run ID"]

        st.dataframe(df_display, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df_display):,} of up to 200 most recent errors.")
