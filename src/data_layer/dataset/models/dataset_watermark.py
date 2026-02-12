from dataclasses import dataclass

from data_layer.dataset.models.dataset_identity import DatasetIdentity


@dataclass(frozen=True)
class DatasetWatermark:
    """Value object whose `serialize` string becomes the gold-promotion watermark."""

    identity: DatasetIdentity
    coverage_from_date: str | None = None
    coverage_to_date: str | None = None

    def serialize(self) -> str:
        return self.identity.serialize_watermark(self.coverage_from_date, self.coverage_to_date)
