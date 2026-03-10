from __future__ import annotations

from typing import Iterable

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.dtos.eod.eod_bulk_price_dto import EodBulkPriceDTO
from sbfoundation.dtos.eod.eod_bulk_company_profile_dto import EodBulkCompanyProfileDTO
from sbfoundation.dtos.fundamentals.bulk.income_statement_bulk_dto import IncomeStatementBulkDTO
from sbfoundation.dtos.fundamentals.bulk.balance_sheet_bulk_dto import BalanceSheetBulkDTO
from sbfoundation.dtos.fundamentals.bulk.cashflow_bulk_dto import CashflowBulkDTO


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
        # EOD bulk domain
        "eod-bulk-price": EodBulkPriceDTO,
        "company-profile-bulk": EodBulkCompanyProfileDTO,
        # Quarter bulk domain
        "income-statement-bulk-quarter": IncomeStatementBulkDTO,
        "balance-sheet-bulk-quarter": BalanceSheetBulkDTO,
        "cashflow-bulk-quarter": CashflowBulkDTO,
        # Annual bulk domain
        "income-statement-bulk-annual": IncomeStatementBulkDTO,
        "balance-sheet-bulk-annual": BalanceSheetBulkDTO,
        "cashflow-bulk-annual": CashflowBulkDTO,
    }
)

__all__ = ["DTORegistry", "DTO_REGISTRY"]
