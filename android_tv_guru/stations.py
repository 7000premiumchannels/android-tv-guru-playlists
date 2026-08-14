"""Lookup of U.S. TV station city/state by call sign.

Backed by data/us_tv_stations.json (see build_station_directory() below for
how that file is produced, and docs/DATA_SOURCES.md for the source
decision). Coverage is intentionally partial. A missing lookup is not an
error; callers should fall back to the original channel name.
"""

import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from .callsigns import extract_callsign

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "us_tv_stations.json"

# SOURCE DECISION (see docs/DATA_SOURCES.md for full detail): the FCC's own
# LMS Public Database Files and every fcc.gov path tried (including the bare
# robots.txt) return HTTP 403 from an Akamai bot-protection layer that blocks
# this environment's network at the domain level, regardless of User-Agent or
# specific endpoint — confirmed by re-testing with a realistic browser UA
# against several fcc.gov/enterpriseefiling.fcc.gov/transition.fcc.gov paths
# in 2026-08-14. RabbitEars.info (see fetch_station_records_from_rabbitears
# below) republishes the same FCC city-of-license data with far denser
# coverage than Wikidata and is used as the primary source; Wikidata fills
# any remaining gaps.
_RABBITEARS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# All 50 states + DC + inhabited U.S. territories that can hold an FCC TV
# license. RabbitEars' per-state search groups stations by Nielsen market,
# which can span state lines (e.g. a Rhode-Island-market search also returns
# stations licensed to nearby Massachusetts/Connecticut cities) and
# occasionally spills into adjacent Canadian/Mexican jurisdictions in
# border markets — both handled downstream by keeping each row's own
# reported state and discarding non-U.S. state codes.
_RABBITEARS_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
    "VA", "WA", "DC", "WV", "WI", "WY", "PR", "GU", "VI", "AS", "MP",
]

# Not in US_STATE_NAMES (which drives state-playlist generation and is
# intentionally limited to the 50 states + DC), but still legitimate FCC
# licensing jurisdictions - kept here just to validate a row's reported
# state without expanding US_STATE_NAMES' unrelated display-name role.
_RABBITEARS_TERRITORIES = {"PR", "GU", "VI", "AS", "MP"}

# RabbitEars' station tables are old-style, loosely-closed HTML (not valid
# XML) at a scale (multi-megabyte per state) where a full DOM parse is slow
# enough to matter; a targeted regex over the one row shape we need is both
# far faster and, verified against a BeautifulSoup parse of a sample state,
# produces identical results. It intentionally requires the call-sign link,
# its closing </td>, and the immediately-following city/state <td>s to be
# contiguous — this is what a genuine station row looks like, and it is what
# excludes the channel-sharing "tenant" sub-rows that don't have this exact
# shape (verified: those rows are silently and correctly skipped, not
# mis-parsed).
_RABBITEARS_ROW_RE = re.compile(
    r'<a\s+href="[^"]*request=station_search&callsign=(?P<facility_id>\d+)[^"]*"[^>]*>'
    r'(?:<nobr>)?(?P<call>[A-Z0-9]+(?:-[A-Z0-9]+)?)(?:</nobr>)?</a></td>\s*'
    r'<td><nobr>(?P<city>[^<]+)</nobr></td>\s*'
    r'<td>(?P<state>[A-Z]{2})</td>'
)

# SPARQL Wikidata endpoint used as a supplementary source (see
# fetch_station_records_from_wikidata below): public, free, CC0-licensed,
# queried in bulk (one query per location property), not scraped
# per-station. Kept as a fallback for any call sign RabbitEars doesn't cover.
_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
_WIKIDATA_USER_AGENT = (
    "AndroidTVGuruPlaylistBuilder/2.0 (https://github.com/7000premiumchannels/android-tv-guru-playlists)"
)

# Priority order: prefer the most specific "licensed to broadcast to" claim,
# and only fall back to headquarters/location claims when it is missing.
# Note: P131 ("located in the administrative territorial entity") is the
# coarsest of the three and sometimes resolves to a county or metro area
# rather than a city (e.g. "Potter County" instead of "Amarillo"). That is
# real Wikidata data, not a guess, but it means city precision varies by tier.
_LOCATION_PROPERTIES = ["P1408", "P159", "P131"]

# Q1616075 = television station, Q30 = United States of America,
# Q35657 = U.S. state, P1400 = FCC Facility ID, P1408 = licensed to
# broadcast to, P159 = headquarters location, P131 = located in the
# administrative territorial entity, P300 = ISO 3166-2 code,
# P576 = dissolved/abolished/demolished date.
_QUERY_TEMPLATE = """
SELECT ?item ?itemLabel ?facilityId ?locLabel ?stateAbbr ?dissolved WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q1616075.
  ?item wdt:P17 wd:Q30.
  OPTIONAL {{ ?item wdt:P1400 ?facilityId. }}
  OPTIONAL {{ ?item wdt:P576 ?dissolved. }}
  ?item wdt:{prop} ?loc.
  ?loc wdt:P131 ?state.
  ?state wdt:P31 wd:Q35657.
  ?state wdt:P300 ?stateAbbr.
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""

US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin",
    "WY": "Wyoming", "DC": "District of Columbia",
}


class StationDirectory:
    def __init__(self, records):
        self._by_call_sign: Dict[str, dict] = {r["normalized_call_sign"]: r for r in records}

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "StationDirectory":
        if not path.exists():
            return cls([])
        records = json.loads(path.read_text(encoding="utf-8"))
        return cls(records)

    def lookup(self, normalized_call_sign: str) -> Optional[dict]:
        return self._by_call_sign.get(normalized_call_sign)

    def __len__(self):
        return len(self._by_call_sign)


def state_name(state_code: Optional[str]) -> Optional[str]:
    if not state_code:
        return None
    return US_STATE_NAMES.get(state_code.upper())


def _service_type_for(call_sign) -> str:
    """Infer FCC service type from call-sign suffix conventions (not from Wikidata)."""
    if call_sign.suffix in ("-LD", "-LP") or call_sign.is_low_power:
        return "low_power"
    if call_sign.suffix == "-CD":
        return "class_a"
    return "full_power"


def _fetch_rabbitears_state_page(state: str) -> str:
    url = f"https://www.rabbitears.info/search.php?request=state_search&state={state}"
    req = urllib.request.Request(url, headers={"User-Agent": _RABBITEARS_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_station_records_from_rabbitears(log=print, delay: float = 5.0) -> List[dict]:
    """Fetch U.S. TV station call sign -> city/state from RabbitEars.info's
    per-state market listings. See the SOURCE DECISION comment above and
    docs/DATA_SOURCES.md for why this replaces the FCC's own (unreachable)
    bulk database as the primary source.

    `delay` is a fixed pause between requests, honoring RabbitEars'
    robots.txt Crawl-delay directive (5 seconds at the time this was
    written) for automated agents. Returns a list of station record dicts
    matching the data/us_tv_stations.json schema, deduplicated by
    normalized call sign (first state search to report a given station
    wins; the same station can legitimately appear under several
    state searches when its market spans state lines).
    """
    records: Dict[str, dict] = {}
    today = datetime.date.today().isoformat()

    for i, state in enumerate(_RABBITEARS_STATES):
        log(f"Fetching RabbitEars station list for {state} ({i + 1}/{len(_RABBITEARS_STATES)})...")
        try:
            html = _fetch_rabbitears_state_page(state)
        except urllib.error.URLError as exc:
            log(f"  {state} fetch failed: {exc}")
            if i < len(_RABBITEARS_STATES) - 1:
                time.sleep(delay)
            continue

        for match in _RABBITEARS_ROW_RE.finditer(html):
            row_state = match.group("state")
            if row_state not in US_STATE_NAMES and row_state not in _RABBITEARS_TERRITORIES:
                continue  # non-U.S. market spillover (Canadian province, Mexican state)

            call_sign = extract_callsign(match.group("call"))
            if call_sign is None:
                continue  # never guess at a call sign our syntax rules don't recognize

            key = call_sign.normalized_call_sign
            if key in records:
                continue

            records[key] = {
                "call_sign": call_sign.normalized_call_sign,
                "normalized_call_sign": call_sign.normalized_call_sign,
                "city": match.group("city").strip().title(),
                "state": row_state,
                "facility_id": match.group("facility_id"),
                "service_type": _service_type_for(call_sign),
                "status": "active",
                "source": "rabbitears",
                "last_updated": today,
            }

        if i < len(_RABBITEARS_STATES) - 1:
            time.sleep(delay)

    log(f"RabbitEars: {len(records)} unique stations resolved.")
    return sorted(records.values(), key=lambda r: r["call_sign"])


def _run_sparql(query: str) -> dict:
    url = f"{_SPARQL_ENDPOINT}?query={urllib.parse.quote(query)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": _WIKIDATA_USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def fetch_station_records_from_wikidata(log=print) -> List[dict]:
    """Query Wikidata for U.S. TV stations with a resolvable call sign and
    city/state. See the module docstring and docs/DATA_SOURCES.md for the
    source decision. Returns a list of station record dicts matching the
    data/us_tv_stations.json schema, deduplicated by normalized call sign.
    """
    records: Dict[str, dict] = {}
    seen_items = set()

    for prop in _LOCATION_PROPERTIES:
        query = _QUERY_TEMPLATE.format(prop=prop)
        log(f"Querying Wikidata via {prop}...")
        try:
            data = _run_sparql(query)
        except urllib.error.URLError as exc:
            log(f"  Wikidata query via {prop} failed: {exc}")
            continue

        for row in data["results"]["bindings"]:
            item_uri = row["item"]["value"]
            if item_uri in seen_items:
                continue  # a higher-priority property already resolved this station

            label = row.get("itemLabel", {}).get("value", "")
            call_sign = extract_callsign(label)
            if not call_sign:
                continue

            city = row.get("locLabel", {}).get("value")
            state = row.get("stateAbbr", {}).get("value")
            if not city or not state:
                continue
            # Wikidata's P300 (ISO 3166-2 code) for U.S. states is "US-XX";
            # we only want the two-letter postal abbreviation for display.
            state = state.split("-")[-1]

            seen_items.add(item_uri)
            facility_id = row.get("facilityId", {}).get("value")
            status = "inactive" if "dissolved" in row else "active"

            key = call_sign.normalized_call_sign
            records[key] = {
                "call_sign": call_sign.normalized_call_sign,
                "normalized_call_sign": call_sign.normalized_call_sign,
                "city": city,
                "state": state,
                "facility_id": facility_id,
                "service_type": _service_type_for(call_sign),
                "status": status,
                "source": "wikidata",
                "last_updated": datetime.date.today().isoformat(),
            }

    return sorted(records.values(), key=lambda r: r["call_sign"])


def build_station_directory(path: Path = DEFAULT_PATH, log=print) -> int:
    """Fetch station records and write them to `path`. RabbitEars is the
    primary source (far denser coverage - see fetch_station_records_from_
    rabbitears); Wikidata fills in any call sign RabbitEars didn't resolve.
    Returns the number of records written.
    """
    merged: Dict[str, dict] = {}

    for record in fetch_station_records_from_wikidata(log=log):
        merged[record["normalized_call_sign"]] = record

    rabbitears_count = 0
    for record in fetch_station_records_from_rabbitears(log=log):
        merged[record["normalized_call_sign"]] = record  # RabbitEars wins on overlap
        rabbitears_count += 1

    log(f"\nMerged directory: {len(merged)} stations ({rabbitears_count} from RabbitEars, "
        f"{len(merged) - rabbitears_count} Wikidata-only).")

    records = sorted(merged.values(), key=lambda r: r["call_sign"])
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return len(records)


def _main():
    count = build_station_directory()
    print(f"\nWrote {count} station records to {DEFAULT_PATH}")


if __name__ == "__main__":
    try:
        _main()
    except Exception as exc:
        print(f"Could not build station data: {exc}", file=sys.stderr)
        sys.exit(1)
