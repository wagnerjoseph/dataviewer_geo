"""Interactive Panel application for dataviewer_geo."""

import logging
from typing import Any

import panel as pn
import pandas as pd

from .config import DataConfig
from .data import DataIndex, load_map_variable, load_timeseries_for_location
from .plotting.maps import create_interactive_map
from .plotting.timeseries import plot_location_timeseries

logger = logging.getLogger(__name__)

pn.extension()


def create_app(config: DataConfig) -> pn.template.FastListTemplate:
    """Create the interactive data viewer application.

    Args:
        config: DataConfig instance pointing to data root

    Returns:
        Panel FastListTemplate application
    """
    # Initialize data index
    index = DataIndex(config)

    if not index.splits:
        raise ValueError(f"No splits found in {config.root}")

    # State management
    state = {
        "selected_location_id": None,
        "selected_split": index.splits[0],
        "selected_variable": index.map_variables[0] if index.map_variables else None,
    }

    # Widgets
    split_select = pn.widgets.Select(
        name="Split",
        options=index.splits,
        value=state["selected_split"],
    )

    variable_select = pn.widgets.Select(
        name="Variable",
        options=index.map_variables if index.map_variables else ["No variables"],
        value=state["selected_variable"],
    )

    location_select = pn.widgets.Select(
        name="Location",
        options=[],
        value=None,
    )

    # Reactive data storage
    def update_location_options(split: str) -> None:
        """Update location dropdown based on selected split."""
        locations_df = index.get_locations_for_split(split)
        if locations_df is not None:
            location_options = {
                f"Loc {loc_id}": loc_id for loc_id in locations_df["location_id"].values[:1000]
            }
            location_select.options = location_options
            if location_options:
                location_select.value = next(iter(location_options.values()))
        else:
            location_select.options = []
            location_select.value = None

    def update_map(split: str, variable: str) -> Any:
        """Update the map display."""
        if not variable:
            return None

        try:
            # Load map data for the variable
            map_df_dict = load_map_variable(config, split, variable)

            if isinstance(map_df_dict, dict):
                # Combine all tiles
                map_df = pd.concat(map_df_dict.values(), ignore_index=True)
            else:
                map_df = map_df_dict

            if map_df.empty:
                logger.warning(f"No data found for {split}/{variable}")
                return None

            # Create interactive map
            map_plot = create_interactive_map(
                data=map_df,
                variable=variable,
                location_id_col="location_id",
            )

            # Add tap callback
            def tap_handler(event):
                if event.y is not None:
                    # Get clicked location
                    points = map_plot.iloc[:, 0]
                    distances = ((points.dimension_values(0) - event.x) ** 2 + (points.dimension_values(1) - event.y) ** 2) ** 0.5
                    if len(distances) > 0:
                        closest_idx = distances.argmin()
                        location_id = points.dimension_values(2)[closest_idx]
                        state["selected_location_id"] = location_id
                        location_select.value = location_id

            map_plot.on_event("tap", tap_handler)

            return map_plot

        except Exception as e:
            logger.error(f"Error creating map: {e}")
            return None

    def update_timeseries(location_id: int | None, split: str, variable: str) -> Any:
        """Update the timeseries plot."""
        if location_id is None:
            return None

        try:
            # Load timeseries data
            ts_df = load_timeseries_for_location(config, split, location_id)

            if ts_df.empty:
                logger.warning(f"No timeseries data for location {location_id}")
                return None

            # Plot timeseries
            fig = plot_location_timeseries(
                data=ts_df,
                variables=variable,
                location_id=location_id,
                split_name=split,
            )

            return fig

        except Exception as e:
            logger.error(f"Error creating timeseries: {e}")
            return None

    # Callbacks
    @pn.depends(split_select.param.value)
    def on_split_change(split: str) -> None:
        state["selected_split"] = split
        update_location_options(split)
        # Update variable options based on split
        variable_select.options = index.map_variables if index.map_variables else ["No variables"]

    @pn.depends(variable_select.param.value)
    def on_variable_change(variable: str) -> None:
        state["selected_variable"] = variable

    @pn.depends(location_select.param.value)
    def on_location_change(location_id: int | None) -> None:
        state["selected_location_id"] = location_id

    # Create layout
    map_panel = pn.bind(update_map, split_select, variable_select)
    timeseries_panel = pn.bind(
        update_timeseries, location_select, split_select, variable_select
    )

    # Main layout
    sidebar = pn.Column(
        pn.pane.Markdown("## Data Viewer"),
        pn.pane.Markdown("### Controls"),
        split_select,
        variable_select,
        location_select,
        pn.pane.Markdown("### Instructions"),
        pn.pane.Markdown(
            """
            1. Select a **split** (time period)
            2. Choose a **variable** to display
            3. Click on a point on the map or use the **location** dropdown
            4. View the **timeseries** for the selected location
            """
        ),
    )

    main_area = pn.Row(
        pn.Column(map_panel, height=600),
        pn.Column(timeseries_panel, height=600),
    )

    app = pn.template.FastListTemplate(
        title="Data Viewer",
        sidebar=sidebar,
        main=main_area,
        header_background="#2c3e50",
    )

    return app
