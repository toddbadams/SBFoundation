from data_layer.dataset.models.dataset_identity import DatasetIdentity
from data_layer.dataset.models.dataset_schema import DatasetDtoSchema


from dataclasses import dataclass


VALID_TICKER_SCOPES = {"per_ticker", "global"}
VALID_INSTRUMENT_BEHAVIORS = {"create", "enrich", "relationship"}
VALID_INSTRUMENT_TYPES = {"equity", "etf", "index", "crypto", "forex"}


@dataclass(frozen=True)
class DatasetKeymapEntry:
    domain: str
    source: str
    dataset: str
    discriminator: str
    ticker_scope: str
    silver_schema: str
    silver_table: str
    key_cols: tuple[str, ...]
    row_date_col: str | None = None
    dto_schema: DatasetDtoSchema | None = None
    instrument_behavior: str | None = None  # 'create', 'enrich', 'relationship'
    instrument_type: str | None = None  # 'equity', 'etf', 'index', 'crypto', 'forex'

    def identity_key(self) -> str:
        """Return the deduplication key used to reject conflicting entries."""
        discriminator = self.discriminator or ""
        return f"{self.domain}|{self.source}|{self.dataset}|{discriminator}|{self.ticker_scope}"

    def matches_identity(self, identity: DatasetIdentity) -> bool:
        discriminator = self.discriminator or ""
        if (
            identity.domain != self.domain
            or identity.source != self.source
            or identity.dataset != self.dataset
            or (identity.discriminator or "") != discriminator
        ):
            return False

        if self.ticker_scope == "global":
            return not identity.ticker
        return bool(identity.ticker)

    @classmethod
    def from_payload(cls, payload: dict[str, object], idx: int) -> "DatasetKeymapEntry":
        """
        Construct a DatasetKeymapEntry from a raw YAML payload dictionary.

        Args:
            payload: Raw dict from dataset_keymap.yaml datasets section
            idx: Index of this entry (for error messages)

        Returns:
            Validated DatasetKeymapEntry instance

        Raises:
            ValueError: If validation fails with descriptive message including idx
        """
        if not isinstance(payload, dict):
            raise ValueError(f"Dataset entry {idx} must be a mapping.")

        domain = cls._require_str(payload, "domain", idx)
        source = cls._require_str(payload, "source", idx)
        dataset = cls._require_str(payload, "dataset", idx)
        silver_schema = cls._require_str(payload, "silver_schema", idx)
        silver_table = cls._require_str(payload, "silver_table", idx)

        discriminator = payload.get("discriminator") or ""
        if not isinstance(discriminator, str):
            raise ValueError(f"Dataset entry {idx} 'discriminator' must be a string.")

        ticker_scope = payload.get("ticker_scope")
        if not isinstance(ticker_scope, str):
            raise ValueError(f"Dataset entry {idx} requires a string 'ticker_scope'.")
        ticker_scope = ticker_scope.strip().lower()
        if ticker_scope not in VALID_TICKER_SCOPES:
            raise ValueError(f"Dataset entry {idx} 'ticker_scope' must be one of {sorted(VALID_TICKER_SCOPES)}.")

        key_cols = payload.get("key_cols")
        if not isinstance(key_cols, list) or not key_cols:
            raise ValueError(f"Dataset entry {idx} requires non-empty 'key_cols'.")
        if not all(isinstance(c, str) and c.strip() for c in key_cols):
            raise ValueError(f"Dataset entry {idx} 'key_cols' must be a list of strings.")
        key_cols_tuple = tuple(key_cols)

        row_date_col = payload.get("row_date_col")
        if row_date_col is not None:
            if not isinstance(row_date_col, str):
                raise ValueError(f"Dataset entry {idx} 'row_date_col' must be a string when provided.")
            row_date_col = row_date_col.strip() or None

        dto_schema = None
        if "dto_schema" in payload:
            dto_schema_payload = payload["dto_schema"]
            if not isinstance(dto_schema_payload, dict):
                raise ValueError(f"Dataset entry {idx} 'dto_schema' must be a mapping.")
            try:
                dto_schema = DatasetDtoSchema.from_payload(dto_schema_payload)
            except ValueError as exc:
                raise ValueError(f"Dataset entry {idx} 'dto_schema' invalid: {exc}") from exc

        # Parse optional instrument_behavior field
        instrument_behavior = payload.get("instrument_behavior")
        if instrument_behavior is not None:
            if not isinstance(instrument_behavior, str):
                raise ValueError(f"Dataset entry {idx} 'instrument_behavior' must be a string.")
            instrument_behavior = instrument_behavior.strip().lower()
            if instrument_behavior not in VALID_INSTRUMENT_BEHAVIORS:
                raise ValueError(
                    f"Dataset entry {idx} 'instrument_behavior' must be one of {sorted(VALID_INSTRUMENT_BEHAVIORS)}."
                )

        # Parse optional instrument_type field
        instrument_type = payload.get("instrument_type")
        if instrument_type is not None:
            if not isinstance(instrument_type, str):
                raise ValueError(f"Dataset entry {idx} 'instrument_type' must be a string.")
            instrument_type = instrument_type.strip().lower()
            if instrument_type not in VALID_INSTRUMENT_TYPES:
                raise ValueError(
                    f"Dataset entry {idx} 'instrument_type' must be one of {sorted(VALID_INSTRUMENT_TYPES)}."
                )

        return cls(
            domain=domain,
            source=source,
            dataset=dataset,
            discriminator=discriminator,
            ticker_scope=ticker_scope,
            silver_schema=silver_schema,
            silver_table=silver_table,
            key_cols=key_cols_tuple,
            row_date_col=row_date_col,
            dto_schema=dto_schema,
            instrument_behavior=instrument_behavior,
            instrument_type=instrument_type,
        )

    @staticmethod
    def _require_str(payload: dict, key: str, idx: int) -> str:
        """Return a required non-empty string from a dataset entry payload."""
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Dataset entry {idx} requires a non-empty '{key}'.")
        return value.strip()
