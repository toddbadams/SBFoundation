# Bronze to Silver DTO (multi-endpoint ingestion prompt)

## Role
You are a code generator for the Strawberry project.

You MUST strictly follow:
- `docs/AI_context/bronze_to_silver_dto_contract.md`
- the provided `BronzeToSilverDTO` base class
- the ingestion behavior implied by `RunProvider`

Do NOT invent lifecycle, ingestion, or persistence logic.

---

## Inputs 
1. Bronze -> Silver DTO contract (`docs/AI_context/bronze_to_silver_dto_contract.md`)
1. Example Silver DTO contract (`src/company/dtos/company_dto.py`)
1. Base DTO class (`src/shared/domain/bronze_to_silver_dto.py`)
1. DatasetRecipe / recipe set (`src/orchestration/dataset_recipes.py`)
1. DatasetRecipe class (`src/shared/run/domain/dataset_recipe.py`)
1. A shared domain name for all endpoints: `econmonics`
1. A list of API documentation URLs (each URL is a single endpoint)
   - https://site.financialmodelingprep.com/developer/docs#treasury-rates
	{
		"date": "2024-02-29",
		"month1": 5.53,
		"month2": 5.5,
		"month3": 5.45,
		"month6": 5.3,
		"year1": 5.01,
		"year2": 4.64,
		"year3": 4.43,
		"year5": 4.26,
		"year7": 4.28,
		"year10": 4.25,
		"year20": 4.51,
		"year30": 4.38
	}
	- https://site.financialmodelingprep.com/developer/docs#market-risk-premium
		{
		"country": "Zimbabwe",
		"continent": "Africa",
		"countryRiskPremium": 13.17,
		"totalEquityRiskPremium": 17.77
	}
	- https://site.financialmodelingprep.com/developer/docs#economics-indicators
	{
		"name": "GDP",
		"date": "2024-01-01",
		"value": 28624.069
	}
	create a run recipe for each indicator: GDP,realGDP,nominalPotentialGDP,realGDPPerCapita,federalFunds,CPI,inflationRate,inflation,retailSales,consumerSentiment,durableGoods,unemploymentRate,totalNonfarmPayroll,initialClaims,industrialProductionTotalIndex,newPrivatelyOwnedHousingUnitsStartedTotalUnits,totalVehicleSales,retailMoneyFunds,smoothedUSRecessionProbabilities,3MonthOr90DayRatesAndYieldsCertificatesOfDeposit,commercialBankInterestRateOnCreditCardPlansAllAccounts,30YearFixedRateMortgageAverage,15YearFixedRateMortgageAverage,tradeBalanceGoodsAndServices

---

## Required workflow
For each URL in the input list:

1) Define the ingestion recipe
   - Create a `DatasetRecipe` in `src/orchestration/dataset_recipes.py` for the endpoint.
   - Use the URL as `help_url`.
   - Set `domain`, `source`, `dataset`, `data_source_path`, `query_vars`, `date_key`, `cadence_mode`, `min_age_days`, and `is_ticker_based` based on the docs.
   - Use placeholders (`TICKER_PLACEHOLDER`, `FROM_DATE_PLACEHOLDER`, `TO_DATE_PLACEHOLDER`) where appropriate.


2) Create the Bronze -> Silver DTO
   - Add a new `BronzeToSilverDTO` child class in `src/<domain>/dtos`.
   - Include field metadata with the API property name (use `field(..., metadata={"api": "<api_key>"})`).
   - Implement `from_row` using `build_from_row`.
   - Implement `to_dict` using `build_to_dict`.
   - Add an `API docs: <URL>` comment at the top of the class docstring.

3) Classify as dim or fact and update gold docs
   - Decide whether the endpoint is a dimension (static descriptors) or a fact (time-variant metrics).
   - Update `docs/AI_context/gold_layer_data_warehouse.md` to list the new dim or fact with its grain and key fields, following the existing format.

4) Create the dim or fact object
   - If a dimension, create a dim object in `src/<domain>/dims`.
   - If a fact, create a fact object in `src/<domain>/facts`.
   - Follow the existing patterns in `src/company/dims` and `src/company/facts`.

5) Update the dim and fact tasks
	- update `src/orchestration/dims.py` with all of the dims from `src/<domain>/dims`
	- update `src/orchestration/facts.py` with all of the facts from `src/<domain>/facts`

---

## Additional repository updates (when needed)
- If a new dataset is introduced, add the dataset constant and update `DTO_TYPES` in `src/shared/domain/settings.py`.
- If a new domain is introduced, add it to `DOMAINS` and any related settings/constants.

---

## Hard constraints (DO NOT VIOLATE)
- One endpoint -> one DTO
- DTOs are pure row mappers
- Factory signature: `from_row(row, ticker)`
- Include `ticker` and `KEY_COLS = ["ticker"]`
- DTO attributes and output keys are snake_case
- Vendor dates remain ISO 8601 strings
- Use base defaults (`""`, `False`, `None`)
- `key_date` derived from vendor date or `date.min`

---

## Required output
- Updated `src/orchestration/dataset_recipes.py` with one DatasetRecipe per URL
- One DTO file per endpoint in `src/<domain>/dtos`
- Updated `docs/AI_context/gold_layer_data_warehouse.md` with the new dim/fact entries
- One dim or fact object per endpoint in `src/<domain>/dims` or `src/<domain>/facts`

