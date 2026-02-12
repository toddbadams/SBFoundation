from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
import logging

from data_layer.dataset.models.dataset_recipe import DatasetRecipe
from data_layer.run.dtos.run_context import RunContext


ChunkProcessor = Callable[[list[DatasetRecipe], RunContext], RunContext]
Promotion = Callable[[RunContext], RunContext]


@dataclass
class OrchestrationTickerChunkService:
    chunk_size: int
    logger: logging.Logger
    process_chunk: ChunkProcessor
    promote_silver: Promotion
    silver_enabled: bool

    def process(self, recipes: Sequence[DatasetRecipe], run_summary: RunContext) -> RunContext:
        if not recipes:
            return run_summary

        total_chunks = ((len(recipes) + self.chunk_size - 1) // self.chunk_size) if self.chunk_size > 0 else 1
        for chunk_index, chunk in enumerate(self._chunk_batches(recipes), start=1):
            if not chunk:
                continue

            label = self._chunk_dataset_label(chunk)
            self.logger.info(
                "Starting ticker chunk %s/%s (%s recipes%s)",
                chunk_index,
                total_chunks or 1,
                len(chunk),
                f" datasets={label}" if label else "",
            )
            run_summary = self.process_chunk(list(chunk), run_summary)
            self.logger.info(
                "Finished ticker chunk %s/%s (%s recipes%s)",
                chunk_index,
                total_chunks or 1,
                len(chunk),
                f" datasets={label}" if label else "",
            )

            if self.silver_enabled and run_summary.bronze_files_passed:
                run_summary = self.promote_silver(run_summary)

        return run_summary

    def _chunk_batches(self, recipes: Sequence[DatasetRecipe]) -> Iterable[Sequence[DatasetRecipe]]:
        size = self.chunk_size
        if size <= 0:
            yield recipes
            return

        for index in range(0, len(recipes), size):
            yield recipes[index : index + size]

    def _chunk_dataset_label(self, chunk: Sequence[DatasetRecipe]) -> str:
        datasets = sorted({recipe.dataset for recipe in chunk if recipe.dataset})
        if not datasets:
            return ""
        if len(datasets) == 1:
            return datasets[0]
        return f"{datasets[0]}-{datasets[-1]}"
