from dataclasses import dataclass

from data_layer.dataset.models.dataset_identity import DatasetIdentity
from data_layer.dataset.models.dataset_keymap_entry import DatasetKeymapEntry


@dataclass(frozen=True)
class DatasetKeymap:
    version: int
    entries: tuple[DatasetKeymapEntry, ...]

    def find(self, identity: DatasetIdentity) -> DatasetKeymapEntry | None:
        for entry in self.entries:
            if entry.matches_identity(identity):
                return entry
        return None

    def require(self, identity: DatasetIdentity) -> DatasetKeymapEntry:
        entry = self.find(identity)
        if entry is None:
            raise KeyError(f"Missing dataset keymap entry for {identity}")
        return entry
