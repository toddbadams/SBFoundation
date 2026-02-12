from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromotionConfig:
    chunk_strategy: str = "none"  # none | year | month
    chunk_key: str = "key_date"
    max_rows_per_chunk: int = 200_000
    use_duckdb_engine: bool = True
    dedupe_mode: str = "anti_join"  # anti_join | hash_only | none
    watermark_mode: str = "max_key_date"  # max_key_date | bronze_file_only | none
    write_partitioning: list[str] = field(default_factory=list)
    row_group_size: int | None = None
