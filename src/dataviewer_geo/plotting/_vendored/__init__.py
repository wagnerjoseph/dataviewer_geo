"""Vendored plotting code from plotting_joseph.

This module contains vendored code from the plotting_joseph package
to avoid the external git dependency. The original code is MIT licensed.

Source: https://github.com/wagnerjoseph/plotting_geo.git
"""

from .timeseries import plot_time_series, Timeseries
from .config import LookupTables

__all__ = ["plot_time_series", "Timeseries", "LookupTables"]
