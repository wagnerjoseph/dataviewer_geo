"""dataviewer_geo - Interactive geospatial timeseries data viewer.

Provides an interactive Panel/GeoViews application for exploring
spatiotemporal Earth observation data. Supports multiple data formats
via the DatasetAdapter interface.

Features:
- Interactive map with click-to-select location
- Timeseries with interactive var_specs editor
- Feature importance bar charts (when available)
- Metrics comparison table (when available)
- Auto-discovery of data structure
- Pluggable dataset adapters for different data formats

Quick Start::

    from dataviewer_geo import create_app, DataConfig
    from dataviewer_geo.datasets import GenericTimeseriesAdapter, TimeseriesConfig

    # For backscatter ML data (existing format)
    config = DataConfig(root="/path/to/data")
    app = create_app(config)  # or create_app_from_config(config)

    # For generic timeseries data
    ts_config = TimeseriesConfig(root="/path/to/generic/data")
    adapter = GenericTimeseriesAdapter(ts_config)
    app = create_app(adapter)

    # Serve the app
    app.servable()
"""

from .config import DataConfig
from .data import (
    DataIndex,
    find_splits,
    get_variable_names,
    load_location_coordinates,
    load_variable_data,
    load_timeseries_for_location,
    load_feature_importance_for_location,
    load_metrics_from_tile,
    get_timeseries_variables,
    generate_dummy_data,
)
from .var_spec_editor import VarSpecEditor, create_var_spec_editor
from .app import create_app, create_app_from_config, build_viewer, detect_data_format
from .datasets import (
    DatasetAdapter,
    BackscatterMLAdapter,
    GenericTimeseriesAdapter,
    TimeseriesConfig,
)

__version__ = "0.3.0"

__all__ = [
    # Core API
    "DataConfig",
    "DataIndex",
    "VarSpecEditor",
    "create_app",
    "create_app_from_config",
    "build_viewer",
    "detect_data_format",
    "create_var_spec_editor",
    # Dataset adapters
    "DatasetAdapter",
    "BackscatterMLAdapter",
    "GenericTimeseriesAdapter",
    "TimeseriesConfig",
    # Backward compatibility - data loading functions
    "find_splits",
    "get_variable_names",
    "load_location_coordinates",
    "load_variable_data",
    "load_timeseries_for_location",
    "load_feature_importance_for_location",
    "load_metrics_from_tile",
    "get_timeseries_variables",
    "generate_dummy_data",
]
