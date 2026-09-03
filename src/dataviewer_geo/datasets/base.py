"""Base dataset adapter interface for dataviewer_geo.

Defines the abstract interface that all dataset adapters must implement.
This decouples the UI (app.py) from specific data schemas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DatasetAdapter(ABC):
    """Abstract base class for dataset adapters.

    Implement this interface to support new data formats in dataviewer_geo.

    The adapter pattern allows the UI to work with any geo-located timeseries
    dataset without knowing the specific file structure or schema.
    """

    @abstractmethod
    def groups(self) -> list[str]:
        """Return list of available groups (formerly 'splits').

        A group is a logical partition of the data, e.g., a time period,
        experimental condition, or geographic region.

        Returns:
            List of group names.
        """
        pass

    @abstractmethod
    def variables(self, group: str | None = None) -> list[str]:
        """Return list of variables available for map visualization.

        These are typically aggregated metrics (e.g., mean, RMSE) that can
        be displayed as colored points on the map.

        Args:
            group: Optional group name to restrict the variable list to.

        Returns:
            List of variable names.
        """
        pass

    def timeseries_variables(self, group: str | None = None) -> list[str]:
        """Return list of variables available in timeseries data.

        These variables can be configured in the var_specs editor for
        drill-down timeseries visualization.

        Args:
            group: Optional group name to filter variables.

        Returns:
            List of variable names available in timeseries.
        """
        # Default: same as map variables
        return self.variables(group)

    @abstractmethod
    def location_coordinates(self) -> pd.DataFrame | None:
        """Load location coordinates.

        Returns:
            DataFrame with columns: location_id, lat, lon [, tile_id/group]
            or None if no location data is available.
        """
        pass

    @abstractmethod
    def load_variable_data(self, variable: str, group: str | None = None) -> pd.DataFrame:
        """Load data for a map variable.

        Args:
            variable: Name of the variable to load.
            group: Optional group name to load data for.

        Returns:
            DataFrame with columns: location_id, <variable>, lat, lon
        """
        pass

    @abstractmethod
    def load_timeseries(self, group: str, location_id: int) -> pd.DataFrame | None:
        """Load timeseries data for a specific location.

        Args:
            group: Group name (e.g., split/period).
            location_id: Location identifier.

        Returns:
            DataFrame with columns: location_id, time, <variables>
            or None if data is not available.
        """
        pass

    def metrics(
        self,
        group: str,
        location_id: int,
        tile_id: str | None = None,
    ) -> dict[str, dict[str, float]] | None:
        """Load model metrics for a location (optional).

        Args:
            group: Group name.
            location_id: Location identifier.
            tile_id: Optional tile identifier for indexing.

        Returns:
            Nested dict: {model_name: {metric: value}} or None if not supported.
        """
        return None

    def feature_importance(
        self,
        group: str,
        location_id: int,
        tile_id: str | None = None,
    ) -> dict[str, pd.Series] | None:
        """Load feature importance data for a location (optional).

        Args:
            group: Group name.
            location_id: Location identifier.
            tile_id: Optional tile identifier for indexing.

        Returns:
            Dict: {model_name: Series of feature importances} or None.
        """
        return None

    def resolve_tile(self, group: str, location_id: int) -> str | None:
        """Resolve the tile ID for a location (optional indexing hint).

        Args:
            group: Group name.
            location_id: Location identifier.

        Returns:
            Tile ID string or None if not applicable.
        """
        return None

    # ------------------------------------------------------------------
    # Dataset schema metadata (column names used by the UI)
    # ------------------------------------------------------------------

    @property
    def id_column(self) -> str:
        """Name of the location identifier column in returned dataframes."""
        return "location_id"

    @property
    def time_column(self) -> str:
        """Name of the time column in returned timeseries dataframes."""
        return "time"

    @property
    def metric_models(self) -> dict | None:
        """Metric model configuration, if the dataset provides metrics."""
        return None

    @property
    def fi_col_prefix(self) -> str:
        """Prefix for feature-importance columns, if provided."""
        return "fi_"
