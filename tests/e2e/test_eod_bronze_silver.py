"""E2E test: EOD bulk Bronze -> Silver pipeline using fixture data."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from tests.e2e.conftest import FIXTURES_DIR

# Skip if fixture not present
pytestmark = pytest.mark.skipif(
    not (FIXTURES_DIR / "v4" / "batch-request" / "end-of-day-prices.json").exists(),
    reason="EOD bulk fixture not present (tests/e2e/fixtures/fmp/v4/batch-request/end-of-day-prices.json)",
)


def test_eod_bulk_dto_parses_fixture():
    """EodBulkPriceDTO.from_row parses the fixture correctly."""
    import json
    from sbfoundation.dtos.eod.eod_bulk_price_dto import EodBulkPriceDTO

    fixture_path = FIXTURES_DIR / "v4" / "batch-request" / "end-of-day-prices.json"
    rows = json.loads(fixture_path.read_text())
    assert len(rows) > 0

    for row in rows:
        dto = EodBulkPriceDTO.from_row(row)
        assert dto.symbol
        assert dto.date is not None
        assert dto.close is not None


def test_company_profile_bulk_dto_parses_fixture():
    """EodBulkCompanyProfileDTO.from_row parses the fixture correctly."""
    import json
    from sbfoundation.dtos.eod.eod_bulk_company_profile_dto import EodBulkCompanyProfileDTO

    fixture_path = FIXTURES_DIR / "v4" / "profile" / "all.json"
    rows = json.loads(fixture_path.read_text())
    assert len(rows) > 0

    for row in rows:
        dto = EodBulkCompanyProfileDTO.from_row(row)
        assert dto.symbol
        assert dto.company_name
