from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetIdentity:
    domain: str
    source: str
    dataset: str
    discriminator: str = ""
    ticker: str = ""

    def serialize_watermark(self, coverage_from: str | None, coverage_to: str | None) -> str:
        coverage_from = "" if coverage_from is None else str(coverage_from)
        coverage_to = "" if coverage_to is None else str(coverage_to)
        discriminator = self.discriminator or ""
        ticker = self.ticker or ""
        return f"{self.domain}|{self.source}|{self.dataset}|{discriminator}|{ticker}" f"@coverage_from={coverage_from};coverage_to={coverage_to}"
