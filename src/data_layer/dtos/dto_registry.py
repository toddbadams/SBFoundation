from __future__ import annotations

from typing import Iterable

from data_layer.dtos.company.company_delisted_dto import CompanyDelistedDTO
from data_layer.dtos.company.company_dto import CompanyDTO
from data_layer.dtos.company.company_employees_dto import CompanyEmployeesDTO
from data_layer.dtos.company.company_market_cap_dto import CompanyMarketCapDTO
from data_layer.dtos.company.company_officers_dto import CompanyOfficerDTO
from data_layer.dtos.company.company_peers_dto import CompanyPeersDTO
from data_layer.dtos.company.company_shares_float_dto import CompanySharesFloatDTO

from data_layer.dtos.economics.economics_dto import EconomicsDTO
from data_layer.dtos.economics.market_risk_premium_dto import MarketRiskPremiumDTO
from data_layer.dtos.economics.treasury_rates_dto import TreasuryRatesDTO

from data_layer.dtos.fundamentals.balance_sheet_statement_dto import BalanceSheetStatementDTO
from data_layer.dtos.fundamentals.balance_sheet_statement_growth_dto import BalanceSheetStatementGrowthDTO
from data_layer.dtos.fundamentals.cashflow_statement_dto import CashflowStatementDTO
from data_layer.dtos.fundamentals.cashflow_statement_growth_dto import CashflowStatementGrowthDTO
from data_layer.dtos.fundamentals.enterprise_values_dto import EnterpriseValuesDTO
from data_layer.dtos.fundamentals.financial_scores_dto import FinancialScoresDTO
from data_layer.dtos.fundamentals.financial_statement_growth_dto import FinancialStatementGrowthDTO
from data_layer.dtos.fundamentals.income_statement_dto import IncomeStatementDTO
from data_layer.dtos.fundamentals.income_statement_growth_dto import IncomeStatementGrowthDTO
from data_layer.dtos.fundamentals.key_metrics_dto import KeyMetricsDTO
from data_layer.dtos.fundamentals.key_metrics_ttm_dto import KeyMetricsTtmDTO
from data_layer.dtos.fundamentals.metrics_ratios_dto import MetricsRatiosDTO
from data_layer.dtos.fundamentals.owner_earnings_dto import OwnerEarningsDTO
from data_layer.dtos.fundamentals.revenue_segmentation_dto import RevenueSegmentationDTO

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO

from data_layer.dtos.technicals.average_directional_index_dto import AverageDirectionalIndexDTO
from data_layer.dtos.technicals.double_exponential_moving_average_dto import DoubleExponentialMovingAverageDTO
from data_layer.dtos.technicals.exponential_moving_average_dto import ExponentialMovingAverageDTO
from data_layer.dtos.technicals.historical_price_eod_dividend_adjusted_dto import HistoricalPriceEodDividendAdjustedDTO
from data_layer.dtos.technicals.historical_price_eod_full_dto import HistoricalPriceEodFullDTO
from data_layer.dtos.technicals.historical_price_eod_non_split_adjusted_dto import HistoricalPriceEodNonSplitAdjustedDTO
from data_layer.dtos.technicals.relative_strength_index_dto import RelativeStrengthIndexDTO
from data_layer.dtos.technicals.simple_moving_average_dto import SimpleMovingAverageDTO
from data_layer.dtos.technicals.standard_deviation_dto import StandardDeviationDTO
from data_layer.dtos.technicals.triple_exponential_moving_average_dto import TripleExponentialMovingAverageDTO
from data_layer.dtos.technicals.weighted_moving_average_dto import WeightedMovingAverageDTO
from data_layer.dtos.technicals.williams_dto import WilliamsDTO

from data_layer.dtos.instrument.stock_list_dto import StockListDTO
from data_layer.dtos.instrument.etf_list_dto import ETFListDTO
from data_layer.dtos.instrument.index_list_dto import IndexListDTO
from data_layer.dtos.instrument.cryptocurrency_list_dto import CryptocurrencyListDTO
from data_layer.dtos.instrument.forex_list_dto import ForexListDTO
from data_layer.dtos.instrument.etf_holdings_dto import ETFHoldingsDTO


class DTORegistry:
    def __init__(self, mapping: dict[str, type[BronzeToSilverDTO]]) -> None:
        self._mapping = dict(mapping)

    def get(self, dataset: str, default: type[BronzeToSilverDTO] | None = None) -> type[BronzeToSilverDTO] | None:
        return self._mapping.get(dataset, default)

    def require(self, dataset: str) -> type[BronzeToSilverDTO]:
        try:
            return self._mapping[dataset]
        except KeyError as exc:
            raise KeyError(f"Missing DTO mapping for dataset={dataset}") from exc

    def keys(self) -> Iterable[str]:
        return self._mapping.keys()

    def items(self) -> Iterable[tuple[str, type[BronzeToSilverDTO]]]:
        return self._mapping.items()

    def values(self) -> Iterable[type[BronzeToSilverDTO]]:
        return self._mapping.values()

    def as_dict(self) -> dict[str, type[BronzeToSilverDTO]]:
        return dict(self._mapping)

    def __contains__(self, dataset: object) -> bool:
        return dataset in self._mapping

    def __getitem__(self, dataset: str) -> type[BronzeToSilverDTO]:
        return self._mapping[dataset]

    def __iter__(self) -> Iterable[str]:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)


DTO_REGISTRY = DTORegistry(
    {
        "economic-indicators": EconomicsDTO,
        "treasury-rates": TreasuryRatesDTO,
        "market-risk-premium": MarketRiskPremiumDTO,
        "company-profile": CompanyDTO,
        "company-notes": CompanyDTO,
        "company-peers": CompanyPeersDTO,
        "company-employees": CompanyEmployeesDTO,
        "company-market-cap": CompanyMarketCapDTO,
        "company-shares-float": CompanySharesFloatDTO,
        "company-officers": CompanyOfficerDTO,
        "company-delisted": CompanyDelistedDTO,
        "income-statement": IncomeStatementDTO,
        "balance-sheet-statement": BalanceSheetStatementDTO,
        "cashflow-statement": CashflowStatementDTO,
        "key-metrics": KeyMetricsDTO,
        "metric-ratios": MetricsRatiosDTO,
        "key-metrics-ttm": KeyMetricsTtmDTO,
        "financial-scores": FinancialScoresDTO,
        "owner-earnings": OwnerEarningsDTO,
        "enterprise-values": EnterpriseValuesDTO,
        "income-statement-growth": IncomeStatementGrowthDTO,
        "balance-sheet-statement-growth": BalanceSheetStatementGrowthDTO,
        "cashflow-statement-growth": CashflowStatementGrowthDTO,
        "finanical-statement-growth": FinancialStatementGrowthDTO,
        "revenue-product-segementation": RevenueSegmentationDTO,
        "revenue-geographic-segementation": RevenueSegmentationDTO,
        "technicals-historical-price-eod-full": HistoricalPriceEodFullDTO,
        "technicals-historical-price-eod-non-split-adjusted": HistoricalPriceEodNonSplitAdjustedDTO,
        "technicals-historical-price-eod-dividend-adjusted": HistoricalPriceEodDividendAdjustedDTO,
        "technicals-sma-20": SimpleMovingAverageDTO,
        "technicals-sma-50": SimpleMovingAverageDTO,
        "technicals-sma-200": SimpleMovingAverageDTO,
        "technicals-ema-12": ExponentialMovingAverageDTO,
        "technicals-ema-26": ExponentialMovingAverageDTO,
        "technicals-ema-50": ExponentialMovingAverageDTO,
        "technicals-ema-200": ExponentialMovingAverageDTO,
        "technicals-wma-20": WeightedMovingAverageDTO,
        "technicals-wma-50": WeightedMovingAverageDTO,
        "technicals-wma-200": WeightedMovingAverageDTO,
        "technicals-dema-12": DoubleExponentialMovingAverageDTO,
        "technicals-dema-26": DoubleExponentialMovingAverageDTO,
        "technicals-dema-50": DoubleExponentialMovingAverageDTO,
        "technicals-dema-200": DoubleExponentialMovingAverageDTO,
        "technicals-tema-20": TripleExponentialMovingAverageDTO,
        "technicals-rsi-14": RelativeStrengthIndexDTO,
        "technicals-rsi-7": RelativeStrengthIndexDTO,
        "technicals-standard-deviation-20": StandardDeviationDTO,
        "technicals-williams-14": WilliamsDTO,
        "technicals-adx-14": AverageDirectionalIndexDTO,
        # Instrument domain
        "stock-list": StockListDTO,
        "etf-list": ETFListDTO,
        "index-list": IndexListDTO,
        "cryptocurrency-list": CryptocurrencyListDTO,
        "forex-list": ForexListDTO,
        "etf-holdings": ETFHoldingsDTO,
    }
)

__all__ = ["DTORegistry", "DTO_REGISTRY"]
