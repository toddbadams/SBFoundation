Cool — your answers basically lock the architecture. Here’s what I’d change/add to make it *feel exactly like RunProvider*, but for charts.

## Problem

Right now you’ve got:

* `ChartRecipe` (one chart) ✅
* `SeriesRecipe` (what a series is) ✅
  …but you’re missing the **execution wrapper** (`ChartSetRecipe`) and the **lineage + calculation contract** for `SeriesRecipe` (where data comes from + how it’s computed).

## Solution

### 1) Add `ChartSetRecipe` (unit of execution)

You said it explicitly: a set contains multiple charts, and title comes from the set.

**ChartSetRecipe should include:**

* `chart_set_id` (identity)
* `title`
* `charts: list[ChartRecipe]`
* `builder_class` (or `builder_ref`) — the class that knows how to build the set from silver
* optional scheduling/gating fields (mirrors DatasetRecipe ideas): `min_age_days`, `is_ticker_based`, etc.

This keeps your current `ChartRecipe` intact.

---

### 2) Upgrade `SeriesRecipe` to include lineage + calculation

You want: “series is an output from a calculation based on multiple silver columns” and “series recipe needs to understand where data is coming from and what class/method calculates the series”.

So keep the existing descriptive fields, **and add two things**:

#### A) Silver lineage spec

Something like:

* `inputs: list[SeriesInputSpec]`

Where each `SeriesInputSpec` includes:

* `dataset` (silver dataset/table identity)
* `discriminator: dict[str, str] | None` (for multi-series tables; e.g., `{ "name": "GDP" }`)
* `cols: list[str]` (which columns the calc needs)
* optional `required: bool = True` (so you can gracefully degrade)

#### B) Calculation hook (serializable)

* `calc_ref: str` (example: `"analytics.macro.builders.GdpBuilder:real_gdp_series"`)

Why string? Because recipes should be portable/config-driven like your DatasetRecipes (no hard runtime function pointers in dataclasses).

This gives you:

* lineage for audit/debug
* deterministic “how this was made”
* ability to load/execute the calc at runtime

---

### 3) ChartRequest mirrors RunRequest

You said yes: include `from_date`, `to_date`, `as_of` and ticker/date runtime vars.

So `ChartRequest` becomes:

* `chart_set_id`
* `ticker: str | None`
* `from_date`
* `to_date`
* `as_of` (requested window end)
* `run_id` (new run_id for chart builds)
* `recipe: ChartSetRecipe`

---

### 4) ChartProvider mirrors RunProvider

**Execution flow (same vibe as RunProvider):**

1. Build requests from recipes (ticker-based expands across tickers)
2. Gate builds using a `ChartDataDatesDTO` (your chart equivalent of `RunDataDatesDTO`)
3. For each request:

   * load silver inputs (provider doesn’t need to understand DTO schema; builder does)
   * call builder
   * builder returns `ChartSetDTO`
   * provider computes `as_of = max date across all series points` (your rule)
   * drop failed series (your rule)
4. Persist to **Gold parquet**, overwriting latest by `(chart_set_id, ticker)` (your rule)
5. Emit a **ChartBuildSummary** artifact (your RunContext equivalent)

---

### 5) Contract tweaks to match your decisions

#### A) `ChartDTO.subtitle` should be optional

You want: allow `None` and don’t render it.

So update `ChartDTO.subtitle: str | None` and make `from_json_row` tolerant of missing/None.

#### B) Remove snapshot from chart logic

You said: “LET’s remove ChartSnapshotDTO from our logic.”

Fastest safe path:

* Make `ChartSetDTO.snapshot: ChartSnapshotDTO | None = None`
* `to_dict()` omits snapshot if None
* `from_json_row()` only reads snapshot if present

That lets you stop generating snapshot immediately without breaking existing DTO plumbing.

---

## The only remaining “sharp edge” question (to finalize the contract)

When a series fails and you “drop the series”, do you also want to drop the **chart** if it ends up with **zero series**?

I’d default to:

* drop failed series
* if chart has 0 series → drop chart
* if chart set has 0 charts → still persist (with empty charts) *or* mark summary as failed (your call)

If you answer that one, we can lock the error semantics completely.

If you want, I can also propose the exact field names/types for `ChartSetRecipe`, `SeriesInputSpec`, `ChartRequest`, `ChartDataDatesDTO`, and `ChartBuildSummary` so they line up cleanly with your existing Run* objects and feel “same factory, different product.”
