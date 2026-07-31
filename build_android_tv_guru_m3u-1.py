#!/usr/bin/env python3
"""
Build the Android TV Guru legal/public IPTV playlists from IPTV-org's public API.

Downloads channels.json, streams.json, cities.json, and subdivisions.json from
https://iptv-org.github.io/api/ and produces:

  - AndroidTVGuru.m3u          the full master playlist (all valid public streams)
  - playlists/*.m3u            16 category playlists, each a filtered view of the master

Only channels with at least one valid http/https stream URL are included, NSFW
channels are skipped, and duplicate stream URLs are removed.
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

API = "https://iptv-org.github.io/api"
OUT = Path("AndroidTVGuru.m3u")
PLAYLISTS_DIR = Path("playlists")
EPG_HEADER = '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/7000premiumchannels/android-tv-guru-playlists/main/AndroidTVGuru.xml.gz"\n'

NETWORK_PATTERNS = [
    ("ABC", re.compile(r"\bABC\b|American Broadcasting", re.I)),
    ("CBS", re.compile(r"\bCBS\b", re.I)),
    ("NBC", re.compile(r"\bNBC\b", re.I)),
    ("FOX", re.compile(r"\bFOX\b", re.I)),
    ("CW", re.compile(r"\bCW\b|The CW", re.I)),
    ("PBS", re.compile(r"\bPBS\b|Public Broadcasting", re.I)),
    ("Telemundo", re.compile(r"\bTelemundo\b", re.I)),
    ("Univision", re.compile(r"\bUnivision\b", re.I)),
]

CATEGORY_GROUPS = {
    "news": "US News & Weather",
    "weather": "US News & Weather",
    "movies": "Movies & Classic TV",
    "classic": "Movies & Classic TV",
    "series": "Movies & Classic TV",
    "kids": "Kids & Family",
    "family": "Kids & Family",
    "sports": "Sports & Highlights",
    "music": "Music",
    "religious": "Religious",
}

# IPTV-org's public API (as pulled from the four endpoints below) does not
# ship a languages.json, so "Spanish-language" is approximated:
#  - for US channels: name/network/owners keyword matching (see US_SPANISH_RE)
#  - for non-US channels: country code membership in a fixed list of Spain +
#    Latin American Spanish-speaking countries (see SPANISH_SPEAKING_COUNTRIES)
# This is a heuristic, not a real language field, and can misclassify a small
# number of channels (e.g. a bilingual or minority-language channel in one of
# these countries).
US_SPANISH_RE = re.compile(r"\bspanish\b|\bazteca\b|\blatino\b|\bhispan", re.I)

SPANISH_SPEAKING_COUNTRIES = {
    "ES",  # Spain
    "MX", "AR", "BO", "CL", "CO", "CR", "CU", "DO", "EC", "SV",
    "GQ", "GT", "HN", "NI", "PA", "PY", "PE", "UY", "VE",
}

AFRICAN_COUNTRIES = {
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CM", "CV", "CF", "TD", "KM", "CD", "CG", "CI",
    "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR",
    "LY", "MG", "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN",
    "SC", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "ZM", "ZW",
}
CARIBBEAN_COUNTRIES = {
    "AG", "BS", "BB", "CU", "DM", "DO", "GD", "HT", "JM", "KN", "LC", "VC", "TT", "PR",
    "AW", "CW", "BQ", "KY", "TC", "VG", "VI", "GP", "MQ",
}

GROUP_ORDER = [
    "US Local - ABC",
    "US Local - CBS",
    "US Local - NBC",
    "US Local - FOX",
    "US Local - CW",
    "US Local - PBS",
    "US Local - Telemundo",
    "US Local - Univision",
    "US News & Weather",
    "Movies & Classic TV",
    "Kids & Family",
    "Sports & Highlights",
    "Music",
    "Religious",
    "Spanish",
    "African & Caribbean",
    "Other US Public Channels",
]
GROUP_ORDER_INDEX = {group: i for i, group in enumerate(GROUP_ORDER)}

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


def get_json(name):
    req = urllib.request.Request(
        f"{API}/{name}.json",
        headers={"User-Agent": "Android-TV-Guru-Playlist-Builder/1.0"},
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


def determine_group(channel):
    name = channel.get("name") or ""
    network = channel.get("network") or ""
    owners = " ".join(channel.get("owners") or [])
    text = f"{name} {network} {owners}"
    country = channel.get("country")
    categories = channel.get("categories") or []

    if country == "US":
        for label, pattern in NETWORK_PATTERNS:
            if pattern.search(text):
                return f"US Local - {label}"

        for category in categories:
            if category in CATEGORY_GROUPS:
                return CATEGORY_GROUPS[category]

        if US_SPANISH_RE.search(text):
            return "Spanish"

        return "Other US Public Channels"

    if country in SPANISH_SPEAKING_COUNTRIES:
        return "Spanish"

    if country in AFRICAN_COUNTRIES or country in CARIBBEAN_COUNTRIES:
        return "African & Caribbean"

    for category in categories:
        if category in CATEGORY_GROUPS:
            return CATEGORY_GROUPS[category]

    return f"Other International - {country or 'XX'}"


def channel_display_name(channel, city_by_code, subdivision_by_code):
    name = channel.get("name") or channel.get("id")

    # NOTE: as of this writing, IPTV-org's public channels.json does not
    # include a "city" (or "subdivision") field per channel, so there is no
    # join key back into cities.json/subdivisions.json for most channels.
    # This lookup is written defensively so it activates automatically if
    # IPTV-org adds these fields in the future; today it is effectively a
    # no-op and channel names are used as-is.
    if channel.get("country") == "US":
        city_code = channel.get("city")
        city = city_by_code.get(city_code) if city_code else None
        if city:
            city_name = city.get("name")
            subdivision_name = subdivision_by_code.get(city.get("subdivision"))
            if city_name and subdivision_name:
                return f"{name} — {city_name}, {subdivision_name}"
            if city_name:
                return f"{name} — {city_name}"

    return name


def sort_key(entry):
    group, name_lower, _block = entry
    if group in GROUP_ORDER_INDEX:
        return (0, GROUP_ORDER_INDEX[group], name_lower)
    return (1, group, name_lower)


def write_playlist(path, entries):
    path.write_text(EPG_HEADER + "".join(e[2] for e in entries), encoding="utf-8")


def main():
    print("Downloading current public IPTV-org data...")
    channels = get_json("channels")
    streams = get_json("streams")
    cities = get_json("cities")
    subdivisions = get_json("subdivisions")

    channel_by_id = {c["id"]: c for c in channels if c.get("id")}
    city_by_code = {c["code"]: c for c in cities if c.get("code")}
    subdivision_by_code = {s["code"]: s["name"] for s in subdivisions if s.get("code")}

    entries = []
    seen_urls = set()

    for stream in streams:
        channel_id = stream.get("channel")
        url = stream.get("url")

        if not channel_id or not is_valid_stream_url(url):
            continue
        if url in seen_urls:
            continue

        channel = channel_by_id.get(channel_id)
        if not channel or channel.get("is_nsfw"):
            continue

        seen_urls.add(url)

        group = determine_group(channel)
        display_name = channel_display_name(channel, city_by_code, subdivision_by_code)

        logo = safe(channel.get("logo"))
        tvg_id = safe(channel.get("id"))
        name = safe(display_name)
        block = (
            f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" '
            f'tvg-logo="{logo}" group-title="{safe(group)}",{name}\n'
            f'{url}\n'
        )
        entries.append((group, name.lower(), block))

    entries.sort(key=sort_key)

    write_playlist(OUT, entries)

    PLAYLISTS_DIR.mkdir(exist_ok=True)
    for filename, groups in CATEGORY_FILES.items():
        filtered = [e for e in entries if e[0] in groups]
        write_playlist(PLAYLISTS_DIR / filename, filtered)

    counts = defaultdict(int)
    for group, _, _ in entries:
        counts[group] += 1

    print(f"\nCreated: {OUT.resolve()}")
    print(f"Total public streams: {len(entries)}")
    for group in sorted(counts):
        print(f"  {group}: {counts[group]}")

    print(f"\nCreated {len(CATEGORY_FILES)} category playlists in {PLAYLISTS_DIR.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nCould not build playlists: {exc}", file=sys.stderr)
        print("Check your internet connection and try again.", file=sys.stderr)
        sys.exit(1)
