from __future__ import annotations

from datetime import date
import logging
import os
from pathlib import Path


from sbfoundation.dataset.loaders.dataset_keymap_loader import DatasetKeymapLoader
from sbfoundation.dataset.models.dataset_keymap import DatasetKeymap
from sbfoundation.dataset.models.dataset_keymap_entry import DatasetKeymapEntry
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.settings import *


class DatasetService:
    """Aggregate root for the dataset identity catalog.

    This class owns the canonical `config/dataset_keymap.yaml` context map, so any
    addition to the DTO registry must also land here. It validates every entry
    (domain/source/dataset/ticker_scope/key_cols) and enforces uniqueness of the
    serialized identity key before handing the `DatasetKeymap` to downstream
    services."""

    def __init__(self, today: str, plan: str, *, logger: logging.Logger | None = None, strict_dto_registry: bool | None = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        if strict_dto_registry is None:
            strict_dto_registry = os.getenv("STRICT_DTO_REGISTRY", "").strip().lower() in {"1", "true", "yes"}
        self._strict_dto_registry = strict_dto_registry
        self._today = date.fromisoformat(today)
        self._plan = plan

        # Load and cache keymap and recipes on init
        self._keymap = self.load_dataset_keymap()
        self._recipes = self._load_recipes()

    def load_dataset_keymap(self) -> DatasetKeymap:
        """Load and validate the dataset keymap.

        Delegates raw YAML loading to DatasetKeymapLoader.
        Validates structure, enforces uniqueness, and constructs domain models.
        """
        payload = DatasetKeymapLoader.load_raw_keymap()
        if not isinstance(payload, dict):
            raise ValueError("Dataset keymap must be a YAML mapping at the top level.")

        version = payload.get("version")
        if not isinstance(version, int):
            raise ValueError("Dataset keymap requires an integer 'version'.")

        datasets = payload.get("datasets") or []
        if not isinstance(datasets, list):
            raise ValueError("Dataset keymap 'datasets' must be a list.")

        entries: list[DatasetKeymapEntry] = []
        seen: set[str] = set()

        for idx, raw in enumerate(datasets):
            entry = DatasetKeymapEntry.from_payload(raw, idx)
            identity_key = entry.identity_key()
            if identity_key in seen:
                raise ValueError(f"Duplicate dataset mapping for {identity_key}.")
            seen.add(identity_key)
            entries.append(entry)

        keymap = DatasetKeymap(version=version, entries=tuple(entries))
        # Defer DTO registry validation to after init completes
        return keymap

    def validate_dto_registry(self) -> None:
        """Validate that DTO registry matches keymap entries."""
        self._validate_dto_registry(self._keymap.entries)

    def _validate_dto_registry(self, entries: tuple[DatasetKeymapEntry, ...]) -> None:
        try:
            from sbfoundation.dtos.dto_registry import DTO_REGISTRY
        except Exception as exc:
            self._logger.warning("DTO registry unavailable; skipping keymap validation | error=%s", exc)
            return

        # Datasets with dto_schema defined in keymap don't need DTO_REGISTRY entries
        # Only validate datasets that rely on the legacy DTO_REGISTRY
        datasets_with_schema = {entry.dataset for entry in entries if entry.dto_schema is not None}
        keymap_datasets = {entry.dataset for entry in entries} - datasets_with_schema
        registry_datasets = set(DTO_REGISTRY.keys()) - datasets_with_schema
        missing = sorted(keymap_datasets - registry_datasets)
        extra = sorted(registry_datasets - keymap_datasets)
        if not missing and not extra:
            return

        message = "DTO registry mismatch | missing=%s | extra=%s" % (missing, extra)
        if self._strict_dto_registry:
            raise ValueError(message)
        self._logger.warning(message)

    def _load_recipe_rows_from_keymap(self) -> list[dict]:
        datasets = DatasetKeymapLoader.load_raw_datasets()

        recipe_rows: list[dict] = []
        for entry in datasets:
            if not isinstance(entry, dict):
                continue
            entry_recipes = entry.get("recipes") or entry.get("recipe") or []
            if isinstance(entry_recipes, dict):
                entry_recipes = [entry_recipes]
            for recipe in entry_recipes:
                if not isinstance(recipe, dict):
                    continue
                date_key = recipe.get("date_key") or entry.get("row_date_col")
                is_ticker_based = entry.get("ticker_scope") == "per_ticker"
                recipe_row = {
                    "domain": entry.get("domain"),
                    "source": entry.get("source"),
                    "dataset": entry.get("dataset"),
                    "data_source_path": recipe.get("data_source_path"),
                    "query_vars": recipe.get("query_vars") or {},
                    "date_key": date_key,
                    "cadence_mode": recipe.get("cadence_mode"),
                    "min_age_days": recipe.get("min_age_days"),
                    "is_ticker_based": is_ticker_based,
                    "help_url": recipe.get("help_url"),
                    "run_days": recipe.get("run_days"),
                    "discriminator": entry.get("discriminator") or None,
                    "plans": recipe.get("plans"),
                }
                # Only include execution_phase if explicitly set (otherwise use default)
                if recipe.get("execution_phase"):
                    recipe_row["execution_phase"] = recipe.get("execution_phase")
                recipe_rows.append(recipe_row)

        return recipe_rows

    def _load_recipes(self) -> list[DatasetRecipe]:
        """Load and filter recipes based on today and plan. Called once on init."""
        recipe_rows = self._load_recipe_rows_from_keymap()
        day_of_week = DAYS_OF_WEEK_BY_INDEX.get(self._today.weekday())
        if not day_of_week:
            return []
        plan_norm = self._plan.strip().lower() if self._plan else ""
        # Build set of plans included in the user's plan (additive hierarchy)
        included_plans: set[str] = set()
        if plan_norm:
            fmp_plans_lower = [p.lower() for p in FMP_PLANS]
            if plan_norm in fmp_plans_lower:
                plan_idx = fmp_plans_lower.index(plan_norm)
                included_plans = set(fmp_plans_lower[: plan_idx + 1])
            else:
                included_plans = {plan_norm}
        recipes: list[DatasetRecipe] = []
        for row in recipe_rows:
            plans = row.get("plans") or []
            if isinstance(plans, str):
                plans = [plans]
            if plans:
                plans_norm = {str(item).strip().lower() for item in plans if str(item).strip()}
                # Recipe runs if any of its plans are within the user's included plans
                if plan_norm and not plans_norm.intersection(included_plans):
                    continue
            recipe = DatasetRecipe.from_row(row)
            if not recipe.isValid():
                self._logger.warning("Skipping invalid recipe: %s | error=%s", recipe.msg, recipe.error)
                continue
            if recipe.runs_on(day_of_week):
                recipes.append(recipe)
        return recipes

    @property
    def recipes(self) -> list[DatasetRecipe]:
        """Return cached recipes for today and plan."""
        return self._recipes

    @property
    def keymap(self) -> DatasetKeymap:
        """Return cached dataset keymap."""
        return self._keymap

    def non_ticker_recipes(self) -> list[DatasetRecipe]:
        """Return non-ticker recipes from cache."""
        return [recipe for recipe in self._recipes if not recipe.is_ticker_based]

    def ticker_recipes(self) -> list[DatasetRecipe]:
        """Return ticker-based recipes from cache."""
        return [r for r in self._recipes if r.is_ticker_based]
