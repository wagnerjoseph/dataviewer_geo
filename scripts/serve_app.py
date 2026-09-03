#!/usr/bin/env python3
"""Serve the dataviewer_geo application with `panel serve`.

This is the target for the `panel serve` command. The app is built and
registered with .servable() at module level (no __main__ guard) because
Panel runs this file as a module, not as the main script.

If DATAVIEWER_DATA is unset, a dummy dataset is generated automatically.

Usage:
    # Auto-generate dummy data
    panel serve scripts/serve_app.py --show --port 5006

    # Use your own data (auto-detect format)
    DATAVIEWER_DATA=/path/to/data panel serve scripts/serve_app.py --show --port 5006

    # Force a specific format
    DATAVIEWER_DATA=/path/to/data DATAVIEWER_FORMAT=backscatter \
        panel serve scripts/serve_app.py --show --port 5006
"""

import os
from pathlib import Path

from dataviewer_geo.app import build_viewer

data_root = os.environ.get("DATAVIEWER_DATA")
data_format = os.environ.get("DATAVIEWER_FORMAT", "auto")

app = build_viewer(
    data_root=Path(data_root) if data_root else None,
    data_format=data_format,
)
print("Viewer is ready. Open http://localhost:<port>/serve_app in your browser.", flush=True)
app.servable()
