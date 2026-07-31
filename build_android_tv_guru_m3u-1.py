#!/usr/bin/env python3
"""Compatibility entry point for CI/cron: `python build_android_tv_guru_m3u-1.py`.

The real implementation lives in the android_tv_guru package (see
docs/ARCHITECTURE.md). This file exists so the GitHub Actions workflow and any
existing bookmarks/scripts referencing it keep working unchanged.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from android_tv_guru.playlists import main  # noqa: E402

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nCould not build playlists: {exc}", file=sys.stderr)
        print("Check your internet connection and try again.", file=sys.stderr)
        sys.exit(1)
