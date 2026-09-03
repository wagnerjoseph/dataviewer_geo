"""dataviewer_geo - Interactive geospatial timeseries data viewer.

Provides an interactive Panel/GeoViews application for exploring
spatiotemporal Earth observation data with automatic discovery of
splits, variables, and locations from parquet files.
"""

from .config import DataConfig
from .data import (
    DataIndex,
    find_splits,
    generate_dummy_data,
    load_map_variable,
    load_timeseries_for_location,
)
from .plotting import plot_location_timeseries
from .app import create_app

__version__ = "0.1.0"

__all__ = [
    "DataConfig",
    "DataIndex",
    "create_app",
    "find_splits",
    "generate_dummy_data",
    "load_map_variable",
    "load_timeseries_for_location",
    "plot_location_timeseries",
]
