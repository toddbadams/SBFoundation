from dataclasses import dataclass
from datetime import date
import typing
import uuid
from pathlib import Path
import pandas as pd

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.dtos.dto_registry import DTO_REGISTRY
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.folders import Folders
from sbfoundation.settings import *


@dataclass(slots=True, kw_only=True)
class RunRequest(BronzeToSilverDTO):
    T = typing.TypeVar("TDTO", bound=BronzeToSilverDTO)

    recipe: DatasetRecipe
    injestion_date: str  # ISO8601 date of data injestion
    run_id: str  # UUID indicating the run identifier
    ticker: str  # the stock symbol, otherwise None
    dto_type: type[T]  # the Silver DTO type
    data_source_path: str  # the relative path for the source URL
    url: str  # the full source URL
    query_vars: dict[str, typing.Any]  # the source request queary parameters
    date_key: str  # a property name to find the date associated the data object injested
    allows_empty_content: bool = False  # are empty content responses allowed for Bronze acceptance
    from_date: str  # ISO 8601 date representing the earliest data date, as given by the date key
    to_date: str  # ISO 8601 date representing the latest data date, as given by the date key
    limit: int  # limit the number of returned items
    cadence_mode: str  # interval or calendar
    min_age_days: int  # when in interval cadence mode the minimum cooldown days in market days.  ingestion_date >= from_date + min_age_days
    release_day: str  # ISO 8601 date, used when in calendar cadence mode, the day of expected data release.
    error: str = None  # error description
    file_id: str = None  # a unique filename property
    instrument_sk: int = None  # resolved from gold.dim_instrument for orchestration awareness (not stored in Bronze)

    @property
    def bronze_absolute_filename(self) -> str:
        """
        A fully qualified bronze layer filename for the result, preserving the raw payload in alignment
        with the Bronze guarantees documented in docs/AI_context/architecture.md.
        """
        folder = Folders.bronze_result_absolute_path(domain=self.recipe.domain, source=self.recipe.source, dataset=self.recipe.dataset)
        if self.ticker is not None:
            folder = folder / self.ticker
        return str(folder / self._filename)

    @property
    def bronze_relative_filename(self) -> str:
        """
        A fully qualified bronze layer filename for the result, preserving the raw payload in alignment
        with the Bronze guarantees documented in docs/AI_context/architecture.md.
        """
        folder = Folders.bronze_result_relative_path(domain=self.recipe.domain, source=self.recipe.source, dataset=self.recipe.dataset)
        if self.ticker is not None:
            folder = folder / self.ticker
        return str(folder / self._filename)

    @property
    def _filename(self) -> str:
        filename = self.file_id
        if self.recipe.discriminator is not None and len(self.recipe.discriminator) > 0:
            filename = f"{filename}-{self.recipe.discriminator}"
        filename = f"{filename}.json"
        return str(filename)

    @property
    def msg(self) -> str:
        return f"{self.recipe.msg} | ticker={self.ticker} | injestion_date={self.injestion_date} | run_id={self.run_id}"

    @property
    def data_date_key(self) -> str:
        x = f"{self.recipe.domain}-{self.recipe.source}-{self.recipe.dataset}-{self.ticker}"
        if self.recipe.discriminator is not None:
            x = f"{x}-{self.recipe.discriminator}"
        if self.ticker is not None:
            x = f"{x}-{self.ticker}"
        return x

    def canRun(self) -> bool:
        # todo: surface validation detail metrics for observability dashboards
        if not self.recipe.isValid():
            self.error = "INVALID RUN RECIPE"
            return False

        if self.recipe.is_ticker_based and (self.ticker is None or len(self.ticker) < 1 or len(self.ticker) > 12):
            self.error = "INVALID TICKER"
            return False

        if not isinstance(self.run_id, str):
            self.error = "INVALID RUN ID"
            return False

        if not issubclass(self.dto_type, BronzeToSilverDTO):
            self.error = "INVALID DTO TYPE"
            return False

        if self.data_source_path is None or len(self.data_source_path) < 1:
            self.error = "INVALID DATA SOURCE PATH"
            return False

        start = date.fromisoformat(self.from_date)
        end = date.fromisoformat(self.injestion_date)
        if (end - start).days <= self.min_age_days:
            self.error = "REQUEST IS TOO SOON"
            return False

        return True

    def ingest_identity(self) -> tuple[str, str, str, str, str]:
        discriminator = self.recipe.discriminator or ""
        ticker = self.ticker or ""
        if not self.recipe.is_ticker_based:
            ticker = ""
        return self.recipe.domain, self.recipe.source, self.recipe.dataset, discriminator, ticker

    @classmethod
    def from_recipe(cls, *, recipe: DatasetRecipe, run_id: str, from_date: str, today: str, api_key: str, ticker: str = None, instrument_sk: int = None, snapshot_date: str | None = None) -> "RunRequest":
        data_source_config = DATA_SOURCES_CONFIG[recipe.source]
        r = RunRequest(
            recipe=recipe,
            injestion_date=today,
            run_id=run_id,
            ticker=ticker,
            dto_type=DTO_REGISTRY[recipe.dataset],
            data_source_path=recipe.data_source_path,
            url=f"{data_source_config[BASE_URL]}{recipe.data_source_path}",
            query_vars=recipe.get_query_vars(
                from_date=from_date,
                ticker=ticker,
                to_date=today,
                api_key=api_key,
                snapshot_date=snapshot_date,
            ),
            date_key=recipe.date_key,
            from_date=from_date,
            to_date=today,
            limit=DEFAULT_LIMIT,
            cadence_mode=recipe.cadence_mode,
            min_age_days=recipe.min_age_days,
            release_day=None,  # todo: wire up some logic here
            file_id=recipe.create_file_id(),
            instrument_sk=instrument_sk,
        )

        # update the release day (if calendar mode)
        if r.cadence_mode == CALENDAR_CADENCE_MODE:
            pass  # todo: align calendar cadence to upstream release patterns

        return r

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "RunRequest":
        row = cls._normalize_row(row)
        return cls(
            ticker=ticker if ticker is not None else (cls.s(row, "ticker") or None),
            recipe=cls.dto(row, "recipe", DatasetRecipe),
            injestion_date=cls.s(row, "injestion_date"),
            run_id=cls.s(row, "run_id"),
            dto_type=cls.ty(row, "dto_type"),
            data_source_path=cls.s(row, "data_source_path"),
            url=cls.s(row, "url"),
            query_vars=cls.qv(row, "query_vars"),
            date_key=cls.s(row, "date_key"),
            allows_empty_content=cls.b(row, "allows_empty_content"),
            from_date=cls.s(row, "from_date"),
            to_date=cls.s(row, "to_date"),
            limit=cls.i(row, "limit"),
            cadence_mode=cls.s(row, "cadence_mode"),
            min_age_days=cls.i(row, "min_age_days"),
            release_day=cls.s(row, "release_day"),
            error=cls.s(row, "error"),
            file_id=cls.s(row, "file_id"),
        )

    def to_dict(self) -> dict[str, typing.Any]:
        return self._to_snake_dict(
            {
                "ticker": self.ticker,
                "recipe": self.recipe.to_dict() if self.recipe else None,
                "injestion_date": self.injestion_date,
                "run_id": self.run_id,
                "dto_type": self.type_to_str(self.dto_type) if self.dto_type else None,
                "data_source_path": self.data_source_path,
                "url": self.url,
                "query_vars": self.query_vars or {},
                "date_key": self.date_key,
                "allows_empty_content": bool(self.allows_empty_content),
                "from_date": self.from_date,
                "to_date": self.to_date,
                "limit": self.limit,
                "cadence_mode": self.cadence_mode,
                "min_age_days": self.min_age_days,
                "release_day": self.release_day,
                "error": self.error,
                "file_id": self.file_id,
            }
        )
