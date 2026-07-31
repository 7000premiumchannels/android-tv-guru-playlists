"""Conservative EPG (XMLTV id) matching and reporting.

See docs/EPG_MATCHING.md for the full rationale. Summary: this module does NOT
fetch programme listings from any third-party guide site, and does NOT change
which tvg-id we publish (we always publish the IPTV-org channel id, which is
also what the existing tvguide.com fallback guide expects). What it DOES do is
report, per channel, whether IPTV-org's own public guide-source index
(api/guides.json) lists a known EPG source for that exact channel id — this
turns "do we have a guide for WABC?" from a guess into a documented fact,
without us scraping tvpassport.com/tvtv.us/etc. ourselves.

Match tiers, most to least confident:
  1. manual_override   - data/epg-overrides.json (human-reviewed, exact)
  2. exact_channel_id   - our channel id appears verbatim in the guides.json
                          source index (this is also an "exact call sign"
                          match whenever the id itself is a call sign, since
                          IPTV-org's local-station ids already are the call
                          sign, e.g. "WABCTV71.us")
  (anything else)      - unmatched; conservatively left with no guide claim,
                          never guessed by shared network alone
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

GUIDES_API_URL = "https://iptv-org.github.io/api/guides.json"
OVERRIDES_PATH = Path(__file__).resolve().parent.parent / "data" / "epg-overrides.json"

# Preference order when a channel id has guide entries from multiple sites.
SOURCE_PRIORITY = [
    "tvguide.com",
    "tvtv.us",
    "tvpassport.com",
    "i.mjh.nz",
    "ontvtonight.com",
    "gracenote.com",
]

_CITY_STATE_RE = re.compile(r"([A-Za-z .'-]+),\s*([A-Z]{2})\b")


@dataclass
class EpgMatch:
    channel_id: str
    call_sign: Optional[str]
    display_name: str
    city: Optional[str]
    state: Optional[str]
    original_tvg_id: str
    selected_epg_id: Optional[str]
    source_name: Optional[str]
    match_method: str
    confidence: str
    reason: str


def load_overrides(path: Path = OVERRIDES_PATH) -> Dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["channel_id"]: entry["epg_id"] for entry in data.get("overrides", [])}


def build_guide_index(guide_rows: List[dict]) -> Dict[str, List[dict]]:
    index: Dict[str, List[dict]] = {}
    for row in guide_rows:
        channel_id = row.get("channel")
        if not channel_id:
            continue
        index.setdefault(channel_id, []).append(row)
    return index


def _best_source(rows: List[dict]) -> dict:
    def priority(row):
        site = row.get("site", "")
        try:
            return SOURCE_PRIORITY.index(site)
        except ValueError:
            return len(SOURCE_PRIORITY)

    return sorted(rows, key=priority)[0]


def _extract_city_state(site_name: Optional[str]):
    if not site_name:
        return None, None
    match = _CITY_STATE_RE.search(site_name)
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).strip()


def match_channel(channel_id, call_sign, display_name, station, guide_index, overrides) -> EpgMatch:
    city = station.get("city") if station else None
    state = station.get("state") if station else None

    if channel_id in overrides:
        selected = overrides[channel_id]
        return EpgMatch(
            channel_id=channel_id,
            call_sign=call_sign,
            display_name=display_name,
            city=city,
            state=state,
            original_tvg_id=channel_id,
            selected_epg_id=selected,
            source_name="manual_override",
            match_method="manual_override",
            confidence="high",
            reason="present in data/epg-overrides.json",
        )

    rows = guide_index.get(channel_id)
    if rows:
        best = _best_source(rows)
        return EpgMatch(
            channel_id=channel_id,
            call_sign=call_sign,
            display_name=display_name,
            city=city,
            state=state,
            original_tvg_id=channel_id,
            selected_epg_id=channel_id,
            source_name=best.get("site"),
            match_method="exact_channel_id",
            confidence="high",
            reason=f"channel id listed in IPTV-org guide-source index for {best.get('site')}",
        )

    return EpgMatch(
        channel_id=channel_id,
        call_sign=call_sign,
        display_name=display_name,
        city=city,
        state=state,
        original_tvg_id=channel_id,
        selected_epg_id=None,
        source_name=None,
        match_method="unmatched",
        confidence="none",
        reason="no guide source found for this channel id and no manual override",
    )


def find_conflicts(channel_id, rows: List[dict], station: Optional[dict]) -> List[dict]:
    """Flag guide-source rows whose embedded city disagrees with our known
    station city. Only runs when we actually have station data to compare
    against — we never guess a conflict we can't verify.
    """
    if not station or not station.get("city"):
        return []

    known_city = station["city"].lower()
    conflicts = []
    for row in rows:
        city, _state = _extract_city_state(row.get("site_name"))
        if city and known_city not in city.lower() and city.lower() not in known_city:
            conflicts.append(
                {
                    "channel_id": channel_id,
                    "site": row.get("site"),
                    "site_name": row.get("site_name"),
                    "known_city": station["city"],
                    "known_state": station.get("state"),
                    "reason": "guide source city does not match known station city",
                }
            )
    return conflicts
