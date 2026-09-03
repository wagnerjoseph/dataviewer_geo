"""Dataset adapters for dataviewer_geo.

This module provides adapters that decouple the UI from specific data schemas.
Implement the DatasetAdapter interface to support new data formats.

Example::

    from dataviewer_geo.datasets import BackscatterMLAdapter, GenericTimeseriesAdapter
    from dataviewer_geo.config import DataConfig
    from dataviewer_geo.datasets.timeseries import TimeseriesConfig

    # Backscatter ML data
    config = DataConfig(root="/path/to/backscatter/data")
    adapter = BackscatterMLAdapter(config)

    # Generic timeseries data
    ts_config = TimeseriesConfig(
        root="/path/to/generic/data",
        lookup_file="locations.parquet",
        id_column="station_id",
    )
    adapter = GenericTimeseriesAdapter(ts_config)
"""

from .base import DatasetAdapter
from .backscatter import BackscatterMLAdapter
from .timeseries import GenericTimeseriesAdapter, TimeseriesConfig

__all__ = [
    "DatasetAdapter",
    "BackscatterMLAdapter",
    "GenericTimeseriesAdapter",
    "TimeseriesConfig",
]
