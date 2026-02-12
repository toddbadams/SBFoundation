# Core Concepts of an Algorithmic Trading Platform
### Canonical Definitions & System Relationships

This document defines the fundamental terms used throughout the algorithmic trading platform and explains how they relate to one another.

The intent is to:
- establish a shared vocabulary
- enforce separation of concerns
- prevent architectural drift
- make research, production, and risk systems interoperable

---

## 1. Asset

An **asset** is a tradable financial instrument.

Examples:
- equities
- ETFs
- futures
- options
- bonds
- FX pairs
- crypto assets

Assets are uniquely identified by an internal identifier (not by ticker alone).

---

## 2. Instrument

An **instrument** is a concrete, tradeable representation of an asset.

Examples:
- AAPL common stock (NASDAQ)
- ES March 2026 futures contract
- SPY ETF

An asset may map to multiple instruments (e.g., different listings or contracts).

---

## 3. Universe

A **universe** is a defined set of instruments considered for analysis or trading.

Universes are explicit and versioned.

Examples:
- S&P 500 constituents
- Top 3000 U.S. equities by market cap
- Custom watchlist

A universe answers:
> “Which instruments exist *in principle* for this strategy?”

---

## 4. Data

**Data** is raw or processed information sourced from external or internal systems.

Categories:
- market data (prices, volume)
- fundamental data (financial statements)
- macroeconomic data
- alternative data (sentiment, flows)

Data by itself has no semantics until processed.

---

## 5. Dataset

A **dataset** is a structured collection of data with a defined schema and meaning.

Examples:
- daily adjusted prices
- quarterly balance sheets
- rolling volatility series

Datasets are immutable within a run and versioned over time.

---

## 6. Feature

A **feature** is a *measured property* of an instrument at a specific point in time.

It answers:
> “What is true about this instrument right now?”

Features are descriptive, not prescriptive.

Properties:
- time-indexed
- instrument-specific
- reproducible
- economically interpretable
- opinion-free

Examples:
- EBIT / TEV
- manipulation probability
- 8-year ROA
- financial strength score

---

## 7. Factor

A **factor** is a *hypothesis about expected returns*.

It answers:
> “Instruments with this characteristic tend to earn a return premium.”

Factors are:
- cross-sectional
- directional
- empirically validated
- typically expressed as long–short portfolios

Examples:
- Value
- Momentum
- Quality
- Low Volatility

A factor is not a column; it is a **construction**.

---

## 8. Signal

A **signal** converts features (and sometimes factors) into **investment intent**.

It answers:
> “Given these characteristics, what stance should I take?”

Signals:
- encode opinions
- may be continuous or discrete
- are allowed to be wrong
- are portfolio- or strategy-specific

Examples:
- rank score
- long / neutral / short flag
- conviction weight

---

## 9. Screener

A **screener** is a hard eligibility filter.

It answers:
> “Which instruments are allowed to participate at all?”

Screeners:
- are binary (in/out)
- reduce the universe
- enforce constraints
- are defensive, not predictive

Examples:
- exclude high distress probability
- exclude insufficient history
- exclude illiquid instruments

---

## 10. Strategy

A **strategy** is a coherent decision framework that combines:
- universe definition
- screeners
- signals
- portfolio construction rules

A strategy defines *what* to do, not *how* to execute it.

---

## 11. Portfolio

A **portfolio** is a capital allocation across instruments.

It answers:
> “How much capital is assigned to each instrument?”

Inputs:
- eligible universe
- signals
- risk estimates
- constraints

Outputs:
- target weights
- target exposures

The portfolio layer does not generate signals or features.

---

## 12. Position

A **position** is the realized holding of an instrument.

Attributes:
- quantity
- market value
- exposure
- unrealized PnL

Positions are the stateful result of execution.

---

## 13. Trade

A **trade** is a discrete transaction that changes positions.

Attributes:
- instrument
- quantity
- price
- timestamp
- fees

Trades are atomic and irreversible.

---

## 14. Execution

**Execution** is the process of converting portfolio intent into trades.

Responsibilities:
- order generation
- broker interaction
- fill handling
- slippage and fees

Execution does not decide *what* to trade.

---

## 15. Order

An **order** is an instruction sent to a broker or exchange.

Examples:
- market order
- limit order
- stop order

Orders may be partially filled or rejected.

---

## 16. Risk

**Risk** is the uncertainty of outcomes relative to objectives.

Common forms:
- volatility risk
- drawdown risk
- liquidity risk
- concentration risk
- tail risk

Risk is measured, constrained, and monitored — not eliminated.

---

## 17. Risk Model

A **risk model** estimates the distribution of potential outcomes.

Outputs may include:
- volatility
- correlations
- factor exposures
- Value-at-Risk (VaR)

Risk models inform portfolio construction and limits.

---

## 18. Constraint

A **constraint** is a hard or soft limit imposed on decisions.

Examples:
- max position size
- sector exposure caps
- leverage limits
- turnover limits

Constraints express policy, regulation, or risk tolerance.

---

## 19. Backtest

A **backtest** simulates a strategy on historical data.

Purpose:
- evaluate performance
- assess robustness
- identify failure modes

Backtests must enforce:
- temporal correctness
- realistic execution assumptions
- fixed rules

---

## 20. Simulation

A **simulation** is a broader class of hypothetical evaluation.

Includes:
- backtests
- stress tests
- scenario analysis
- Monte Carlo paths

---

## 21. Regime

A **regime** is a persistent market state.

Examples:
- risk-on / risk-off
- expansion / contraction
- low / high volatility

Regimes may alter signals, constraints, or allocations.

---

## 22. Model

A **model** is a mathematical mapping from inputs to outputs.

Examples:
- regression
- classifier
- optimizer
- probabilistic model

Models are tools, not strategies.

---

## 23. Parameter

A **parameter** is a tunable input to a model or rule.

Examples:
- lookback window
- threshold
- decay rate

Parameters must be explicit and versioned.

---

## 24. Hyperparameter

A **hyperparameter** controls model training or structure.

Examples:
- regularization strength
- tree depth
- learning rate

---

## 25. Experiment

An **experiment** is a controlled evaluation of a hypothesis.

It freezes:
- data
- parameters
- rules
- code version

Experiments produce auditable results.

---

## 26. Metric

A **metric** measures performance or behavior.

Examples:
- CAGR
- Sharpe ratio
- max drawdown
- turnover

Metrics describe outcomes; they do not drive decisions directly.

---

## 27. Benchmark

A **benchmark** is a reference for comparison.

Examples:
- S&P 500
- risk-free rate
- factor index

Benchmarks contextualize results.

---

## 28. Pipeline

A **pipeline** is an ordered sequence of processing steps.

Pipelines enforce:
- determinism
- reproducibility
- lineage

---

## 29. Versioning

**Versioning** tracks changes in:
- data
- code
- parameters
- models

Versioning is mandatory for auditability.

---

## 30. Run

A **run** is a single execution of a pipeline or strategy.

Each run has:
- a unique identifier
- immutable inputs
- immutable outputs

---

## 31. Monitoring

**Monitoring** observes live system behavior.

Includes:
- performance drift
- risk breaches
- data quality issues
- execution anomalies

Monitoring feeds feedback loops.

---

## 32. Feedback Loop

A **feedback loop** uses observed outcomes to adjust future behavior.

Examples:
- model retraining
- parameter recalibration
- regime reassessment

Feedback loops must be controlled and auditable.

---

## 33. End-to-End Flow

Canonical flow:

```

Data
→ Datasets
→ Features
→ Screeners
→ Signals
→ Portfolio
→ Orders
→ Trades
→ Positions
→ Monitoring
→ Feedback

```

Each stage answers exactly one question.

---

## 34. Guiding Principle

> Facts are not opinions.  
> Opinions are not allocations.  
> Allocations are not executions.

Respecting these boundaries is what makes an algorithmic trading platform
robust, explainable, and scalable.

---

``` mermaid
flowchart TB
  %% Canonical concepts and how they hang together

  subgraph D["Data & Identity"]
    A["Asset\n(economic thing)"]
    I["Instrument\n(tradable representation)"]
    U["Universe\n(set of instruments)"]
    SRC["Sources\n(vendors, brokers, internal)"]
    DATA["Raw Data\n(payloads, ticks, filings)"]
    DS["Datasets\n(structured tables/series)"]
  end

  subgraph R["Research Primitives"]
    FTR["Feature\n(measurement per instrument per time)"]
    FAC["Factor\n(return hypothesis)"]
    FACC["Factor Construction\n(ranking + long/short rules)"]
    FRET["Factor Returns\n(time series of factor portfolio returns)"]
    SCR["Screener\n(binary eligibility gate)"]
    SIG["Signal\n(opinion/intent from features)"]
  end

  subgraph P["Portfolio & Trading"]
    RM["Risk Model\n(vol, corr, exposures)"]
    CON["Constraints\n(limits, caps, turnover)"]
    PC["Portfolio Construction\n(weights from signals + risk + constraints)"]
    ORD["Orders\n(instructions to broker)"]
    EXE["Execution\n(order routing + fills)"]
    TRD["Trades\n(fills, fees, slippage)"]
    POS["Positions\n(holdings/exposure)"]
    PNL["PnL\n(realized + unrealized)"]
  end

  subgraph O["Operations"]
    MON["Monitoring\n(ops, risk, performance)"]
    FB["Feedback Loop\n(recalibration/retraining)"]
    EXP["Experiments\n(frozen config + run)"]
    MET["Metrics\n(Sharpe, DD, turnover)"]
    BM["Benchmarks\n(S&P 500, rf, factor idx)"]
    RUN["Run\n(single execution instance)"]
    VER["Versioning\n(code/data/params)"]
    REG["Regime\n(state classification)"]
    MOD["Model\n(mapping inputs->outputs)"]
    PAR["Parameters\n(tunable inputs)"]
    HYP["Hyperparameters\n(training controls)"]
  end

  %% Identity & universe
  A --> I --> U

  %% Data lineage
  SRC --> DATA --> DS

  %% Features derived from datasets for instruments in a universe
  U --> DS
  DS --> FTR

  %% Screeners and signals consume features
  FTR --> SCR
  FTR --> SIG

  %% Factors: hypothesis + construction + returns (built from features)
  FAC --> FACC
  FTR --> FACC
  FACC --> FRET

  %% Regime can influence signals/constraints/portfolio
  DS --> REG
  REG --> SIG
  REG --> CON

  %% Portfolio construction consumes eligible universe + signals + risk + constraints
  U --> SCR
  SCR --> PC
  SIG --> PC
  RM --> PC
  CON --> PC

  %% Trading lifecycle
  PC --> ORD --> EXE --> TRD --> POS --> PNL

  %% Monitoring and feedback
  POS --> MON
  TRD --> MON
  PNL --> MON
  MON --> FB
  FB --> PAR
  FB --> MOD

  %% Experiments / backtests / evaluation
  EXP --> RUN
  RUN --> DS
  RUN --> VER
  PAR --> EXP
  HYP --> EXP
  MOD --> EXP
  EXP --> MET
  BM --> MET
  FRET --> MET
  PNL --> MET
```