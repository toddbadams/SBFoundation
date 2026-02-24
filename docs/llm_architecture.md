# QUANT AI / ML ARCHITECTURE (LOCAL WORKSTATION)

## TOP LAYER — USER & DECISION

Human / Strategy Logic
– Reviews signals and explanations
– Sets constraints (risk, leverage, regimes)
– Approves or automates execution

↓

## REASONING LAYER (LLM)

Reasoning Model (≈20–30B parameters)
Inputs:
– Numeric model outputs (signals, regimes, risk)
– Retrieved context (RAG)
– Rules & constraints

Functions:
– Synthesise signals
– Rank strategies
– Explain market state
– Sanity-check trades

Output:
– Trade recommendations
– Regime narrative
– Confidence / rationale

↓

## RETRIEVAL (RAG) LAYER

Vector Database
– Embedded research
– Earnings transcripts
– Historical regime notes
– Feature descriptions

Embedding Model
– Converts text → vectors
– Indexes new data continuously

Query Flow:
LLM → vector DB → relevant chunks → LLM context

↓

## PREDICTION LAYER (NUMERIC ML)

Numeric Models (XGBoost / LightGBM / small NN)
Inputs:
– Price features
– Technical indicators
– Macro factors
– Volatility & liquidity

Outputs:
– Return forecasts
– Regime labels
– Risk scores
– Signal strengths

These are *numbers*, not language.

↓

## FEATURE ENGINEERING LAYER

Feature Store
– Returns (multi-horizon)
– Momentum / trend
– Valuation / fundamentals
– Macro & breadth
– Volatility & correlation

Batch + rolling updates

↓

## DATA LAYER

Market Data
– Prices
– Volumes
– Fundamentals
– Macro
– News / transcripts

Stored as:
– Time-series tables
– Document store (for RAG)

↓

## HARDWARE LAYER (BOTTOM)

Workstation Hardware
– GPU: ASUS RTX 5090 TUF Gaming 32GB
– Runs reasoning LLM
– Runs embedding model
– Accelerates fine-tuning
– CPU: High-core Ryzen / Threadripper
– Feature engineering
– Data prep
– RAM: 128 GB
– In-memory feature store
– Dataset caching
– NVMe Storage: 4–8 TB
– Market data
– Vector DB
– Model checkpoints

---

ROLE SEPARATION (KEY DESIGN PRINCIPLE)

Numeric models = predict
LLM = interpret
RAG = remember

They never replace each other.

---

WHAT RUNS CONTINUOUSLY
– Feature generation
– Embedding + indexing
– Signal models

WHAT RUNS ON DEMAND
– LLM reasoning
– Strategy synthesis
– Trade explanation

---

WHY THIS ARCHITECTURE WORKS

– Avoids using LLMs for price prediction
– Keeps alpha in numeric models
– Uses LLM only for synthesis and reasoning
– Scales from manual trading → automation
– Matches your 32GB GPU constraints

