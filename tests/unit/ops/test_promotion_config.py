from sbfoundation.ops.requests.promotion_config import PromotionConfig


def test_promotion_config_custom_values_preserved() -> None:
    cfg = PromotionConfig(
        chunk_strategy="year",
        dedupe_mode="hash_only",
        watermark_mode="bronze_file_only",
        row_group_size=1_000,
        use_duckdb_engine=False,
    )
    assert cfg.chunk_strategy == "year"
    assert cfg.dedupe_mode == "hash_only"
    assert cfg.watermark_mode == "bronze_file_only"
    assert cfg.row_group_size == 1_000
    assert cfg.use_duckdb_engine is False
