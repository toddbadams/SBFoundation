Absolutely. Here's your **full specification** for the UK-focused financial planning tool, designed to support configurable income, expenses, assets, tax optimization, and Monte Carlo simulations—complete with a dashboard and modular architecture.

---

# 🧾 Full Specification – Financial Planning Tool

---

## 🚀 Overview

This tool provides personalized financial forecasts for individuals or couples in the UK. It allows flexible income, expense, and asset modeling with inflation, tax optimization, and Monte Carlo simulation to project retirement outcomes. A Streamlit dashboard visualizes drawdowns, tax, and asset balances across future years.

---

## 💻 Technical Stack

| Layer         | Technology                               |
| ------------- | ---------------------------------------- |
| Language      | Python 3.11+                             |
| Storage       | Parquet via Pandas                       |
| Config Input  | JSON                                     |
| Dashboard     | Streamlit                                |
| Logging       | `LoggerFactory` (custom)                 |
| Config Loader | `ConfigLoader` (custom)                  |
| APIs          | ONS (inflation), Moneyfacts (cash rates) |

---

## 📂 Project Structure

```
/config                  # JSON config inputs
  ├─ income.json
  ├─ expenses.json
  └─ accounts.json

/financial_plan          # Output data (post-simulation)
  ├─ results.parquet
  ├─ tax_summary.parquet
  └─ cone_simulation.parquet

/src
  ├─ config/             # DTOs and configuration logic
  │   ├─ config_loader.py
  │   ├─ income_config.py
  │   ├─ expense_config.py
  │   ├─ account_config.py
  │   └─ financial_config_bundle.py

  ├─ modeling/           # Core simulation + tax logic
  │   ├─ simulate.py
  │   ├─ tax.py
  │   └─ inflation.py

  ├─ ui/                 # Streamlit-based dashboard
  │   └─ dashboard.py

  └─ logger_factory.py   # Environment-aware logging utility
```

---

## 📁 Input JSON Specifications

### `income.json`

```json
[
  {
    "name": "Todd Salary",
    "owner": "Todd",
    "start_date": "2025-01-01",
    "end_date": "2035-12-31",
    "annual_amount": 80000,
    "annual_increase_rate": 0.03,
    "one_time": false
  }
]
```

### DTO

```python
@dataclass(frozen=True)
class IncomeConfig:
    name: str
    owner: str
    start_date: str
    end_date: Optional[str]
    annual_amount: float
    annual_increase_rate: Optional[float] = 0.0
    one_time: bool = False
```

---

### `expenses.json`

```json
{
  "annual_expense": 60000,
  "start_date": "2025-01-01",
  "end_date": null,
  "notes": "Equally divided between Todd and Spouse"
}
```

### DTO

```python
@dataclass(frozen=True)
class ExpenseConfig:
    annual_expense: float
    start_date: str
    end_date: Optional[str] = None
    notes: Optional[str] = ""
```

---

### `accounts.json`

```json
[
  {
    "owner": "Todd",
    "type": "ISA",
    "name": "Todd ISA",
    "current_balance": 50000
  }
]
```

### DTO

```python
@dataclass(frozen=True)
class AccountConfig:
    owner: str
    type: str  # ISA, SIPP, Stocks, Bonds, Cash
    name: str
    current_balance: float
```

---

### Bundle DTO

```python
@dataclass(frozen=True)
class FinancialConfigBundle:
    incomes: List[IncomeConfig]
    expenses: ExpenseConfig
    accounts: List[AccountConfig]
```

---

## 🔄 Engine Specifications

### `simulate.py` Responsibilities

* Load all config using `ConfigLoader`
* For each simulation path:

  * Apply inflation and return rate scenarios
  * Compute annual net income vs expenses
  * Apply tax rules and withdraw from accounts
  * Track asset depletion and drawdown % each year
* Generate cone of outcomes (P25/P50/P75)

---

### `tax.py` Responsibilities

* UK personal income tax bands
* Capital gains tax
* Dividend tax
* Allowance logic for:

  * ISAs (tax-free)
  * SIPPs (25% tax-free lump sum, income tax thereafter)
* Optimal withdrawal order: Taxable → ISA → SIPP

---

### `inflation.py` Responsibilities

* Query latest CPI from:

  * **ONS** (Office for National Statistics)
  * or fallback static rate if API unavailable
* Inflate income, expenses, and account values

---

## 📊 Dashboard (Streamlit)

### `dashboard.py`

* Page layout and user controls (owner, scenario)
* Displays:

  1. **Income vs. Expense Table**
  2. **Tax Summary Table**
  3. **Asset Cone Chart**

     * Median, pessimistic (P25), optimistic (P75)
  4. **Drawdown % Chart**

     * Compares against sustainable thresholds

---

## 🧠 Modeling Assumptions

| Component    | Details                                  |
| ------------ | ---------------------------------------- |
| Inflation    | Pulled from API or fixed (e.g. 2.5%)     |
| Return Rates | Randomized using historical bands        |
| Cash Growth  | Uses current saver rate                  |
| Expenses     | Grows with inflation                     |
| Withdrawals  | Satisfy expenses from available accounts |
| Monte Carlo  | 1000 simulations over planning years     |

---

## 📤 Outputs (All Parquet)

| File                      | Description                                     |
| ------------------------- | ----------------------------------------------- |
| `results.parquet`         | Yearly breakdown of income, expenses, drawdowns |
| `tax_summary.parquet`     | Year-by-year tax estimate per person            |
| `cone_simulation.parquet` | All simulated paths for asset balances          |

---

## 🛠 Extensibility

* Add additional income types (rental, business)
* Support different expense categories
* Handle state pension eligibility
* Adjust portfolio rebalancing logic

---

## ✅ Next Steps

Let me know if you want:

* 🧱 Boilerplate code scaffold
* 📋 Dev task list (with modules and deadlines)
* 🧪 Unit test structure and coverage strategy
* 🧪 Jupyter notebook to prototype simulation logic

This spec is ready for build. Just say the word.
