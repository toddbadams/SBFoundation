from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd

from data_layer.dtos.models import BronzeManifestRow
from data_layer.infra.result_file_adaptor import ResultFileAdapter
from data_layer.run.dtos.run_result import RunResult
from folders import Folders


@dataclass(frozen=True)
class BronzeBatchItem:
    row: BronzeManifestRow
    result: RunResult
    df_content: pd.DataFrame


class BronzeBatchReader:
    def __init__(self, result_file_adapter: ResultFileAdapter | None = None) -> None:
        self._result_file_adapter = result_file_adapter or ResultFileAdapter()

    def read(self, row: BronzeManifestRow) -> BronzeBatchItem:
        rel_path = Path(row.file_path_rel)
        abs_path = (Folders.data_absolute_path() / rel_path).resolve()
        if not abs_path.exists():
            raise FileNotFoundError(f"Bronze payload missing: {abs_path}")

        result = self._result_file_adapter.read(abs_path)
        if not isinstance(result, RunResult):
            raise ValueError(f"Bronze payload is not a RunResult: {abs_path}")

        payload = result.content or []
        if not isinstance(payload, list):
            raise ValueError(f"Bronze payload content is not a list for {row.file_path_rel}")

        df_content = pd.DataFrame(payload)
        return BronzeBatchItem(row=row, result=result, df_content=df_content)
