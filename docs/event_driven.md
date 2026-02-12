# ChatGPT Conversation Reference

**Problem statement:**
You’re building a bronze→silver data pipeline driven by “next call” logic per *(ticker, endpoint)*. You need a durable **State** that records past calls and decides the next one, event-driven orchestration, and clean hand-offs between ingestion (bronze) and validation/standardization (silver). Prefect should coordinate events, retries, and visibility.

---

# Spec: Event-driven Bronze→Silver Ingestion with Prefect

## 1) Domain model

### 1.1 Entities

* **Ticker**: canonical symbol (e.g., `AAPL`). Given by the `NormalizedTicker` class.
* **Endpoint**: external API resource (e.g., `TIME_SERIES_DAILY_ADJUSTED`, `CASH_FLOW`, `BALANCE_SHEET`). Given by the `TickerTable` Enum class.
* **CallWindow**: `TimeSeriesSnapshotWindow` and `FundamentalsSnapshotWindow`

### 1.2 State (per *(ticker, endpoint)*)

Stored in a Parquet-backed repository, one row per active state (latest wins), plus history table. The base class is `TickerState`.

**Partitioning & storage**

* **State snapshot table**: `/state/current/` (Parquet), partitioned by `endpoint` then `ticker`.
* **State history** (append-only): `/state/history/` with event metadata (see §3.3).

### 1.3 Endpoint “Next-Call” Strategy (shared logic)

Introduce a pluggable strategy interface applied across endpoints:

See `TimeSeriesSnapshotWindow` class and `FundamentalsSnapshotWindow` class.

Each endpoint maps to a strategy and `schedule_policy` via configuration (see §6).

### 1.4 Ticker State Service

Provide a `TickerStateService` abstraction on top of the Parquet state tables. The service:

* Fetches a state's latest snapshot for a given `(ticker, endpoint)`.
* Persists state updates back to storage.
* Computes the next time a ticker should be evaluated.
* Lists states due for evaluation.

Flows interact with this service instead of touching storage directly, allowing the underlying repository to change without
affecting orchestration code.

### 1.5 Ticker Event Service

Add a `TickerEventService` responsible for persisting all pipeline events to a Parquet-backed repository. The service captures each event emitted in the system and writes it to durable storage for auditing and replay. Consumers can query this repository to reconstruct event timelines or drive downstream analytics.

---

## 2) Storage layout

### 2.1 Bronze (raw API JSON)

```
/bronze/{endpoint}/ticker={TICKER}/ingest_date={YYYY-MM-DD}/{timestamp}_{idempotency_key}.json
```

* **Write-once**; include full request/response envelope (headers, status, timings).

### 2.2 Silver (validated & normalized)

```
/silver/{endpoint}/ticker={TICKER}.parquet
```

* Columnar schema per endpoint; include provenance columns:

  * `_ingest_ts`, `_ingest_idempotency_key`, `_source_file`, `_event_id`.

---

## 3) Events & contracts (managed via Prefect Events)

### 3.1 Event types

> see `EventType` class.
> Use Prefect Events to emit and Automations to trigger flows (see §4).

### 3.2 Event schema (common envelope)

> see `PipelineEvent` class.

### 3.3 Type-specific payloads

* **State.Evaluate**: `{ "reason": "scheduled|manual|retry" }`
* **Ingestion.Requested**: `{ "window": CallWindow, "request": {url, params, headers}, "deadline": datetime }`
* **Ingestion.Succeeded**: `{ "window": CallWindow, "bronze_uri": str, "api_stats": {...}, "response_summary": {...} }`
* **Ingestion.Failed**: `{ "window": CallWindow, "error": {type, message, code}, "http": {...}? }`
* **State.Updated**: `{ "previous": State?, "current": State }`
* **Silver.Validated**: `{ "bronze_uri": str, "silver_uri": str, "rowcount": int, "schema_ver": str }`
* **Silver.Failed**: `{ "bronze_uri": str, "error": {...} }`

---

## 4) Orchestration with Prefect

### 4.1 Flows & responsibilities

* **Flow A: State Scanner**
  Uses `TickerStateService.states_due` to scan `/state/current/` and publish `State.Evaluate` for eligible states (idle & not in backoff).
* **Flow B: Evaluate State** (trigger: `State.Evaluate`)
  Loads state via `TickerStateService` → applies `NextCallStrategy` → emits `Ingestion.Requested` or sets `status=idle` if nothing to do.
* **Flow C: Perform Ingestion** (trigger: `Ingestion.Requested`)
  Executes API call, persists to bronze, emits `Ingestion.Succeeded` or `Ingestion.Failed`.
* **Flow D: Update State** (triggers: `Ingestion.Succeeded`, `Ingestion.Failed`)
  Persists updates via `TickerStateService` (`last_*`, `watermark`, `error_count`, `backoff_until`, `status`, `next_window_hint`). Emits `State.Updated`.
* **Flow E: Silver Validate & Save** (trigger: `Ingestion.Succeeded`)
  Endpoint-specific validation/cleaning; writes Parquet to silver; emits `Silver.Validated` or `Silver.Failed`.

> Each flow is a Prefect 2.x flow with small, testable tasks. Use Prefect **Work Queues** to route by endpoint family and apply concurrency limits per provider.

To support lightweight testing outside of Prefect, dedicated service classes (`StateScannerService`, `EvaluateStateService`, `PerformIngestionService`, `UpdateStateService`, `SilverValidateService`) offer thin wrappers around these flows, emitting the same `PipelineEvent` messages while delegating persistence to `TickerStateService` and `TickerEventService`.

### 4.2 Automations (events → flows)

* Automation A: on `State.Evaluate` → run **Evaluate State**.
* Automation B: on `Ingestion.Requested` → run **Perform Ingestion**.
* Automation C: on `Ingestion.Succeeded|Ingestion.Failed` → run **Update State**.
* Automation D: on `Ingestion.Succeeded` → run **Silver Validate & Save**.

### 4.3 Scheduling

* **State Scanner** runs on a cron every day at 21:05 UTC.
  It also honors endpoint SLA windows (e.g., “only after market close”).
* Backoff is handled in State and respected by Scanner and Evaluate.

### 4.4 Concurrency, rate limits, and QoS

* Per-endpoint **Concurrency Limits** via Prefect task runners (`limit=5` per provider account).
* Global **Rate Limiters**: shared `asyncio` semaphore or token bucket keyed by `(provider, tier)`.
* Per-ticker serial execution (one active request per *(ticker, endpoint)*) enforced by State `status` + idempotency key.

### 4.5 Silver validation & `TickerState` queries

Silver validation is responsible for promoting cleaned records to the
`/silver` layer and marking progress in the
[`TickerState`](../src/strawberry/services/dtos/ticker_state.py) table for
`DataLayer.SILVER`.

When `Flow E` succeeds it calls `TickerStateService.save_state` with
`data_layer=DataLayer.SILVER`.  The service persists a parallel state row
under a dedicated partition:

```
/state/current/endpoint=EARNINGS/ticker=AAPL/part-000.parquet
/state/current/endpoint=EARNINGS/ticker=AAPL/part-000.parquet
```

Both partitions share the same schema but represent different stages of the
pipeline.  The scanner can target either layer by supplying
`DataLayer` filters:

```python
svc = TickerStateService()

# Bronze ingestion states
bronze_due = svc.states_due(now=utcnow())

# Silver validation states
silver_due = svc.states_due(now=utcnow())

# Retrieve a single silver state
state = svc.get_state(
    NormalizedTicker("AAPL"),
    TickerTable.EARNINGS,
)
```

This approach keeps ingestion and validation progress isolated while
maintaining a unified API for querying and updating state.

---

## 5) Idempotency & exactly-once semantics

* **Idempotency key** = `hash(ticker|endpoint|window|endpoint_version)`.
* **Perform Ingestion** checks bronze for an existing file with the same key; if found, short-circuit to `Ingestion.Succeeded` re-emit (idempotent replay).
* **Update State** applies **compare-and-swap** semantics using the previous `status` and `idempotency_key` to avoid double updates.
* **Silver** writes are **append-only** with deterministic partition paths; a secondary **upsert** job (optional) can compact duplicates by `(ticker, endpoint, natural_key)`.

---

## 6) Configuration

* **Endpoints registry** (YAML, versioned):

  ```yaml
  endpoints:
    dividends:
      strategy: TimeWindowStrategy
      window: {period: "P1M", overlap: "P3D"}
      url: "https://api.vendor.com/v1/dividends"
      params_template: {ticker: "{ticker}", from: "{from}", to: "{to}"}
      headers_block: "vendor-api-headers"    # Prefect Secret/Block
      rate_limit_key: "vendor:standard"
    quotes:
      strategy: CursorStrategy
      url: "..."
      params_template: {ticker: "{ticker}", cursor: "{cursor}"}
  ```
* **Environment** (Azure-friendly defaults):

  * Storage: ADLS Gen2 paths for bronze/silver/state.
  * Auth: Prefect **Azure** blocks for credentials; Key Vault for secrets.
  * Network: Private endpoints + retriable transient errors.

---

## 7) Validation rules (silver)

For each endpoint define:

* **Schema contract** (types, required fields, nullable fields).
* **Row checks** (e.g., timestamp within window; price > 0; ISO currency).
* **Set-level checks** (no duplicate `(ticker, ts)`; expected count range).
* **Cross-file checks** (optional): e.g., watermark continuity.

On failure: emit `Silver.Failed` with a compact error summary and drop file into `/quarantine/{endpoint}/...`.

---

## 8) Observability & lineage

* **Prefect UI** for run status, retries, logs.
* **Event timeline** (via Prefect Events) links `State.Evaluate → Ingestion.Requested → Ingestion.Succeeded → Silver.Validated`.
* **Structured logs** include `correlation_id`, `idempotency_key`, `window`.
* **Metrics** (push to Azure Monitor/App Insights): request latency, rows ingested, validation pass rate, retry counts, backlog size.
* **Data lineage tags** embedded as Parquet metadata: `{event_id, correlation_id, source_url, request_hash}`.

---

## 9) Error handling & retries

* Network/5xx: exponential backoff using strategy `backoff_policy`.
* 4xx rate limit: respect `Retry-After`; update `backoff_until`.
* Parse/contract errors: mark `Ingestion.Failed` (no retry unless strategy says the window should be retried).
* Circuit breaker: if `error_count >= N`, set `status=disabled` and alert.

---

## 10) Security

* Read secrets via Prefect **Blocks** (no secrets in code/events).
* Encrypt bronze payloads at rest; redact sensitive headers in events/logs.
* Principle of least privilege on storage ACLs:

  * Ingestion writer: write `/bronze`, read `/state/current`.
  * Silver writer: read `/bronze`, write `/silver`.
  * State writer: write `/state/*`.

---

## 11) Pseudocode (flows/tasks)

```python
# Flow A
@flow("state-scanner")
def state_scanner():

    svc = TickerStateService()
    for state in svc.states_due(now=utcnow()):
        emit_event("State.Evaluate", ticker=state.ticker, endpoint=state.endpoint,
                   payload={"reason": "scheduled"})

# Flow B
@flow("evaluate-state")
def evaluate_state(ticker, endpoint):
    svc = TickerStateService()
    st = svc.get_state(ticker, endpoint)
    if not st or st.status in ["disabled", "backoff", "running"]:
        return
    window = Strategy.for_endpoint(endpoint).compute_next_window(st, last_result=None, now=utcnow())
    if not window:
        st.status = "idle"
        svc.save_state(st)
        return
    req = build_request(endpoint, ticker, window)
    st.status = "pending"
    svc.save_state(st)
    emit_event(
        "Ingestion.Requested",
        ticker,
        endpoint,
        idempotency_key=st.idempotency_key,
        payload={"window": window, "request": req},
    )

# Flow C
@flow("perform-ingestion", retries=3)
def perform_ingestion(ticker, endpoint, window, request, idempotency_key):
    if BronzeRepo.exists(idempotency_key):
        bronze_uri = BronzeRepo.uri_for(idempotency_key)
        emit_event("Ingestion.Succeeded", ticker, endpoint,
                   payload={"window": window, "bronze_uri": bronze_uri})
        return
    resp = call_api(request)
    bronze_uri = BronzeRepo.write_json(idempotency_key, envelope(resp, request))
    emit_event("Ingestion.Succeeded", ticker, endpoint,
               payload={"window": window, "bronze_uri": bronze_uri})

# Flow D
@flow("update-state")
def update_state(event):
    svc = TickerStateService()
    st = svc.get_state(event.ticker, event.endpoint)
    if event.type == "Ingestion.Succeeded":
        st.error_count = 0
        st.last_success_at = utcnow()
        st.watermark = Strategy.for_endpoint(st.endpoint).advance_watermark(st, event.payload.window)
        st.status = "idle"
    else:  # Failed
        st.error_count += 1
        st.backoff_until = utcnow() + Strategy.for_endpoint(st.endpoint).backoff_policy(st.error_count, event.payload.error)
        st.status = "backoff"
    svc.save_state(st)
    emit_event("State.Updated", st.ticker, st.endpoint, payload={"current": st})

# Flow E
@flow("silver-validate-save")
def silver_validate_save(ticker, endpoint, bronze_uri, idempotency_key):
    df = read_bronze(bronze_uri)
    validated = validate(endpoint, df)
    silver_uri = SilverRepo.write_parquet(endpoint, ticker, validated, metadata={"_ingest_idempotency_key": idempotency_key})
    emit_event("Silver.Validated", ticker, endpoint,
               payload={"bronze_uri": bronze_uri, "silver_uri": silver_uri, "rowcount": len(validated)})
```

---

## 12) Data quality & SLA dashboards

* **Freshness** by endpoint (max `now - last_success_at` per ticker).
* **Coverage** (% of expected windows completed).
* **Error budget** (retries, failure rate).
* **Validation KPIs** (row drop %, schema drift incidents).

---

## 13) Testing & rollout

* **Unit tests** for strategies (window math, backoff, watermark movement).
* **Contract tests** per endpoint (golden API responses → expected bronze files & silver rows).
* **Replay tests**: feed recorded bronze JSONs and verify deterministic silver outputs & idempotent state.
* **Chaos tests**: inject timeouts, 429s, partial writes.

---

## 14) Deliverables

1. **Endpoint registry** (config).
2. **Ticker state service** (fetch/update & scheduling helpers).
3. **State repository** (Parquet I/O + optimistic updates).
4. **Strategies library** (time, cursor, sequence, hybrid).
5. **Prefect flows** A–E + Automations wiring.
6. **Storage schema** (bronze/silver/state paths & metadata).
7. **Validation rules** per endpoint.
8. **Runbooks** (retry/backoff, disabling endpoints, manual replays).

---

### Notes for your environment

Given your Azure stack, use:

* **ADLS Gen2** for `/bronze`, `/silver`, `/state`.
* **Managed Identity + Prefect Azure Blocks** for auth.
* **Azure Application Insights** for metrics/logs export.

If you want, I can turn this into a repo scaffold (dirs, config templates, Prefect deployments, and a sample `TimeWindowStrategy`) so you can start wiring endpoints immediately.
