# Pub / Sub

| Pub Service            | Event / Payload                                                                                        | Sub Service                           | Sync API                                                                                |
|------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------|-----------------------------------------------------------------------------------------|
| PrefectScheduler       |                                                                                                        | TickerScanner.process(event)          | DB READ: control/TICKER_STATE                                                           |
| TickerScanner          | READY_TO_INJEST / Ticker                                                                               | TickerBronzeInjestor.process(event)   | API {ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code}   |
| TickerBronzeInjestor   | READY_TO_STORE / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)     | TickerAPIStore.process(event)         | DB STORE:  layer/endpoint/ticker/injest_date                                            |
| TickerAPIStore         | BRONZE_FAILED / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)      | TickerAPIFailed.process(event)        | DB STORE:  control/TICKER_FAILURES                                                      |
| TickerAPIStore         | BRONZE_COMPLETED / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)   | TickerSilverIngestor.process(event)   | DB UPDATE: control/TICKER_STATE                                                         |
| TickerSilverIngestor   | READY_TO_STORE / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)     | TickerAPIStore.process(event)         | DB STORE:  layer/endpoint/ticker/injest_date                                            |
| TickerAPIStore         | SILVER_FAILED / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)      | TickerAPIFailed.process(event)        | DB STORE:  control/TICKER_FAILURES                                                      |
| TickerAPIStore         | SILVER_COMPLETED / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)   | TickerGoldIngestor.process(event)     | DB UPDATE: control/TICKER_STATE                                                         |
| TickerGoldIngestor     | READY_TO_STORE / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)     | TickerAPIStore.process(event)         | DB STORE:  layer/endpoint/ticker/injest_date                                            |
| TickerAPIStore         | GOLD_FAILED / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)        | TickerAPIFailed.process(event)        | DB STORE:  control/TICKER_FAILURES                                                      |
| TickerAPIStore         | GOLD_COMPLETED / (ticker, injest_date, endpoint, layer, req, req_hash, res, res_hash, status_code)     | TickerReadyToScan.process(event)      | DB UPDATE: control/TICKER_STATE                                                         |
| TickerReadyToScan      | IDLE / (ticker)                                                                                        | TickerIdler.process(event)            | DB UPDATE:  control/TICKER_STATE                                                        |

``` mermaid
flowchart TD
  %% ===========
  %% Legend
  %% ===========
  classDef pub fill:#e3f2fd,stroke:#1565c0,stroke-width:1px
  classDef sub fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px
  classDef store fill:#fff3e0,stroke:#ef6c00,stroke-width:1px
  classDef fail fill:#ffebee,stroke:#c62828,stroke-width:1px
  classDef sys fill:#f3e5f5,stroke:#6a1b9a,stroke-width:1px
  classDef db fill:#fafafa,stroke:#616161,stroke-dasharray: 3 3

  %% ===========
  %% Services
  %% ===========
  TickerScanner["TickerScanner (sub)"]:::pub
  TickerBronzeInjestor["TickerBronzeInjestor (sub→pub)"]:::sub
  TickerSilverIngestor["TickerSilverIngestor (sub→pub)"]:::sub
  TickerGoldIngestor["TickerGoldIngestor (sub→pub)"]:::sub
  TickerAPIStore["TickerAPIStore (sub→pub)"]:::store
  TickerAPIFailed["TickerAPIFailed (sub)"]:::fail
  TickerReadyToScan["TickerReadyToScan (sub→pub)"]:::sub
  TickerIdler["TickerIdler (sub)"]:::sub

  %% ===========
  %% Datastores (Sync APIs)
  %% ===========
  DBState["DB: control/TICKER_STATE"]:::db
  DBFailures["DB: control/TICKER_FAILURES"]:::db
  DBLayer["DB: layer/endpoint/ticker/injest_date"]:::db

  %% ===========
  %% Scan → Ingest pipeline
  %% ===========
  TickerScanner -- "READY_TO_INJEST" --> TickerBronzeInjestor

  %% Bronze
  TickerBronzeInjestor -- "READY_TO_STORE" --> TickerAPIStore
  TickerAPIStore -- "BRONZE_COMPLETED" --> TickerSilverIngestor
  TickerAPIStore -- "BRONZE_FAILED" --> TickerAPIFailed

  %% Silver
  TickerSilverIngestor -- "READY_TO_STORE" --> TickerAPIStore
  TickerAPIStore -- "SILVER_COMPLETED" --> TickerGoldIngestor
  TickerAPIStore -- "SILVER_FAILED" --> TickerAPIFailed

  %% Gold
  TickerGoldIngestor -- "READY_TO_STORE" --> TickerAPIStore
  TickerAPIStore -- "GOLD_COMPLETED" --> TickerReadyToScan
  TickerAPIStore -- "GOLD_FAILED " --> TickerAPIFailed

  %% Ready → Idle cycle
  TickerReadyToScan -- "IDLE" --> TickerIdler

  %% ===========
  %% Sync API calls (dashed)
  %% ===========
  TickerScanner -. "DB: control/TICKER_STATE" .- DBState
  TickerBronzeInjestor -. "API: write state & payload indexes" .- DBState
  TickerSilverIngestor -. "Sync API: write state & payload indexes" .- DBState
  TickerGoldIngestor -. "Sync API: write state & payload indexes" .- DBState
  TickerAPIStore -. "DB: layer/endpoint/ticker/injest_date" .- DBLayer
  TickerAPIStore -. "DB: control/TICKER_STATE" .- DBState
  TickerAPIFailed -. "DB: control/TICKER_FAILURES" .- DBFailures
  TickerIdler -. "DB: control/TICKER_STATE" .- DBState
```
