# dataviewer_geo

Interactive geospatial timeseries data viewer for Earth observation data.

## Features

- **Interactive Map**: GeoViews-based map with clickable points for location selection
- **Timeseries Display**: Integrated with `plotting_joseph` for publication-quality timeseries plots
- **Auto-Discovery**: Automatically discovers splits, variables, and locations from data files
- **Panel UI**: Clean, responsive web interface built with Panel

## Installation

```bash
# Clone the repository
git clone https://github.com/wagnerjoseph/dataviewer_geo.git
cd dataviewer_geo

# Set up virtual environment with uv
uv sync

# Install in development mode
uv pip install -e .
```

## Quick Start

### Using Dummy Data

```python
from pathlib import Path
from dataviewer_geo import generate_dummy_data, create_app

# Generate sample data
data_root = Path("/tmp/test_data")
generate_dummy_data(data_root, n_locations=100, n_tiles=4)

# Create and launch the app
from dataviewer_geo.config import DataConfig
config = DataConfig(root=data_root)
app = create_app(config)
app.servable()
```

### Using Your Own Data

Structure your data as follows:

```
data_root/
├── lookup.parquet            # location_id, lat, lon, tile_id
├── split_1/
│   ├── map/
│   │   ├── tile_0.parquet    # location_id, lat, lon, var1, var2, ...
│   │   └── tile_1.parquet
│   └── timeseries/
│       ├── tile_0.parquet    # location_id, time, var1, var2, ...
│       └── tile_1.parquet
└── split_2/
    ├── map/
    │   └── ...
    └── timeseries/
        └── ...
```

```python
from dataviewer_geo import DataConfig, create_app

config = DataConfig(root=Path("/path/to/your/data"))
app = create_app(config)
app.servable()
```

### Running the App

```bash
# Serve the app
panel serve scripts/run_app.py --show

# Or programmatically
python -c "from dataviewer_geo import create_app, DataConfig; app = create_app(DataConfig('/path/to/data')); app.show()"
```

## API Reference

### Data Loading

```python
from dataviewer_geo import DataIndex, DataConfig

config = DataConfig(root="/path/to/data")
index = DataIndex(config)

# Discover available splits
print(index.splits)

# Discover available variables
print(index.map_variables)
print(index.timeseries_variables)

# Get locations for a split
locations = index.get_locations_for_split("split_1")
```

### Loading Data

```python
from dataviewer_geo import load_map_variable, load_timeseries_for_location

# Load map data
map_data = load_map_variable(config, "split_1", "backscatter")

# Load timeseries for a location
ts_data = load_timeseries_for_location(
    config,
    "split_1",
    location_id=123,
    variables=["backscatter", "lai"],
)
```

### Plotting

```python
from dataviewer_geo import create_interactive_map, plot_location_timeseries

# Create interactive map
map_plot = create_interactive_map(
    data=map_df,
    variable="backscatter",
    width=800,
    height=600,
)

# Create timeseries plot
fig = plot_location_timeseries(
    data=ts_df,
    variables=["backscatter", "lai"],
    location_id=123,
    split_name="split_1",
)
```

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

### Code Quality

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Generating Dummy Data

```bash
uv run python scripts/generate_dummy_data.py --output /tmp/test_data --locations 100
```

## Examples

See the `examples/` directory for complete examples:

- `examples/01_basic_app.py` - Basic app usage
- `examples/02_api_usage.py` - Using the API programmatically

## Dependencies

- `panel` - Web application framework
- `holoviews` - Declarative objects for data visualization
- `geoviews` - Geospatial extensions for HoloViews
- `bokeh` - Interactive visualization library
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `matplotlib` - Plotting
- `pyarrow` - Fast parquet I/O
- `plotting_joseph` - Timeseries plotting functions

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

## Contact

Joseph Wagner - joseph.wagner@geo.tuwien.ac.at

TU Wien, Institute of Geodesy and Geoinformation
