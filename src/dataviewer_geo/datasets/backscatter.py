"""Backscatter ML dataset adapter.

Implements the DatasetAdapter interface for the existing backscatter
analysis data format (splits, metrics, feature importance, timeseries).
"""

from __future__ import annotations

import pandas as pd

from ..config import DataConfig
from ..data import (
    DataIndex,
    get_variable_names,
    load_location_coordinates,
    load_variable_data,
    load_timeseries_for_location,
    load_feature_importance_for_location,
    load_metrics_from_tile,
    get_timeseries_variables,
)
from .base import DatasetAdapter


class BackscatterMLAdapter(DatasetAdapter):
    """Adapter for the backscatter ML analysis data format.

    This adapter wraps the existing DataConfig and data.py functions
    to implement the DatasetAdapter interface. It supports:
    - Multiple splits (time periods)
    - Map variables from metrics_global_plot
    - Timeseries with multiple variables
    - Model metrics (RMSE, MAE, Pearson)
    - Feature importance for multiple models

    Args:
        config: DataConfig instance pointing to the data root.
    """

    def __init__(self, config: DataConfig) -> None:
        self.config = config
        self._index = DataIndex(config)
        self._coords: pd.DataFrame | None = None
        self._load_coords()

    def _load_coords(self) -> None:
        """Pre-load location coordinates."""
        try:
            self._coords = load_location_coordinates(self.config)
        except Exception:
            self._coords = None

    def groups(self) -> list[str]:
        """Return list of available splits."""
        return self._index.splits

    def _resolve_group(self, group: str | None) -> str | None:
        """Return the group to use, defaulting to the last split."""
        if group is None:
            return self._index.splits[-1] if self._index.splits else None
        return group if group in self._index.splits else None

    def variables(self, group: str | None = None) -> list[str]:
        """Return list of map variables from metrics_global_plot."""
        split = self._resolve_group(group)
        if split is None:
            return []
        return get_variable_names(self.config, split)

    def timeseries_variables(self, group: str | None = None) -> list[str]:
        """Return list of timeseries variables."""
        split = self._resolve_group(group)
        if split is None:
            return []
        return get_timeseries_variables(self.config, split)

    def location_coordinates(self) -> pd.DataFrame | None:
        """Load location coordinates."""
        return self._coords

    def load_variable_data(self, variable: str, group: str | None = None) -> pd.DataFrame:
        """Load variable data for map visualization."""
        split = self._resolve_group(group)
        if split is None:
            return pd.DataFrame()
        return load_variable_data(self.config, split, variable)

    def load_timeseries(self, group: str, location_id: int) -> pd.DataFrame | None:
        """Load timeseries for a location."""
        tile_id = self.resolve_tile(group, location_id)
        return load_timeseries_for_location(
            self.config, group, location_id, tile_id
        )

    def metrics(
        self,
        group: str,
        location_id: int,
        tile_id: str | None = None,
    ) -> dict[str, dict[str, float]] | None:
        """Load model metrics for a location."""
        if tile_id is None:
            tile_id = self.resolve_tile(group, location_id)
        if tile_id is None:
            return None
        return load_metrics_from_tile(self.config, group, tile_id, location_id)

    def feature_importance(
        self,
        group: str,
        location_id: int,
        tile_id: str | None = None,
    ) -> dict[str, pd.Series] | None:
        """Load feature importance for a location."""
        if tile_id is None:
            tile_id = self.resolve_tile(group, location_id)
        if tile_id is None:
            return None
        fi_data = load_feature_importance_for_location(
            self.config, group, location_id, tile_id
        )
        if fi_data is None:
            return None
        # Convert to Series format
        return {k: v for k, v in fi_data.items()}

    def resolve_tile(self, group: str, location_id: int) -> str | None:
        """Resolve tile ID for a location."""
        if self._coords is None:
            return None
        matching = self._coords[self._coords[self.config.id_column] == location_id]
        if matching.empty:
            return None
        return str(matching[self.config.tile_col].iloc[0])

    # ------------------------------------------------------------------
    # Dataset schema metadata
    # ------------------------------------------------------------------

    @property
    def id_column(self) -> str:
        return self.config.id_column

    @property
    def time_column(self) -> str:
        return "time"

    @property
    def metric_models(self) -> dict | None:
        return self.config.metric_models

    @property
    def fi_col_prefix(self) -> str:
        return self.config.fi_col_prefix
