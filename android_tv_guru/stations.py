"""Lookup of U.S. TV station city/state by call sign.

Backed by data/us_tv_stations.json (see build_station_directory() below for
how that file is produced, and docs/DATA_SOURCES.md for the source
decision). Coverage is intentionally partial. A missing lookup is not an
error; callers should fall back to the original channel name.
"""

import datetime
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from .callsigns import extract_callsign

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "us_tv_stations.json"

# SOURCE DECISION (see docs/DATA_SOURCES.md for full detail): the FCC's LMS
# Public Database Files (https://enterpriseefiling.fcc.gov/dataentry/public/tv/lmsDatabase.html)
# would be the preferred, authoritative source, but return HTTP 403 (Akamai
# bot protection) to automated requests, and the catalog.data.gov listing for
# the same dataset is a JS-rendered page with no static download link — both
# unusable without browser automation, which is out of scope for a data
# importer. We use Wikidata instead: public, free, CC0-licensed, queried in
# bulk (one query per location property), not scraped per-station.
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
    """Fetch station records from Wikidata and write them to `path`.
    Returns the number of records written.
    """
    records = fetch_station_records_from_wikidata(log=log)
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
