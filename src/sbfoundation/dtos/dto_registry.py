from __future__ import annotations

from typing import Iterable

from sbfoundation.dtos.company.company_delisted_dto import CompanyDelistedDTO
from sbfoundation.dtos.company.company_dto import CompanyDTO
from sbfoundation.dtos.company.company_notes_dto import CompanyNotesDTO
from sbfoundation.dtos.company.company_employees_dto import CompanyEmployeesDTO
from sbfoundation.dtos.company.company_market_cap_dto import CompanyMarketCapDTO
from sbfoundation.dtos.company.company_officers_dto import CompanyOfficerDTO
from sbfoundation.dtos.company.company_peers_dto import CompanyPeersDTO
from sbfoundation.dtos.company.company_shares_float_dto import CompanySharesFloatDTO

from sbfoundation.dtos.economics.economics_dto import EconomicsDTO
from sbfoundation.dtos.economics.market_risk_premium_dto import MarketRiskPremiumDTO
from sbfoundation.dtos.economics.treasury_rates_dto import TreasuryRatesDTO

from sbfoundation.dtos.fundamentals.balance_sheet_statement_dto import BalanceSheetStatementDTO
from sbfoundation.dtos.fundamentals.balance_sheet_statement_growth_dto import BalanceSheetStatementGrowthDTO
from sbfoundation.dtos.fundamentals.cashflow_statement_dto import CashflowStatementDTO
from sbfoundation.dtos.fundamentals.cashflow_statement_growth_dto import CashflowStatementGrowthDTO
from sbfoundation.dtos.fundamentals.enterprise_values_dto import EnterpriseValuesDTO
from sbfoundation.dtos.fundamentals.financial_scores_dto import FinancialScoresDTO
from sbfoundation.dtos.fundamentals.financial_statement_growth_dto import FinancialStatementGrowthDTO
from sbfoundation.dtos.fundamentals.income_statement_dto import IncomeStatementDTO
from sbfoundation.dtos.fundamentals.income_statement_growth_dto import IncomeStatementGrowthDTO
from sbfoundation.dtos.fundamentals.key_metrics_dto import KeyMetricsDTO
from sbfoundation.dtos.fundamentals.key_metrics_ttm_dto import KeyMetricsTtmDTO
from sbfoundation.dtos.fundamentals.metrics_ratios_dto import MetricsRatiosDTO
from sbfoundation.dtos.fundamentals.owner_earnings_dto import OwnerEarningsDTO
from sbfoundation.dtos.fundamentals.revenue_segmentation_dto import RevenueSegmentationDTO

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO

from sbfoundation.dtos.technicals.average_directional_index_dto import AverageDirectionalIndexDTO
from sbfoundation.dtos.technicals.double_exponential_moving_average_dto import DoubleExponentialMovingAverageDTO
from sbfoundation.dtos.technicals.exponential_moving_average_dto import ExponentialMovingAverageDTO
from sbfoundation.dtos.technicals.historical_price_eod_dividend_adjusted_dto import HistoricalPriceEodDividendAdjustedDTO
from sbfoundation.dtos.technicals.historical_price_eod_full_dto import HistoricalPriceEodFullDTO
from sbfoundation.dtos.technicals.historical_price_eod_non_split_adjusted_dto import HistoricalPriceEodNonSplitAdjustedDTO
from sbfoundation.dtos.technicals.relative_strength_index_dto import RelativeStrengthIndexDTO
from sbfoundation.dtos.technicals.simple_moving_average_dto import SimpleMovingAverageDTO
from sbfoundation.dtos.technicals.standard_deviation_dto import StandardDeviationDTO
from sbfoundation.dtos.technicals.triple_exponential_moving_average_dto import TripleExponentialMovingAverageDTO
from sbfoundation.dtos.technicals.weighted_moving_average_dto import WeightedMovingAverageDTO
from sbfoundation.dtos.technicals.williams_dto import WilliamsDTO

from sbfoundation.dtos.instrument.stock_list_dto import StockListDTO
from sbfoundation.dtos.instrument.etf_list_dto import ETFListDTO
from sbfoundation.dtos.instrument.index_list_dto import IndexListDTO
from sbfoundation.dtos.instrument.cryptocurrency_list_dto import CryptocurrencyListDTO
from sbfoundation.dtos.instrument.etf_holdings_dto import ETFHoldingsDTO

from sbfoundation.dtos.market.market_countries_dto import MarketCountriesDTO
from sbfoundation.dtos.market.market_exchanges_dto import MarketExchangesDTO
from sbfoundation.dtos.market.market_sectors_dto import MarketSectorsDTO
from sbfoundation.dtos.market.market_industries_dto import MarketIndustriesDTO
from sbfoundation.dtos.market.market_screener_dto import MarketScreenerDTO
from sbfoundation.dtos.market.market_sector_performance_dto import MarketSectorPerformanceDTO
from sbfoundation.dtos.market.market_industry_performance_dto import MarketIndustryPerformanceDTO
from sbfoundation.dtos.market.market_sector_pe_dto import MarketSectorPeDTO
from sbfoundation.dtos.market.market_industry_pe_dto import MarketIndustryPeDTO
from sbfoundation.dtos.market.market_hours_dto import MarketHoursDTO
from sbfoundation.dtos.market.market_holidays_dto import MarketHolidaysDTO

from sbfoundation.dtos.commodities.commodities_list_dto import CommoditiesListDTO
from sbfoundation.dtos.commodities.commodities_price_eod_dto import CommoditiesPriceEodDTO
from sbfoundation.dtos.crypto.crypto_price_eod_dto import CryptoPriceEodDTO
from sbfoundation.dtos.fx.fx_list_dto import FxListDTO
from sbfoundation.dtos.fx.fx_price_eod_dto import FxPriceEodDTO


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
        "company-notes": CompanyNotesDTO,
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
        # Market domain (list datasets)
        "stock-list": StockListDTO,
        "etf-list": ETFListDTO,
        "index-list": IndexListDTO,
        "cryptocurrency-list": CryptocurrencyListDTO,
        "etf-holdings": ETFHoldingsDTO,
        # Market domain
        "market-countries": MarketCountriesDTO,
        "market-exchanges": MarketExchangesDTO,
        "market-sectors": MarketSectorsDTO,
        "market-industries": MarketIndustriesDTO,
        "market-sector-performance": MarketSectorPerformanceDTO,
        "market-industry-performance": MarketIndustryPerformanceDTO,
        "market-sector-pe": MarketSectorPeDTO,
        "market-industry-pe": MarketIndustryPeDTO,
        "market-hours": MarketHoursDTO,
        "market-holidays": MarketHolidaysDTO,
        "market-screener": MarketScreenerDTO,
        # Commodities domain
        "commodities-list": CommoditiesListDTO,
        "commodities-price-eod": CommoditiesPriceEodDTO,
        # Crypto domain
        "crypto-list": CryptocurrencyListDTO,
        "crypto-price-eod": CryptoPriceEodDTO,
        # FX domain
        "fx-list": FxListDTO,
        "fx-price-eod": FxPriceEodDTO,
    }
)

__all__ = ["DTORegistry", "DTO_REGISTRY"]
