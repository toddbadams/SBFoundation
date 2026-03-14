# Dataset Coverage Analysis Summary

**Status**: In Progress
**Created**: 2026-02-18
**Last Updated**: 2026-02-18

## Summary

**Total Datasets:**
- In keymap: 111 entries
- In prompt files: 94 entries
- Missing from prompts: 32 entries
- Extra in prompts (errors): 15 entries

---

## ⚠️ Critical Issues Found

### 1. Datasets in Prompt Files But NOT in Keymap

These 2 datasets are documented in prompt files but missing from the keymap configuration:

- ❌ **company-compensation** (in company.md) — Need to add to keymap
- ❌ **ratios-ttm** (in fundamentals.md) — Need to add to keymap

**Action Required**: Add these datasets to config/dataset_keymap.yaml with proper configuration

### 2. Typos in Keymap (Spelling Issues)

The keymap contains these spelling errors that need correction:

- `finanical-statement-growth` → should be `financial-statement-growth`
- `revenue-product-segementation` → should be `revenue-product-segmentation`
- `revenue-geographic-segementation` → should be `revenue-geographic-segmentation`

**Note**: Prompt files use the CORRECT spelling, which is why they show as "extra" in comparison.

**Action Required**: Update dataset names in config/dataset_keymap.yaml to fix spelling

### 3. Missing Economic Indicators

Missing 12 economic indicators from economics.md that exist in keymap:

- economic-indicators (discriminator: 15YearFixedRateMortgageAverage)
- economic-indicators (discriminator: 30YearFixedRateMortgageAverage)
- economic-indicators (discriminator: 3MonthOr90DayRatesAndYieldsCertificatesOfDeposit)
- economic-indicators (discriminator: commercialBankInterestRateOnCreditCardPlansAllAccounts)
- economic-indicators (discriminator: durableGoods)
- economic-indicators (discriminator: industrialProductionTotalIndex)
- economic-indicators (discriminator: initialClaims)
- economic-indicators (discriminator: newPrivatelyOwnedHousingUnitsStartedTotalUnits)
- economic-indicators (discriminator: retailMoneyFunds)
- economic-indicators (discriminator: smoothedUSRecessionProbabilities)
- economic-indicators (discriminator: totalVehicleSales)
- economic-indicators (discriminator: tradeBalanceGoodsAndServices)

**Action Required**: Add these economic indicators to docs/prompts/economics.md

### 4. Fundamentals Datasets Missing Base Entries

The keymap has base entries (discriminator: '') for these datasets, but prompts only documented the FY/quarter variants:

- balance-sheet-statement (has '', FY, quarter in keymap; prompts only have FY and quarter)
- balance-sheet-statement-growth (has '', FY, quarter in keymap; prompts only have FY and quarter)
- cashflow-statement (has '', FY, quarter in keymap; prompts only have FY and quarter)
- cashflow-statement-growth (has '', FY, quarter in keymap; prompts only have FY and quarter)
- income-statement (has '', FY, quarter in keymap; prompts only have FY and quarter)
- income-statement-growth (has '', FY, quarter in keymap; prompts only have FY and quarter)
- key-metrics (has '', FY in keymap; prompts only have FY and quarter)
- metric-ratios (has '', FY in keymap; prompts only have FY and quarter)

**Decision Needed**: Should base entries (empty discriminator) be documented in prompts? They exist in keymap but may be legacy/unused entries.

**Action Required**: If base entries are used, add them to docs/prompts/fundamentals.md with discriminator notation

### 5. Technicals Missing Discriminators

All 23 technical indicators exist in prompts BUT are missing their period discriminators.

**In keymap**: `technicals-sma-20 (discriminator: 20)`
**In prompts**: `technicals-sma-20` (no discriminator notation)

Affected datasets:
- technicals-adx-14 (discriminator: 14)
- technicals-dema-12, 26, 50, 200 (discriminators: 12, 26, 50, 200)
- technicals-ema-12, 26, 50, 200 (discriminators: 12, 26, 50, 200)
- technicals-rsi-7, 14 (discriminators: 7, 14)
- technicals-sma-20, 50, 200 (discriminators: 20, 50, 200)
- technicals-standard-deviation-20 (discriminator: 20)
- technicals-tema-20 (discriminator: 20)
- technicals-williams-14 (discriminator: 14)
- technicals-wma-20, 50, 200 (discriminators: 20, 50, 200)

**Decision Needed**: Should discriminators be explicitly shown in prompts? The period is already in the dataset name (e.g., "sma-20").

**Action Required**: If discriminators should match exactly, add notation to docs/prompts/technicals.md

---

## 📝 Action Plan Summary

### Phase 1: Keymap Updates (config/dataset_keymap.yaml)
1. **Add missing datasets**:
   - company-compensation
   - ratios-ttm

2. **Fix spelling errors**:
   - finanical-statement-growth → financial-statement-growth
   - revenue-product-segementation → revenue-product-segmentation
   - revenue-geographic-segementation → revenue-geographic-segmentation

### Phase 2: Prompt File Updates
1. **economics.md**: Add 12 missing economic indicators
2. **fundamentals.md**: Decision needed on base entries (empty discriminator)
3. **technicals.md**: Decision needed on explicit discriminator notation

### Phase 3: Verification
1. Re-run coverage analysis to ensure 100% alignment
2. Verify all dataset names match between keymap and prompts
3. Update exec_plan_domain_documentation.md with findings

---

## 🔍 Questions for Resolution

1. **Base entries**: Should fundamentals datasets with empty discriminator be documented?
2. **Technicals discriminators**: Should explicit discriminator notation be added when period is in name?
3. **Priority**: Which phase should be completed first?