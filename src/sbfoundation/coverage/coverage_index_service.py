from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sbfoundation.dataset.loaders.dataset_keymap_loader import DatasetKeymapLoader
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo


class CoverageIndexService:
    """Computes and materializes ops.coverage_index from ops.file_ingestions.

    Called once per pipeline run via OpsService.refresh_coverage_index() after
    all bronze and silver processing is complete.  The index is rebuilt in full
    each refresh (DELETE + INSERT in one transaction) so it is always consistent.
    """

    def __init__(
        self,
        ops_repo: DuckDbOpsRepo | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._ops_repo = ops_repo or DuckDbOpsRepo()
        self._owns_ops_repo = ops_repo is None
        self._is_timeseries_map: dict[tuple[str, str, str], bool] = self._load_timeseries_map()

    def close(self) -> None:
        if self._owns_ops_repo:
            self._ops_repo.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(
        self,
        *,
        run_id: str,
        universe_from_date: date,
        today: date,
    ) -> int:
        """Recompute ops.coverage_index from ops.file_ingestions.

        Args:
            run_id: Current pipeline run ID (for log correlation).
            universe_from_date: Earliest expected data date (e.g. 1990-01-01).
            today: Date used as the expected end of coverage.

        Returns:
            Number of rows upserted into ops.coverage_index.
        """
        self._logger.info("Starting coverage index refresh", run_id=run_id)

        raw_rows = self._ops_repo.aggregate_file_ingestions_for_coverage()
        if not raw_rows:
            self._logger.info("No file_ingestions rows found; coverage index unchanged", run_id=run_id)
            return 0

        expected_days = max((today - universe_from_date).days, 1)
        updated_at = datetime.now(tz=timezone.utc)

        coverage_rows = [
            self._build_row(raw, expected_days, universe_from_date, today, updated_at)
            for raw in raw_rows
        ]

        count = self._ops_repo.upsert_coverage_index(coverage_rows)
        self._logger.info("Coverage index refreshed: %d rows", count, run_id=run_id)
        return count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_row(
        self,
        raw: dict[str, Any],
        expected_days: int,
        universe_from_date: date,
        today: date,
        updated_at: datetime,
    ) -> dict[str, Any]:
        domain: str = raw["domain"]
        source: str = raw["source"]
        dataset: str = raw["dataset"]
        is_timeseries: bool = self._is_timeseries_map.get((domain, source, dataset), True)

        min_date: date | None = raw["min_date"]
        max_date: date | None = raw["max_date"]
        total_files: int = int(raw["total_files"] or 0)
        error_count: int = int(raw["error_count"] or 0)

        coverage_ratio: float | None = None
        snapshot_count: int = 0
        last_snapshot_date: date | None = None
        age_days: int | None = None

        if is_timeseries:
            if min_date is not None and max_date is not None:
                actual_days = max((max_date - min_date).days, 0)
                coverage_ratio = round(actual_days / expected_days, 4)
        else:
            snapshot_count = total_files
            last_snapshot_date = max_date
            # Snapshot endpoints typically have no bronze date range; fall back to ingestion time
            if last_snapshot_date is None:
                last_ingested_at = raw.get("last_ingested_at")
                if last_ingested_at is not None:
                    last_snapshot_date = last_ingested_at.date() if hasattr(last_ingested_at, "date") else None
            if last_snapshot_date is not None:
                age_days = (today - last_snapshot_date).days

        return {
            "domain": domain,
            "source": source,
            "dataset": dataset,
            "discriminator": raw["discriminator"],
            "ticker": raw["ticker"],
            "min_date": min_date,
            "max_date": max_date,
            "coverage_ratio": coverage_ratio,
            "expected_start_date": universe_from_date,
            "expected_end_date": today,
            "total_files": total_files,
            "promotable_files": int(raw["promotable_files"] or 0),
            "ingestion_runs": int(raw["ingestion_runs"] or 0),
            "silver_rows_created": int(raw["silver_rows_created"] or 0),
            "silver_rows_failed": int(raw["silver_rows_failed"] or 0),
            "error_count": error_count,
            "error_rate": round(error_count / total_files, 4) if total_files > 0 else None,
            "last_ingested_at": raw["last_ingested_at"],
            "last_run_id": raw["last_run_id"],
            "snapshot_count": snapshot_count,
            "last_snapshot_date": last_snapshot_date,
            "age_days": age_days,
            "is_timeseries": is_timeseries,
            "updated_at": updated_at,
        }

    def _load_timeseries_map(self) -> dict[tuple[str, str, str], bool]:
        """Build {(domain, source, dataset): is_timeseries} from dataset_keymap.yaml.

        Uses row_date_col as the discriminator: non-null means timeseries.
        The first entry seen per (domain, source, dataset) key wins; all recipes
        for a given dataset share the same row_date_col.
        """
        try:
            result: dict[tuple[str, str, str], bool] = {}
            for raw in DatasetKeymapLoader.load_raw_datasets():
                if not isinstance(raw, dict):
                    continue
                domain = str(raw.get("domain") or "")
                source = str(raw.get("source") or "")
                dataset = str(raw.get("dataset") or "")
                if not (domain and source and dataset):
                    continue
                key = (domain, source, dataset)
                if key not in result:
                    result[key] = bool(raw.get("row_date_col"))
            return result
        except Exception as exc:
            self._logger.warning("Failed to load timeseries map from keymap: %s", exc)
            return {}


__all__ = ["CoverageIndexService"]
