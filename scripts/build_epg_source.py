#!/usr/bin/env python3
"""Match our published channels against legal, public EPG sources and produce:

  - epg/grabber-input.channels.xml  (input for iptv-org/epg's `grab` command;
    see scripts/generate_epg.sh)
  - reports/epg-matches.csv
  - reports/epg-unmatched.csv
  - reports/epg-conflicts.csv
  - reports/epg-coverage.csv

See docs/DATA_SOURCES.md for the full source research. Summary:

  - tvguide.com: the source our existing (now-dead) x-tvg-url pointed at.
    153 channels, mostly national/cable networks. Grabbed via iptv-org/epg's
    open-source (Unlicense) grabber, same as IPTV-org used to run centrally.
  - i.mjh.nz (Roku, Pluto TV, PBS, Plex, Samsung TV Plus, MeTV): a
    well-established, openly published (GitHub) project that mirrors these
    platforms' own official app-facing APIs — not scraped from a commercial
    listings aggregator. Crucially, Roku Channel rebroadcasts many U.S. local
    affiliates with real EPG data, giving us legal LOCAL station coverage
    that tvguide.com alone does not have. Subscription-only i.mjh.nz
    providers (Foxtel, Kayo, Sky, DStv, Binge, Singtel) are excluded — we
    only use the free, ad-supported ones.

Matching tiers (never guess on a low-confidence signal):
  1. exact_channel_id  - the source's xmltv_id (base, before any "@feed"
                          suffix) equals our IPTV-org channel id exactly.
  2. call_sign_in_name  - (i.mjh.nz entries with no xmltv_id filled in only)
                          our extracted call sign appears as a whole word in
                          the source's display name, AND our channel is a US
                          channel with a syntactically valid call sign.
  Anything else is left unmatched — never inferred from a shared network.

Conflict detection compares the matched source's display name against our
Wikidata-derived station city (data/us_tv_stations.json); a station whose
known city is not a substring of the matched source's name is flagged for
manual review, not auto-corrected.
"""

import csv
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from callsigns import extract_callsign  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MASTER_PLAYLIST = ROOT / "AndroidTVGuru.m3u"
STATIONS_PATH = ROOT / "data" / "us_tv_stations.json"
GRABBER_INPUT_PATH = ROOT / "epg" / "grabber-input.channels.xml"
REPORTS_DIR = ROOT / "reports"

RAW_BASE = "https://raw.githubusercontent.com/iptv-org/epg/master/sites"

# (source_label, raw path, site attribute override or None to use the file's own)
SOURCES = [
    ("tvguide.com", f"{RAW_BASE}/tvguide.com/tvguide.com.channels.xml"),
    ("i.mjh.nz/roku", f"{RAW_BASE}/i.mjh.nz/i.mjh.nz_roku.channels.xml"),
    ("i.mjh.nz/pluto", f"{RAW_BASE}/i.mjh.nz/i.mjh.nz_pluto.channels.xml"),
    ("i.mjh.nz/pbs", f"{RAW_BASE}/i.mjh.nz/i.mjh.nz_pbs.channels.xml"),
    ("i.mjh.nz/plex", f"{RAW_BASE}/i.mjh.nz/i.mjh.nz_plex.channels.xml"),
    ("i.mjh.nz/samsung", f"{RAW_BASE}/i.mjh.nz/i.mjh.nz_samsung.channels.xml"),
    ("i.mjh.nz/metv", f"{RAW_BASE}/i.mjh.nz/i.mjh.nz_metv.channels.xml"),
]

# Priority when the same base id is available from more than one source.
SOURCE_PRIORITY = [label for label, _ in SOURCES]

# Within a single source, prefer a feed suffix in this order when the same
# base id appears more than once (avoids emitting duplicate xmltv_ids).
FEED_PRIORITY = ["", "HD", "East", "SD", "West"]

USER_AGENT = "AndroidTVGuruEPGBuilder/1.0 (https://github.com/7000premiumchannels/android-tv-guru-playlists)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def base_id_and_feed(xmltv_id):
    if not xmltv_id:
        return None, None
    if "@" in xmltv_id:
        base, feed = xmltv_id.split("@", 1)
        return base, feed
    return xmltv_id, ""


def load_source_rows(label, url):
    xml_bytes = fetch(url)
    root = ET.fromstring(xml_bytes)
    rows = []
    for el in root.findall("channel"):
        rows.append(
            {
                "source": label,
                "site": el.get("site"),
                "site_id": el.get("site_id"),
                "xmltv_id": el.get("xmltv_id") or "",
                "display_name": (el.text or "").strip(),
            }
        )
    return rows


def our_channel_universe():
    text = MASTER_PLAYLIST.read_text(encoding="utf-8")
    ids = set(re.findall(r'tvg-id="([^"]*)"', text))
    names = dict(re.findall(r'tvg-id="([^"]*)" tvg-name="([^"]*)"', text))
    return ids, names


def build_exact_index(all_rows):
    index = defaultdict(list)
    for row in all_rows:
        base, feed = base_id_and_feed(row["xmltv_id"])
        if not base:
            continue
        index[base].append({**row, "feed": feed})
    return index


def pick_best(rows_for_id):
    def key(row):
        try:
            source_rank = SOURCE_PRIORITY.index(row["source"])
        except ValueError:
            source_rank = len(SOURCE_PRIORITY)
        try:
            feed_rank = FEED_PRIORITY.index(row["feed"])
        except ValueError:
            feed_rank = len(FEED_PRIORITY)
        return (source_rank, feed_rank)

    return sorted(rows_for_id, key=key)[0]


def build_name_index(all_rows):
    """Entries with no xmltv_id at all — candidates for call-sign matching."""
    return [row for row in all_rows if not row["xmltv_id"]]


_WORD_RE = re.compile(r"[A-Z0-9]+")


def name_contains_call_sign(display_name, call_sign):
    tokens = set(_WORD_RE.findall(display_name.upper()))
    return call_sign.call_sign in tokens


def find_conflict(channel_id, call_sign, display_name, stations):
    if not call_sign:
        return None
    station = stations.get(call_sign.normalized_call_sign)
    if not station:
        return None
    if station["city"].lower() not in display_name.lower():
        return {
            "channel_id": channel_id,
            "call_sign": call_sign.normalized_call_sign,
            "matched_display_name": display_name,
            "known_city": station["city"],
            "known_state": station["state"],
            "reason": "known station city not found in matched EPG source's display name",
        }
    return None


def main():
    print("Fetching EPG source channel lists...")
    all_rows = []
    for label, url in SOURCES:
        rows = load_source_rows(label, url)
        print(f"  {label}: {len(rows)} channels")
        all_rows.extend(rows)

    exact_index = build_exact_index(all_rows)
    name_index = build_name_index(all_rows)

    stations = {}
    if STATIONS_PATH.exists():
        for record in json.loads(STATIONS_PATH.read_text(encoding="utf-8")):
            stations[record["normalized_call_sign"]] = record

    channel_ids, names = our_channel_universe()
    print(f"\nOur published channel universe: {len(channel_ids)} unique channel ids")

    matches = []
    unmatched = []
    conflicts = []
    seen_output_ids = set()

    for channel_id in sorted(channel_ids):
        display_name = names.get(channel_id, channel_id)
        call_sign = extract_callsign(display_name) if channel_id.endswith(".us") else None

        chosen = None
        method = None
        confidence = None
        reason = None

        if channel_id in exact_index:
            chosen = pick_best(exact_index[channel_id])
            method = "exact_channel_id"
            confidence = "high"
            reason = f"channel id matched verbatim in {chosen['source']} guide-source list"
        elif call_sign is not None:
            for row in name_index:
                if row["source"].startswith("i.mjh.nz") and name_contains_call_sign(row["display_name"], call_sign):
                    chosen = row
                    method = "call_sign_in_name"
                    confidence = "medium"
                    reason = (
                        f"call sign {call_sign.call_sign!r} found as a whole word in "
                        f"{row['source']} display name {row['display_name']!r}"
                    )
                    break

        if chosen is None:
            unmatched.append(
                {
                    "channel_id": channel_id,
                    "call_sign": call_sign.normalized_call_sign if call_sign else "",
                    "display_name": display_name,
                    "reason": "no EPG source lists this channel id or call sign",
                }
            )
            continue

        if channel_id in seen_output_ids:
            # Same base id matched twice (shouldn't happen given pick_best,
            # but guard against it explicitly so we never emit duplicates).
            continue
        seen_output_ids.add(channel_id)

        matches.append(
            {
                "channel_id": channel_id,
                "call_sign": call_sign.normalized_call_sign if call_sign else "",
                "display_name": display_name,
                "source": chosen["source"],
                "site": chosen["site"],
                "site_id": chosen["site_id"],
                "match_method": method,
                "confidence": confidence,
                "reason": reason,
            }
        )

        conflict = find_conflict(channel_id, call_sign, chosen["display_name"], stations)
        if conflict:
            conflicts.append(conflict)

    REPORTS_DIR.mkdir(exist_ok=True)
    _write_csv(
        REPORTS_DIR / "epg-matches.csv",
        ["channel_id", "call_sign", "display_name", "source", "site", "site_id", "match_method", "confidence", "reason"],
        matches,
    )
    _write_csv(
        REPORTS_DIR / "epg-unmatched.csv",
        ["channel_id", "call_sign", "display_name", "reason"],
        unmatched,
    )
    _write_csv(
        REPORTS_DIR / "epg-conflicts.csv",
        ["channel_id", "call_sign", "matched_display_name", "known_city", "known_state", "reason"],
        conflicts,
    )

    total = len(channel_ids)
    matched_count = len(matches)
    unmatched_count = len(unmatched)
    coverage_after = round(100 * matched_count / total, 2) if total else 0.0
    _write_csv(
        REPORTS_DIR / "epg-coverage.csv",
        ["metric", "value"],
        [
            {"metric": "total_channels", "value": total},
            {"metric": "matched_channels", "value": matched_count},
            {"metric": "unmatched_channels", "value": unmatched_count},
            {"metric": "conflicts", "value": len(conflicts)},
            {"metric": "coverage_before_percent", "value": 0.0},
            {"metric": "coverage_after_percent", "value": coverage_after},
        ],
    )

    GRABBER_INPUT_PATH.parent.mkdir(exist_ok=True)
    write_grabber_input(matches)

    print(f"\nTotal channels: {total}")
    print(f"Matched: {matched_count} ({coverage_after}%)")
    print(f"Unmatched: {unmatched_count}")
    print(f"Conflicts: {len(conflicts)}")
    print(f"Wrote grabber input: {GRABBER_INPUT_PATH}")


def write_grabber_input(matches):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<channels>"]
    for m in matches:
        name = m["display_name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cid = m["channel_id"].replace('"', "&quot;")
        lines.append(
            f'  <channel site="{m["site"]}" site_id="{m["site_id"]}" lang="en" xmltv_id="{cid}">{name}</channel>'
        )
    lines.append("</channels>")
    GRABBER_INPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Could not build EPG source: {exc}", file=sys.stderr)
        sys.exit(1)
