"""Production EPG: match our published channels to legal EPG sources, drive
the actual XMLTV grab, and merge the results into AndroidTVGuru.xml(.gz).

See docs/DATA_SOURCES.md for the source research and docs/EPG_MATCHING.md for
the full matching-tier rationale. Summary:

  - tvguide.com: grabbed via iptv-org/epg's open-source (Unlicense) grabber,
    the same source our playlist's guide URL referenced before it went dead
    (see docs/DATA_SOURCES.md for that history). ~150 national/cable
    channels.
  - i.mjh.nz (Roku, Pluto TV, PBS, Plex, Samsung TV Plus, MeTV): a
    third-party, independently-run public GitHub project (owner:
    `matthuisman`) that mirrors data derived from these free, ad-supported
    streaming platforms' apps. This is NOT an official source published by
    Roku/Pluto/PBS/Plex/Samsung, and its redistribution terms are not
    formally documented anywhere we could find — see docs/DATA_SOURCES.md
    for the full, honest evaluation. It is, however, the only source we
    found with real U.S. local-affiliate programme data that doesn't involve
    scraping a commercial listings aggregator (tvtv.us/tvpassport.com/
    Zap2it) or a paid, redistribution-restricted service (Schedules Direct).
    Subscription-only i.mjh.nz providers (Foxtel, Kayo, Sky, DStv, Binge,
    Singtel) are excluded.

Matching tiers (never guess on a low-confidence signal):
  1. manual_override   - data/epg-overrides.json (human-reviewed, exact)
  2. exact_channel_id  - the source's xmltv_id (base, before any "@feed"
                         suffix) equals our IPTV-org channel id exactly.
  3. call_sign_in_name - (i.mjh.nz entries with no xmltv_id filled in only)
                         our extracted call sign appears as a whole word in
                         the source's display name, AND our channel is a US
                         channel with a syntactically valid call sign.
  Anything else is left unmatched — never inferred from a shared network.

This module also merges grabbed per-source XMLTV fragments into a single
AndroidTVGuru.xml/.xml.gz, guarding against duplicate channel ids and
programmes that reference a channel not present in the merged output.
"""

import csv
import gzip
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
MASTER_PLAYLIST = ROOT / "AndroidTVGuru.m3u"
OVERRIDES_PATH = ROOT / "data" / "epg-overrides.json"
GRABBER_INPUT_PATH = ROOT / "epg" / "grabber-input.channels.xml"
REPORTS_DIR = ROOT / "reports"

RAW_BASE = "https://raw.githubusercontent.com/iptv-org/epg/master/sites"

# (source_label, raw channel-list URL). See docs/DATA_SOURCES.md for why
# each of these is here and what was rejected.
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

_WORD_RE = re.compile(r"[A-Z0-9]+")


@dataclass
class EpgMatch:
    channel_id: str
    call_sign: str
    display_name: str
    city: Optional[str]
    state: Optional[str]
    source: str
    site: str
    site_id: str
    match_method: str
    confidence: str
    reason: str


# ---------------------------------------------------------------------------
# Fetching source channel lists (no programme data — just "what's available")
# ---------------------------------------------------------------------------


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def load_source_rows(label: str, url: str) -> List[dict]:
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


def fetch_all_source_rows(sources=SOURCES) -> List[dict]:
    all_rows = []
    for label, url in sources:
        all_rows.extend(load_source_rows(label, url))
    return all_rows


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def load_overrides(path: Path = OVERRIDES_PATH) -> Dict[str, dict]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["channel_id"]: entry for entry in data.get("overrides", [])}


def base_id_and_feed(xmltv_id: Optional[str]):
    if not xmltv_id:
        return None, None
    if "@" in xmltv_id:
        base, feed = xmltv_id.split("@", 1)
        return base, feed
    return xmltv_id, ""


def build_exact_index(all_rows: List[dict]) -> Dict[str, List[dict]]:
    index = defaultdict(list)
    for row in all_rows:
        base, feed = base_id_and_feed(row["xmltv_id"])
        if not base:
            continue
        index[base].append({**row, "feed": feed})
    return index


def build_name_index(all_rows: List[dict]) -> List[dict]:
    """Entries with no xmltv_id at all — candidates for call-sign matching."""
    return [row for row in all_rows if not row["xmltv_id"]]


def pick_best(rows_for_id: List[dict]) -> dict:
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


def name_contains_call_sign(display_name: str, call_sign) -> bool:
    tokens = set(_WORD_RE.findall(display_name.upper()))
    return call_sign.call_sign in tokens


def find_conflict(channel_id: str, call_sign, display_name: str, station: Optional[dict]) -> Optional[dict]:
    """Flag a match whose display name doesn't contain the channel's known
    station city. Only runs when we actually have station data to compare
    against — we never guess a conflict we can't verify.
    """
    if not call_sign or not station or not station.get("city"):
        return None
    if station["city"].lower() not in display_name.lower():
        return {
            "channel_id": channel_id,
            "call_sign": call_sign.normalized_call_sign,
            "matched_display_name": display_name,
            "known_city": station["city"],
            "known_state": station.get("state"),
            "reason": "known station city not found in matched EPG source's display name",
        }
    return None


def our_channel_universe(master_playlist: Path = MASTER_PLAYLIST):
    text = master_playlist.read_text(encoding="utf-8")
    ids = set(re.findall(r'tvg-id="([^"]*)"', text))
    names = dict(re.findall(r'tvg-id="([^"]*)" tvg-name="([^"]*)"', text))
    return ids, names


def match_all_channels(channel_ids, names, stations, source_rows, overrides=None):
    """Match every channel id against the given source rows.

    `stations` is an android_tv_guru.stations.StationDirectory (or any object
    with a .lookup(normalized_call_sign) method returning a dict or None).
    Returns (matches: list[EpgMatch], unmatched: list[dict], conflicts: list[dict]).
    """
    from .callsigns import extract_callsign

    overrides = overrides or {}
    exact_index = build_exact_index(source_rows)
    name_index = build_name_index(source_rows)

    matches: List[EpgMatch] = []
    unmatched: List[dict] = []
    conflicts: List[dict] = []
    seen_output_ids = set()

    for channel_id in sorted(channel_ids):
        display_name = names.get(channel_id, channel_id)
        call_sign = extract_callsign(display_name) if channel_id.endswith(".us") else None
        station = stations.lookup(call_sign.normalized_call_sign) if call_sign else None
        city = station.get("city") if station else None
        state = station.get("state") if station else None

        if channel_id in overrides:
            override = overrides[channel_id]
            if channel_id in seen_output_ids:
                continue
            seen_output_ids.add(channel_id)
            matches.append(
                EpgMatch(
                    channel_id=channel_id,
                    call_sign=call_sign.normalized_call_sign if call_sign else "",
                    display_name=display_name,
                    city=city,
                    state=state,
                    source="manual_override",
                    site="manual_override",
                    site_id=override.get("epg_id", ""),
                    match_method="manual_override",
                    confidence="high",
                    reason="present in data/epg-overrides.json",
                )
            )
            continue

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
            continue
        seen_output_ids.add(channel_id)

        matches.append(
            EpgMatch(
                channel_id=channel_id,
                call_sign=call_sign.normalized_call_sign if call_sign else "",
                display_name=display_name,
                city=city,
                state=state,
                source=chosen["source"],
                site=chosen["site"],
                site_id=chosen["site_id"],
                match_method=method,
                confidence=confidence,
                reason=reason,
            )
        )

        conflict = find_conflict(channel_id, call_sign, chosen["display_name"], station)
        if conflict:
            conflicts.append(conflict)

    return matches, unmatched, conflicts


# ---------------------------------------------------------------------------
# Report + grabber-input writing
# ---------------------------------------------------------------------------


def _write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_reports(matches: List[EpgMatch], unmatched: List[dict], conflicts: List[dict], total_channels: int,
                   reports_dir: Path = REPORTS_DIR):
    match_fields = ["channel_id", "call_sign", "display_name", "city", "state", "source", "site", "site_id",
                     "match_method", "confidence", "reason"]
    _write_csv(reports_dir / "epg-matches.csv", match_fields, [vars(m) for m in matches])
    _write_csv(reports_dir / "epg-unmatched.csv", ["channel_id", "call_sign", "display_name", "reason"], unmatched)
    _write_csv(
        reports_dir / "epg-conflicts.csv",
        ["channel_id", "call_sign", "matched_display_name", "known_city", "known_state", "reason"],
        conflicts,
    )

    matched_count = len(matches)
    coverage_after = round(100 * matched_count / total_channels, 2) if total_channels else 0.0
    _write_csv(
        reports_dir / "epg-coverage.csv",
        ["metric", "value"],
        [
            {"metric": "total_channels", "value": total_channels},
            {"metric": "matched_channels", "value": matched_count},
            {"metric": "unmatched_channels", "value": len(unmatched)},
            {"metric": "conflicts", "value": len(conflicts)},
            {"metric": "coverage_before_percent", "value": 0.0},
            {"metric": "coverage_after_percent", "value": coverage_after},
        ],
    )


def write_grabber_input(matches: List[EpgMatch], path: Path = GRABBER_INPUT_PATH):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<channels>"]
    for m in matches:
        name = m.display_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cid = m.channel_id.replace('"', "&quot;")
        lines.append(f'  <channel site="{m.site}" site_id="{m.site_id}" lang="en" xmltv_id="{cid}">{name}</channel>')
    lines.append("</channels>")
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_and_write(stations, master_playlist: Path = MASTER_PLAYLIST, log=print):
    """End-to-end: fetch source lists, match, write reports + grabber input.
    Returns (matches, unmatched, conflicts).
    """
    log("Fetching EPG source channel lists...")
    all_rows = []
    for label, url in SOURCES:
        rows = load_source_rows(label, url)
        log(f"  {label}: {len(rows)} channels")
        all_rows.extend(rows)

    channel_ids, names = our_channel_universe(master_playlist)
    log(f"\nOur published channel universe: {len(channel_ids)} unique channel ids")

    overrides = load_overrides()
    matches, unmatched, conflicts = match_all_channels(channel_ids, names, stations, all_rows, overrides)

    write_reports(matches, unmatched, conflicts, len(channel_ids))
    write_grabber_input(matches)

    coverage = round(100 * len(matches) / len(channel_ids), 2) if channel_ids else 0.0
    log(f"\nTotal channels: {len(channel_ids)}")
    log(f"Matched: {len(matches)} ({coverage}%)")
    log(f"Unmatched: {len(unmatched)}")
    log(f"Conflicts: {len(conflicts)}")
    log(f"Wrote grabber input: {GRABBER_INPUT_PATH}")

    return matches, unmatched, conflicts


# ---------------------------------------------------------------------------
# Merging grabbed XMLTV fragments into the final AndroidTVGuru.xml(.gz)
# ---------------------------------------------------------------------------


def merge_guides(paths: List[Path]):
    """Merge per-source XMLTV guide fragments into one <tv> document.

    Guards against the two ways a merge can produce a broken guide:
      - duplicate <channel id="..."> across input files (first file wins, in
        the order given; later duplicates are dropped and counted)
      - <programme channel="..."> referencing a channel id that isn't in the
        merged channel set (dropped and counted)

    Returns (tv_element, stats_dict).
    """
    channels: Dict[str, ET.Element] = {}
    programmes = []
    duplicate_channels = 0

    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            print(f"  WARNING: skipping unparseable file {path}: {exc}")
            continue

        for channel_el in root.findall("channel"):
            cid = channel_el.get("id")
            if not cid:
                continue
            if cid in channels:
                duplicate_channels += 1
                continue
            channels[cid] = channel_el

        programmes.extend(root.findall("programme"))

    kept_programmes = []
    orphan_programmes = 0
    for p in programmes:
        if p.get("channel") in channels:
            kept_programmes.append(p)
        else:
            orphan_programmes += 1

    tv = ET.Element("tv")
    for cid in sorted(channels):
        tv.append(channels[cid])
    for p in kept_programmes:
        tv.append(p)

    return tv, {
        "input_files": len(paths),
        "channel_count": len(channels),
        "programme_count": len(kept_programmes),
        "duplicate_channels_dropped": duplicate_channels,
        "orphan_programmes_dropped": orphan_programmes,
    }


def write_guide_outputs(tv_element, out_dir: Path, basename: str = "AndroidTVGuru"):
    out_dir.mkdir(parents=True, exist_ok=True)
    xml_path = out_dir / f"{basename}.xml"
    gz_path = out_dir / f"{basename}.xml.gz"

    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tv_element, encoding="utf-8")
    xml_path.write_bytes(xml_bytes)
    with gzip.open(gz_path, "wb") as fh:
        fh.write(xml_bytes)

    return xml_path, gz_path
