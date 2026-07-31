#!/usr/bin/env python3
"""
Build a legal/public IPTV M3U playlist from IPTV-org's public API.

Output groups:
- US Local - ABC
- US Local - CBS
- US Local - NBC
- US Local - FOX
- US Local - CW
- US Local - PBS
- US Local - Telemundo
- US Local - Univision
- US News & Weather
- Movies & Classic TV
- Kids & Family
- Sports & Highlights
- Music
- Religious
- Spanish
- African & Caribbean
- Other US Public Channels

Only channels with publicly listed stream URLs are included.
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

API = "https://iptv-org.github.io/api"
OUT = Path("Android_TV_Guru_Legal_Public_TV.m3u")

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

SPANISH_CODES = {"spa"}
AFRICAN_COUNTRIES = {
    "DZ","AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM","CD","CG","CI",
    "DJ","EG","GQ","ER","SZ","ET","GA","GM","GH","GN","GW","KE","LS","LR",
    "LY","MG","MW","ML","MR","MU","MA","MZ","NA","NE","NG","RW","ST","SN",
    "SC","SL","SO","ZA","SS","SD","TZ","TG","TN","UG","ZM","ZW"
}
CARIBBEAN_COUNTRIES = {
    "AG","BS","BB","CU","DM","DO","GD","HT","JM","KN","LC","VC","TT","PR",
    "AW","CW","BQ","KY","TC","VG","VI","GP","MQ"
}

def get_json(name):
    req = urllib.request.Request(
        f"{API}/{name}.json",
        headers={"User-Agent": "Android-TV-Guru-Playlist-Builder/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)

def safe(value):
    return str(value or "").replace('"', "'").replace("\n", " ").strip()

def choose_group(channel):
    name = channel.get("name", "")
    network = channel.get("network") or ""
    owners = " ".join(channel.get("owners") or [])
    text = f"{name} {network} {owners}"

    if channel.get("country") == "US":
        for label, pattern in NETWORK_PATTERNS:
            if pattern.search(text):
                return f"US Local - {label}"

        categories = channel.get("categories") or []
        for category in categories:
            if category in CATEGORY_GROUPS:
                return CATEGORY_GROUPS[category]

        if "spa" in (channel.get("languages") or []):
            return "Spanish"

        return "Other US Public Channels"

    if SPANISH_CODES.intersection(channel.get("languages") or []):
        return "Spanish"

    if channel.get("country") in AFRICAN_COUNTRIES | CARIBBEAN_COUNTRIES:
        return "African & Caribbean"

    categories = channel.get("categories") or []
    for category in categories:
        if category in CATEGORY_GROUPS:
            return CATEGORY_GROUPS[category]

    return None

def main():
    print("Downloading current public channel and stream data...")
    channels = get_json("channels")
    streams = get_json("streams")
    cities = get_json("cities")

    channel_by_id = {c["id"]: c for c in channels if c.get("id")}
    city_by_code = {c["code"]: c["name"] for c in cities if c.get("code")}

    streams_by_channel = defaultdict(list)
    for stream in streams:
        channel_id = stream.get("channel")
        url = stream.get("url")
        if channel_id and url:
            streams_by_channel[channel_id].append(stream)

    entries = []
    seen_urls = set()

    for channel_id, channel_streams in streams_by_channel.items():
        channel = channel_by_id.get(channel_id)
        if not channel or channel.get("is_nsfw"):
            continue

        group = choose_group(channel)
        if not group:
            continue

        city = city_by_code.get(channel.get("city"), "")
        location = city
        if channel.get("country") == "US" and city:
            display_name = f"{channel.get('name')} — {city}"
        else:
            display_name = channel.get("name")

        for stream in channel_streams:
            url = stream.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            logo = safe(channel.get("logo"))
            tvg_id = safe(channel.get("id"))
            name = safe(display_name)
            entry = (
                f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" '
                f'tvg-logo="{logo}" group-title="{safe(group)}",{name}\n'
                f'{url}\n'
            )
            entries.append((group, name.lower(), entry))

    entries.sort(key=lambda x: (x[0], x[1]))
    header = '#EXTM3U x-tvg-url="https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml"\n'
    OUT.write_text(header + "".join(e[2] for e in entries), encoding="utf-8")

    counts = defaultdict(int)
    for group, _, _ in entries:
        counts[group] += 1

    print(f"\nCreated: {OUT.resolve()}")
    print(f"Total public streams: {len(entries)}")
    for group in sorted(counts):
        print(f"  {group}: {counts[group]}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nCould not build playlist: {exc}", file=sys.stderr)
        print("Check your internet connection and try again.", file=sys.stderr)
        sys.exit(1)
