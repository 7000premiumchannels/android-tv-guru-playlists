#!/usr/bin/env python3
"""Build data/us_tv_stations.json — U.S. TV station call sign -> city/state lookup.

Used by scripts/build_epg_source.py for two things:
  1. Detecting conflicts between an EPG source's claimed city and a station's
     actual city (e.g. don't let KQED (San Francisco) and KQED2 (San Jose)
     get silently treated as the same market).
  2. Nothing else — this file never gates which channels get a guide entry,
     it only helps validate matches we already have from an exact channel-id
     or call-sign match.

SOURCE: Wikidata (query.wikidata.org SPARQL endpoint), CC0-licensed, queried
in bulk (one query per location property), not scraped per-station. FCC LMS
bulk data (the preferred source) returns HTTP 403 (Akamai bot protection)
from this environment and its catalog.data.gov listing is a JS-rendered page
with no static download link — see docs/DATA_SOURCES.md. This importer is
isolated so a real FCC importer can replace it later without touching
anything downstream (only the output JSON schema matters to callers).

Coverage is intentionally partial: most Wikidata TV station articles don't
have a structured city/state claim. That's fine here since this file is only
used for conflict *detection*, never to invent a channel's city.
"""

import datetime
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from callsigns import extract_callsign  # noqa: E402

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
OUT = Path(__file__).resolve().parent.parent / "data" / "us_tv_stations.json"
USER_AGENT = "AndroidTVGuruEPGBuilder/1.0 (https://github.com/7000premiumchannels/android-tv-guru-playlists)"

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

_LOCATION_PROPERTIES = ["P1408", "P159", "P131"]


def run_sparql(query):
    url = f"{SPARQL_ENDPOINT}?query={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def service_type_for(call_sign):
    if call_sign.suffix in ("-LD", "-LP") or call_sign.is_low_power:
        return "low_power"
    if call_sign.suffix == "-CD":
        return "class_a"
    return "full_power"


def main():
    records = {}
    seen_items = set()

    for prop in _LOCATION_PROPERTIES:
        query = _QUERY_TEMPLATE.format(prop=prop)
        print(f"Querying Wikidata via {prop}...")
        try:
            data = run_sparql(query)
        except urllib.error.URLError as exc:
            print(f"  Wikidata query via {prop} failed: {exc}", file=sys.stderr)
            continue

        for row in data["results"]["bindings"]:
            item_uri = row["item"]["value"]
            if item_uri in seen_items:
                continue

            label = row.get("itemLabel", {}).get("value", "")
            call_sign = extract_callsign(label)
            if not call_sign:
                continue

            city = row.get("locLabel", {}).get("value")
            state = row.get("stateAbbr", {}).get("value")
            if not city or not state:
                continue
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
                "service_type": service_type_for(call_sign),
                "status": status,
                "source": "wikidata",
                "last_updated": datetime.date.today().isoformat(),
            }

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(sorted(records.values(), key=lambda r: r["call_sign"]), indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {len(records)} station records to {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Could not build station data: {exc}", file=sys.stderr)
        sys.exit(1)
