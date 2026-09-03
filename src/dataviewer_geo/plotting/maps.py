"""Interactive map plotting for dataviewer_geo."""

import logging

import geoviews as gv
import holoviews as hv
import pandas as pd

logger = logging.getLogger(__name__)

hv.extension("bokeh")


def create_interactive_map(
    data: pd.DataFrame,
    variable: str,
    lat_col: str = "lat",
    lon_col: str = "lon",
    location_id_col: str = "location_id",
    cmap: str = "RdYlBu_r",
    width: int = 800,
    height: int = 600,
    point_size: int = 3,
    title: str | None = None,
) -> gv.Points:
    """Create an interactive GeoViews map with clickable points.

    Args:
        data: DataFrame with lat, lon, variable, and location_id columns
        variable: Name of the variable column to display
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        location_id_col: Name of location ID column
        cmap: Colormap name
        width: Plot width in pixels
        height: Plot height in pixels
        point_size: Size of points
        title: Plot title (default: variable name)

    Returns:
        GeoViews Points object with hover and click tools
    """
    if variable not in data.columns:
        raise ValueError(f"Variable '{variable}' not found in data. Available: {data.columns.tolist()}")

    if lat_col not in data.columns or lon_col not in data.columns:
        raise ValueError(f"Data must contain '{lat_col}' and '{lon_col}' columns")

    # Create Points element
    points = gv.Points(data, kdims=["lon", "lat"], vdims=[variable, location_id_col])

    # Configure styling
    plot_opts = {
        "width": width,
        "height": height,
        "color": variable,
        "cmap": cmap,
        "tools": ["hover", "tap"],
        "show_legend": True,
        "colorbar": True,
        "title": title or variable,
        "size": point_size,
    }

    points = points.opts(**plot_opts)

    return points
