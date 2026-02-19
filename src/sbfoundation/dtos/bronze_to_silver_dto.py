from dataclasses import dataclass, fields, MISSING
from datetime import date, datetime, timezone
import importlib
import json
import re
import types
import typing
from requests.structures import CaseInsensitiveDict
import pandas as pd
from abc import abstractmethod


@dataclass(slots=True, kw_only=True, order=True)
class BronzeToSilverDTO:
    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = "_none_"

    @property
    def msg(self) -> str:
        return f"ticker={self.ticker}"

    @property
    def key_date(self) -> date:
        # Best available "date" in the payload.
        return None

    # ---- MAPPING ----#
    @classmethod
    def transform_df_content(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Override in subclasses to reshape df_content before schema projection.

        Called by SilverService before DTOProjection when the dataset's dto_schema
        declares a dto_type. Use this to explode nested structures (e.g. a 'data'
        dict column) into flat rows prior to column-level projection.
        """
        return df

    @classmethod
    @abstractmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "BronzeToSilverDTO":
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, typing.Any]:
        raise NotImplementedError

    # ---- row helpers ---- #
    @staticmethod
    def _key(d: dict, camel: str, snake: str | None = None) -> str:
        if camel in d or snake is None:
            return camel
        return snake

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        if not name:
            return name
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @staticmethod
    def _snake_to_camel(name: str) -> str:
        if not name:
            return name
        parts = name.split("_")
        return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:] if p)

    @classmethod
    def _to_snake_dict(cls, data: dict[str, typing.Any]) -> dict[str, typing.Any]:
        if not data:
            return {}
        return {(cls._camel_to_snake(key) if isinstance(key, str) else key): value for key, value in data.items()}

    @classmethod
    def _normalize_row(cls, row: typing.Mapping[str, typing.Any]) -> dict[str, typing.Any]:
        d = row if isinstance(row, dict) else dict(row)
        if not d:
            return d

        out = dict(d)
        for key, value in d.items():
            if not isinstance(key, str):
                continue
            if "_" in key:
                camel = cls._snake_to_camel(key)
                if camel not in out:
                    out[camel] = value
                else:
                    out[key] = out[camel]
                continue

            snake = cls._camel_to_snake(key)
            if snake not in out:
                out[snake] = value
            else:
                out[snake] = value

        return out

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

    @classmethod
    def _coerce_value(cls, value: typing.Any, target_type: typing.Any) -> typing.Any:
        origin = typing.get_origin(target_type)
        args = typing.get_args(target_type)

        if origin in (typing.Union, types.UnionType):
            non_none = [t for t in args if t is not type(None)]
            if len(non_none) == 1:
                return cls._coerce_value(value, non_none[0])
            for t in non_none:
                try:
                    return cls._coerce_value(value, t)
                except Exception:
                    continue
            return value

        if origin is list:
            if cls._is_na(value):
                return []
            if isinstance(value, list):
                item_type = args[0] if args else typing.Any
                return [cls._coerce_value(v, item_type) for v in value]
            if isinstance(value, str):
                return [value] if value else []
            return [value]

        if origin is dict:
            if cls._is_na(value):
                return {}
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                s = value.strip()
                if not s:
                    return {}
                try:
                    parsed = json.loads(s)
                    return parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    return {}
            if hasattr(value, "items"):
                return dict(value)
            return {}

        if target_type in (typing.Any,):
            return value

        if target_type is str:
            if cls._is_na(value):
                return ""
            s = str(value).strip()
            return s if s != "" else ""

        if target_type is bool:
            if cls._is_na(value):
                return False
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                try:
                    return bool(int(value))
                except Exception:
                    return False
            if isinstance(value, str):
                v = value.strip().lower()
                if v in {"true", "t", "1", "yes", "y"}:
                    return True
                if v in {"false", "f", "0", "no", "n"}:
                    return False
            return False

        if target_type is int:
            if cls._is_na(value):
                return None
            try:
                return int(str(value))
            except (TypeError, ValueError):
                return None

        if target_type is float:
            if cls._is_na(value):
                return None
            try:
                return float(str(value))
            except (TypeError, ValueError):
                return None

        if target_type is date:
            if cls._is_na(value):
                return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            ts = pd.to_datetime(value, utc=False, errors="coerce")
            return None if pd.isna(ts) else ts.date()

        if target_type is datetime:
            if cls._is_na(value):
                return None
            if isinstance(value, datetime):
                return value
            ts = pd.to_datetime(value, utc=False, errors="coerce")
            return None if pd.isna(ts) else ts.to_pydatetime()

        return value

    @classmethod
    def build_from_row(
        cls,
        row: typing.Mapping[str, typing.Any],
        *,
        ticker_override: typing.Optional[str] = None,
    ) -> "BronzeToSilverDTO":
        data = cls._normalize_row(row)
        kwargs: dict[str, typing.Any] = {}
        for f in fields(cls):
            if not f.init:
                continue
            if f.name == "ticker" and ticker_override is not None:
                kwargs[f.name] = ticker_override
                continue
            api_key = f.metadata.get("api", f.name)
            raw = data.get(api_key)
            if raw is None and api_key != f.name:
                raw = data.get(f.name)
            # If raw is None and the field has a default, skip to use the default
            if raw is None and (f.default is not MISSING or f.default_factory is not MISSING):
                continue
            kwargs[f.name] = cls._coerce_value(raw, f.type)
        return cls(**kwargs)

    @classmethod
    def _serialize_value(cls, value: typing.Any) -> typing.Any:
        if isinstance(value, (date, datetime)):
            return cls.to_iso8601(value)
        if isinstance(value, CaseInsensitiveDict):
            return cls.hdr_to_str(value)
        if isinstance(value, BronzeToSilverDTO):
            return value.to_dict()
        if isinstance(value, list):
            return [cls._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: cls._serialize_value(v) for k, v in value.items()}
        return value

    def build_to_dict(self, *, use_api_metadata: bool = False, snake_case: bool = True) -> dict[str, typing.Any]:
        data: dict[str, typing.Any] = {}
        for f in fields(self):
            if not f.init:
                continue
            key = f.metadata.get("api", f.name) if use_api_metadata else f.name
            data[key] = self._serialize_value(getattr(self, f.name))
        return self._to_snake_dict(data) if snake_case else data

    @staticmethod
    def f(d: dict, property: str, snake: str | None = None) -> float | None:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return None
        try:
            return float(str(x))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def d(d: dict, property: str, snake: str | None = None) -> date | None:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        if x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, pd.Timestamp) and pd.isna(x)):
            return None
        if isinstance(x, date):
            return x
        ts = pd.to_datetime(x, utc=False, errors="coerce")
        return None if pd.isna(ts) else ts.date()

    @staticmethod
    def dt(d: dict[str, typing.Any], property: str, snake: str | None = None) -> datetime | None:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        if x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, pd.Timestamp) and pd.isna(x)):
            return None
        if isinstance(x, datetime):
            return x
        ts = pd.to_datetime(x, utc=False, errors="coerce")
        return None if pd.isna(ts) else ts.to_pydatetime()

    @staticmethod
    def s(d: dict, property: str, snake: str | None = None) -> str:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ""
        s = str(x).strip()
        return s if s != "" else ""

    @staticmethod
    def sl(d: dict[str, typing.Any], key: str, snake: str | None = None) -> list[str]:
        resolved = BronzeToSilverDTO._key(d, key, snake)
        v = d.get(resolved)
        if not v:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            return [v]
        return []

    @staticmethod
    def i(d: dict, property: str, snake: str | None = None) -> int | None:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        if x is None or (isinstance(x, int) and pd.isna(x)):
            return None
        try:
            return int(str(x))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def qv(d: dict, property: str, snake: str | None = None) -> dict:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        """
        Accepts:
          - dict -> dict
          - JSON string -> dict
          - None/empty -> {}
        Anything else -> {}
        """
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return {}

        if isinstance(x, dict):
            return x

        if isinstance(x, str):
            s = x.strip()
            if not s:
                return {}
            try:
                parsed = json.loads(s)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

        return {}

    @staticmethod
    def b(d: dict, property: str, snake: str | None = None) -> bool:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return False
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            try:
                return bool(int(x))
            except Exception:
                return False
        if isinstance(x, str):
            v = x.strip().lower()
            if v in {"true", "t", "1", "yes", "y"}:
                return True
            if v in {"false", "f", "0", "no", "n"}:
                return False
        return False

    @staticmethod
    def ty(d: dict, property: str, snake: str | None = None) -> type:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        # expects "package.module.ClassName"
        module_name, _, qual = x.rpartition(".")
        if not module_name:
            raise ValueError(f"Invalid type path: {x}")
        mod = importlib.import_module(module_name)
        tp = getattr(mod, qual, None)
        if tp is None:
            raise ValueError(f"Cannot resolve type from: {x}")
        return tp

    @staticmethod
    def hdrs(d: dict, property: str, snake: str | None = None) -> CaseInsensitiveDict:
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)
        headers = CaseInsensitiveDict()
        if not x:
            return headers

        for part in x.split("; "):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            headers[key] = value
        return headers

    @staticmethod
    def dto(d: dict, property: str, dto_type: type["BronzeToSilverDTO"], snake: str | None = None) -> "BronzeToSilverDTO":
        """
        Reads a nested DTO payload from d[property] and deserializes using dto_type.from_json_row().

        Supports:
          - dict payload
          - JSON string payload
          - already-instantiated DTO payload
          - missing/None -> None
        """
        key = BronzeToSilverDTO._key(d, property, snake)
        x = d.get(key)

        if x is None:
            return None

        # Already deserialized / constructed
        if isinstance(x, dto_type):
            return x

        # Dict payload (expected)
        if isinstance(x, dict):
            return dto_type.from_row(x)

        # JSON string payload (e.g., re-serialized Bronze content)
        if isinstance(x, str):
            s = x.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"{property} is not valid JSON") from e

            if not isinstance(parsed, dict):
                raise TypeError(f"{property} JSON must deserialize to dict, got {type(parsed).__name__}")

            return dto_type.from_json_row(parsed)

        raise TypeError(f"{key} must be dict | JSON str | {dto_type.__name__}, got {type(x).__name__}")

    # ---- to_dict helpers ---- #
    @staticmethod
    def to_iso8601(value: typing.Optional[typing.Union[datetime, date]]) -> typing.Optional[str]:
        if value is None:
            return None

        if isinstance(value, datetime):
            # Normalize to UTC if tz-aware
            if value.tzinfo is not None:
                value = value.astimezone(timezone.utc)
            return value.replace(tzinfo=None).isoformat(timespec="seconds")

        if isinstance(value, date):
            # Convert plain date to ISO8601
            return value.isoformat()

        # Unsupported type — skip
        return None

    @staticmethod
    def type_to_str(value: type) -> str:
        return f"{value.__module__}.{value.__qualname__}"

    @staticmethod
    def hdr_to_str(headers: CaseInsensitiveDict) -> str:
        return "; ".join(f"{key}={value}" for key, value in headers.items())
