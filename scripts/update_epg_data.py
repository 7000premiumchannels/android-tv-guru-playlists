#!/usr/bin/env python3
"""Refresh data/epg-guides-index.json — a trimmed snapshot of IPTV-org's public
guide-source index (https://iptv-org.github.io/api/guides.json), filtered to
U.S. local-station-shaped channel ids.

Why a trimmed local snapshot instead of always fetching live:
  - The full guides.json is ~180,000 rows / ~25MB, covering every channel and
    guide site IPTV-org's grabbers know about worldwide; Phase 1 only cares
    about U.S. local-station coverage.
  - Committing a small, filtered snapshot keeps `android_tv_guru.epg`
    reproducible offline (tests, CI without network) while the main builder
    (build_android_tv_guru_m3u-1.py) still refreshes this file from the live
    API each run before generating reports.

This script does not fetch or scrape any programme data, and does not touch
tvpassport.com/tvtv.us/etc. directly — it only reads IPTV-org's own already
public, already hosted index of which sites configure a guide for which
channel id. See docs/EPG_MATCHING.md and docs/DATA_SOURCES.md.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

GUIDES_API_URL = "https://iptv-org.github.io/api/guides.json"
OUT = Path(__file__).resolve().parent.parent / "data" / "epg-guides-index.json"
USER_AGENT = "AndroidTVGuruPlaylistBuilder/2.0 (https://github.com/7000premiumchannels/android-tv-guru-playlists)"

# Coarse prefilter matching U.S. local-station-shaped channel ids (no spaces/
# hyphens the way channel ids are written, e.g. "WABCTV71.us", "K30FZD41.us").
_LOCAL_ID_RE = re.compile(r"^[KW]([A-Z]{2,3}|\d{2}[A-Z]{2})")


def main():
    req = urllib.request.Request(GUIDES_API_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response:
        rows = json.load(response)

    filtered = [row for row in rows if row.get("channel") and _LOCAL_ID_RE.match(row["channel"])]

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(filtered, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(filtered)} guide-source rows (of {len(rows)} total) to {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Could not refresh EPG guide index: {exc}", file=sys.stderr)
        sys.exit(1)
