"""Interactive Panel application for dataviewer_geo.

This module provides the main application UI, now decoupled from specific
data schemas via the DatasetAdapter interface.
"""

import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import panel as pn
import pandas as pd
import numpy as np
import holoviews as hv
import geoviews as gv

from .config import DataConfig
from .data import generate_dummy_data
from .plotting import (
    plot_location_timeseries,
    create_feature_importance_plot,
    create_metrics_table,
    add_dynamic_sizing,
)
from .var_spec_editor import VarSpecEditor

if TYPE_CHECKING:
    from .datasets import DatasetAdapter

logger = logging.getLogger(__name__)

pn.extension()
hv.extension("bokeh")
gv.extension("bokeh")


def create_app(adapter: "DatasetAdapter") -> pn.Column:
    """Create the interactive data viewer application.

    Args:
        adapter: DatasetAdapter instance providing data access.
                 Can be BackscatterMLAdapter, GenericTimeseriesAdapter, or custom.

    Returns:
        Panel Column application with map, timeseries, and optional metrics/FI.
    """
    # Check for available groups
    groups = adapter.groups()

    if not groups:
        return pn.Column(
            pn.pane.Alert(
                "**Error:** No groups found. "
                "Ensure data directory contains valid data structure.",
                alert_type="danger",
                sizing_mode="stretch_width",
            )
        )

    # Pre-load coordinates
    coords = adapter.location_coordinates()

    # Per-session state
    state = {
        "current_group": None,
        "current_variable": None,
        "selected_location_id": None,
        "map_data": None,
        "points_element": None,
        "highlight_stream": None,
        "updating_location_input": False,
        "last_plot_location_id": None,
        "var_spec_editor": None,
        "ts_data": None,
        "ts_location_id": None,
    }

    # =============================================================================
    # WIDGETS
    # =============================================================================

    group_select = pn.widgets.Select(
        name="Group",
        options={g: g for g in groups},
        value=groups[-1] if groups else None,
    )

    # Get variables for initial group
    initial_variables = adapter.variables()
    variable_select = pn.widgets.Select(
        name="Variable",
        options=initial_variables,
        value=initial_variables[0] if initial_variables else None,
    )

    location_input = pn.widgets.IntInput(
        name="Location ID",
        value=None,
        step=1,
    )

    loading_indicator = pn.indicators.LoadingSpinner(
        value=False, size=25, name="Loading…"
    )

    # =============================================================================
    # PANES
    # =============================================================================

    map_pane = pn.pane.HoloViews(
        None,
        sizing_mode="fixed",
        styles={
            "width": "50vw",
            "height": "75vh",
            "min-width": "50vw",
            "max-width": "50vw",
        },
    )

    timeseries_pane = pn.Column(
        pn.pane.Markdown("**Click a location on the map to view timeseries**"),
        sizing_mode="stretch_width",
    )
    timeseries_pane.min_height = 400

    feature_importance_pane = pn.Column(
        sizing_mode="fixed",
        width=800,
        margin=0,
        styles={"padding": "0"},
    )

    metrics_table_pane = pn.Column(
        sizing_mode="stretch_both",
        margin=0,
        styles={"padding": "0"},
    )

    info_pane = pn.pane.Markdown(
        "**Status:** Ready - Select a location to view details",
        sizing_mode="stretch_width",
    )

    # =============================================================================
    # HELPER FUNCTIONS
    # =============================================================================

    def _get_map_data(group: str, variable_name: str) -> pd.DataFrame:
        """Load and prepare map data with coordinates."""
        var_data = adapter.load_variable_data(variable_name)
        if coords is not None and not var_data.empty:
            # Merge with coordinates if needed
            id_col = "location_id"
            if id_col in var_data.columns and id_col in coords.columns:
                merged = var_data.merge(coords, on=id_col, how="left")
                lon_cols = [c for c in merged.columns if c.startswith("lon")]
                lat_cols = [c for c in merged.columns if c.startswith("lat")]
                if lon_cols and lat_cols:
                    merged = merged.dropna(subset=[lon_cols[0], lat_cols[0]])
                return merged
        return var_data

    def load_and_display_location_data(location_id: int):
        """Load and display timeseries, metrics, and feature importance for a location."""
        try:
            group = group_select.value
            map_data = state.get("map_data")

            if map_data is None:
                return

            id_col = "location_id"
            matching = map_data[map_data[id_col] == location_id]
            if matching.empty:
                return

            # Get tile/group identifier
            tile_id = adapter.resolve_tile(group, location_id)

            # Load data concurrently
            ts_data = None
            fi_data = None
            metrics_data = None

            if tile_id or True:  # Always try to load timeseries
                with ThreadPoolExecutor(max_workers=3) as executor:
                    ts_future = executor.submit(
                        adapter.load_timeseries, group, location_id
                    )
                    fi_future = executor.submit(
                        adapter.feature_importance, group, location_id, tile_id
                    )
                    metrics_future = executor.submit(
                        adapter.metrics, group, location_id, tile_id
                    )

                    ts_data = ts_future.result()
                    fi_data = fi_future.result()
                    metrics_data = metrics_future.result()

            has_timeseries = ts_data is not None and not ts_data.empty

            if has_timeseries:
                # Cache ts_data for config-driven replot
                state["ts_data"] = ts_data
                state["ts_location_id"] = location_id

                # Get var_specs from editor
                var_spec_editor = state.get("var_spec_editor")
                var_specs = (
                    var_spec_editor.to_var_specs() if var_spec_editor else None
                )

                # Plot timeseries
                figs = plot_location_timeseries(
                    data=ts_data,
                    location_ids=[location_id],
                    var_specs=var_specs,
                    time_col="time",
                    location_id_col=id_col,
                    figsize=(10, 5),
                    font_scale=1.0,
                    show_plot=False,
                )

                if figs and len(figs) > 0:
                    timeseries_plot = pn.pane.Matplotlib(figs[0], tight=True)
                    timeseries_pane.clear()
                    timeseries_pane.append(timeseries_plot)
                    state["last_plot_location_id"] = location_id

                # Display metrics if available
                if metrics_data:
                    # Use default metric models config if adapter doesn't provide one
                    from .config import DataConfig
                    default_config = DataConfig(root=adapter.root if hasattr(adapter, 'root') else None)
                    metrics_table = create_metrics_table(
                        metrics_data, default_config.metric_models
                    )
                    metrics_table_pane.clear()
                    metrics_table_pane.append(metrics_table)
                else:
                    metrics_table_pane.clear()
                    metrics_table_pane.append(
                        pn.pane.Markdown("Metrics not available for this dataset")
                    )

                # Display feature importance if available
                if fi_data:
                    fi_plot = create_feature_importance_plot(fi_data, "fi_")
                    feature_importance_pane.clear()
                    feature_importance_pane.append(fi_plot)
                else:
                    feature_importance_pane.clear()
                    feature_importance_pane.append(
                        pn.pane.Markdown("Feature importance not available for this dataset")
                    )
            else:
                state["last_plot_location_id"] = None
                timeseries_pane.clear()
                timeseries_pane.append(
                    pn.pane.Markdown(
                        f"**No timeseries data found for location {location_id}**"
                    )
                )
                metrics_table_pane.clear()
                metrics_table_pane.append(
                    pn.pane.Markdown("Select a location to view metrics")
                )
                feature_importance_pane.clear()
                feature_importance_pane.append(
                    pn.pane.Markdown("Select a location to view feature importance")
                )

        except Exception as e:
            import traceback

            logger.error(f"Error loading location data: {e}\n{traceback.format_exc()}")
            state["last_plot_location_id"] = None
            error_msg = f"Error: {str(e)}"
            timeseries_pane.clear()
            timeseries_pane.append(pn.pane.Markdown(f"**Error:** {error_msg}"))
            metrics_table_pane.clear()
            metrics_table_pane.append(pn.pane.Markdown("Error loading metrics"))
            feature_importance_pane.clear()
            feature_importance_pane.append(
                pn.pane.Markdown("Error loading feature importance")
            )

    def regenerate_timeseries():
        """Re-render timeseries plot with current var_specs (from cached ts_data)."""
        ts_data = state.get("ts_data")
        location_id = state.get("ts_location_id")

        if ts_data is None or location_id is None:
            return  # No data to replot

        # Reset cache to force re-render
        state["last_plot_location_id"] = None

        # Get var_specs from editor
        var_spec_editor = state.get("var_spec_editor")
        var_specs = (
            var_spec_editor.to_var_specs() if var_spec_editor else None
        )

        # Plot timeseries
        figs = plot_location_timeseries(
            data=ts_data,
            location_ids=[location_id],
            var_specs=var_specs,
            time_col="time",
            location_id_col="location_id",
            figsize=(10, 5),
            font_scale=1.0,
            show_plot=False,
        )

        if figs and len(figs) > 0:
            timeseries_plot = pn.pane.Matplotlib(figs[0], tight=True)
            timeseries_pane.clear()
            timeseries_pane.append(timeseries_plot)
            state["last_plot_location_id"] = location_id

    def _make_highlight(
        location_id: int, map_data: pd.DataFrame, lon_col: str, lat_col: str
    ) -> hv.Overlay:
        """Create highlight marker for selected location."""
        if location_id is None or map_data is None:
            return hv.Overlay([])

        id_col = "location_id"
        matching = map_data.loc[map_data[id_col] == location_id]
        if matching.empty:
            return hv.Overlay([])

        h_df = pd.DataFrame(
            {
                lon_col: [float(matching[lon_col].iloc[0])],
                lat_col: [float(matching[lat_col].iloc[0])],
                id_col: [location_id],
            }
        )

        # Create a more visible highlight with multiple rings
        outer_ring = gv.Points(
            h_df, kdims=[lon_col, lat_col], vdims=[id_col]
        ).opts(
            size=30,
            color="red",
            alpha=0.2,
            line_color="red",
            line_width=3,
            line_alpha=0.5,
            marker="circle",
            tools=[],
        )
        middle_ring = gv.Points(
            h_df, kdims=[lon_col, lat_col], vdims=[id_col]
        ).opts(
            size=20,
            color="red",
            alpha=0.3,
            line_color="red",
            line_width=2,
            line_alpha=0.6,
            marker="circle",
            tools=[],
        )
        inner_dot = gv.Points(
            h_df, kdims=[lon_col, lat_col], vdims=[id_col]
        ).opts(
            size=12,
            color="red",
            alpha=1.0,
            line_color="white",
            line_width=2,
            marker="circle",
            tools=[],
        )

        return outer_ring * middle_ring * inner_dot

    def _auto_clim(values: np.ndarray) -> tuple[float, float]:
        """Compute automatic color limits (2nd and 98th percentile)."""
        valid = values[~np.isnan(values)]
        if len(valid) == 0:
            return (None, None)
        return (float(np.percentile(valid, 2)), float(np.percentile(valid, 98)))

    def create_on_selection_update():
        """Create a shared selection update callback."""

        def on_selection_update(index):
            """Update UI elements when selection changes."""
            map_data = state.get("map_data")
            id_col = "location_id"
            if map_data is None or index is None or len(index) == 0:
                state["selected_location_id"] = None
                location_input.value = None
                info_pane.object = ""
                timeseries_pane.clear()
                timeseries_pane.append(
                    pn.pane.Markdown(
                        "**Click a location on the map to view timeseries**"
                    )
                )
                metrics_table_pane.clear()
                metrics_table_pane.append(
                    pn.pane.Markdown("Select a location to view metrics")
                )
                feature_importance_pane.clear()
                feature_importance_pane.append(
                    pn.pane.Markdown("Select a location to view feature importance")
                )
                return

            location_id = int(map_data.iloc[index[0]][id_col])
            state["selected_location_id"] = location_id

            state["updating_location_input"] = True
            try:
                location_input.value = location_id
            finally:
                state["updating_location_input"] = False

            info_pane.object = f"**Selected Location ID:** `{location_id}`"
            load_and_display_location_data(location_id)

        return on_selection_update

    # =============================================================================
    # MAP CREATION
    # =============================================================================

    def create_map(group: str, variable_name: str):
        """Create the initial map with all layers."""
        loading_indicator.value = True

        try:
            # Load data
            map_data = _get_map_data(group, variable_name)

            if map_data.empty:
                return hv.Text(0, 0, "No data available")

            state["map_data"] = map_data

            # Determine actual column names
            lon_cols = [c for c in map_data.columns if c.startswith("lon")]
            lat_cols = [c for c in map_data.columns if c.startswith("lat")]
            actual_lon = lon_cols[0] if lon_cols else "lon"
            actual_lat = lat_cols[0] if lat_cols else "lat"
            id_col = "location_id"

            # Compute color limits
            vmin, vmax = _auto_clim(map_data[variable_name].values)

            # Create points layer
            points = gv.Points(
                map_data,
                kdims=[actual_lon, actual_lat],
                vdims=[id_col, variable_name],
            ).opts(
                color=variable_name,
                cmap="viridis",
                size=2,
                width=800,
                height=700,
                responsive=True,
                tools=["tap", "hover", "box_zoom", "wheel_zoom", "reset"],
                colorbar=True,
                clim=(vmin, vmax),
                title=f"{variable_name} - {group}",
                active_tools=["wheel_zoom"],
                hooks=[add_dynamic_sizing],
                hover_tooltips=[
                    ("Location ID", f"@{id_col}"),
                    ("Value", f"@{variable_name}"),
                    ("Lon", f"@{actual_lon}"),
                    ("Lat", f"@{actual_lat}"),
                ],
            )

            state["points_element"] = points

            # Create highlight stream
            highlight_stream = hv.streams.Selection1D(source=points)
            state["highlight_stream"] = highlight_stream

            # Create and store shared selection callback
            if (
                "on_selection_update" not in state
                or state["on_selection_update"] is None
            ):
                state["on_selection_update"] = create_on_selection_update()
            highlight_stream.add_subscriber(state["on_selection_update"])

            def update_highlight(index):
                """Update highlight based on selection."""
                if index and len(index) > 0:
                    location_id = int(map_data.iloc[index[0]][id_col])
                    state["selected_location_id"] = location_id
                    return _make_highlight(
                        location_id, map_data, actual_lon, actual_lat
                    )
                else:
                    state["selected_location_id"] = None
                    return hv.Overlay([])

            highlight_layer = hv.DynamicMap(
                update_highlight, streams=[highlight_stream]
            )

            # Render with basemap
            basemap = gv.tile_sources.OSM.opts(
                alpha=0.6,
                width=800,
                height=700,
                responsive=True,
            )
            return basemap * points * highlight_layer

        finally:
            loading_indicator.value = False

    # =============================================================================
    # DATA UPDATE
    # =============================================================================

    def update_map_data(group: str, variable_name: str):
        """Update map data without re-creating the plot."""
        loading_indicator.value = True

        try:
            saved_location_id = state.get("selected_location_id")

            # Capture current zoom ranges
            saved_ranges = None
            try:
                if hasattr(map_pane, "_plots") and map_pane._plots:
                    old_plot = list(map_pane._plots.values())[0]
                    if hasattr(old_plot, "state"):
                        saved_ranges = {
                            "x_start": old_plot.state.x_range.start,
                            "x_end": old_plot.state.x_range.end,
                            "y_start": old_plot.state.y_range.start,
                            "y_end": old_plot.state.y_range.end,
                        }
            except Exception:
                pass

            # Load new data
            map_data = _get_map_data(group, variable_name)

            if map_data.empty:
                map_pane.object = hv.Text(0, 0, "No data available")
                return

            state["map_data"] = map_data

            # Determine actual column names
            lon_cols = [c for c in map_data.columns if c.startswith("lon")]
            lat_cols = [c for c in map_data.columns if c.startswith("lat")]
            actual_lon = lon_cols[0] if lon_cols else "lon"
            actual_lat = lat_cols[0] if lat_cols else "lat"
            id_col = "location_id"

            # Compute new color limits
            vmin, vmax = _auto_clim(map_data[variable_name].values)

            # Create new points element
            points = gv.Points(
                map_data,
                kdims=[actual_lon, actual_lat],
                vdims=[id_col, variable_name],
            ).opts(
                color=variable_name,
                cmap="viridis",
                size=2,
                width=800,
                height=700,
                responsive=True,
                tools=["tap", "hover", "box_zoom", "wheel_zoom", "reset"],
                colorbar=True,
                clim=(vmin, vmax),
                title=f"{variable_name} - {group}",
                active_tools=["wheel_zoom"],
                hooks=[add_dynamic_sizing],
                hover_tooltips=[
                    ("Location ID", f"@{id_col}"),
                    ("Value", f"@{variable_name}"),
                    ("Lon", f"@{actual_lon}"),
                    ("Lat", f"@{actual_lat}"),
                ],
            )

            state["points_element"] = points

            # Create new highlight stream
            highlight_stream = hv.streams.Selection1D(source=points)
            state["highlight_stream"] = highlight_stream

            if "on_selection_update" in state:
                highlight_stream.add_subscriber(state["on_selection_update"])

            def update_highlight(index):
                if index and len(index) > 0:
                    location_id = int(map_data.iloc[index[0]][id_col])
                    state["selected_location_id"] = location_id
                    return _make_highlight(
                        location_id, map_data, actual_lon, actual_lat
                    )
                else:
                    state["selected_location_id"] = None
                    return hv.Overlay([])

            highlight_layer = hv.DynamicMap(
                update_highlight, streams=[highlight_stream]
            )

            basemap = gv.tile_sources.OSM.opts(
                alpha=0.6,
                width=800,
                height=700,
                responsive=True,
            )
            map_pane.object = basemap * points * highlight_layer

            # Restore zoom ranges
            if saved_ranges:

                def restore_ranges():
                    try:
                        if hasattr(map_pane, "_plots") and map_pane._plots:
                            bokeh_plot = list(map_pane._plots.values())[0]
                            if hasattr(bokeh_plot, "state"):
                                bokeh_plot.state.x_range.start = saved_ranges["x_start"]
                                bokeh_plot.state.x_range.end = saved_ranges["x_end"]
                                bokeh_plot.state.y_range.start = saved_ranges["y_start"]
                                bokeh_plot.state.y_range.end = saved_ranges["y_end"]
                    except Exception:
                        pass

                pn.state.onload(restore_ranges)

            # Restore location selection
            if saved_location_id is not None:
                try:
                    matching_rows = map_data[
                        map_data[id_col] == saved_location_id
                    ]
                    if not matching_rows.empty:
                        new_index = matching_rows.index[0]
                        pos = map_data.index.get_loc(new_index)
                        highlight_stream.event(index=[pos])
                except Exception:
                    pass

        finally:
            loading_indicator.value = False

    # =============================================================================
    # CALLBACKS
    # =============================================================================

    def on_group_change(event):
        """Handle group selection change."""
        state["last_plot_location_id"] = None

        variables = adapter.variables()
        if variables:
            variable_select.options = variables
            variable_select.value = variables[0]
        else:
            variable_select.options = []
            variable_select.value = None

    def on_variable_change(event):
        """Handle variable selection change."""
        group = group_select.value
        variable_name = event.new
        state["last_plot_location_id"] = None

        if group and variable_name:
            update_map_data(group, variable_name)

    def on_location_input_change(event):
        """Handle manual location ID input."""
        if state.get("updating_location_input", False):
            return

        location_id = event.new
        if location_id is None:
            return

        if state["map_data"] is None:
            return

        id_col = "location_id"
        matching = state["map_data"][state["map_data"][id_col] == location_id]

        if matching.empty:
            info_pane.object = (
                f"**Error:** Location ID `{location_id}` not found in current view"
            )
            return

        state["selected_location_id"] = location_id
        info_pane.object = f"**Selected Location ID:** `{location_id}`"

        highlight_stream = state.get("highlight_stream")
        if highlight_stream is not None:
            pos = state["map_data"].index.get_loc(matching.index[0])
            highlight_stream.event(index=[pos])

    # Wire up callbacks
    group_select.param.watch(on_group_change, "value")
    variable_select.param.watch(on_variable_change, "value")
    location_input.param.watch(on_location_input_change, "value")

    # =============================================================================
    # VAR SPEC EDITOR
    # =============================================================================

    # Initialize var_spec editor with available timeseries variables
    ts_variables = (
        adapter.timeseries_variables(group_select.value)
        if group_select.value
        else []
    )

    # Create editor with callback to regenerate plot on config change
    var_spec_editor = VarSpecEditor(
        available_variables=ts_variables, on_config_change=regenerate_timeseries
    )
    # Add default subplots (one per variable, creating 3 panels by default)
    for var in ts_variables[:3]:
        var_spec_editor.add_subplot(var)
    state["var_spec_editor"] = var_spec_editor

    # Use the editor's live layout (automatically updates on add/remove)
    var_spec_pane = var_spec_editor.layout

    # =============================================================================
    # INITIALIZATION
    # =============================================================================

    if group_select.value and variable_select.value:
        result = create_map(group_select.value, variable_select.value)
        map_pane.object = result

    # =============================================================================
    # LAYOUT
    # =============================================================================

    bottom_row = pn.Row(
        metrics_table_pane,
        feature_importance_pane,
        sizing_mode="fixed",
        height=420,
        styles={
            "width": "100%",
            "gap": "10px",
        },
        margin=0,
    )

    right_column = pn.Column(
        timeseries_pane,
        bottom_row,
        sizing_mode="fixed",
        styles={
            "width": "50vw",
            "height": "78vh",
            "min-width": "50vw",
            "max-width": "50vw",
            "overflow-y": "auto",
        },
    )

    main_layout = pn.Row(
        map_pane,
        right_column,
        sizing_mode="fixed",
        styles={
            "width": "100vw",
            "margin": "0",
            "padding": "0",
        },
    )

    # Collapsible var_spec editor panel
    var_spec_accordion = pn.Accordion(
        ("Timeseries Configuration", var_spec_pane),
        active=[],
    )

    return pn.Column(
        pn.pane.Markdown(
            "# Dataviewer Geo",
            sizing_mode="stretch_width",
        ),
        pn.Row(
            group_select,
            variable_select,
            location_input,
            loading_indicator,
        ),
        info_pane,
        var_spec_accordion,
        main_layout,
        sizing_mode="stretch_width",
        styles={"margin": "0", "padding": "0"},
    )


def create_app_from_config(config: DataConfig) -> pn.Column:
    """Create app from DataConfig (backward compatibility).

    This wraps the DataConfig in a BackscatterMLAdapter for existing users.

    Args:
        config: DataConfig instance pointing to backscatter ML data.

    Returns:
        Panel Column application.
    """
    from .datasets import BackscatterMLAdapter

    adapter = BackscatterMLAdapter(config)
    return create_app(adapter)


_DUMMY_DATA_DIR = Path("/tmp/dataviewer_demo_data")


def detect_data_format(data_path: Path) -> str:
    """Detect data format based on directory structure.

    Args:
        data_path: Root directory of the dataset.

    Returns:
        'backscatter' if ML format detected, 'generic' otherwise.
    """
    data_path = Path(data_path)

    # Check for backscatter ML format indicators
    lookup_files = [
        data_path / "ers_tile_id_location_id.parquet",
        data_path / "lookup.parquet",
    ]
    has_lookup = any(f.exists() for f in lookup_files)

    # Check for split directories with metrics
    has_splits = False
    if data_path.is_dir():
        for item in data_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                if (item / "metrics_global_plot").exists():
                    has_splits = True
                    break

    if has_splits and has_lookup:
        return "backscatter"

    return "generic"


def build_viewer(
    data_root: Path | str | None = None,
    data_format: str = "auto",
) -> pn.Column:
    """Build the viewer app for a data directory.

    If ``data_root`` is None, a dummy dataset is generated automatically
    in ``/tmp/dataviewer_demo_data`` so the app always runs out of the box.

    Args:
        data_root: Path to the dataset root. If None, dummy data is generated.
        data_format: One of "auto", "backscatter", "generic".

    Returns:
        Panel Column application.
    """
    from .datasets import (
        BackscatterMLAdapter,
        GenericTimeseriesAdapter,
        TimeseriesConfig,
    )

    if data_root is None:
        print(
            "No data path provided; generating a fresh dummy dataset at "
            f"{_DUMMY_DATA_DIR}...",
            flush=True,
        )
        data_root = _DUMMY_DATA_DIR
        if data_root.exists():
            import shutil

            shutil.rmtree(data_root)
        generate_dummy_data(data_root, n_locations=100, n_tiles=4)
    else:
        data_root = Path(data_root)

    fmt = data_format
    if fmt == "auto":
        fmt = detect_data_format(data_root)
        print(f"Auto-detected data format: {fmt}", flush=True)

    if fmt == "backscatter":
        config = DataConfig(root=data_root)
        adapter = BackscatterMLAdapter(config)
    else:
        config = TimeseriesConfig(root=data_root)
        adapter = GenericTimeseriesAdapter(config)

    return create_app(adapter)
