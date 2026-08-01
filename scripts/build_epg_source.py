#!/usr/bin/env python3
"""Thin CLI wrapper: match published channels against legal EPG sources.

Writes epg/grabber-input.channels.xml and reports/epg-*.csv. The real
implementation lives in android_tv_guru.epg (see docs/EPG_MATCHING.md and
docs/DATA_SOURCES.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from android_tv_guru.epg import build_and_write  # noqa: E402
from android_tv_guru.stations import StationDirectory  # noqa: E402

if __name__ == "__main__":
    try:
        stations = StationDirectory.load()
        build_and_write(stations)
    except Exception as exc:
        print(f"Could not build EPG source: {exc}", file=sys.stderr)
        sys.exit(1)
