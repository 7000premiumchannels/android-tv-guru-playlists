#!/usr/bin/env python3
"""Build data/us_tv_stations.json — U.S. TV station call sign -> city/state lookup.

SOURCE DECISION (see docs/DATA_SOURCES.md for full detail)
------------------------------------------------------------
The FCC publishes bulk station data ("LMS Public Database Files") at
https://enterpriseefiling.fcc.gov/dataentry/public/tv/lmsDatabase.html, and this
was the preferred source per the Phase 1 spec. In this environment/session:

  - https://enterpriseefiling.fcc.gov/dataentry/public/tv/lmsDatabase.html
    returns HTTP 403 (Akamai bot protection) to automated requests.
  - The data.gov catalog listing (catalog.data.gov/dataset/lms-public-database-files)
    is a JavaScript-rendered page with no static, scriptable download link.

Neither is realistically fetchable here without browser automation, which is out
of scope for a data importer. Per the Phase 1 instructions, this script instead
uses Wikidata (wikidata.org) as the best stable public alternative:

  - Public, free, CC0-licensed, queried via one bulk SPARQL request (not
    per-station scraping).
  - Provides FCC Facility ID (P1400), call sign (via item label), and
    city/state (via P1408 "licensed to broadcast to", falling back to P159
    "headquarters location" or P131 "located in the administrative territorial
    entity" when P1408 is absent).

Coverage is INCOMPLETE: most Wikidata TV station articles do not have a
structured city/state claim, so this produces a partial station index (on the
order of a few hundred stations, not the full ~2,000+ FCC-licensed call signs).
This is intentional and documented, not a bug: per the Phase 1 "never guess a
city or state" rule, an incomplete-but-correct dataset is preferred over a
denser-but-invented one. Stations absent from this file simply keep their
original channel name instead of "CALLSIGN — City, ST".

This importer is intentionally isolated from the rest of the pipeline so a real
FCC LMS bulk-data importer can replace it later without touching any other
module — anything that consumes data/us_tv_stations.json only relies on the
schema below, not on how the file was produced.

Record schema (see android_tv_guru/stations.py):
    call_sign, normalized_call_sign, city, state, facility_id, service_type,
    status, source, last_updated
"""

import datetime
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from android_tv_guru.callsigns import extract_callsign  # noqa: E402

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
OUT = Path(__file__).resolve().parent.parent / "data" / "us_tv_stations.json"
USER_AGENT = "AndroidTVGuruPlaylistBuilder/2.0 (https://github.com/7000premiumchannels/android-tv-guru-playlists)"

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

# Priority order: prefer the most specific "licensed to broadcast to" claim,
# and only fall back to headquarters/location claims when it is missing.
# Note: P131 ("located in the administrative territorial entity") is the
# coarsest of the three and sometimes resolves to a county or metro area
# rather than a city (e.g. "Potter County" instead of "Amarillo"). That is
# real Wikidata data, not a guess, but it means city precision varies by tier.
_LOCATION_PROPERTIES = ["P1408", "P159", "P131"]


def run_sparql(query):
    req = urllib.request.Request(
        f"{SPARQL_ENDPOINT}?query={urllib.parse.quote(query)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def service_type_for(call_sign):
    """Infer FCC service type from call-sign suffix conventions (not from Wikidata)."""
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
                continue  # a higher-priority property already resolved this station

            label = row.get("itemLabel", {}).get("value", "")
            call_sign = extract_callsign(label)
            if not call_sign:
                continue  # not a recognizable call sign; skip rather than guess

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
