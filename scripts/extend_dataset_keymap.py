"""Extend dataset_keymap.yaml with schema metadata for DTOs, dims, and facts."""

from __future__ import annotations

import importlib
import sys
import typing
import types

import yaml
from dataclasses import fields
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sbfoundation.dtos.dto_registry import DTO_REGISTRY

DatasetKeymapPath = Path("config/dataset_keymap.yaml")


def describe_type(tp: Any) -> str:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in {typing.Union, types.UnionType}:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return describe_type(non_none[0])
        inner = " | ".join(describe_type(a) for a in non_none) if non_none else "any"
        return f"{inner} | None"
    if origin:
        name = getattr(origin, "__name__", str(origin))
        if args:
            return f"{name}[{', '.join(describe_type(a) for a in args)}]"
        return name
    if hasattr(tp, "__name__"):
        return tp.__name__
    return str(tp)


def resolve_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        parts = module_name.split(".")
        if len(parts) >= 3 and parts[1] in {"dims", "facts"}:
            remapped = ".".join(["data_layer", parts[1], parts[0], *parts[2:]])
            return importlib.import_module(remapped)
        raise


def resolve_type(type_path: str):
    module_name, _, qualname = type_path.rpartition(".")
    module = resolve_module(module_name)
    cls = getattr(module, qualname, None)
    if cls is None:
        raise ImportError(f"Cannot resolve type from: {type_path}")
    return cls


def columns_from_dataclass(cls: type) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in fields(cls):
        if not f.init:
            continue
        typ = describe_type(f.type)
        nullable = False
        origin = typing.get_origin(f.type)
        if origin in {typing.Union, types.UnionType}:
            nullable = any(arg is type(None) for arg in typing.get_args(f.type))
        if f.default is None or f.default is None:
            nullable = True
        out.append({"name": f.name, "type": typ, "nullable": nullable})
    return out


def annotate_datasets(doc: dict[str, Any]) -> None:
    datasets = doc.get("datasets") or []
    for entry in datasets:
        dataset = entry.get("dataset")
        if not dataset:
            continue
        dto_cls = DTO_REGISTRY.get(dataset)
        if dto_cls is None:
            continue
        schema = entry.setdefault("dto_schema", {})
        schema["dto_type"] = f"{dto_cls.__module__}.{dto_cls.__name__}"
        schema["columns"] = columns_from_dataclass(dto_cls)


def annotate_gold(doc: dict[str, Any]) -> None:
    gold = doc.setdefault("gold", {})
    dims = gold.get("dims") or []
    for entry in dims:
        dim_type_path = entry.get("dim_type")
        if not dim_type_path:
            continue
        try:
            dim_cls = resolve_type(dim_type_path)
        except ModuleNotFoundError:
            continue
        schema = entry.setdefault("schema", {})
        business_keys = list(getattr(dim_cls, "BUSINESS_KEYS", ()) or ())
        schema["business_keys"] = business_keys
        schema["columns"] = columns_from_dataclass(dim_cls)
    facts = gold.get("facts") or []
    for entry in facts:
        fact_type_path = entry.get("fact_type")
        if not fact_type_path:
            continue
        try:
            fact_cls = resolve_type(fact_type_path)
        except ModuleNotFoundError:
            continue
        schema = entry.setdefault("schema", {})
        grain_keys = list(getattr(fact_cls, "GRAIN_KEYS", ()) or ())
        schema["grain_keys"] = grain_keys
        schema["columns"] = columns_from_dataclass(fact_cls)
        schema["has_snapshot_date"] = any(col["name"] == "snapshot_date" for col in schema["columns"])


def main() -> None:
    doc = yaml.safe_load(DatasetKeymapPath.read_text()) or {}
    annotate_datasets(doc)
    annotate_gold(doc)
    DatasetKeymapPath.write_text(yaml.safe_dump(doc, sort_keys=False))


if __name__ == "__main__":
    main()
