"""Tests for timeseries plotting."""

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from dataviewer_geo.data import DataIndex
from dataviewer_geo.plotting.timeseries import plot_location_timeseries


class TestPlotLocationTimeseries:
    """Tests for plot_location_timeseries function."""

    def test_basic_plot(self, data_config):
        """Test basic timeseries plotting."""
        from dataviewer_geo.data import load_timeseries_for_location

        index = DataIndex(data_config)
        location_id = index.locations["location_id"].iloc[0]

        ts_data = load_timeseries_for_location(
            data_config, "split_2020_2022", location_id
        )

        figs = plot_location_timeseries(
            data=ts_data,
            location_id=location_id,
            split_name="split_2020_2022",
        )

        # plot_time_series returns a list of figures
        assert isinstance(figs, list)
        assert len(figs) > 0
        assert isinstance(figs[0], plt.Figure)
        for fig in figs:
            plt.close(fig)

    def test_plot_with_variables(self, data_config):
        """Test plotting specific variables."""
        from dataviewer_geo.data import DataIndex, load_timeseries_for_location

        index = DataIndex(data_config)
        location_id = index.locations["location_id"].iloc[0]
        variable = index.timeseries_variables[0]

        ts_data = load_timeseries_for_location(
            data_config, "split_2020_2022", location_id
        )

        figs = plot_location_timeseries(
            data=ts_data,
            variables=[variable],
            location_id=location_id,
        )

        assert isinstance(figs, list)
        assert len(figs) > 0
        for fig in figs:
            plt.close(fig)

    def test_plot_with_string_variable(self, data_config):
        """Test plotting with string variable name."""
        from dataviewer_geo.data import DataIndex, load_timeseries_for_location

        index = DataIndex(data_config)
        location_id = index.locations["location_id"].iloc[0]
        variable = index.timeseries_variables[0]

        ts_data = load_timeseries_for_location(
            data_config, "split_2020_2022", location_id
        )

        figs = plot_location_timeseries(
            data=ts_data,
            variables=variable,  # String instead of list
            location_id=location_id,
        )

        assert isinstance(figs, list)
        assert len(figs) > 0
        for fig in figs:
            plt.close(fig)

    def test_plot_no_variables_raises(self, data_config):
        """Test that plotting with no variables raises an error."""
        from dataviewer_geo.data import DataIndex, load_timeseries_for_location

        index = DataIndex(data_config)
        location_id = index.locations["location_id"].iloc[0]

        ts_data = load_timeseries_for_location(
            data_config, "split_2020_2022", location_id
        )

        # Drop all numeric columns except time
        ts_data = ts_data[["time"]]

        with pytest.raises(ValueError, match="No variables found"):
            plot_location_timeseries(data=ts_data, location_id=location_id)

    def test_plot_no_time_column_raises(self, data_config):
        """Test that plotting without time column raises an error."""
        df = pd.DataFrame({"var1": [1, 2, 3], "var2": [4, 5, 6]})

        with pytest.raises(ValueError, match="Time column"):
            plot_location_timeseries(data=df)
