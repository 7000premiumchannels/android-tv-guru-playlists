#!/usr/bin/env python3
"""Thin CLI wrapper: refresh data/us_tv_stations.json.

The real implementation lives in android_tv_guru.stations (see
docs/DATA_SOURCES.md for the Wikidata source decision, and
docs/ARCHITECTURE.md for why this is a thin wrapper).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from android_tv_guru.stations import DEFAULT_PATH, build_station_directory  # noqa: E402

if __name__ == "__main__":
    try:
        count = build_station_directory()
        print(f"\nWrote {count} station records to {DEFAULT_PATH}")
    except Exception as exc:
        print(f"Could not build station data: {exc}", file=sys.stderr)
        sys.exit(1)
