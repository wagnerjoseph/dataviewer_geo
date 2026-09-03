"""Timeseries plotting for dataviewer_geo.

Wraps plotting_joseph's plot_time_series function for integration with Panel.
"""

import logging

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def plot_location_timeseries(
    data: pd.DataFrame,
    variables: list[str] | str | None = None,
    time_col: str = "time",
    location_id: int | str | None = None,
    split_name: str | None = None,
    **kwargs,
) -> plt.Figure:
    """Plot timeseries data for a location.

    Wrapper around plotting_joseph's plot_time_series function.

    Args:
        data: DataFrame with time column and variable columns
        variables: Variable name(s) to plot (if None, plots all numeric columns)
        time_col: Name of time column
        location_id: Optional location ID for title
        split_name: Optional split name for title
        **kwargs: Additional arguments passed to plotting_joseph.plot_time_series

    Returns:
        Matplotlib Figure object
    """
    try:
        from plotting_joseph import plot_time_series
    except ImportError as e:
        logger.error(f"Could not import plotting_joseph: {e}")
        raise ImportError(
            "plotting_joseph is required. Install with: pip install plotting-joseph"
        ) from e

    # Prepare data
    df = data.copy()
    if time_col not in df.columns:
        raise ValueError(f"Time column '{time_col}' not found in data. Available: {df.columns.tolist()}")

    # Ensure time is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = pd.to_datetime(df[time_col])

    # Select variables
    if variables is None:
        # Get all numeric columns except time
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        variables = [c for c in numeric_cols if c != time_col]
    elif isinstance(variables, str):
        variables = [variables]

    # Filter to available variables
    available_vars = [v for v in variables if v in df.columns]
    if not available_vars:
        raise ValueError(f"No variables found in data. Requested: {variables}, Available: {df.columns.tolist()}")

    # Build title
    title_parts = []
    if location_id is not None:
        title_parts.append(f"Location {location_id}")
    if split_name:
        title_parts.append(f"({split_name})")

    # Call plotting_joseph's function
    fig = plot_time_series(
        data=df,
        location_ids=[location_id] if location_id is not None else None,
        **kwargs,
    )

    return fig
