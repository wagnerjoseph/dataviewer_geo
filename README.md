# dataviewer_geo

Interactive geospatial timeseries data viewer for Earth observation data.

---

## Quick Start — Run the Viewer

> If you don't provide a data path, the app **automatically creates a dummy
> dataset** and serves it. No setup required.

### Install (once)

```bash
uv sync        # or: pip install -e .
```

### Run it — no data path (auto dummy data)

```bash
python scripts/run_app.py
```

Wait until you see:

```
No data path provided; generating a dummy dataset at /tmp/dataviewer_demo_data...
Viewer running at:  http://localhost:5000
```

Then **open http://localhost:5000 in your browser**.

To open the browser automatically, add `--show`:

```bash
python scripts/run_app.py --show
```

### Point it at your own data

```bash
python scripts/run_app.py --data /path/to/your/data
```

The data format (backscatter ML vs. generic timeseries) is **auto-detected**.
Force it with `--format backscatter|generic`, or change the port with
`--port <n>`:

```bash
python scripts/run_app.py --data /path/to/your/data --port 5006
```

### Alternative: `panel serve` (production / many apps)

```bash
# Dummy data
panel serve scripts/serve_app.py --port 5006

# Your own data (auto-detect format)
DATAVIEWER_DATA=/path/to/your/data panel serve scripts/serve_app.py --port 5006
```

Serve-mode apps are registered at `http://localhost:5006/serve_app`.

### What you should see

A page with a **map** (OSM basemap with colored points), selectors for
**Group** and **Variable**, a **Location ID** box, and a **Timeseries
Configuration** accordion.

1. Pick a variable in the **Variable** dropdown → the map recolors.
2. **Click a point** on the map (or type a Location ID) → the timeseries
   figure opens below.
3. Expand **Timeseries Configuration** to add/arrange plot panels
   ("+ Add subplot", "+ Add variable") — changes re-render live.

### Troubleshooting

- **Nothing appears / no browser opens** → ignore `--show` and just open the
  printed URL (`http://localhost:5000`) manually in your browser.
- **"Port 5000 is already in use"** → a previous instance is still running (or
  another app took the port). Pick a new port: `python scripts/run_app.py --port 5010`.
- **Blank page** → you are likely serving with `panel serve scripts/run_app.py`.
  That script must be launched with `python`, not `panel serve` (see option 3
  for the correct `panel serve` target, `scripts/serve_app.py`).
- **No data path, and you want a fresh dummy dataset** → a fresh dummy dataset is
  generated on every launch in `/tmp/dataviewer_demo_data` (any old one is
  cleared first), so nothing else needed.

---

## Features

- **Interactive Map**: GeoViews map with OSM basemap, clickable points, highlight markers
- **Timeseries Visualization**: Multi-panel timeseries with configurable `var_specs`
- **Interactive var_specs Editor**: configure plots without code (variables, overlays, secondary axes, thresholds, seasons)
- **Feature Importance** bar charts and **Metrics** comparison table (when the dataset provides them)
- **Pluggable Adapters**: `DatasetAdapter` interface supports any geo-timeseries data format
- **Auto-Discovery**: groups, variables, and locations discovered from data files

## Installation

```bash
git clone https://github.com/wagnerjoseph/dataviewer_geo.git
cd dataviewer_geo
uv sync          # or: pip install -e .
```

## How it works

The viewer is driven by a **`DatasetAdapter`**. `create_app(adapter)` renders
the UI and calls back into your adapter for data. Adapters for two formats are
bundled; you can write your own.

### Programmatic usage

```python
from dataviewer_geo import build_viewer

app = build_viewer()                    # dummy data
app = build_viewer("/path/to/data")     # auto-detect format
app.servable()
```

```python
from dataviewer_geo import create_app
from dataviewer_geo.datasets import BackscatterMLAdapter, GenericTimeseriesAdapter, TimeseriesConfig

from dataviewer_geo.config import DataConfig

# Backscatter ML format
config = DataConfig(root="/path/to/backscatter/data")
adapter = BackscatterMLAdapter(config)

# OR generic timeseries format
adapter = GenericTimeseriesAdapter(TimeseriesConfig(root="/path/to/generic/data"))

app = create_app(adapter)
app.servable()
```

## Data Formats

### Format 1: Backscatter ML

For ML model-evaluation data (splits, metrics, feature importance):

```
data_root/
├── ers_tile_id_location_id.parquet    # location_id, lat, lon, tile_id
└── split_1/
    ├── metrics_global_plot/           # <var>.parquet  (map variables)
    ├── metrics_by_tile/               # <tile>.parquet (per-location metrics)
    ├── feature_importance/            # <model>/<tile>.parquet
    └── timeseries/                    # <tile>.parquet (drill-down data)
```

```python
from dataviewer_geo import DataConfig
from dataviewer_geo.datasets import BackscatterMLAdapter

adapter = BackscatterMLAdapter(DataConfig(root="/path/to/data"))
```

### Format 2: Generic Timeseries

Any geo-located timeseries with no ML structure:

```
data_root/
├── lookup.parquet          # location_id, lat, lon [, group]
├── group1/
│   └── data.parquet        # location_id, time, var1, var2, ...
└── group2/
    └── data.parquet        # location_id, time, var1, var2, ...
```

Configure via `TimeseriesConfig` (all names configurable):

```python
from dataviewer_geo.datasets import GenericTimeseriesAdapter, TimeseriesConfig

config = TimeseriesConfig(
    root="/path/to/data",
    lookup_file="lookup.parquet",            # default
    id_column="location_id",                 # default
    lat_column="lat",                        # default
    lon_column="lon",                        # default
    time_column="time",                      # default
    timeseries_file_pattern="data.parquet",  # default
)
adapter = GenericTimeseriesAdapter(config)
```

### Custom format: write your own adapter

```python
from dataviewer_geo.datasets import DatasetAdapter
import pandas as pd

class MyAdapter(DatasetAdapter):
    def groups(self) -> list[str]: ...
    def variables(self) -> list[str]: ...
    def location_coordinates(self) -> pd.DataFrame | None: ...
    def load_variable_data(self, variable: str) -> pd.DataFrame: ...
    def load_timeseries(self, group: str, location_id: int) -> pd.DataFrame | None: ...

app = create_app(MyAdapter(config))
```

`metrics()` and `feature_importance()` are optional — return `None` (the
default) and the corresponding panes show "not available".

## Using the var_specs Editor

1. Expand the **Timeseries Configuration** accordion below the main widgets.
2. **+ Add subplot** → create a new panel.
3. **+ Add variable** → overlay variables on a panel.
4. Configure each variable (name, label, color; advanced options for line
   width, alpha, plot style, seasons, thresholds are in a collapsed accordion).
5. For overlays: secondary-axis and zero-alignment toggles are available.

Changes re-render the current location's timeseries automatically.

## Scripts

- `scripts/run_app.py` — direct Python launch (`python scripts/run_app.py --data ... --show`)
- `scripts/serve_app.py` — target for `panel serve` (uses `DATAVIEWER_DATA`/`DATAVIEWER_FORMAT` env vars)
- `scripts/generate_dummy_data.py` — generate sample data manually

## API Reference

```python
from dataviewer_geo import (
    create_app,            # create app from a DatasetAdapter
    create_app_from_config,# create app from a DataConfig (backward compat)
    build_viewer,          # create app from a path (auto dummy if None)
    detect_data_format,    # 'backscatter' | 'generic'
    DataConfig,
    VarSpecEditor,
)
from dataviewer_geo.datasets import (
    DatasetAdapter,
    BackscatterMLAdapter,
    GenericTimeseriesAdapter,
    TimeseriesConfig,
)
```

Legacy data-loading helpers (`find_splits`, `load_timeseries_for_location`, ...)
remain available for backward compatibility.

## Development

```bash
uv run pytest tests/ -v          # run tests
uv run ruff check src/ tests/    # lint
uv run ruff format src/ tests/   # format
```

## Dependencies

`panel`, `holoviews`, `geoviews`, `bokeh`, `pandas`, `numpy`, `matplotlib`, `pyarrow`

## License

MIT — see LICENSE file.

## Contact

Joseph Wagner — joseph.wagner@geo.tuwien.ac.at
TU Wien, Institute of Geodesy and Geoinformation
