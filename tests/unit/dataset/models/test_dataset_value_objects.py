from __future__ import annotations

from datetime import date

from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.dataset.models.dataset_watermark import DatasetWatermark


def test_dataset_identity_watermark_serialization() -> None:
    identity = DatasetIdentity(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker="AAPL",
    )
    serialized = identity.serialize_watermark("2026-01-01", "2026-01-31")
    assert serialized == "company|fmp|company-profile||AAPL@coverage_from=2026-01-01;coverage_to=2026-01-31"

    serialized_empty = identity.serialize_watermark(None, None)
    assert serialized_empty.endswith("@coverage_from=;coverage_to=")


def test_dataset_watermark_proxy_serialization() -> None:
    identity = DatasetIdentity(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker="AAPL",
    )
    watermark = DatasetWatermark(identity=identity, coverage_from_date="2026-01-01", coverage_to_date="2026-01-31")
    assert watermark.serialize() == identity.serialize_watermark("2026-01-01", "2026-01-31")


def test_dataset_identity_watermark_serialization() -> None:
    identity = DatasetIdentity(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker="AAPL",
    )
    serialized = identity.serialize_watermark("2026-01-01", "2026-01-31")
    assert serialized == "company|fmp|company-profile||AAPL@coverage_from=2026-01-01;coverage_to=2026-01-31"

    serialized_empty = identity.serialize_watermark(None, None)
    assert serialized_empty.endswith("@coverage_from=;coverage_to=")


def test_dataset_watermark_proxy_serialization() -> None:
    identity = DatasetIdentity(
        domain="company",
        source="fmp",
        dataset="company-profile",
        discriminator="",
        ticker="AAPL",
    )
    watermark = DatasetWatermark(identity=identity, coverage_from_date="2026-01-01", coverage_to_date="2026-01-31")
    assert watermark.serialize() == identity.serialize_watermark("2026-01-01", "2026-01-31")
