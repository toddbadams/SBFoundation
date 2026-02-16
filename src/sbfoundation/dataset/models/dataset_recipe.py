from datetime import datetime
import uuid
from dateutil.relativedelta import relativedelta
import os
from dataclasses import dataclass
import typing


from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.settings import *


@dataclass(slots=True, kw_only=True, order=True)
class DatasetRecipe(BronzeToSilverDTO):

    T = typing.TypeVar("T", bound=BronzeToSilverDTO)

    domain: str  # the domain such as company, economics, fundamentals, technicals
    source: str  # the data source such as FMP, AV, BIS, FRED, Alpaca, Schwab
    dataset: str  # the internal dataset name such as company_profile, economic-indicators, etc.
    data_source_path: str  # the relative path for the source URL
    query_vars: dict  # the source request queary parameters
    date_key: str  # a property name to find the date associated the data object injested
    cadence_mode: str  # interval or calendar
    min_age_days: int  # when in interval cadendnce mode in market days.  ingestion_date >= base_date + N
    is_ticker_based: bool  # does this recipe run across all tickers?
    help_url: str  # a URL for online API documentation of this source endpoint
    run_days: list[str] | None = None  # which weekdays this recipe can run (defaults to all)
    discriminator: str | None = None  # an optional discriminator to build deterministic filenames, partitions to avoid collisions
    execution_phase: str = EXECUTION_PHASE_DATA_ACQUISITION  # 'instrument_discovery' or 'data_acquisition'
    error: str = None  # error description

    # todo: expand recipe metadata to include Bronze/Silver lineage hints from
    # docs/AI_context/architecture.md.md for richer manifests.

    def __post_init__(self) -> None:
        if not self.run_days:
            self.run_days = list(DAYS_OF_WEEK)
            return

        if isinstance(self.run_days, str):
            raw = [self.run_days]
        else:
            raw = list(self.run_days)

        self.run_days = [str(day).strip().lower() for day in raw if str(day).strip()]
        if not self.run_days:
            self.run_days = list(DAYS_OF_WEEK)

    def create_file_id(self) -> str:
        return uuid.uuid4().hex

    def isValid(self) -> bool:
        # Validate the recipe against configured domains and cadences to avoid
        # polluting Bronze with unsupported endpoints.
        if self.domain not in DOMAINS:
            self.error = "INVALID DOMAIN"
            return False

        if self.source not in DATA_SOURCES:
            self.error = "INVALID DATA SOURCE"
            return False

        if self.dataset not in DATASETS:
            self.error = "INVALID DATA SET"
            return False

        if self.cadence_mode not in CADENCES:
            self.error = "INVALID CADENCE MODE"
            return False

        if any(day not in DAYS_OF_WEEK for day in (self.run_days or [])):
            self.error = "INVALID RUN DAYS"
            return False

        if self.execution_phase not in EXECUTION_PHASES:
            self.error = "INVALID EXECUTION PHASE"
            return False

        self.error = None
        return True

    @property
    def msg(self) -> str:
        return f"domain={self.domain} | source={self.source} | dataset={self.dataset} | discriminator={self.discriminator}"

    def runs_on(self, day: str) -> bool:
        if not day:
            return True
        return day.lower() in (self.run_days or DAYS_OF_WEEK)

    def get_query_vars(
        self,
        *,
        from_date: str | None = None,
        ticker: str | None = None,
        to_date: str | None = None,
        api_key: str | None = None,
        snapshot_date: str | None = None,
    ) -> dict[str, typing.Any]:
        # Copy so we don't mutate the recipe's template dict while expanding
        # placeholders for ticker and date ranges.
        q: dict[str, typing.Any] = dict(self.query_vars or {})

        # Placeholder substitution
        for k, v in list(q.items()):
            if v == TICKER_PLACEHOLDER:
                q[k] = ticker
            elif v == FROM_DATE_PLACEHOLDER:
                q[k] = from_date
            elif v == FROM_ONE_MONTH_AGO_PLACEHOLDER:
                d: datetime = datetime.fromisoformat(to_date)
                d = d - relativedelta(months=1)
                q[k] = d.date().isoformat()
            elif v == TO_DATE_PLACEHOLDER:
                q[k] = to_date
            elif v == DATE_PLACEHOLDER:
                q[k] = snapshot_date
            elif v == LIMIT_PLACEHOLDER:
                q[k] = DEFAULT_LIMIT
            elif v == PERIOD_PLACEHOLDER:
                q[k] = PERIOD_ANNUAL

        # Always include api key (will be filtered if None)
        api_key_env = DATA_SOURCES_CONFIG[self.source][API_KEY]
        api_key_value = api_key if api_key else os.getenv(api_key_env)
        if api_key_value:
            q["apikey"] = api_key_value

        # Remove None-valued items
        return {k: v for k, v in q.items() if v is not None}

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "DatasetRecipe":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()
