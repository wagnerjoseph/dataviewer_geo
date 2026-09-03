"""Data loading and indexing for dataviewer_geo."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .config import DataConfig

logger = logging.getLogger(__name__)


def find_splits(config: DataConfig) -> list[str]:
    """Find all splits in the data root directory.

    Splits are subdirectories of the root that contain map and timeseries folders.

    Args:
        config: DataConfig with root path

    Returns:
        List of split names (sorted alphabetically)
    """
    splits = []
    for item in config.root.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            map_dir = item / config.map_subfolder
            ts_dir = item / config.timeseries_subfolder
            if map_dir.exists() and ts_dir.exists():
                splits.append(item.name)
    return sorted(splits)


def _discover_variables_from_parquet_files(
    directory: Path,
    exclude_cols: set[str] | None = None,
) -> list[str]:
    """Discover variable names from parquet files in a directory.

    Reads the first parquet file and returns column names excluding common index columns.

    Args:
        directory: Directory containing parquet files
        exclude_cols: Set of column names to exclude (e.g., location_id, time, tile_id)

    Returns:
        List of variable names
    """
    if exclude_cols is None:
        exclude_cols = {"location_id", "time", "tile_id", "lat", "lon", "latitude", "longitude"}

    parquet_files = list(directory.glob("*.parquet"))
    if not parquet_files:
        return []

    first_file = parquet_files[0]
    try:
        parquet_file = pq.ParquetFile(first_file)
        columns = parquet_file.schema.names
        variables = [col for col in columns if col not in exclude_cols]
        return sorted(variables)
    except Exception as e:
        logger.warning(f"Could not read schema from {first_file}: {e}")
        return []


class DataIndex:
    """Index for discovering and accessing data.

    Automatically discovers splits, variables, and locations from the data structure.

    Attributes:
        config: DataConfig instance
        splits: List of discovered split names
        map_variables: Variables available in map files
        timeseries_variables: Variables available in timeseries files
        locations: DataFrame with location_id, lat, lon, tile_id
    """

    def __init__(self, config: DataConfig) -> None:
        """Initialize the data index.

        Args:
            config: DataConfig with root path
        """
        self.config = config
        self.splits = find_splits(config)
        self.map_variables: list[str] = []
        self.timeseries_variables: list[str] = []
        self.locations: pd.DataFrame | None = None
        self._tile_to_split: dict[str, str] = {}

        self._discover()

    def _discover(self) -> None:
        """Discover splits, variables, and locations."""
        if not self.splits:
            logger.warning(f"No splits found in {self.config.root}")
            return

        # Load lookup table
        if self.config.lookup_path.exists():
            self.locations = pd.read_parquet(self.config.lookup_path)
            logger.info(f"Loaded {len(self.locations)} locations from lookup table")
        else:
            logger.warning(f"Lookup file not found: {self.config.lookup_path}")

        # Discover variables from first split
        if self.splits:
            first_split = self.splits[0]
            map_dir = self.config.root / first_split / self.config.map_subfolder
            ts_dir = self.config.root / first_split / self.config.timeseries_subfolder

            self.map_variables = _discover_variables_from_parquet_files(map_dir)
            self.timeseries_variables = _discover_variables_from_parquet_files(ts_dir)

            logger.info(f"Discovered {len(self.map_variables)} map variables")
            logger.info(f"Discovered {len(self.timeseries_variables)} timeseries variables")

        # Build tile to split mapping
        for split in self.splits:
            map_dir = self.config.root / split / self.config.map_subfolder
            for tile_file in map_dir.glob("*.parquet"):
                tile_id = tile_file.stem
                self._tile_to_split[tile_id] = split

    @property
    def all_variables(self) -> list[str]:
        """Get all unique variables across map and timeseries."""
        return sorted(set(self.map_variables) | set(self.timeseries_variables))

    def get_split_for_tile(self, tile_id: str) -> str | None:
        """Get the split name for a given tile ID."""
        return self._tile_to_split.get(tile_id)

    def get_locations_for_split(self, split: str) -> pd.DataFrame | None:
        """Get locations that have data for a specific split.

        Reads all map files for the split and returns unique location IDs.
        """
        map_dir = self.config.root / split / self.config.map_subfolder
        if not map_dir.exists():
            return None

        location_ids = []
        for tile_file in map_dir.glob("*.parquet"):
            try:
                df = pd.read_parquet(tile_file, columns=["location_id"])
                location_ids.extend(df["location_id"].unique().tolist())
            except Exception as e:
                logger.warning(f"Could not read {tile_file}: {e}")

        if not location_ids or self.locations is None:
            return None

        return self.locations[self.locations["location_id"].isin(location_ids)]


def load_map_variable(
    config: DataConfig,
    split: str,
    variable: str,
    tile_id: str | None = None,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Load map data for a variable.

    Args:
        config: DataConfig instance
        split: Split name
        variable: Variable name to load
        tile_id: Optional tile ID to load (if None, loads all tiles)

    Returns:
        DataFrame with location_id, lat, lon, and the variable, or dict of DataFrames by tile
    """
    map_dir = config.root / split / config.map_subfolder
    if not map_dir.exists():
        raise FileNotFoundError(f"Map directory not found: {map_dir}")

    if tile_id:
        tile_file = map_dir / f"{tile_id}.parquet"
        if not tile_file.exists():
            raise FileNotFoundError(f"Tile file not found: {tile_file}")

        df = pd.read_parquet(tile_file)
        if variable not in df.columns:
            raise ValueError(f"Variable '{variable}' not found in {tile_file}")

        return df[["location_id", variable] + [c for c in ["lat", "lon"] if c in df.columns]]
    else:
        # Load all tiles
        result = {}
        for tile_file in map_dir.glob("*.parquet"):
            try:
                df = pd.read_parquet(tile_file)
                if variable in df.columns:
                    tile_id = tile_file.stem
                    result[tile_id] = df[
                        ["location_id", variable] + [c for c in ["lat", "lon"] if c in df.columns]
                    ]
            except Exception as e:
                logger.warning(f"Could not read {tile_file}: {e}")
        
        if not result:
            raise ValueError(f"Variable '{variable}' not found in any tile in {map_dir}")
        
        return result


def load_timeseries_for_location(
    config: DataConfig,
    split: str,
    location_id: int | str,
    variables: list[str] | str | None = None,
) -> pd.DataFrame:
    """Load timeseries data for a specific location.

    Searches all tiles in the split to find the location and loads its timeseries.

    Args:
        config: DataConfig instance
        split: Split name
        location_id: Location ID to load
        variables: Variable name(s) to load (if None, loads all available)

    Returns:
        DataFrame with time and variable columns
    """
    ts_dir = config.root / split / config.timeseries_subfolder
    if not ts_dir.exists():
        raise FileNotFoundError(f"Timeseries directory not found: {ts_dir}")

    if isinstance(variables, str):
        variables = [variables]

    # Find which tile contains this location
    for tile_file in ts_dir.glob("*.parquet"):
        try:
            # Read just the location_id column to check if this tile has our location
            tile_data = pd.read_parquet(tile_file, columns=["location_id"])
            if location_id in tile_data["location_id"].values:
                # Load the full timeseries for this location
                df = pd.read_parquet(tile_file)
                location_data = df[df["location_id"] == location_id].copy()

                # Select variables
                if variables:
                    cols = ["location_id", "time"] + variables
                    available_cols = [c for c in cols if c in location_data.columns]
                    return location_data[available_cols]
                else:
                    return location_data
        except Exception as e:
            logger.debug(f"Could not read {tile_file}: {e}")
            continue

    raise ValueError(f"Location {location_id} not found in split '{split}'")


def generate_dummy_data(
    root: Path | str,
    n_locations: int = 100,
    n_tiles: int = 4,
    splits: list[str] | None = None,
    map_variables: list[str] | None = None,
    timeseries_variables: list[str] | None = None,
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    seed: int = 42,
) -> DataConfig:
    """Generate dummy data for testing and development.

    Creates a complete data structure with:
    - lookup.parquet with location_id, lat, lon, tile_id
    - <split>/map/<tile>.parquet with location_id and variables
    - <split>/timeseries/<tile>.parquet with location_id, time, and variables

    Args:
        root: Root directory for the data
        n_locations: Number of locations to generate
        n_tiles: Number of tiles
        splits: List of split names (default: ["split_2020_2022", "split_2023_2024"])
        map_variables: Map variable names (default: ["backscatter", "soil_moisture"])
        timeseries_variables: Timeseries variable names (default: ["backscatter", "lai", "soil_moisture"])
        start_date: Start date for timeseries
        end_date: End date for timeseries
        seed: Random seed for reproducibility

    Returns:
        DataConfig for the generated data
    """
    rng = np.random.default_rng(seed)
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    if splits is None:
        splits = ["split_2020_2022", "split_2023_2024"]

    if map_variables is None:
        map_variables = ["backscatter", "soil_moisture"]

    if timeseries_variables is None:
        timeseries_variables = ["backscatter", "lai", "soil_moisture"]

    # Generate locations
    location_ids = np.arange(n_locations)
    tile_ids = np.arange(n_tiles)
    lats = rng.uniform(45, 55, n_locations)  # Central Europe
    lons = rng.uniform(10, 20, n_locations)
    location_tile_ids = rng.choice(tile_ids, n_locations)

    lookup_df = pd.DataFrame(
        {
            "location_id": location_ids,
            "lat": lats,
            "lon": lons,
            "tile_id": location_tile_ids,
        }
    )
    lookup_df.to_parquet(root / "lookup.parquet", index=False)
    logger.info(f"Generated lookup table with {n_locations} locations")

    # Generate data for each split
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    for split in splits:
        split_dir = root / split

        # Generate map data for each tile
        map_dir = split_dir / "map"
        map_dir.mkdir(parents=True, exist_ok=True)

        for tile_id in tile_ids:
            tile_locations = location_ids[location_tile_ids == tile_id]
            tile_lats = lats[location_tile_ids == tile_id]
            tile_lons = lons[location_tile_ids == tile_id]

            map_data = {"location_id": tile_locations, "lat": tile_lats, "lon": tile_lons}

            # Generate static map variables
            for var in map_variables:
                map_data[var] = rng.normal(0, 1, len(tile_locations))

            map_df = pd.DataFrame(map_data)
            map_df.to_parquet(map_dir / f"{tile_id}.parquet", index=False)

        # Generate timeseries data for each tile
        ts_dir = split_dir / "timeseries"
        ts_dir.mkdir(parents=True, exist_ok=True)

        for tile_id in tile_ids:
            tile_locations = location_ids[location_tile_ids == tile_id]

            # Create timeseries for all locations in this tile
            rows = []
            for loc_id in tile_locations:
                for date in date_range:
                    row = {"location_id": loc_id, "time": date}
                    for var in timeseries_variables:
                        # Generate correlated timeseries with some seasonality
                        day_of_year = date.dayofyear
                        seasonal = np.sin(2 * np.pi * day_of_year / 365)
                        row[var] = seasonal + rng.normal(0, 0.5)
                    rows.append(row)

            ts_df = pd.DataFrame(rows)
            ts_df.to_parquet(ts_dir / f"{tile_id}.parquet", index=False)

        logger.info(f"Generated data for split '{split}'")

    return DataConfig(root=root)
