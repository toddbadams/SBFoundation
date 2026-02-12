from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime
import types
import typing

import pandas as pd

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.dataset.models.dataset_schema import DatasetDtoSchema


class DTOProjection:
    def project(
        self,
        df_raw: pd.DataFrame,
        *,
        dto_type: type[BronzeToSilverDTO] | None = None,
        dto_schema: DatasetDtoSchema | None = None,
        ticker_override: str | None = None,
    ) -> pd.DataFrame:
        if df_raw.empty:
            return pd.DataFrame()

        df = df_raw.copy()
        self._add_snake_case_columns(df)

        output: dict[str, pd.Series] = {}
        if dto_schema is not None:
            return self._project_from_schema(df, dto_schema, ticker_override)
        if dto_type is None:
            raise ValueError("DTO projection requires either dto_type or dto_schema.")

        for f in fields(dto_type):
            if not f.init:
                continue
            if f.name == "ticker" and ticker_override is not None:
                output[f.name] = pd.Series([ticker_override] * len(df), index=df.index)
                continue

            source_series = self._resolve_series(df, f)
            if source_series is None:
                output[f.name] = pd.Series([None] * len(df), index=df.index)
                continue

            output[f.name] = self._coerce_series(source_series, f.type)

        return pd.DataFrame(output)

    @staticmethod
    def _add_snake_case_columns(df: pd.DataFrame) -> None:
        for col in list(df.columns):
            if not isinstance(col, str):
                continue
            snake = BronzeToSilverDTO._camel_to_snake(col)
            if snake and snake not in df.columns:
                df[snake] = df[col]

    @staticmethod
    def _resolve_series(df: pd.DataFrame, f) -> pd.Series | None:
        api_key = f.metadata.get("api", f.name)
        if api_key in df.columns:
            return df[api_key]
        snake_api = BronzeToSilverDTO._camel_to_snake(api_key) if isinstance(api_key, str) else None
        if snake_api and snake_api in df.columns:
            return df[snake_api]
        if f.name in df.columns:
            return df[f.name]
        return None

    def _project_from_schema(
        self,
        df: pd.DataFrame,
        schema: DatasetDtoSchema,
        ticker_override: str | None,
    ) -> pd.DataFrame:
        output: dict[str, pd.Series] = {}
        for column in schema.columns:
            if column.name == "ticker" and ticker_override is not None:
                output[column.name] = pd.Series([ticker_override] * len(df), index=df.index)
                continue

            source_series = self._resolve_column_by_name(df, column.name, api_name=column.api)
            output[column.name] = self._coerce_schema_series(source_series, column.type)
        return pd.DataFrame(output)

    def _resolve_column_by_name(self, df: pd.DataFrame, name: str, api_name: str | None = None) -> pd.Series:
        candidates: list[str] = []

        # If api_name is provided, check it first (highest priority)
        if api_name:
            candidates.append(api_name)
            snake_api = BronzeToSilverDTO._camel_to_snake(api_name)
            if snake_api and snake_api != api_name:
                candidates.append(snake_api)

        # Then check the column name and its variants
        candidates.append(name)
        camel = BronzeToSilverDTO._snake_to_camel(name)
        if camel and camel not in candidates:
            candidates.append(camel)
        snake = BronzeToSilverDTO._camel_to_snake(name)
        if snake and snake not in candidates:
            candidates.append(snake)

        for candidate in candidates:
            if candidate in df.columns:
                return df[candidate]
        return pd.Series([None] * len(df), index=df.index)

    def _coerce_schema_series(self, series: pd.Series, type_hint: str) -> pd.Series:
        target = self._normalize_type_hint(type_hint)
        if target == "str":
            return series.where(series.notna(), "").astype(str)
        if target in {"int", "int64", "bigint"}:
            return pd.to_numeric(series, errors="coerce").round().astype("Int64")
        if target == "float":
            return pd.to_numeric(series, errors="coerce")
        if target == "bool":
            return series.map(self._coerce_bool)
        if target in {"date", "datetime.date"}:
            return pd.to_datetime(series, errors="coerce").dt.normalize()
        if target in {"datetime", "datetime.datetime"}:
            return pd.to_datetime(series, errors="coerce")
        if target == "list":
            return series.map(lambda v: [] if self._is_na(v) else (v if isinstance(v, list) else [v]))
        if target == "dict":
            return series.map(lambda v: {} if self._is_na(v) else (v if isinstance(v, dict) else {}))
        return series

    @staticmethod
    def _normalize_type_hint(value: str) -> str:
        if not value:
            return ""
        normalized = value.strip()
        if "|" in normalized:
            normalized = normalized.split("|")[0].strip()
        return normalized

    def _coerce_series(self, series: pd.Series, target_type: typing.Any) -> pd.Series:
        resolved = self._resolve_target_type(target_type)

        if resolved is str:
            return series.where(series.notna(), "").astype(str)

        if resolved is int:
            return pd.to_numeric(series, errors="coerce").round().astype("Int64")

        if resolved is float:
            return pd.to_numeric(series, errors="coerce")

        if resolved is bool:
            return series.map(self._coerce_bool)

        if resolved is date:
            return pd.to_datetime(series, errors="coerce").dt.normalize()

        if resolved is datetime:
            return pd.to_datetime(series, errors="coerce")

        origin = typing.get_origin(resolved)
        if origin is list:
            return series.map(lambda v: [] if self._is_na(v) else (v if isinstance(v, list) else [v]))
        if origin is dict:
            return series.map(lambda v: {} if self._is_na(v) else (v if isinstance(v, dict) else {}))

        return series

    @staticmethod
    def _resolve_target_type(target_type: typing.Any) -> typing.Any:
        origin = typing.get_origin(target_type)
        args = typing.get_args(target_type)
        if origin in (typing.Union, types.UnionType):
            non_none = [t for t in args if t is not type(None)]
            if len(non_none) == 1:
                return non_none[0]
        return target_type

    @staticmethod
    def _is_na(value: typing.Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, dict)):
            return False
        try:
            return bool(pd.isna(value))
        except Exception:
            return False

    @staticmethod
    def _coerce_bool(value: typing.Any) -> bool:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            try:
                return bool(int(value))
            except Exception:
                return False
        if isinstance(value, str):
            token = value.strip().lower()
            if token in {"true", "t", "1", "yes", "y"}:
                return True
            if token in {"false", "f", "0", "no", "n"}:
                return False
        return False
