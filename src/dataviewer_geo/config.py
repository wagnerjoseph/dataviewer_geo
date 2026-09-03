"""Configuration for dataviewer_geo."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DataConfig:
    """Configuration for data paths and structure.

    Attributes:
        root: Root directory containing lookup.parquet and split folders
        lookup_file: Name of the lookup file (default: lookup.parquet)
        map_subfolder: Name of the map subfolder within each split (default: map)
        timeseries_subfolder: Name of the timeseries subfolder (default: timeseries)
    """

    root: Path
    lookup_file: str = "lookup.parquet"
    map_subfolder: str = "map"
    timeseries_subfolder: str = "timeseries"

    def __post_init__(self) -> None:
        if isinstance(self.root, str):
            self.root = Path(self.root)
        self.root = self.root.expanduser().resolve()

    @property
    def lookup_path(self) -> Path:
        """Path to the lookup file."""
        return self.root / self.lookup_file
