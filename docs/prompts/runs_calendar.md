# Runs Calendar with Streamlit Calendar

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

PLANS.md is checked into this repo at `docs/AI_context/PLANS.md`. Maintain this ExecPlan in accordance with that file.

## Purpose / Big Picture

After this change, the Runs page will show a calendar view of runs using the streamlit-calendar component so a user can see runs placed by date at a glance. Each run will appear as a Streamlit badge styled green for success and red for failure, and clicking that badge will navigate directly to the Run Detail page. A user will be able to start the Streamlit UI, open the Runs page, see colored runs on the calendar, and click a run badge to open its Run Detail view.

## Progress

- [x] (2026-01-17T11:01Z) Drafted the ExecPlan with repo context, decisions, and validation criteria.
- [x] (2026-01-17T13:03Z) Add the streamlit-calendar dependency and confirm the calendar API shape in this environment.
- [x] (2026-01-17T11:21Z) Build run calendar events and badge buttons, then integrate them into `src/ui/pages/2_Runs.py` while keeping existing filters and table behavior (including start-date-only events and status+suffix badge labels).
- [x] (2026-01-17T13:10Z) Validate the calendar UI and badge navigation in the running Streamlit app.

## Surprises & Discoveries

- Observation: `requirements.txt` is UTF-16, so UTF-8 patch tooling fails.
  Evidence: `Get-Content -Encoding Byte -TotalCount 4 requirements.txt` returned `255 254`.

- Observation: `streamlit_calendar` is not installed in the current virtual environment.
  Evidence: `importlib.util.find_spec("streamlit_calendar")` returned `MISSING`.

- Observation: Installing `streamlit-calendar` failed with an OSError on Windows during dependency resolution.
  Evidence: `python -m pip install streamlit-calendar` ended with `OSError: [Errno 22] Invalid argument`.

- Observation: `streamlit-calendar` is installed in the repo virtual environment and exposes the expected `calendar` signature.
  Evidence: `.venv\\Scripts\\python` reports version `1.4.0` and signature `(events=[], options={}, custom_css='', callbacks=[...], license_key=..., key=None)`.

- Observation: Run Detail raised `KeyError: 'promotion_started_at'` because the UI column list omitted promotion fields.
  Evidence: `src/ui/services/ops_data.py` attempted `bronze_df["promotion_started_at"]` while `src/ui/ui_settings.py` lacked promotion columns.

## Decision Log

- Decision: Use `started_at` as the primary calendar date and fall back to `finished_at` when `started_at` is missing.
  Rationale: The start date best represents when a run occurred; the fallback ensures runs with only a finish timestamp still appear on the calendar.
  Date/Author: 2026-01-17 / Codex.

- Decision: Determine failure status by checking `bronze_failed`, `silver_failed_rows`, `gold_builds_failed`, and `status` values of `failure`, `failed`, or `partial`.
  Rationale: This matches existing "only failures" filtering logic and aligns with how the Runs page already interprets failed runs.
  Date/Author: 2026-01-17 / Codex.

- Decision: Use Streamlit badges as clickable buttons by rendering the badge directive inside `st.button` labels and routing clicks to `OpsUIService.navigate_to_run`.
  Rationale: `st.badge` is not clickable, while `st.button` supports the same Markdown directives; this keeps the UI aligned with the "badge" requirement and allows direct navigation.
  Date/Author: 2026-01-17 / Codex.

- Decision: Show calendar events only on `started_at` dates and omit fallback to `finished_at`.
  Rationale: The calendar should represent run starts only, per the latest UI requirement.
  Date/Author: 2026-01-17 / Codex.

- Decision: Badge labels include the run status plus the last four characters of the run ID.
  Rationale: This aligns with the request to show status and a short identifier on the badges.
  Date/Author: 2026-01-17 / Codex.

- Decision: The calendar is locked to a month-only view without week/day toggles.
  Rationale: The UI requirement is for a month-only calendar display.
  Date/Author: 2026-01-17 / Codex.

- Decision: Pin `streamlit-calendar` to version `1.4.0`.
  Rationale: Pip resolved `streamlit-calendar-1.4.0` as the latest available during install; pinning stabilizes dependency resolution.
  Date/Author: 2026-01-17 / Codex.

- Decision: Include promotion columns in `BRONZE_COLUMNS` to align UI dataframes with ops.bronze_manifest schema.
  Rationale: The UI converts promotion timestamps and expects these columns; adding them prevents KeyErrors even when values are null.
  Date/Author: 2026-01-17 / Codex.

## Outcomes & Retrospective

Completed. The Runs page shows a month-only calendar with events on start dates, badges navigate to Run Detail, and Run Detail renders without errors after aligning promotion columns. Remaining gaps: none noted.

## Context and Orientation

The Streamlit UI entrypoint is `src/ui/app.py`, which routes to `src/ui/pages/2_Runs.py` for the Runs page and `src/ui/pages/3_Run_Detail.py` for the Run Detail page. The Runs page pulls data from DuckDB via `src/ui/infra/duckdb_ops_repo.py` and `src/ui/services/ops_data.py`, which exposes a DataFrame of run summaries with columns defined in `src/ui/ui_settings.py`. Navigation to Run Detail uses `OpsUIService.navigate_to_run` in `src/ui/services/ops_ui.py`, which sets the `run_id` query parameter and switches pages.

The streamlit-calendar component is an external Streamlit component that renders a calendar view and accepts a list of event dictionaries and a set of calendar options. It returns a dictionary containing user interactions such as event clicks, which can be used to drive navigation.

## Plan of Work

First, add the `streamlit-calendar` dependency to the repo so the component can be imported from `streamlit_calendar`. Confirm the installed API by opening the installed package in the virtual environment and verifying the `calendar` function signature and the structure of event click callbacks.

Next, add a small, pure helper module that converts the run summaries DataFrame into calendar events and determines success or failure status per run. This keeps logic deterministic and testable and avoids embedding data shaping directly in the page script. Then update `src/ui/pages/2_Runs.py` to build a filtered run set as it does today, render the calendar using `streamlit_calendar.calendar`, and render a list of clickable run badges that call `OpsUIService.navigate_to_run` when clicked. The calendar should be driven by the same filtered runs so that date range and failure filters apply consistently to both the calendar and the table.

Finally, update any UI documentation that describes the Runs page (`docs/stock_ui/ops_ui.md`) to mention the calendar and badge navigation, and validate the behavior by running the app locally and navigating through the UI.

## Concrete Steps

Work in `c:/strawberry`. Use search to confirm the Runs page and supporting services.

    PS C:\sb\SBFoundation> rg -n "2_Runs.py|Run Detail|OpsUIService|run_summary" src/ui

Add the dependency. If you are using Poetry, add the dependency there and propagate the pinned version into `requirements.txt` so both installation paths remain usable.

    PS C:\sb\SBFoundation> poetry add streamlit-calendar

If you are using pip, install and then record the installed version into `requirements.txt`.

    PS C:\sb\SBFoundation> pip install streamlit-calendar

Inspect the installed package to confirm the import path and the `calendar` API.

    PS C:\sb\SBFoundation> python - <<'PY'
    import streamlit_calendar
    import inspect
    print(streamlit_calendar.__file__)
    print(inspect.signature(streamlit_calendar.calendar))
    PY

Create a new helper module at `src/ui/services/ops_calendar.py` with functions to pick the run date, classify status, and build calendar events plus a list of undated runs. Then update `src/ui/pages/2_Runs.py` to import this helper, render the calendar, and render badge buttons for each run. Keep the existing filters and table selection behavior intact.

Run the app to validate manually.

    PS C:\sb\SBFoundation> streamlit run src/ui/app.py

You should see the local URL in the terminal, similar to:

    Local URL: http://localhost:8501

## Validation and Acceptance

Start the Streamlit UI and open the Runs page. The calendar should render a monthly grid populated with runs from `ops.file_ingestions`, using the filtered set of runs. Runs classified as failures should appear in red, and successes in green, and the calendar should show the run label in each event. Below or beside the calendar, each run should appear as a Streamlit badge button; clicking a badge should navigate to the Run Detail page and set the `run_id` query parameter. The existing run table should still appear and selecting a row should still navigate to Run Detail. Acceptance is met when a user can navigate to Run Detail by clicking either a calendar event or a run badge, and the status colors consistently match the failure logic.

## Idempotence and Recovery

Dependency installation can be re-run safely; if the install fails, remove the dependency entries from `pyproject.toml` and `requirements.txt` and retry. UI edits are additive and can be re-applied; if the Runs page fails to load, comment out the calendar section to return to the previous table-only view and then reintroduce changes incrementally. The helper module is pure and can be safely modified without data side effects.

## Artifacts and Notes

Example calendar event dictionary used with streamlit-calendar:

    {
        "title": "Run 1a2b3c",
        "start": "2026-01-16",
        "allDay": True,
        "className": "run-status-failure",
        "extendedProps": {"run_id": "full-run-id", "status": "failure"},
    }

Example click handling pattern after calling `calendar(...)`:

    if calendar_state and calendar_state.get("eventClick"):
        payload = calendar_state["eventClick"]["event"]
        run_id = (payload.get("extendedProps") or {}).get("run_id") or payload.get("id")
        if run_id:
            ui.navigate_to_run(run_id)

Badge button label pattern:

    label = f":green-badge[Run {run_suffix}]"
    if st.button(label, key=f"run-badge-{run_id}", type="tertiary"):
        ui.navigate_to_run(run_id)

## Interfaces and Dependencies

Add `streamlit-calendar` as a dependency and import it in `src/ui/pages/2_Runs.py` with `from streamlit_calendar import calendar`. The calendar function should accept `events`, `options`, and `custom_css` arguments and return a dict containing an `eventClick` payload. Use `className` values like `run-status-success` and `run-status-failure` in event dicts and supply CSS to render those classes as pill-style badges.

Define the following helper functions in `src/ui/services/ops_calendar.py` to keep the data shaping deterministic:

    def pick_run_date(row: dict[str, object]) -> datetime.date | None: ...
    def classify_run_status(row: dict[str, object]) -> str: ...
    def build_calendar_events(runs_df: pd.DataFrame) -> tuple[list[dict[str, object]], list[str]]: ...

`build_calendar_events` must return a list of event dicts for the calendar and a list of run_ids that could not be assigned a date so they can still be shown as badges outside the calendar.

Change Note: 2026-01-17T13:10Z Marked validation complete and recorded outcomes.
