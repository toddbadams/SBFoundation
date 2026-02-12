from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class BronzeManifestRow:
    bronze_file_id: str
    run_id: str | None
    domain: str
    source: str
    dataset: str
    discriminator: str
    ticker: str
    file_path_rel: str
    coverage_from_date: date | None
    coverage_to_date: date | None
    ingested_at: datetime
