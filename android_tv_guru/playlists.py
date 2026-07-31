"""Build the Android TV Guru master, category, and state playlists.

Orchestrates: android_tv_guru.callsigns, .stations, .grouping, .epg.
"""

import csv
import json
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from . import epg as epg_module
from . import grouping
from .callsigns import extract_callsign
from .stations import US_STATE_NAMES, StationDirectory

API = "https://iptv-org.github.io/api"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "AndroidTVGuru.m3u"
PLAYLISTS_DIR = ROOT / "playlists"
STATES_DIR = PLAYLISTS_DIR / "states"
REPORTS_DIR = ROOT / "reports"
EPG_INDEX_PATH = ROOT / "data" / "epg-guides-index.json"
EPG_HEADER = '#EXTM3U x-tvg-url="https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml"\n'

CATEGORY_FILES = {
    "US_Networks.m3u": {
        "US Local - ABC", "US Local - CBS", "US Local - NBC",
        "US Local - FOX", "US Local - CW", "US Local - PBS",
    },
    "US_ABC.m3u": {"US Local - ABC"},
    "US_CBS.m3u": {"US Local - CBS"},
    "US_NBC.m3u": {"US Local - NBC"},
    "US_FOX.m3u": {"US Local - FOX"},
    "US_CW.m3u": {"US Local - CW"},
    "US_PBS.m3u": {"US Local - PBS"},
    "US_Spanish_Networks.m3u": {"US Local - Telemundo", "US Local - Univision"},
    "US_News_Weather.m3u": {"US News & Weather"},
    "Movies_Classic_TV.m3u": {"Movies & Classic TV"},
    "Kids_Family.m3u": {"Kids & Family"},
    "Sports.m3u": {"Sports & Highlights"},
    "Music.m3u": {"Music"},
    "Religious.m3u": {"Religious"},
    "Spanish.m3u": {"Spanish"},
    "African_Caribbean.m3u": {"African & Caribbean"},
}

LOCAL_GROUPS = {
    "US Local - ABC", "US Local - CBS", "US Local - NBC", "US Local - FOX",
    "US Local - CW", "US Local - PBS", "US Local - Telemundo", "US Local - Univision",
}


def get_json(name):
    req = urllib.request.Request(
        f"{API}/{name}.json",
        headers={"User-Agent": "Android-TV-Guru-Playlist-Builder/2.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def safe(value):
    return str(value or "").replace('"', "'").replace("\n", " ").strip()


def is_valid_stream_url(url):
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


@dataclass
class Entry:
    channel_id: str
    country: str
    group: str
    display_name: str
    tvg_id: str
    tvg_logo: str
    url: str
    network_label: Optional[str]
    call_sign: Optional[str]
    station_confident: bool
    state_code: Optional[str]
    city: Optional[str]

    @property
    def sort_name(self):
        return self.display_name.lower()

    def m3u_block(self, group_override=None):
        group = group_override or self.group
        name = safe(self.display_name)
        return (
            f'#EXTINF:-1 tvg-id="{safe(self.tvg_id)}" tvg-name="{name}" '
            f'tvg-logo="{safe(self.tvg_logo)}" group-title="{safe(group)}",{name}\n'
            f'{self.url}\n'
        )


def build_entries(channels, streams, stations: StationDirectory) -> List[Entry]:
    channel_by_id = {c["id"]: c for c in channels if c.get("id")}
    seen_urls = set()
    entries = []

    for stream in streams:
        channel_id = stream.get("channel")
        url = stream.get("url")
        if not channel_id or not is_valid_stream_url(url) or url in seen_urls:
            continue

        channel = channel_by_id.get(channel_id)
        if not channel or channel.get("is_nsfw"):
            continue

        seen_urls.add(url)

        group = grouping.determine_group(channel)
        network_label = None
        if group.startswith("US Local - "):
            network_label = group[len("US Local - "):]

        call_sign_info = extract_callsign(channel.get("name")) if channel.get("country") == "US" else None
        call_sign = call_sign_info.normalized_call_sign if call_sign_info else None

        station = stations.lookup(call_sign) if call_sign else None
        station_confident = station is not None and network_label is not None

        display_name = channel.get("name")
        state_code = None
        city = None
        if station_confident:
            state_code = station["state"]
            city = station["city"]
            display_name = f"{call_sign} — {city}, {state_code}"

        entries.append(
            Entry(
                channel_id=channel_id,
                country=channel.get("country"),
                group=group,
                display_name=display_name,
                tvg_id=channel.get("id"),
                tvg_logo=channel.get("logo"),
                url=url,
                network_label=network_label,
                call_sign=call_sign,
                station_confident=station_confident,
                state_code=state_code,
                city=city,
            )
        )

    return entries


def write_playlist(path: Path, blocks: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EPG_HEADER + "".join(blocks), encoding="utf-8")


def write_master_and_categories(entries: List[Entry]):
    ordered = sorted(entries, key=lambda e: (grouping.sort_key(e.group), e.sort_name))
    write_playlist(OUT, [e.m3u_block() for e in ordered])

    PLAYLISTS_DIR.mkdir(exist_ok=True)
    for filename, groups in CATEGORY_FILES.items():
        filtered = [e for e in ordered if e.group in groups]
        write_playlist(PLAYLISTS_DIR / filename, [e.m3u_block() for e in filtered])

    return ordered


def write_state_playlists(entries: List[Entry]):
    STATES_DIR.mkdir(parents=True, exist_ok=True)

    confident_locals = [e for e in entries if e.group in LOCAL_GROUPS and e.station_confident]

    def local_sort_key(e):
        return (
            grouping.GROUP_ORDER_INDEX.get(e.group, 999),
            e.state_code or "",
            e.city or "",
            e.call_sign or "",
        )

    all_locals_sorted = sorted(confident_locals, key=local_sort_key)
    write_playlist(STATES_DIR.parent / "US_Locals_All.m3u", [e.m3u_block() for e in all_locals_sorted])

    by_state = defaultdict(list)
    for e in confident_locals:
        by_state[e.state_code].append(e)

    # The Phase 1 spec's state-playlist list runs Alabama..Wyoming (the 50
    # states only); DC is excluded from file generation even though it
    # remains in US_STATE_NAMES for display-name purposes elsewhere.
    for code, name in sorted(US_STATE_NAMES.items(), key=lambda kv: kv[1]):
        if code == "DC":
            continue
        state_entries = sorted(by_state.get(code, []), key=local_sort_key)
        blocks = [
            e.m3u_block(group_override=f"{e.group} - {name}")
            for e in state_entries
        ]
        write_playlist(STATES_DIR / f"{name}.m3u", blocks)

    return confident_locals, by_state


def run_epg_matching(entries: List[Entry]):
    guide_rows = []
    if EPG_INDEX_PATH.exists():
        guide_rows = json.loads(EPG_INDEX_PATH.read_text(encoding="utf-8"))
    guide_index = epg_module.build_guide_index(guide_rows)
    overrides = epg_module.load_overrides()

    local_entries = [e for e in entries if e.group in LOCAL_GROUPS]

    matches = []
    conflicts = []
    for e in local_entries:
        station = None
        if e.station_confident:
            station = {"city": e.city, "state": e.state_code}
        match = epg_module.match_channel(
            channel_id=e.channel_id,
            call_sign=e.call_sign,
            display_name=e.display_name,
            station=station,
            guide_index=guide_index,
            overrides=overrides,
        )
        matches.append(match)

        rows = guide_index.get(e.channel_id, [])
        conflicts.extend(epg_module.find_conflicts(e.channel_id, rows, station))

    return matches, conflicts


def _write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_epg_reports(matches, conflicts):
    match_fields = [
        "channel_id", "call_sign", "display_name", "city", "state",
        "original_tvg_id", "selected_epg_id", "source_name", "match_method",
        "confidence", "reason",
    ]
    matched_rows = [vars(m) for m in matches if m.match_method != "unmatched"]
    unmatched_rows = [vars(m) for m in matches if m.match_method == "unmatched"]

    _write_csv(REPORTS_DIR / "epg-matches.csv", match_fields, matched_rows)
    _write_csv(REPORTS_DIR / "epg-unmatched.csv", match_fields, unmatched_rows)
    _write_csv(
        REPORTS_DIR / "epg-conflicts.csv",
        ["channel_id", "site", "site_name", "known_city", "known_state", "reason"],
        conflicts,
    )

    coverage = defaultdict(int)
    for m in matches:
        key = m.source_name or "unmatched"
        coverage[key] += 1
    coverage_rows = [{"source_name": k, "channel_count": v} for k, v in sorted(coverage.items(), key=lambda kv: -kv[1])]
    _write_csv(REPORTS_DIR / "epg-source-coverage.csv", ["source_name", "channel_count"], coverage_rows)

    return matched_rows, unmatched_rows, conflicts


def main():
    print("Downloading current public IPTV-org data...")
    channels = get_json("channels")
    streams = get_json("streams")
    get_json("cities")  # fetched per spec; not used for city/state resolution
    get_json("subdivisions")  # fetched per spec; not used for city/state resolution

    stations = StationDirectory.load()
    print(f"Loaded {len(stations)} U.S. station records for confident local matching.")

    entries = build_entries(channels, streams, stations)
    ordered = write_master_and_categories(entries)
    confident_locals, by_state = write_state_playlists(entries)
    matches, conflicts = run_epg_matching(entries)
    matched_rows, unmatched_rows, conflict_rows = write_epg_reports(matches, conflicts)

    counts = defaultdict(int)
    for e in ordered:
        counts[e.group] += 1

    print(f"\nCreated: {OUT.resolve()}")
    print(f"Total public streams: {len(ordered)}")
    for group in sorted(counts):
        print(f"  {group}: {counts[group]}")

    print(f"\nCreated {len(CATEGORY_FILES)} category playlists in {PLAYLISTS_DIR.resolve()}")
    print(f"Confidently matched local stations: {len(confident_locals)} across {len(by_state)} states")
    print(f"EPG matches: {len(matched_rows)}  unmatched: {len(unmatched_rows)}  conflicts: {len(conflict_rows)}")

    return {
        "entries": ordered,
        "confident_locals": confident_locals,
        "matches": matched_rows,
        "unmatched": unmatched_rows,
        "conflicts": conflict_rows,
    }


if __name__ == "__main__":
    main()
