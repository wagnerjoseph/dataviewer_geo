#!/usr/bin/env python3
"""Basic example: Create and display the dataviewer_geo app."""

from pathlib import Path

from dataviewer_geo import DataConfig, create_app, generate_dummy_data

# Generate dummy data for demonstration
data_root = Path("/tmp/dataviewer_example_data")
print(f"Generating dummy data at {data_root}...")
generate_dummy_data(data_root, n_locations=100, n_tiles=4)

# Create configuration
config = DataConfig(root=data_root)

# Discover available data
from dataviewer_geo import DataIndex

index = DataIndex(config)
print(f"\nDiscovered {len(index.splits)} splits: {index.splits}")
print(f"Map variables: {index.map_variables}")
print(f"Timeseries variables: {index.timeseries_variables}")
print(f"Locations: {len(index.locations)}")

# Create the app
print("\nCreating app...")
app = create_app(config)

# Display the app (opens in browser)
print("Opening app in browser...")
app.show()

# Or serve it programmatically:
# app.servable()
# print("App served at http://localhost:5000")
