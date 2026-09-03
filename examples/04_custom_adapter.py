#!/usr/bin/env python3
"""Example: Creating a custom dataset adapter.

This example shows how to implement a custom DatasetAdapter
to support your own data format.
"""

from pathlib import Path
import pandas as pd
import numpy as np

from dataviewer_geo import create_app
from dataviewer_geo.datasets import DatasetAdapter


class SimpleCSVAdapter(DatasetAdapter):
    """Custom adapter for simple CSV-based timeseries data.

    Data format:
        data_root/
        ├── locations.csv         # id, latitude, longitude
        └── timeseries.csv        # id, date, value1, value2, ...

    This is a minimal example - real adapters would be more sophisticated.
    """

    def __init__(self, data_root: Path) -> None:
        self.data_root = Path(data_root)
        self._locations: pd.DataFrame | None = None
        self._timeseries: pd.DataFrame | None = None
        self._load_data()

    def _load_data(self) -> None:
        """Load location and timeseries data."""
        # Load locations
        loc_file = self.data_root / "locations.csv"
        if loc_file.exists():
            self._locations = pd.read_csv(loc_file)
            # Standardize column names
            self._locations = self._locations.rename(columns={
                'id': 'location_id',
                'latitude': 'lat',
                'longitude': 'lon',
            })
        else:
            self._locations = None

        # Load timeseries
        ts_file = self.data_root / "timeseries.csv"
        if ts_file.exists():
            self._timeseries = pd.read_csv(ts_file)
            self._timeseries = self._timeseries.rename(columns={
                'id': 'location_id',
                'date': 'time',
            })
            self._timeseries['time'] = pd.to_datetime(self._timeseries['time'])
        else:
            self._timeseries = None

    def groups(self) -> list[str]:
        """Return list of groups (single group for this format)."""
        return ["all"] if self._timeseries is not None else []

    def variables(self) -> list[str]:
        """Return map variables (mean of each timeseries variable)."""
        if self._timeseries is None:
            return []
        # Exclude id and time columns
        exclude = {'location_id', 'time'}
        return [c for c in self._timeseries.columns if c not in exclude]

    def timeseries_variables(self, group: str | None = None) -> list[str]:
        """Return timeseries variables."""
        return self.variables()

    def location_coordinates(self) -> pd.DataFrame | None:
        """Return location coordinates."""
        if self._locations is None:
            return None
        return self._locations[['location_id', 'lon', 'lat']].copy()

    def load_variable_data(self, variable: str) -> pd.DataFrame:
        """Load variable data (mean per location)."""
        if self._timeseries is None or self._locations is None:
            return pd.DataFrame()

        if variable not in self._timeseries.columns:
            return pd.DataFrame()

        # Compute mean per location
        aggregated = self._timeseries.groupby('location_id')[variable].mean().reset_index()

        # Merge with coordinates
        merged = aggregated.merge(self._locations, on='location_id', how='left')
        return merged.dropna(subset=['lon', 'lat'])

    def load_timeseries(self, group: str, location_id: int) -> pd.DataFrame | None:
        """Load timeseries for a location."""
        if self._timeseries is None:
            return None

        loc_data = self._timeseries[self._timeseries['location_id'] == location_id]
        if loc_data.empty:
            return None

        return loc_data.copy()


def create_example_data(data_root: Path) -> None:
    """Create example CSV data."""
    data_root.mkdir(parents=True, exist_ok=True)

    # Create locations
    n_locations = 30
    locations_df = pd.DataFrame({
        'id': range(n_locations),
        'latitude': np.random.uniform(45, 55, n_locations),
        'longitude': np.random.uniform(10, 20, n_locations),
    })
    locations_df.to_csv(data_root / 'locations.csv', index=False)

    # Create timeseries
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    rows = []
    for loc_id in range(n_locations):
        for date in dates:
            rows.append({
                'id': loc_id,
                'date': date,
                'value1': np.random.randn() + 10,
                'value2': np.random.randn() * 5 + 50,
            })

    ts_df = pd.DataFrame(rows)
    ts_df.to_csv(data_root / 'timeseries.csv', index=False)
    print(f"Created example CSV data at {data_root}")


def main() -> None:
    """Main entry point."""
    # Create example data
    data_root = Path("/tmp/dataviewer_custom_adapter_example")
    print(f"Creating example CSV data...")
    create_example_data(data_root)

    # Create custom adapter
    adapter = SimpleCSVAdapter(data_root)

    # Discover available data
    print(f"\nDiscovered {len(adapter.groups())} groups: {adapter.groups()}")
    print(f"Variables: {adapter.variables()}")
    print(f"Locations: {len(adapter.location_coordinates())}")

    # Create the app
    print("\nCreating app with custom adapter...")
    app = create_app(adapter)

    # Display the app
    print("\nOpening app in browser...")
    app.show()


if __name__ == "__main__":
    main()
