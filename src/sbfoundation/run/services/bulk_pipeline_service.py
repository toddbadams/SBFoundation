"""Abstract base class for bulk Bronze+Silver ingestion domain services."""
from __future__ import annotations

import traceback
from abc import ABC, abstractmethod

from sbfoundation.bronze import BronzeService
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.ops.requests.promotion_config import PromotionConfig
from sbfoundation.silver import SilverService


class BulkPipelineService(ABC):
    """Shared Bronze + Silver pipeline mechanics for bulk ingestion domain services.

    Subclasses implement run() with domain-specific recipe selection and
    season gating. Bronze fetch, Silver promotion, and helper utilities
    are provided here.
    """

    def __init__(
        self,
        *,
        ops_service: OpsService,
        dataset_service: DatasetService,
        bootstrap: DuckDbBootstrap,
        logger: SBLogger | None = None,
        enable_bronze: bool,
        enable_silver: bool,
        concurrent_requests: int,
        force_from_date: str | None,
        today: str,
    ) -> None:
        self._ops_service = ops_service
        self._dataset_service = dataset_service
        self._bootstrap = bootstrap
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._enable_bronze = enable_bronze
        self._enable_silver = enable_silver
        self._concurrent_requests = concurrent_requests
        self._force_from_date = force_from_date
        self._today = today

    @abstractmethod
    def run(self, run: RunContext) -> RunContext:
        """Execute Bronze + Silver ingestion for this domain. Return updated RunContext."""

    # ------------------------------------------------------------------ #
    # Shared helpers                                                       #
    # ------------------------------------------------------------------ #

    def _processing_msg(self, enabled: bool, layer: str) -> str:
        return f"PROCESSING {layer} | " if enabled else f"DRY-RUN {layer} |"

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run: RunContext) -> RunContext:
        """Process a list of recipes through the Bronze layer."""
        if not recipes:
            return run
        bronze_service = BronzeService(
            ops_service=self._ops_service,
            concurrent_requests=self._concurrent_requests,
            force_from_date=self._force_from_date,
        )
        try:
            return bronze_service.register_recipes(run, recipes).process(run)
        except Exception as exc:
            self._logger.error("Bronze ingestion failed: %s", exc, run_id=run.run_id)
            traceback.print_exc()
            return run

    def _promote_silver(self, run: RunContext, domain: str | None = None) -> RunContext:
        """Promote Bronze data to Silver, restricted to the given domain."""
        # When force_from_date is set (backfill/year-specific fetch), disable the watermark
        # filter so rows with dates before the current watermark are not silently dropped.
        promotion_config = PromotionConfig(watermark_mode="none") if self._force_from_date else None
        silver_service = SilverService(
            enabled=self._enable_silver,
            ops_service=self._ops_service,
            keymap_service=self._dataset_service,
            bootstrap=self._bootstrap,
            promotion_config=promotion_config,
        )
        try:
            _promoted_ids, promoted_rows = silver_service.promote(run, domain=domain)
        except Exception as e:
            self._logger.error(f"Silver promotion: {e}", run_id=run.run_id)
            promoted_rows = 0
            traceback.print_exc()
        finally:
            silver_service.close()
        run.silver_dto_count += promoted_rows
        return run
