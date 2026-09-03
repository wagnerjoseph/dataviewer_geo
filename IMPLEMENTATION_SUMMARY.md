# Dataviewer Geo - Standalone Package Implementation

## Summary

This implementation transforms `dataviewer_geo` into a truly standalone, pip-installable package that can visualize **any geo-located timeseries dataset** through a pluggable adapter interface.

## Key Changes

### 1. Dataset Adapter Interface (`src/dataviewer_geo/datasets/`)

New adapter layer decouples the UI from specific data schemas:

- **`base.py`**: Abstract `DatasetAdapter` interface with methods:
  - `groups()` - logical partitions (formerly "splits")
  - `variables()` - map visualization variables
  - `timeseries_variables(group)` - drill-down variables
  - `location_coordinates()` - lat/lon lookup
  - `load_variable_data(var)` - map data
  - `load_timeseries(group, location_id)` - timeseries data
  - `metrics()` / `feature_importance()` - optional ML metrics

- **`backscatter.py`**: `BackscatterMLAdapter` - wraps existing `DataConfig` for backward compatibility

- **`timeseries.py`**: `GenericTimeseriesAdapter` + `TimeseriesConfig` - for arbitrary geo-timeseries datasets

### 2. Vendored Plotting Code (`src/dataviewer_geo/plotting/_vendored/`)

Removed dependency on `plotting-joseph @ git+...` by vendoring:
- `timeseries.py` - multi-panel timeseries plotting (~975 lines)
- `config.py` - `LookupTables` dataclass + constants

The vendored code handles missing optional dependencies gracefully.

### 3. Refactored Application (`src/dataviewer_geo/app.py`)

- `create_app(adapter)` - main entry point, takes `DatasetAdapter`
- `create_app_from_config(config)` - backward compatibility wrapper
- UI terminology changed: "split" → "group"
- Metrics/FI panes gracefully handle "not available" for generic datasets

### 4. Updated Package Configuration (`pyproject.toml`)

- Removed `plotting-joseph` git dependency
- Version bumped to 0.3.0
- Now fully standalone - installs with `pip install -e .`

### 5. Enhanced Documentation (`README.md`)

Comprehensive documentation including:
- Quick start with dummy data
- Backscatter ML format (existing)
- Generic timeseries format (new)
- Custom adapter examples
- Full API reference

### 6. New Examples

- `examples/01_basic_app.py` - Updated for `create_app_from_config`
- `examples/03_generic_data.py` - Generic timeseries adapter usage
- `examples/04_custom_adapter.py` - Creating custom adapters

## Usage

### Quick Start (Dummy Data)

```bash
python scripts/run_app.py --show
```

### Backscatter ML Format (Existing)

```python
from dataviewer_geo import DataConfig, create_app_from_config

config = DataConfig(root="/path/to/backscatter/data")
app = create_app_from_config(config)
app.servable()
```

### Generic Timeseries Format (New)

```python
from dataviewer_geo.datasets import GenericTimeseriesAdapter, TimeseriesConfig
from dataviewer_geo import create_app

config = TimeseriesConfig(root="/path/to/generic/data")
adapter = GenericTimeseriesAdapter(config)
app = create_app(adapter)
app.servable()
```

### Custom Adapter

```python
from dataviewer_geo.datasets import DatasetAdapter
from dataviewer_geo import create_app

class MyAdapter(DatasetAdapter):
    def groups(self) -> list[str]: ...
    def variables(self) -> list[str]: ...
    def location_coordinates(self) -> pd.DataFrame | None: ...
    def load_variable_data(self, variable: str) -> pd.DataFrame: ...
    def load_timeseries(self, group: str, location_id: int) -> pd.DataFrame | None: ...

adapter = MyAdapter(my_config)
app = create_app(adapter)
```

## Generic Data Format

Simple layout for arbitrary timeseries data:

```
data_root/
├── lookup.parquet          # location_id, lat, lon [, group]
├── group1/
│   └── data.parquet        # location_id, time, var1, var2, ...
└── group2/
    └── data.parquet        # location_id, time, var1, var2, ...
```

Configure via `TimeseriesConfig`:
```python
config = TimeseriesConfig(
    root="/path/to/data",
    lookup_file="lookup.parquet",
    id_column="location_id",
    lat_column="lat",
    lon_column="lon",
    time_column="time",
    timeseries_file_pattern="data.parquet",
)
```

## Backward Compatibility

All existing code continues to work:
- `DataConfig` unchanged
- `find_splits()`, `get_variable_names()`, etc. still available
- `create_app_from_config(config)` wraps `DataConfig` in adapter

## Testing

All 45 existing tests pass. New functionality tested via:
- `examples/03_generic_data.py`
- `examples/04_custom_adapter.py`

## Files Changed/Created

### New Files
- `src/dataviewer_geo/datasets/base.py`
- `src/dataviewer_geo/datasets/backscatter.py`
- `src/dataviewer_geo/datasets/timeseries.py`
- `src/dataviewer_geo/datasets/__init__.py`
- `src/dataviewer_geo/plotting/_vendored/timeseries.py` (vendored)
- `src/dataviewer_geo/plotting/_vendored/config.py` (vendored)
- `src/dataviewer_geo/plotting/_vendored/__init__.py`
- `examples/03_generic_data.py`
- `examples/04_custom_adapter.py`
- `IMPLEMENTATION_SUMMARY.md`

### Modified Files
- `src/dataviewer_geo/app.py` (refactored for adapter pattern)
- `src/dataviewer_geo/__init__.py` (new exports)
- `src/dataviewer_geo/plotting/timeseries.py` (use vendored module)
- `pyproject.toml` (removed git dependency)
- `README.md` (comprehensive rewrite)
- `scripts/run_app.py` (auto-detect format)
- `examples/01_basic_app.py` (updated API)
- `tests/test_app.py` (use `create_app_from_config`)

## Next Steps

1. Test with real-world datasets
2. Add more adapter implementations (netCDF, Zarr, etc.)
3. Consider publishing to PyPI
4. Add CLI entry point: `dataviewer --data /path/to/data`
