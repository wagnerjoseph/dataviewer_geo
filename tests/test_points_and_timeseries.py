"""Regression tests for point selection and timeseries plotting.

These guard against the bug where selecting a point on the map produced an
error instead of the timeseries (caused by a broken DataConfig construction
in the metrics block) and where the Group dropdown was ignored.
"""

import matplotlib
import pandas as pd

matplotlib.use("Agg")

from dataviewer_geo.config import DataConfig
from dataviewer_geo.datasets import BackscatterMLAdapter
from dataviewer_geo.plotting import create_metrics_table, create_feature_importance_plot
from dataviewer_geo.plotting.timeseries import plot_location_timeseries


class TestPointSelectionAndTimeseries:
    """Test the full drill-down path for all groups, variables, and locations."""

    def _adapter(self, tmp_path):
        from dataviewer_geo import generate_dummy_data

        generate_dummy_data(tmp_path, n_locations=15, n_tiles=2, seed=3)
        return BackscatterMLAdapter(DataConfig(root=tmp_path))

    def test_group_specific_map_data_and_variables(self, tmp_path):
        """Switching group must change the map variables/data."""
        adapter = self._adapter(tmp_path)
        assert len(adapter.groups()) >= 2

        # Each group yields its own (potentially different) variable data.
        for group in adapter.groups():
            variables = adapter.variables(group)
            assert variables, f"no variables for group {group}"
            for var in variables:
                df = adapter.load_variable_data(var, group)
                assert not df.empty, f"empty map data for {group}/{var}"

    def test_timeseries_plots_and_metrics_table_for_every_selection(self, tmp_path):
        """Clicking any point must plot a timeseries and a metrics table (no crash)."""
        adapter = self._adapter(tmp_path)

        for group in adapter.groups():
            locations = adapter.location_coordinates()[adapter.id_column].tolist()
            for loc in locations[::3]:  # sample every 3rd location
                ts = adapter.load_timeseries(group, loc)
                assert ts is not None and not ts.empty, f"no timeseries {group}/{loc}"

                # The core reported bug: plotting the timeseries.
                figs = plot_location_timeseries(
                    ts,
                    [loc],
                    None,
                    time_col=adapter.time_column,
                    location_id_col=adapter.id_column,
                )
                assert figs, f"timeseries did not plot for {group}/{loc}"

                # Metrics table must build without raising (regression for DataConfig(root=None)).
                tile = adapter.resolve_tile(group, loc)
                metrics = adapter.metrics(group, loc, tile)
                if metrics:
                    table = create_metrics_table(metrics, adapter.metric_models)
                    assert table is not None

                fi = adapter.feature_importance(group, loc, tile)
                if fi:
                    plot = create_feature_importance_plot(fi, adapter.fi_col_prefix)
                    assert plot is not None

    def test_timeseries_dataframe_has_expected_columns(self, tmp_path):
        adapter = self._adapter(tmp_path)
        group = adapter.groups()[0]
        ts = adapter.load_timeseries(group, 0)
        assert adapter.id_column in ts.columns
        assert adapter.time_column in ts.columns
        assert pd.api.types.is_datetime64_any_dtype(ts[adapter.time_column])
