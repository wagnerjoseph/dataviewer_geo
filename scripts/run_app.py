#!/usr/bin/env python3
"""Run the dataviewer_geo application directly with Python.

If no --data path is given, a dummy dataset is generated automatically.

Examples:
    # Auto-generate dummy data, serve on http://localhost:5000
    python scripts/run_app.py

    # ...and open the browser automatically
    python scripts/run_app.py --show

    # Use your own data (auto-detect format) on a specific port
    python scripts/run_app.py --data /path/to/data --port 5006
"""

import argparse
import socket
from pathlib import Path

import panel as pn

from dataviewer_geo.app import build_viewer


def port_is_busy(port: int) -> bool:
    """Return True if the given port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the dataviewer_geo application"
    )
    parser.add_argument(
        "--data",
        "-d",
        type=Path,
        default=None,
        help="Path to data directory (default: generate dummy data)",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["auto", "backscatter", "generic"],
        default="auto",
        help="Data format (default: auto-detect)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=5000,
        help="Port to serve the app on (default: 5000)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the app in the browser automatically",
    )

    args = parser.parse_args()

    if port_is_busy(args.port):
        print(
            f"\n[WARNING] Port {args.port} is already in use. "
            f"Run with --port <number> to pick another port, e.g. "
            f"`python scripts/run_app.py --port {args.port + 1}`.\n"
        )

    # Build the app (auto-generates dummy data if no path given)
    app = build_viewer(data_root=args.data, data_format=args.format)

    # Serve the app
    if args.data is None:
        print("\nData directory: (auto-generated dummy data)")
    else:
        print(f"\nData directory: {args.data}")

    print(f"\nViewer running at:  http://localhost:{args.port}")
    if args.data is None:
        print("(no data path given - dummy data was generated automatically)")
    print(
        "(press Ctrl+C to stop)\n"
    )
    pn.serve(app, port=args.port, show=args.show)


if __name__ == "__main__":
    main()
