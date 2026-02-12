from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SchemaColumn:
    name: str
    type: str
    nullable: bool
    api: str | None = None  # Optional API/Bronze field name (if different from name)

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "SchemaColumn":
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Schema column requires a non-empty 'name'.")
        type_value = payload.get("type")
        if not isinstance(type_value, str) or not type_value.strip():
            raise ValueError(f"Schema column '{name}' requires a non-empty 'type'.")
        nullable = bool(payload.get("nullable"))
        api = payload.get("api")
        api_value = api.strip() if isinstance(api, str) and api.strip() else None
        return cls(name=name.strip(), type=type_value.strip(), nullable=nullable, api=api_value)


@dataclass(frozen=True)
class DatasetDtoSchema:
    dto_type: str | None
    columns: tuple[SchemaColumn, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "DatasetDtoSchema":
        dto_type = payload.get("dto_type")
        if dto_type is not None and not isinstance(dto_type, str):
            raise ValueError("dto_schema.dto_type must be a string when provided.")
        columns_raw = payload.get("columns") or []
        if not isinstance(columns_raw, Iterable):
            raise ValueError("dto_schema.columns must be iterable.")
        columns = tuple(SchemaColumn.from_payload(col) for col in columns_raw if isinstance(col, dict))
        return cls(dto_type=dto_type, columns=columns)


@dataclass(frozen=True)
class TableSchema:
    columns: tuple[SchemaColumn, ...]
    business_keys: tuple[str, ...] = ()
    grain_keys: tuple[str, ...] = ()
    has_snapshot_date: bool = False

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "TableSchema":
        columns_raw = payload.get("columns") or []
        if not isinstance(columns_raw, Iterable):
            raise ValueError("schema.columns must be iterable.")
        columns = tuple(SchemaColumn.from_payload(col) for col in columns_raw if isinstance(col, dict))
        business_keys_raw = payload.get("business_keys") or []
        grain_keys_raw = payload.get("grain_keys") or []
        return cls(
            columns=columns,
            business_keys=tuple(str(key) for key in business_keys_raw if isinstance(key, str)),
            grain_keys=tuple(str(key) for key in grain_keys_raw if isinstance(key, str)),
            has_snapshot_date=bool(payload.get("has_snapshot_date")),
        )
