# Strawberry AI Context: Ops Host Telemetry (CPU/RAM/Temp/Disk/Network)

## Goal

Add a new “Ops Host Telemetry” data stream to Strawberry that periodically samples host performance metrics and makes them available in:
1) Silver as append-only time-series tables (Parquet / DuckDB landing),
2) Gold as rollups for dashboards and alerting.

This must work on:
- Raspberry Pi (Linux) as the primary runtime target.
- Windows laptop as a secondary dev/runtime target.

Temperature and throttling are optional and may be unavailable on Windows; the pipeline must degrade gracefully (nulls, no crashes).

## Non-goals

- No tight coupling between core ingestion flows and hardware sensors.
- No vendor-specific Windows temperature integration by default (only implement if cheap and robust).
- No privileged/unsafe system access.
- No background daemon requirements beyond running inside Strawberry’s existing orchestration/scheduling.

## Architecture Fit

Treat telemetry as its own domain (e.g., `ops/telemetry`) with:
- Sampling: lightweight collector(s).
- Persistence: Silver dataset(s) storing raw samples.
- Analytics: Gold rollups for ops dashboards and alerts.

Telemetry is independent of financial ingestion, but may attach a `run_id` when called from within ingestion runs for correlation.

## Datasets

### Silver Dataset: OPS_HOST_METRICS_DATASET

Append-only, one row per sample per host.

Required columns:
- as_of: TIMESTAMP (UTC)
- host_id: TEXT (stable identifier; configurable)
- os: TEXT (e.g., linux, windows)
- arch: TEXT (e.g., aarch64, x86_64)
- cpu_pct: DOUBLE (0..100)
- cpu_count_logical: INT
- ram_total_mb: BIGINT
- ram_used_mb: BIGINT
- ram_available_mb: BIGINT
- swap_total_mb: BIGINT (0 if not supported)
- swap_used_mb: BIGINT
- disk_root_total_gb: DOUBLE (or MB, but be consistent)
- disk_root_free_gb: DOUBLE
- net_rx_bytes: BIGINT (monotonic counter since boot)
- net_tx_bytes: BIGINT (monotonic counter since boot)

Optional columns (nullable):
- cpu_temp_c: DOUBLE NULL
- throttle_flags: TEXT NULL (Pi only; raw string or bitmask string)
- cpu_freq_mhz: DOUBLE NULL (if available)
- process_rss_mb: BIGINT NULL (Strawberry process memory, optional)
- process_cpu_pct: DOUBLE NULL (optional)

### Gold Dataset: OPS_HOST_METRICS_5M_ROLLUP_DATASET

Aggregated rollups per host per 5m bucket:
- bucket_start (timestamp)
- host_id
- cpu_pct_avg, cpu_pct_p95, cpu_pct_max
- ram_used_mb_avg, ram_used_mb_max
- disk_root_free_gb_min
- cpu_temp_c_max (nullable)
- net_rx_rate_bps_avg, net_tx_rate_bps_avg (derived from counters)

### Gold Dataset: OPS_HOST_ALERTS_DATASET (optional)

Rows represent triggered alerts:
- as_of
- host_id
- alert_type (ENUM-like text)
- severity
- message
- context_json

## Collection Semantics

Sampling interval:
- Default: 10 seconds for raw samples (configurable).
Rollup interval:
- Default: 5 minutes for Gold rollups.

Sampling must be:
- Low overhead.
- Robust to partial failures (e.g., temp read fails => set null; do not abort).

## Cross-platform strategy

Use a “provider” abstraction:
- Portable metrics provider: works on Linux + Windows for CPU/RAM/disk/network via cross-platform OS counters.
- Linux Pi sensor provider: attempts CPU temperature + throttling flags, only on Linux (and only if paths/commands exist).

Provider resolution:
- Detect OS at runtime.
- Compose providers: always include portable, optionally include linux-pi sensors.

## Configuration

Add config object (yaml/toml/json; follow Strawberry conventions) with:
- enabled: bool
- host_id: string (default: hostname; override allowed)
- sample_interval_seconds: int (default 10)
- rollup_interval_minutes: int (default 5)
- include_process_metrics: bool (default false)
- disk_mount: string (default "/" on linux; "C:\\" on windows)
- network_interface: optional string (if absent, total across interfaces)

## Storage & Contracts

Persist samples in Silver as Parquet (partition by date) and expose in DuckDB.
Do not invent new persistence patterns; follow existing repository conventions in Strawberry (Parquet repositories and/or DuckDB landing tables).

Data quality rules:
- as_of required
- host_id required
- cpu_pct must be 0..100
- all *_mb and *_bytes must be >= 0
- cpu_temp_c may be null; if present must be plausible (0..120)

## Integration points

1) Prefect flow (or existing scheduler) that runs indefinitely or on schedule:
- "collect host metrics samples" task: appends to Silver dataset.
- "build rollups" task: reads Silver, writes Gold.

2) Streamlit Ops UI:
- Timeseries charts for cpu_pct, ram_used_mb, disk_root_free_gb, cpu_temp_c (if not null).
- A status card: current CPU, RAM, Disk, Temp, last sample age.

3) Optional correlation:
- If run_id exists in Strawberry ingestion context, include it; otherwise null.

## Testing Requirements

Unit tests:
- Provider returns required fields with correct types.
- Provider handles missing temp gracefully.
- Config parsing + defaults.
- Rollup computation for a small synthetic dataset.

Integration test (optional):
- Run sampler once, write parquet, read back and validate schema.

## Implementation Constraints

- Python only.
- Avoid privileged operations.
- Prefer a single dependency for portable metrics (e.g., psutil) if already acceptable in the stack.
- Any OS-specific reads must be conditional and safe.

## Deliverables

- telemetry domain module with providers, DTO/schema, repository writer, flow/scheduler.
- rollup builder module.
- Streamlit ops page enhancements.
- docs updates: how to enable/disable and how metrics map to dashboards.

## Codex implementation steps (sequenced, no ambiguity)

1. Create domain structure

* Add `src/strawberry/ops/telemetry/` with:

  * `config.py`
  * `providers/base.py`
  * `providers/portable_psutil.py`
  * `providers/linux_pi_sensors.py`
  * `schemas.py` (or DTOs)
  * `writer.py` (Silver append)
  * `rollups.py` (Gold aggregations)
  * `flow.py` (Prefect flow or your scheduler integration)

2. Define the schema once

* Implement a dataclass (or pydantic if that’s your convention) `HostMetricsSample`.
* Make optional fields nullable and default to `None`.
* Add a `to_row()` that returns a dict with stable keys and types.

3. Implement config with defaults

* `TelemetryConfig` with the options in the context file.
* Host ID default: hostname, but allow override (env var / config).

4. Implement the provider abstraction

* `SystemMetricsProvider` protocol:

  * `collect(config) -> dict[str, Any]` returning partial metrics.
* `CompositeProvider` merges dicts; later providers override only their own keys.

5. Portable provider (Windows + Linux)

* Use cross-platform OS counters to populate all required non-optional fields:

  * CPU %, logical cores
  * RAM totals/available/used, swap
  * Disk root usage
  * Network rx/tx bytes
* Include `os`, `arch`, `host_id`, `as_of` centrally (not per-provider).

6. Linux Pi sensors provider (optional enrichment)

* If `platform.system().lower() == "linux"`:

  * Try CPU temp: read from `/sys/class/thermal/thermal_zone0/temp` if present (convert millidegree C).
  * Try throttling flags (optional): if `vcgencmd` exists, parse output; else skip.
* Any failure returns `{}` or sets fields to `None`; never raise.

7. Writer for Silver (append-only)

* Implement `HostMetricsRepository.append(samples: list[HostMetricsSample])`.
* Store to Parquet with partitioning by date derived from `as_of`.
* Keep file naming consistent with your existing conventions (dataset/partition pathing).

8. Rollup builder for Gold

* Read Silver samples for a date/time range.
* Compute 5-minute buckets per host:

  * avg/p95/max for cpu_pct
  * avg/max for ram_used_mb
  * min for disk_root_free_gb
  * max for cpu_temp_c (ignore nulls)
  * network rate bps from counter deltas per bucket
* Write results as a Gold dataset (Parquet, partitioned by date).

9. Prefect (or scheduler) integration

* Create a flow that:

  * loops on interval (or uses Prefect scheduling) to collect and append samples
  * periodically triggers rollups (e.g., every 5 minutes, or on schedule)
* Ensure it can be turned off via `TelemetryConfig.enabled`.

10. Streamlit ops enhancements

* Add a new “Host Telemetry” section:

  * latest sample card
  * charts: cpu_pct, ram_used_mb, disk_root_free_gb, cpu_temp_c (conditional)
* If temp is null, hide temp chart or show “Temp not available on this host”.

11. Tests

* Unit tests for:

  * portable provider returns required keys with non-null values
  * linux provider returns temp on mocked sysfs file, returns {} when missing
  * repository append writes correct schema and can be read back
  * rollups produce expected aggregates on synthetic data

12. Documentation

* Add a short doc page:

  * enabling telemetry
  * what metrics exist
  * what differs on Windows vs Pi
  * how to interpret throttling flags (if implemented)

