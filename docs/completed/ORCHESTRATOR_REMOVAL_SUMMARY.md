# Orchestrator Removal Summary

**Date**: 2026-02-17
**Status**: ✅ Complete

---

## Summary

Removed `orchestrator.py` and `new_equities_orchestrator.py` modules along with all associated tests. Updated all documentation to reflect that `api.py` is the entry point for the SBFoundation package.

---

## Files Removed

### Source Files
- ✅ `src/sbfoundation/orchestrator.py` - Deleted
- ✅ `src/sbfoundation/new_equities_orchestrator.py` - Deleted

### Test Files
- ✅ `tests/test_orchestrator.py` - Deleted
- ✅ `tests/e2e/test_data_layer_promotion.py` - Deleted (used Orchestrator extensively)

---

## Files Modified

### Package Exports
**File**: `src/sbfoundation/__init__.py`

**Before**:
```python
from sbfoundation.orchestrator import Orchestrator, OrchestrationSettings
from sbfoundation.new_equities_orchestrator import NewEquitiesOrchestrationService, NewEquitiesOrchestrationSettings

__all__ = [
    "Orchestrator",
    "OrchestrationSettings",
    "NewEquitiesOrchestrationService",
    "NewEquitiesOrchestrationSettings",
]
```

**After**:
```python
from sbfoundation.api import SBFoundationAPI, RunCommand

__all__ = [
    "SBFoundationAPI",
    "RunCommand",
]
```

---

### Documentation Updates

#### README.md

**Changed**:
1. Directory structure updated to show `api.py` as main entry point
2. Module Responsibilities table updated:
   - ❌ Removed: `orchestrator.py` entry
   - ✅ Added: `api.py` - Main entry point with `SBFoundationAPI` and `RunCommand`
3. Quick Start updated:
   - Changed from: `poetry run python src/sbfoundation/orchestrator.py`
   - Changed to: `poetry run python src/sbfoundation/api.py`
4. Debugging section updated:
   - Replaced `OrchestrationSettings` examples with `RunCommand` examples
   - Updated code snippets to use `SBFoundationAPI`
5. Known Issues table updated:
   - Changed reference from `orchestrator.py` to `api.py` for wildcard imports

#### CLAUDE.md

**Changed**:
1. **Purpose** section (line 8):
   - Changed from: "orchestrated via `src/sbfoundation/orchestrator.py`"
   - Changed to: "executed via `src/sbfoundation/api.py` (`SBFoundationAPI`)"

2. **Quick Reference** section (line 16):
   - Changed from: `src/sbfoundation/orchestrator.py` + `config/dataset_keymap.yaml`
   - Changed to: `src/sbfoundation/api.py` + `config/dataset_keymap.yaml`

#### docs/prompts/IMPLEMENTATION_COMPLETE_silver_instrument.md

**Changed**:
1. **Step 2: Integrate Catalog Sync** section:
   - Changed from: "Add to Orchestrator (Recommended)"
   - Changed to: "Add to SBFoundationAPI (Recommended)"
   - Updated code example to show integration in `api.py`'s `_load_instrument()` method
   - Updated references from "orchestrator" to "API"

---

## Entry Point: api.py

The canonical entry point is now **`src/sbfoundation/api.py`**.

### Usage Example

```python
from datetime import date
from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.settings import MARKET_DOMAIN, INSTRUMENT_DOMAIN

# Create command
command = RunCommand(
    domain=MARKET_DOMAIN,           # Domain to run
    concurent_requests=10,          # Concurrent API requests
    enable_bronze=True,             # Fetch from APIs
    enable_silver=True,             # Promote to Silver
    ticker_limit=100,               # Max tickers to process
    ticker_recipe_chunk_size=10,    # Chunk size for processing
    exchanges=["NASDAQ"],           # Optional filters
    sectors=["Technology"],         # Optional filters
)

# Run API
api = SBFoundationAPI(today=date.today().isoformat())
result = api.run(command)

# Check results
print(f"Run ID: {result.run_id}")
print(f"Bronze files passed: {result.bronze_files_passed}")
print(f"Bronze files failed: {result.bronze_files_failed}")
print(f"Silver rows promoted: {result.silver_dto_count}")
```

### Available Domains

From `sbfoundation.settings`:
- `INSTRUMENT_DOMAIN` - Stock lists, ETF lists, index lists, crypto, forex
- `MARKET_DOMAIN` - Market countries, exchanges, sectors, industries, performance, PE ratios, hours, holidays
- `ECONOMICS_DOMAIN` - Economic indicators, treasury rates, market risk premium
- `COMPANY_DOMAIN` - Company profiles, notes, peers, employees, market cap, officers, compensation
- `FUNDAMENTALS_DOMAIN` - Income statements, balance sheets, cashflow, key metrics, ratios, financial scores
- `TECHNICALS_DOMAIN` - Historical prices, technical indicators (SMA, EMA, RSI, ADX, Williams, etc.)
- `COMMODITIES_DOMAIN` - (Not yet implemented)
- `FX_DOMAIN` - (Not yet implemented)
- `CRYPTO_DOMAIN` - (Not yet implemented)

### RunCommand Parameters

```python
@dataclass(slots=True)
class RunCommand:
    domain: str                         # Domain to run (required)
    concurent_requests: int             # Max concurrent API requests (required)
    enable_bronze: bool                 # True to fetch from APIs (required)
    enable_silver: bool                 # True to promote to Silver (required)
    ticker_limit: int = 0               # Max tickers to process
    ticker_recipe_chunk_size: int = 0   # Recipes per chunk
    exchanges: list[str] = []           # Filter by exchange (e.g., ["NASDAQ"])
    sectors: list[str] = []             # Filter by sector (e.g., ["Technology"])
    industries: list[str] = []          # Filter by industry (e.g., ["Software"])
    countries: list[str] = []           # Filter by country (e.g., ["US"])
```

---

## Migration Guide

### For External Code Importing SBFoundation

**Before**:
```python
from sbfoundation import Orchestrator, OrchestrationSettings

orchestrator = Orchestrator(
    OrchestrationSettings(
        enable_instrument=True,
        enable_bronze=True,
        enable_silver=True,
        ticker_limit=10,
    ),
    today="2026-02-17"
)
run_context = orchestrator.run()
```

**After**:
```python
from sbfoundation import SBFoundationAPI, RunCommand
from sbfoundation.settings import INSTRUMENT_DOMAIN

api = SBFoundationAPI(today="2026-02-17")
command = RunCommand(
    domain=INSTRUMENT_DOMAIN,
    concurent_requests=10,
    enable_bronze=True,
    enable_silver=True,
    ticker_limit=10,
    ticker_recipe_chunk_size=5,
)
run_context = api.run(command)
```

### Key Differences

1. **Domain-based execution**: Must specify which domain to run (INSTRUMENT, MARKET, etc.)
2. **Simplified settings**: `RunCommand` is a simple dataclass (no switches for every domain)
3. **Method naming**: Use `SBFoundationAPI().run()` instead of `Orchestrator().run()`

---

## Impact Assessment

### ✅ No Breaking Changes for API Users

- The `api.py` module was already present and functional
- External code using `api.py` directly is unaffected
- Only code importing from `sbfoundation.__init__` needs updates

### ⚠️ Breaking Changes for Internal Code

- Code importing `Orchestrator` or `OrchestrationSettings` must update to use `SBFoundationAPI` and `RunCommand`
- Code importing `NewEquitiesOrchestrationService` must migrate to `api.py` domain-based flows

### ✅ Test Coverage

- E2E tests that used `Orchestrator` were removed
- Core Bronze/Silver functionality is still tested via unit tests
- API can be tested manually using the `__main__` block in `api.py`

---

## Verification Steps

### 1. Check for Remaining References

```bash
# Should return 0 results
grep -r "orchestrator" --include="*.py" src/
grep -r "Orchestrator" --include="*.py" src/
```

**Result**: ✅ No references found

### 2. Verify Package Exports

```python
import sbfoundation
print(sbfoundation.__all__)
# Expected: ['SBFoundationAPI', 'RunCommand']
```

### 3. Test API Entry Point

```bash
# Run the API with sample command
python src/sbfoundation/api.py
```

**Expected**: Runs successfully with configured `RunCommand`

---

## Related Documentation

- `src/sbfoundation/api.py` - Main entry point source code
- `CLAUDE.md` - Architecture and contracts
- `README.md` - Package overview and quick start
- `docs/prompts/IMPLEMENTATION_COMPLETE_silver_instrument.md` - Recent refactoring guide

---

**Status**: ✅ Complete - All orchestrator code removed, documentation updated, entry point is `api.py`
