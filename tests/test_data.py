"""Tests for data loading and indexing."""

import pytest

from dataviewer_geo.config import DataConfig
from dataviewer_geo.data import (
    DataIndex,
    find_splits,
    generate_dummy_data,
    load_map_variable,
    load_timeseries_for_location,
)


class TestFindSplits:
    """Tests for find_splits function."""

    def test_finds_splits(self, temp_data_dir):
        """Test that splits are discovered correctly."""
        config = DataConfig(root=temp_data_dir)
        splits = find_splits(config)
        assert len(splits) == 2
        assert "split_2020_2022" in splits
        assert "split_2023_2024" in splits

    def test_no_splits(self, tmp_path):
        """Test with empty directory."""
        config = DataConfig(root=tmp_path)
        splits = find_splits(config)
        assert len(splits) == 0


class TestDataIndex:
    """Tests for DataIndex class."""

    def test_discover_splits(self, data_config):
        """Test split discovery."""
        index = DataIndex(data_config)
        assert len(index.splits) == 2

    def test_discover_variables(self, data_config):
        """Test variable discovery."""
        index = DataIndex(data_config)
        assert len(index.map_variables) > 0
        assert len(index.timeseries_variables) > 0

    def test_load_locations(self, data_config):
        """Test location loading."""
        index = DataIndex(data_config)
        assert index.locations is not None
        assert len(index.locations) > 0

    def test_all_variables(self, data_config):
        """Test all_variables property."""
        index = DataIndex(data_config)
        all_vars = index.all_variables
        assert len(all_vars) >= len(index.map_variables)
        assert len(all_vars) >= len(index.timeseries_variables)

    def test_get_locations_for_split(self, data_config):
        """Test getting locations for a specific split."""
        index = DataIndex(data_config)
        locations = index.get_locations_for_split("split_2020_2022")
        assert locations is not None
        assert len(locations) > 0


class TestLoadMapVariable:
    """Tests for load_map_variable function."""

    def test_load_single_variable(self, data_config):
        """Test loading a single variable."""
        index = DataIndex(data_config)
        variable = index.map_variables[0]
        data = load_map_variable(data_config, "split_2020_2022", variable)

        assert isinstance(data, dict) or hasattr(data, "columns")
        if isinstance(data, dict):
            assert len(data) > 0
            first_tile = next(iter(data.values()))
            assert variable in first_tile.columns
        else:
            assert variable in data.columns

    def test_load_nonexistent_variable(self, data_config):
        """Test loading a variable that doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            load_map_variable(data_config, "split_2020_2022", "nonexistent_var")


class TestLoadTimeseries:
    """Tests for load_timeseries_for_location function."""

    def test_load_timeseries(self, data_config):
        """Test loading timeseries for a location."""
        index = DataIndex(data_config)
        location_id = index.locations["location_id"].iloc[0]

        ts_data = load_timeseries_for_location(
            data_config, "split_2020_2022", location_id
        )

        assert len(ts_data) > 0
        assert "time" in ts_data.columns

    def test_load_timeseries_with_variables(self, data_config):
        """Test loading specific variables."""
        index = DataIndex(data_config)
        location_id = index.locations["location_id"].iloc[0]
        variable = index.timeseries_variables[0]

        ts_data = load_timeseries_for_location(
            data_config,
            "split_2020_2022",
            location_id,
            variables=[variable],
        )

        assert variable in ts_data.columns

    def test_load_nonexistent_location(self, data_config):
        """Test loading timeseries for a location that doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            load_timeseries_for_location(
                data_config, "split_2020_2022", -99999
            )


class TestGenerateDummyData:
    """Tests for generate_dummy_data function."""

    def test_generate_basic(self, tmp_path):
        """Test basic dummy data generation."""
        config = generate_dummy_data(tmp_path, n_locations=20, n_tiles=2)

        assert config.root == tmp_path
        assert config.lookup_path.exists()

    def test_generate_custom_splits(self, tmp_path):
        """Test with custom split names."""
        config = generate_dummy_data(
            tmp_path,
            splits=["custom_split_1", "custom_split_2"],
            n_locations=10,
        )

        splits = find_splits(config)
        assert "custom_split_1" in splits
        assert "custom_split_2" in splits

    def test_generate_reproducible(self, tmp_path):
        """Test that data generation is reproducible."""
        config1 = generate_dummy_data(tmp_path / "run1", seed=42)
        config2 = generate_dummy_data(tmp_path / "run2", seed=42)

        import pandas as pd

        lookup1 = pd.read_parquet(config1.lookup_path)
        lookup2 = pd.read_parquet(config2.lookup_path)

        assert lookup1.equals(lookup2)
