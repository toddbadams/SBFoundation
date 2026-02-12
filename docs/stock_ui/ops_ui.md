

You are implementing a Streamlit Ops UI for the Strawberry project. Build a local-only (laptop-only) Streamlit application using Streamlit’s native multipage URLs (the `pages/` folder approach). Do not implement any networking for LAN access; bind to localhost only. The UI must support dark and light themes via Streamlit theme configuration. The UI must be designed to extend beyond Bronze ingest to Silver promotion, Gold builds, chart builds, backtests, and execution as those stages are developed.

Primary data input: the run summary JSON files produced by the pipeline. The json filename is determined as: `destination = Path(ROOT_FOLDER) / MANIFEST_FOLDER / f"summary-{summary.run_id}-{summary.started_at.date().isoformat()}.json"` in the `RunContextFileAdapter` class. Use `RunContext` class to infer the current schema. The code should load many such summary JSON files from `ROOT_FOLDER / MANIFEST_FOLDER` directory. Do not hardcode absolute paths; use configuration.

Canonical status taxonomy: `passed`, `failed`, `too-soon`. A failed item will populate the `error` property. Preserve these exactly. Treat any unexpected status as non-canonical but still display it.

Navigation and pages:

1. Home (Overview): show the latest run (by finished_at or file mtime), including run_id, started_at, finished_at, derived duration, and KPI tiles for Bronze passed/failed/too-soon plus Silver dto_count. Include a “Top failures” section (most recent failed items) with links to the relevant Run Detail page.
2. Runs: list runs across all domains keyed by run_id. Provide filters: date range (if timestamps available), “only runs with failures”. Show columns: run_id, started_at, finished_at, bronze_files_passed, bronze_files_failed, bronze_files_toosoon, silver_dto_count. Selecting a run must navigate to Run Detail via query parameters (e.g., `?run_id=...`) and/or Streamlit page switching. Also render a calendar view of runs with green/red status badges that link to Run Detail.
3. Run Detail: given a run_id query parameter, show run header + KPI tiles + tabs:

   * Items tab: unified items table with filtering on stage, domain, dataset, discriminator, source, status.
   * Errors tab: only failed items with the error column prominent.
   * Artifact Viewer tab: user selects an item and the app opens the Bronze JSON artifact referenced by that item (filename/path) and renders it in an in-app JSON viewer. If the artifact file doesn’t exist, show a clear error. If invalid JSON, show raw text safely.
4. Datasets: aggregate view across runs. For each (domain, dataset, discriminator) show last run_id, last finished_at, last status, and “days since last passed” (if timestamps allow). This page must be resilient if fields are missing.
5. Artifacts: simple explorer rooted at a configured artifacts root. Allow filtering by pipeline stage (bronze/silver/gold) and show a list of available artifact files. Provide an in-app viewer for JSON artifacts.
6. Settings: show effective configuration values (summaries_dir, artifacts_root, theme info) and instructions for changing them (but do not build a full settings editor unless trivial).

Extensibility requirement:

* Implement the data model and UI so that it can naturally incorporate additional pipeline stages later. Today the summary JSON has `bronze_injest_items` and a few top-level counters (bronze_* and silver_dto_count). Design an internal “pipeline items” abstraction so future additions like `silver_items`, `gold_items`, `chart_build_items`, `backtest_items`, `execution_items` can be added with minimal changes. For now, map `bronze_injest_items` to stage=`bronze`. Keep the UI stage-filterable even if only bronze exists today.
* Do not change the pipeline outputs; the UI must adapt to them. However, you may define an internal normalized representation.

Configuration:

* Use `.streamlit/config.toml` for default theme (dark or light) and localhost binding. Also include a user-visible note that Streamlit allows toggling theme.
* Use `.streamlit/secrets.toml` or an equivalent local config file for `SUMMARIES_DIR` and optionally `ARTIFACTS_ROOT`. Provide sensible defaults (e.g., `./ops_summaries` and `./`).
* The app must run entirely locally.

UX requirements:

* Favor readable tables with filtering controls.
* Clicking/choosing a run should feel like drill-down navigation.
* Artifact viewer must be the primary drill-down for Bronze items: open the bronze JSON file referenced by the item and render it in the UI.
* Use wide layout.

Deliverables:

* Create the full Streamlit app scaffold with the multipage structure described.
* Implement a loader that reads all summary JSON files in SUMMARIES_DIR and produces:
  a) a runs table (one row per run_id)
  b) an items table (one row per item across stages; currently bronze only)
* Implement all pages listed above, ensuring navigation works and Run Detail honors `run_id` query parameter.
* Include basic error handling for missing directories, missing files, invalid JSON, and empty datasets.
* Keep the code clean and modular (separate data loading/normalization from UI page rendering).

Constraints:

* Do not include any code generation in this prompt output; you must produce the actual code in the repository.
* Do not use external services.
* Do not bind to non-localhost addresses.
* Do not invent new statuses beyond displaying unexpected ones as “non-canonical”.

Acceptance criteria (must be demonstrable):

* With the provided sample summary JSON placed into the summaries directory, the Runs page shows at least one run row and the Run Detail page shows its bronze items. The Artifact Viewer can open and render the corresponding bronze artifact JSON file when the file exists.
* Theme config exists and the app can run in dark or light mode.
* The structure supports adding new stage items later without redesigning the UI.
* the outputed streamlit app is placed int he `src/ui` folder

Incorporate the following:
Problem: Streamlit makes it very easy to “just write code,” which often turns into a single file with mixed concerns (UI widgets, data access, business rules, plotting, caching, state). That’s why what you’re seeing feels pattern-less compared to MVP.

Solution: treat Streamlit as the View layer and impose structure yourself. You can absolutely use MVP/MVVM-style separation, but you adapt it to Streamlit’s execution model (top-to-bottom reruns, session state, caching).

Core Streamlit best practices (the ones that prevent spaghetti).

1. Separate concerns explicitly (even if you keep it lightweight).

* View (Streamlit): layout, widgets, rendering, navigation, user feedback.
* “Presenter”/Controller: transforms UI inputs into calls, validation, orchestration, assembling view models.
* Domain/services: scoring logic, data transforms, portfolio logic, chart building.
* Data access: provider clients (FMP/AV), repositories (Bronze/Silver/Gold readers/writers), file adapters.

This fits Strawberry well because your platform already has clear layer boundaries (Bronze → Silver → Gold → Consumers). Keep ingestion/analytics logic out of Streamlit, and make Streamlit a consumer of Gold artifacts (and sometimes a trigger to run ingestion), consistent with your medallion separation.  

2. Make reruns cheap and deterministic.

* Streamlit reruns the script on every interaction. If your code hits external APIs or does heavy compute inline, the app will feel slow and unstable.
* Put expensive work behind:

  * st.cache_data for pure data fetch/transform results (inputs → outputs).
  * st.cache_resource for long-lived objects (clients, adapters, model loaders).
* Keep side-effects (writes, ingestion triggers) behind explicit buttons, and gate them with clear “are you sure” style UI flow.

3. Use a “page model” (a view model) instead of passing raw DataFrames everywhere.

* Presenter returns a dataclass/dict that contains exactly what the page needs: tables already shaped, chart DTOs already built, status messages, error states.
* Your existing chart DTO approach is a good example of turning “messy chart inputs” into a clean contract the UI can render. 

4. Treat st.session_state as UI state only.
   Good uses:

* selected ticker, selected layer, date range, toggles, last action result, navigation state.
  Avoid:
* storing large DataFrames permanently (it bloats memory and makes behavior hard to reason about).
  Prefer caching for data, session_state for selections.

5. Establish a consistent app structure.
   A pragmatic structure that stays close to MVP:

* ui/

  * app.py (entry, config, routing)
  * pages/

    * macro_dashboard.py
    * universe_screeners.py
    * portfolio_optimizer.py
  * components/

    * filters.py
    * kpi_tiles.py
    * charts.py
* app/

  * presenters/

    * macro_presenter.py
    * optimizer_presenter.py
  * services/

    * chart_service.py
    * scoring_service.py
* data/

  * providers/ (FMP/AV clients)
  * repos/ (bronze_repo.py, silver_repo.py, gold_repo.py)
* domain/

  * dtos/, models/, logic/

This aligns with your existing “domains / packages” split (company, economics, fundamentals, technicals, analytics, ui, shared). 

6. Keep ingestion orchestration out of the UI; UI can trigger it.
   In Strawberry terms:

* UI should not embed Bronze/Silver promotion rules or recipe semantics.
* UI can call into a RunProvider/runner service, then display the RunContext and artifacts (run_id, status, counts).
  That preserves the contract-driven ingestion pipeline discipline.  

How to apply “MVP” concretely in Streamlit.

A workable mental model is “Presenter + ViewModel”:

* Streamlit page:

  * reads UI inputs
  * calls presenter.get_page_model(inputs)
  * renders from model
* Presenter:

  * validates inputs
  * calls services/repos
  * returns PageModel (view model)
* Services/repos:

  * no Streamlit imports
  * testable with pytest

Example responsibilities (for a Strawberry dashboard page).

* View: select universe layer, ticker(s), date range, “Run ingestion” button, render KPIs and charts.
* Presenter: maps selections to “which Gold dataset(s) do I load?”, handles empty-data cases, assembles ChartSetDTO.
* Service: builds ChartSetDTO from Gold series; applies transforms; returns DTO graph for consistent UI rendering. 

Common anti-patterns to look for in the code you’re reviewing.

* API calls (FMP/AV) inside the page body without caching.
* Business logic embedded in the widget callbacks.
* DataFrame shaping duplicated across multiple pages instead of a single service.
* “God modules”: pages that import everything and do everything.
* Hidden side-effects on rerun (writing files, running ingestion) without explicit user action.

If you want, paste a representative Streamlit page from your codebase and I’ll refactor it into a Presenter + PageModel shape (keeping it idiomatic Streamlit, not over-engineered).
