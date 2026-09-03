#!/usr/bin/env python3
"""Example: Using dataviewer_geo with generic timeseries data.

This example shows how to use the GenericTimeseriesAdapter
for arbitrary geo-located timeseries datasets.

Data format expected:
    data_root/
    ├── lookup.parquet              # location_id, lat, lon
    ├── group1/
    │   └── data.parquet            # location_id, time, var1, var2, ...
    └── group2/
        └── data.parquet            # location_id, time, var1, var2, ...
"""

from pathlib import Path
import pandas as pd
import numpy as np

from dataviewer_geo import create_app
from dataviewer_geo.datasets import GenericTimeseriesAdapter, TimeseriesConfig


def create_example_data(data_root: Path) -> None:
    """Create example generic timeseries data."""
    data_root.mkdir(parents=True, exist_ok=True)

    # Create lookup table
    n_locations = 50
    lookup_df = pd.DataFrame({
        'location_id': range(n_locations),
        'lat': np.random.uniform(45, 55, n_locations),
        'lon': np.random.uniform(10, 20, n_locations),
    })
    lookup_df.to_parquet(data_root / 'lookup.parquet', index=False)
    print(f"Created lookup table with {n_locations} locations")

    # Create timeseries for two groups
    date_range1 = pd.date_range('2020-01-01', '2022-12-31', freq='D')
    date_range2 = pd.date_range('2023-01-01', '2024-12-31', freq='D')

    for group, dates in [('2020_2022', date_range1), ('2023_2024', date_range2)]:
        group_dir = data_root / group
        group_dir.mkdir(exist_ok=True)

        rows = []
        for loc_id in range(n_locations):
            for date in dates:
                # Simulate seasonal patterns
                day_of_year = date.dayofyear
                seasonal = np.sin(2 * np.pi * day_of_year / 365)

                rows.append({
                    'location_id': loc_id,
                    'time': date,
                    'temperature': 15 + 10 * seasonal + np.random.randn() * 2,
                    'precipitation': np.random.exponential(2),
                    'humidity': 60 + 20 * seasonal + np.random.randn() * 5,
                })

        ts_df = pd.DataFrame(rows)
        ts_df.to_parquet(group_dir / 'data.parquet', index=False)
        print(f"Created timeseries for group '{group}': {len(dates)} days × {n_locations} locations")


def main() -> None:
    """Main entry point."""
    # Create example data
    data_root = Path("/tmp/dataviewer_generic_example")
    print(f"Creating example generic data at {data_root}...")
    create_example_data(data_root)

    # Create adapter configuration
    config = TimeseriesConfig(
        root=data_root,
        lookup_file="lookup.parquet",
        id_column="location_id",
        lat_column="lat",
        lon_column="lon",
        time_column="time",
        timeseries_file_pattern="data.parquet",
    )

    # Create adapter
    adapter = GenericTimeseriesAdapter(config)

    # Discover available data
    print(f"\nDiscovered {len(adapter.groups())} groups: {adapter.groups()}")
    print(f"Variables: {adapter.variables()}")
    print(f"Timeseries variables: {adapter.timeseries_variables('2020_2022')}")

    # Create the app
    print("\nCreating app...")
    print("The app includes:")
    print("  - Interactive map with OSM basemap")
    print("  - Group and variable selectors")
    print("  - Location ID input (or click on map)")
    print("  - Timeseries with var_specs editor")
    print("  - Metrics/FI: Not available (generic format)")
    app = create_app(adapter)

    # Display the app
    print("\nOpening app in browser...")
    print("(Expand 'Timeseries Configuration' to configure var_specs interactively)")
    app.show()


if __name__ == "__main__":
    main()
