"""Generic timeseries dataset adapter.

Implements the DatasetAdapter interface for arbitrary geo-located
timeseries datasets without the ML metrics/feature importance structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .base import DatasetAdapter


@dataclass
class TimeseriesConfig:
    """Configuration for a generic timeseries dataset.

    Attributes:
        root: Root directory containing the data.
        lookup_file: Name of the lookup file with location coordinates.
        id_column: Name of location identifier column.
        lat_column: Name of latitude column.
        lon_column: Name of longitude column.
        time_column: Name of time column in timeseries files.
        group_column: Optional column name for group assignment in lookup.
        group_dir_pattern: Pattern for group subdirectories (default: group name).
        timeseries_file_pattern: Pattern for timeseries files within groups.
        map_variable: Default variable for map visualization (if in lookup).
    """

    root: Path
    lookup_file: str = "lookup.parquet"
    id_column: str = "location_id"
    lat_column: str = "lat"
    lon_column: str = "lon"
    time_column: str = "time"
    group_column: str | None = None
    group_dir_pattern: str = "{group}"
    timeseries_file_pattern: str = "data.parquet"
    map_variable: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.root, str):
            self.root = Path(self.root)
        self.root = self.root.expanduser().resolve()

    @property
    def lookup_path(self) -> Path:
        """Path to the lookup file."""
        return self.root / self.lookup_file


class GenericTimeseriesAdapter(DatasetAdapter):
    """Adapter for generic geo-located timeseries datasets.

    This adapter supports a simple data layout:
    - A lookup file with location_id, lat, lon (and optionally group)
    - Timeseries files (parquet) organized by group

    Data layout example::

        root/
        ├── lookup.parquet          # location_id, lat, lon [, group]
        ├── group1/
        │   └── data.parquet        # location_id, time, var1, var2, ...
        └── group2/
            └── data.parquet        # location_id, time, var1, var2, ...

    Or with custom naming::

        root/
        ├── locations.csv           # id, latitude, longitude
        ├── 2020_2022/
        │   └── timeseries.parquet  # id, date, temperature, precipitation
        └── 2023_2024/
            └── timeseries.parquet  # id, date, temperature, precipitation

    Args:
        config: TimeseriesConfig instance.
    """

    def __init__(self, config: TimeseriesConfig) -> None:
        self.config = config
        self._coords: pd.DataFrame | None = None
        self._groups: list[str] = []
        self._group_files: dict[str, Path] = {}
        self._ts_variables: dict[str, list[str]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load and cache metadata about groups and variables."""
        # Load coordinates
        if self.config.lookup_path.exists():
            try:
                if self.config.lookup_path.suffix == ".csv":
                    self._coords = pd.read_csv(self.config.lookup_path)
                else:
                    self._coords = pd.read_parquet(self.config.lookup_path)
            except Exception:
                self._coords = None
        else:
            self._coords = None

        # Discover groups
        self._groups = []
        self._group_files = {}

        for item in self.config.root.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                ts_file = item / self.config.timeseries_file_pattern
                if ts_file.exists():
                    self._groups.append(item.name)
                    self._group_files[item.name] = ts_file

        self._groups.sort()

        # Discover timeseries variables from first group
        if self._group_files:
            first_group = self._groups[0]
            first_file = self._group_files[first_group]
            try:
                pf = pq.ParquetFile(first_file)
                columns = set(pf.schema.names)
                exclude = {self.config.id_column, self.config.time_column}
                self._ts_variables[first_group] = sorted(columns - exclude)

                # Assume same variables across groups
                for g in self._groups[1:]:
                    self._ts_variables[g] = self._ts_variables[first_group]
            except Exception:
                self._ts_variables[first_group] = []

    def groups(self) -> list[str]:
        """Return list of available groups."""
        return self._groups

    def variables(self, group: str | None = None) -> list[str]:
        """Return list of map variables.

        For generic datasets, this returns timeseries variables
        (aggregated to a single value per location for mapping).
        """
        if not self._groups:
            return []
        g = group if (group and group in self._groups) else self._groups[0]
        return self._ts_variables.get(g, self._ts_variables.get(self._groups[0], []))

    def timeseries_variables(self, group: str | None = None) -> list[str]:
        """Return list of timeseries variables for a group."""
        if group is None:
            group = self._groups[0] if self._groups else None
        if group is None:
            return []
        return self._ts_variables.get(group, [])

    def location_coordinates(self) -> pd.DataFrame | None:
        """Load location coordinates."""
        if self._coords is None:
            return None

        # Ensure required columns exist
        required = [self.config.id_column, self.config.lat_column, self.config.lon_column]
        if not all(col in self._coords.columns for col in required):
            return None

        return self._coords[[self.config.id_column, self.config.lon_column, self.config.lat_column]].copy()

    def load_variable_data(self, variable: str, group: str | None = None) -> pd.DataFrame:
        """Load variable data for map visualization.

        For generic datasets, this computes the mean of the variable
        across time for each location in the selected group.
        """
        if self._coords is None or not self._groups:
            return pd.DataFrame()

        # Use the selected group, defaulting to the first
        g = group if (group and group in self._groups) else self._groups[0]
        ts_file = self._group_files.get(g)
        if ts_file is None:
            return pd.DataFrame()

        try:
            ts_data = pd.read_parquet(ts_file)
        except Exception:
            return pd.DataFrame()

        if variable not in ts_data.columns:
            return pd.DataFrame()

        # Compute mean per location
        aggregated = ts_data.groupby(self.config.id_column)[variable].mean().reset_index()

        # Merge with coordinates
        coords = self.location_coordinates()
        if coords is None:
            return aggregated

        merged = aggregated.merge(coords, on=self.config.id_column, how="left")
        return merged.dropna(subset=[self.config.lon_column, self.config.lat_column])

    def load_timeseries(self, group: str, location_id: int) -> pd.DataFrame | None:
        """Load timeseries for a location."""
        ts_file = self._group_files.get(group)
        if ts_file is None:
            return None

        try:
            ts_data = pd.read_parquet(ts_file)
        except Exception:
            return None

        loc_data = ts_data[ts_data[self.config.id_column] == location_id]
        if loc_data.empty:
            return None

        return loc_data.copy()

    def resolve_tile(self, group: str, location_id: int) -> str | None:
        """Return group as tile identifier (for API compatibility)."""
        return group

    # ------------------------------------------------------------------
    # Dataset schema metadata
    # ------------------------------------------------------------------

    @property
    def id_column(self) -> str:
        return self.config.id_column

    @property
    def time_column(self) -> str:
        return self.config.time_column
