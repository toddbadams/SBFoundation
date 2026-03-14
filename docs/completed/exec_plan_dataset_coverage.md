# ExecPlan: Dataset Coverage Alignment

**Version**: 1.0
**Created**: 2026-02-18
**Status**: Draft - Pending Approval

---

## Purpose / Big Picture

Achieve 100% alignment between `config/dataset_keymap.yaml` (authoritative source) and domain prompt files (documentation). Currently there are 32 missing datasets in prompts and spelling inconsistencies between keymap and documentation.

This work will:
1. Add missing datasets to keymap (company-compensation, ratios-ttm)
2. Fix spelling errors in keymap (finanical → financial, segementation → segmentation)
3. Add 12 missing economic indicators to economics.md
4. Resolve discriminator documentation discrepancies
5. Ensure prompt files accurately reflect all available datasets

**User-visible outcome**: Complete, accurate documentation of all 111+ datasets with consistent naming across keymap and prompts.

---

## Progress

- [x] Initial coverage analysis - 2026-02-18
- [x] Document findings in dataset_coverage.md - 2026-02-18
- [ ] Add company-compensation to keymap
- [ ] Add ratios-ttm to keymap
- [ ] Fix spelling errors in keymap
- [ ] Add missing economic indicators to economics.md
- [x] Resolve fundamentals base entry decision - APPROVED: Document all base entries
- [x] Resolve technicals discriminator decision - APPROVED: Add explicit notation
- [ ] Add base entry variants to fundamentals.md
- [ ] Add discriminator notation to technicals.md
- [ ] Re-run coverage analysis for verification
- [ ] Update main ExecPlan with findings

---

## Surprises & Discoveries

### 2026-02-18: Coverage Gap Analysis
- Started with assumption that prompt files had errors (extra datasets)
- Discovery: Actually keymap is missing 2 datasets that exist in prompts (company-compensation, ratios-ttm)
- These are valid FMP API endpoints that should be added to keymap

### 2026-02-18: Keymap Spelling Errors
- Found 3 systematic spelling errors in keymap dataset names:
  - `finanical` (missing 'n') appears 3 times
  - `segementation` (missing 'n') appears 2 times
- Prompt files use correct spelling, which appeared as mismatches
- Decision: Fix keymap (authoritative) rather than propagate errors to prompts

### 2026-02-18: Discriminator Inconsistencies
- Keymap has base entries (empty discriminator) for fundamentals datasets
- Purpose unclear - may be legacy entries or used for non-period-specific queries
- Technicals have discriminators in keymap (period numbers) but dataset names already include period
- Need decision on whether discriminators add value in documentation

### 2026-02-18: Economic Indicators Undercount
- Economics.md has 15 indicators
- Keymap has 26 total economic-indicators entries (24 unique discriminators + 2 other economics datasets)
- Missing 12 indicators in documentation (housing, monetary, industrial production, etc.)

---

## Decision Log

### Decision 1: Add Missing Datasets to Keymap (2026-02-18)
**Rationale**: company-compensation and ratios-ttm are valid FMP endpoints documented in prompts but missing from keymap
**Source**:
- company-compensation: https://site.financialmodelingprep.com/developer/docs#executive-compensation
- ratios-ttm: https://site.financialmodelingprep.com/developer/docs#financial-ratios-ttm
**Action**: Add both to keymap with proper configuration (domain, source, recipes, DTO schema)
**Alternative considered**: Remove from prompts
**Why rejected**: These are valid, useful datasets; keymap should be expanded, not documentation reduced

### Decision 2: Fix Keymap Spelling (2026-02-18)
**Rationale**: Keymap is authoritative source; spelling errors should be corrected there
**Impact**: Will require updates to:
- DTO class names (if they match dataset names)
- Table names in DuckDB silver schema
- Any code referencing these dataset names
**Approach**: Search-and-replace with verification in:
1. config/dataset_keymap.yaml
2. src/sbfoundation/dtos/ (DTO files)
3. Database migrations if tables exist
4. settings.py constants

### Decision 3: Complete Economic Indicators Coverage (2026-02-18)
**Rationale**: Full transparency - users should know all available indicators
**Action**: Add all 12 missing indicators to economics.md
**Format**: Follow existing pattern with endpoint, description, discriminator notation

### Decision 4: Document Base Entries - APPROVED (2026-02-18)
**Decision**: Option A - Document base entries as separate items
**Rationale**: User confirmed empty discriminator entries should be documented for completeness
**Action**: Add base entry variants (discriminator: '') to fundamentals.md for all applicable datasets
**Impact**: Will achieve 100% coverage (113/113)

### Decision 5: Technicals Discriminators - APPROVED (2026-02-18)
**Decision**: Option A - Add explicit discriminator notation
**Rationale**: User confirmed explicit notation should be added to match keymap exactly
**Action**: Update all technical indicators in technicals.md to include (discriminator: X) notation
**Example**: `dataset: technicals-sma-20 (discriminator: 20)`
**Impact**: Exact alignment with keymap format

---

## Outcomes & Retrospective

_To be completed after implementation_

---

## Context and Orientation

### Current State
- **Keymap**: 111 dataset entries across 9 domains
- **Prompts**: 94 documented datasets
- **Gap**: 32 missing entries (some are discriminator variants)
- **Errors**: 2 datasets in prompts not in keymap, 3 spelling inconsistencies

### Key Files
- `config/dataset_keymap.yaml` — authoritative dataset definitions (111 entries)
- `docs/prompts/dataset_coverage.md` — analysis document with findings
- `docs/prompts/economics.md` — missing 12 indicators
- `docs/prompts/fundamentals.md` — base entry decision needed
- `docs/prompts/technicals.md` — discriminator notation decision needed

### Datasets to Add to Keymap
1. **company-compensation**
   - Domain: company
   - Endpoint: `governance/executive_compensation`
   - Description: Executive compensation data (salary, bonuses, stock awards)
   - Documented in: company.md

2. **ratios-ttm**
   - Domain: fundamentals
   - Endpoint: `financial-ratios-ttm`
   - Description: Trailing twelve month financial ratios
   - Documented in: fundamentals.md

### Spelling Corrections Needed
- `finanical-statement-growth` → `financial-statement-growth` (3 occurrences)
- `revenue-product-segementation` → `revenue-product-segmentation` (1 occurrence)
- `revenue-geographic-segementation` → `revenue-geographic-segmentation` (1 occurrence)

### Missing Economic Indicators
12 indicators from keymap not in economics.md:
1. 15YearFixedRateMortgageAverage
2. 30YearFixedRateMortgageAverage
3. 3MonthOr90DayRatesAndYieldsCertificatesOfDeposit
4. commercialBankInterestRateOnCreditCardPlansAllAccounts
5. durableGoods
6. industrialProductionTotalIndex
7. initialClaims
8. newPrivatelyOwnedHousingUnitsStartedTotalUnits
9. retailMoneyFunds
10. smoothedUSRecessionProbabilities
11. totalVehicleSales
12. tradeBalanceGoodsAndServices

---

## Plan of Work

### Phase 1: Keymap Additions & Corrections

#### Step 1.1: Add company-compensation to keymap
**File**: `config/dataset_keymap.yaml`
**Location**: After `company-officers` entry (around line 850)
**Action**: Add new entry following existing company domain pattern:
```yaml
- domain: company
  source: fmp
  dataset: company-compensation
  discriminator: ''
  ticker_scope: per_ticker
  silver_schema: silver
  silver_table: fmp_company_compensation
  key_cols:
    - ticker
    - year
  row_date_col: year
  instrument_behavior: enrich
  recipes:
    - plans:
        - basic
      data_source_path: governance/executive_compensation
      query_vars:
        symbol: __ticker__
      date_key: year
      cadence_mode: interval
      min_age_days: 365
      run_days:
        - sat
      help_url: https://site.financialmodelingprep.com/developer/docs#executive-compensation
  dto_schema:
    dto_type: sbfoundation.dtos.company.company_compensation_dto.CompanyCompensationDTO
    columns:
      - name: ticker
        type: str
        nullable: false
      - name: year
        type: int
        nullable: false
      - name: name
        type: str
        nullable: true
      - name: title
        type: str
        nullable: true
      - name: salary
        type: float
        nullable: true
      - name: bonus
        type: float
        nullable: true
      - name: stock_award
        type: float
        nullable: true
      - name: total_compensation
        type: float
        nullable: true
```

#### Step 1.2: Add ratios-ttm to keymap
**File**: `config/dataset_keymap.yaml`
**Location**: After `key-metrics-ttm` entry (around line 4124)
**Action**: Add new entry following existing fundamentals domain pattern:
```yaml
- domain: fundamentals
  source: fmp
  dataset: ratios-ttm
  discriminator: ''
  ticker_scope: per_ticker
  silver_schema: silver
  silver_table: fmp_ratios_ttm
  key_cols:
    - ticker
  row_date_col: null
  recipes:
    - plans:
        - basic
      data_source_path: financial-ratios-ttm
      query_vars:
        symbol: __ticker__
      date_key: null
      cadence_mode: interval
      min_age_days: 1
      run_days:
        - mon
        - tues
        - wed
        - thurs
        - fri
      help_url: https://site.financialmodelingprep.com/developer/docs#financial-ratios-ttm
  dto_schema:
    dto_type: sbfoundation.dtos.fundamentals.ratios_ttm_dto.RatiosTTMDTO
    columns:
      - name: ticker
        type: str
        nullable: false
      - name: current_ratio
        type: float
        nullable: true
      - name: quick_ratio
        type: float
        nullable: true
      - name: debt_equity_ratio
        type: float
        nullable: true
      - name: return_on_equity
        type: float
        nullable: true
      - name: return_on_assets
        type: float
        nullable: true
```

#### Step 1.3: Fix spelling errors in keymap
**File**: `config/dataset_keymap.yaml`
**Action**: Search and replace across entire file:
1. `finanical-statement-growth` → `financial-statement-growth`
2. `revenue-product-segementation` → `revenue-product-segmentation`
3. `revenue-geographic-segementation` → `revenue-geographic-segmentation`

**Verification**:
```bash
grep -n "finanical\|segementation" config/dataset_keymap.yaml
# Should return no results after fixes
```

### Phase 2: Prompt File Updates

#### Step 2.1: Add missing economic indicators to economics.md
**File**: `docs/prompts/economics.md`
**Location**: After existing indicators (after line 161)
**Action**: Add 12 missing indicators following existing pattern:

```markdown
16. Economic Indicators - Durable Goods API
Access U.S. Durable Goods Orders data for manufacturing and business investment tracking.

Endpoint: https://financialmodelingprep.com/stable/economic-indicator/durableGoods?from=__from__&to=__to__
Documentation: https://site.financialmodelingprep.com/developer/docs#economic-indicators
dataset: economic-indicators (discriminator: durableGoods)
min_age_days: 30 days
run_days: mon, tues, wed, thurs, fri, sat
plans: basic, starter, premium, ultimate

17. Economic Indicators - Industrial Production Total Index API
Access U.S. Industrial Production Total Index data for manufacturing output tracking.

Endpoint: https://financialmodelingprep.com/stable/economic-indicator/industrialProductionTotalIndex?from=__from__&to=__to__
Documentation: https://site.financialmodelingprep.com/developer/docs#economic-indicators
dataset: economic-indicators (discriminator: industrialProductionTotalIndex)
min_age_days: 30 days
run_days: mon, tues, wed, thurs, fri, sat
plans: basic, starter, premium, ultimate

... (continue for all 12 indicators)
```

#### Step 2.2: Update fundamentals.md discriminator spelling
**File**: `docs/prompts/fundamentals.md`
**Action**: Update dataset names to match corrected keymap spelling:
- `financial-statement-growth` (no change needed - already correct)
- `revenue-product-segmentation` (no change needed - already correct)
- `revenue-geographic-segmentation` (no change needed - already correct)

**Note**: Prompt files already use correct spelling; no changes needed.

### Phase 3: Verification & Validation

#### Step 3.1: Re-run coverage analysis
**Command**:
```bash
cd C:/sb/SBFoundation && python3 << 'EOF'
import re
from pathlib import Path

# Parse keymap
keymap_datasets = []
with open('config/dataset_keymap.yaml', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        match = re.match(r'^  dataset: (.+)$', line)
        if match:
            dataset = match.group(1).strip()
            disc = ""
            if i + 1 < len(lines):
                disc_match = re.match(r"^  discriminator: '(.+)'$", lines[i+1])
                if disc_match:
                    disc = disc_match.group(1)
            keymap_datasets.append((dataset, disc))

# Parse prompt files
prompt_datasets = []
for md_file in Path('docs/prompts').glob('*.md'):
    if md_file.stem not in ['instrument', 'company', 'fundamentals', 'technicals', 'economics', 'crypto', 'fx', 'commodities', 'markets']:
        continue

    with open(md_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            match = re.match(r'^dataset: ([^\(]+)(?:\s*\(discriminator: ([^\)]+)\))?', line)
            if match:
                dataset = match.group(1).strip()
                disc = match.group(2).strip() if match.group(2) else ""
                prompt_datasets.append((dataset, disc))

keymap_set = set(keymap_datasets)
prompt_set = set(prompt_datasets)

missing = keymap_set - prompt_set
extra = prompt_set - keymap_set

print(f"Keymap entries: {len(keymap_datasets)}")
print(f"Prompt entries: {len(prompt_datasets)}")
print(f"Missing from prompts: {len(missing)}")
print(f"Extra in prompts: {len(extra)}")
print(f"\nCoverage: {100 - (len(missing) / len(keymap_datasets) * 100):.1f}%")

if len(missing) == 0 and len(extra) == 0:
    print("\n✅ PERFECT ALIGNMENT ACHIEVED!")
else:
    print(f"\n⚠️  Still {len(missing)} missing and {len(extra)} extra")
EOF
```

**Expected output after all fixes**:
```
Keymap entries: 113 (was 111, added 2)
Prompt entries: 106 (was 94, added 12)
Missing from prompts: 7 (base entries - decision pending)
Extra in prompts: 0
Coverage: 93.8%
```

#### Step 3.2: Verify spelling corrections
**Command**:
```bash
# Check for old typos
grep -n "finanical\|segementation" config/dataset_keymap.yaml

# Should return: (no output)

# Check for corrected spellings
grep -n "financial-statement-growth\|revenue.*segmentation" config/dataset_keymap.yaml

# Should return: 3 matches for financial-statement-growth, 2 for segmentation
```

#### Step 3.3: Update dataset_coverage.md status
**File**: `docs/prompts/dataset_coverage.md`
**Action**: Update status from "In Progress" to "Completed" and add results summary

---

## Validation and Acceptance

### Acceptance Criteria
1. ⬜ company-compensation added to keymap with complete configuration
2. ⬜ ratios-ttm added to keymap with complete configuration
3. ⬜ All spelling errors corrected in keymap (0 matches for "finanical" or "segementation")
4. ⬜ 12 economic indicators added to economics.md
5. ⬜ Coverage analysis shows ≥90% alignment (113 keymap / 106+ prompts)
6. ⬜ Zero "extra in prompts" (all prompt datasets exist in keymap)
7. ⬜ Decision made on base entry documentation
8. ⬜ Decision made on technicals discriminators

### Test Cases

**Test 1: Keymap Additions**
```bash
# Verify company-compensation exists
grep -A 30 "dataset: company-compensation" config/dataset_keymap.yaml
# Should show full entry with domain, recipes, dto_schema

# Verify ratios-ttm exists
grep -A 25 "dataset: ratios-ttm" config/dataset_keymap.yaml
# Should show full entry with domain, recipes, dto_schema
```

**Test 2: Spelling Corrections**
```bash
# No typos remain
grep -c "finanical\|segementation" config/dataset_keymap.yaml
# Should return: 0

# Correct spellings present
grep -c "financial-statement-growth" config/dataset_keymap.yaml
# Should return: 3

grep -c "revenue.*segmentation" config/dataset_keymap.yaml
# Should return: 2
```

**Test 3: Economic Indicators Complete**
```bash
# Count economic-indicators in economics.md
grep -c "dataset: economic-indicators" docs/prompts/economics.md
# Should return: 24 (was 12, added 12)
```

**Test 4: Coverage Percentage**
```bash
# Run verification script
python3 verify_coverage.py
# Should show: Coverage: ≥90%
# Missing should be ≤10 (base entries only)
```

---

## Idempotence and Recovery

### Safe Retry
- All keymap edits are additive (adding entries) or corrections (spelling)
- Prompt file updates are additive (adding indicators)
- No deletions or destructive changes
- Can rerun coverage analysis script unlimited times

### Rollback
```bash
# If keymap additions are incorrect
git checkout HEAD -- config/dataset_keymap.yaml

# If prompt updates are incorrect
git checkout HEAD -- docs/prompts/economics.md

# Verify clean state
git status
```

### Verification Before Commit
```bash
# 1. Syntax check YAML
python3 -c "import yaml; yaml.safe_load(open('config/dataset_keymap.yaml'))"

# 2. Verify no duplicates
grep "^  dataset:" config/dataset_keymap.yaml | sort | uniq -c | grep -v " 1 "

# 3. Run coverage analysis
python3 verify_coverage.py
```

---

## Artifacts and Notes

### Files Modified
1. ✅ `docs/prompts/dataset_coverage.md` — Updated analysis with action plan
2. ⬜ `config/dataset_keymap.yaml` — Add 2 datasets, fix 3 spellings
3. ⬜ `docs/prompts/economics.md` — Add 12 indicators

### New Entries Added
- company-compensation (company domain)
- ratios-ttm (fundamentals domain)

### Spelling Corrections
- finanical → financial (3 occurrences)
- segementation → segmentation (2 occurrences)

### Coverage Progression
- **Before**: 94/111 documented (84.7%)
- **After Phase 1**: 94/113 documented (83.2%) - added 2 to keymap
- **After Phase 2**: 106/113 documented (93.8%) - added 12 to prompts
- **Target**: 106-113/113 documented (93.8-100%) - pending base entry decision

---

## Interfaces and Dependencies

### Required Tools
- Edit tool (keymap and prompt file updates)
- Bash tool (verification scripts)
- Python (coverage analysis script)

### Input Dependencies
- `config/dataset_keymap.yaml` — authoritative source
- `docs/prompts/*.md` — domain documentation files
- FMP API documentation — for endpoint verification

### Output Artifacts
- Updated keymap with 2 new datasets
- Corrected spelling in keymap (3 fixes)
- Updated economics.md with 12 indicators
- Coverage analysis showing ≥90% alignment

### External Dependencies
- None - all changes are local configuration and documentation

---

## Decisions Resolved (2026-02-18)

### ✅ Base Entries in Fundamentals - APPROVED
**Decision**: Document all base entries (empty discriminator) for completeness
**Action Required**: Add base entry variants to fundamentals.md:
- balance-sheet-statement (discriminator: '')
- balance-sheet-statement-growth (discriminator: '')
- cashflow-statement (discriminator: '')
- cashflow-statement-growth (discriminator: '')
- income-statement (discriminator: '')
- income-statement-growth (discriminator: '')
- key-metrics (discriminator: '')
- metric-ratios (discriminator: '')

**Expected Impact**: Achieves 100% coverage (113/113)

### ✅ Technicals Discriminator Notation - APPROVED
**Decision**: Add explicit discriminator notation to all technical indicators
**Action Required**: Update technicals.md with notation for all 23 indicators
**Format**: `dataset: technicals-sma-20 (discriminator: 20)`

**Expected Impact**: Exact alignment with keymap format

---

## Next Steps After Approval

1. Make keymap edits (add datasets, fix spelling)
2. Add economic indicators to economics.md
3. Run coverage verification
4. Get decisions on pending questions
5. Implement decisions (if needed)
6. Final verification and documentation update
7. Update main ExecPlan with completion status

---

**END OF EXEC PLAN**
