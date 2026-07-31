# Data sources

This document records every public data source investigated for Phase 1
(station data and EPG matching), whether it was accepted, and why. Research
was performed on 2026-07-31.

## Base channel/stream data (unchanged from Phase 0)

| Source | URL | Notes |
|---|---|---|
| IPTV-org channels | `https://iptv-org.github.io/api/channels.json` | Channel id, name, network, owners, country, categories, is_nsfw. No city/subdivision field. |
| IPTV-org streams | `https://iptv-org.github.io/api/streams.json` | Public stream URLs keyed by channel id. |
| IPTV-org cities | `https://iptv-org.github.io/api/cities.json` | Fetched per spec; no join key exists from a channel to a city (see below). |
| IPTV-org subdivisions | `https://iptv-org.github.io/api/subdivisions.json` | Same as above. |

**Why cities.json/subdivisions.json are fetched but not used for lookups:**
`channels.json` does not carry a `city` or `subdivision` field on any channel
record (verified against the live schema), so there is no key to join a
channel to a city. They are still downloaded each run, matching the required
IPTV data list, and `android_tv_guru/playlists.py` calls them defensively —
if IPTV-org ever adds a join field, the code path is ready — but today they
are inert. City/state for local stations instead comes from
`data/us_tv_stations.json` (below).

## U.S. station data (call sign -> city/state)

| Source | Coverage | Call sign | City/state | License | Status |
|---|---|---|---|---|---|
| **FCC LMS Public Database Files** | Full — the authoritative source | Yes | Yes | Public domain (U.S. government work) | **Rejected — not fetchable this session** |
| **Wikidata (SPARQL)** | Partial (~135 call signs resolved) | Yes (via item label) | Yes (via P1408/P159/P131) | CC0 | **Accepted** |

### FCC LMS Public Database Files — attempted, not usable this session

URL: `https://enterpriseefiling.fcc.gov/dataentry/public/tv/lmsDatabase.html`
(a single bulk zip download, per `catalog.data.gov/dataset/lms-public-database-files`).
This was the preferred source per the Phase 1 spec ("prefer FCC bulk data
where practical"). What was tried:

- Direct fetch of the LMS database page: **HTTP 403**, blocked by Akamai bot
  protection, from this environment, with a browser-like User-Agent.
- The `catalog.data.gov` listing page for the same dataset: loads, but is a
  JavaScript-rendered SPA with no static download link in the HTML — would
  require headless-browser automation to extract, which is out of scope for
  a data importer script (and arguably crosses into the kind of scraping the
  Phase 1 spec asks us to avoid).

**Decision:** do not implement an FCC importer this phase. `scripts/update_station_data.py`
is isolated specifically so a real FCC LMS importer can replace its Wikidata
query later without touching any other module (`android_tv_guru/stations.py`
only depends on the output JSON schema, not on how it was produced).

### Wikidata — accepted

URL: `https://query.wikidata.org/sparql` (public SPARQL endpoint, CC0-licensed
data). Used via `scripts/update_station_data.py`, one bulk query per location
property (`P1408` "licensed to broadcast to", `P159` "headquarters location",
`P131` "located in the administrative territorial entity", in that priority
order), not per-station scraping.

- Call sign: derived from the Wikidata item label, validated through the same
  `android_tv_guru.callsigns.extract_callsign()` used everywhere else, so a
  malformed/non-call-sign label is dropped rather than guessed.
- City/state: from the location property chain, `wdt:P300` (ISO 3166-2 code)
  gives a two-letter state.
- FCC Facility ID: `wdt:P1400`, present on some records.
- Coverage is **partial by nature** — most Wikidata TV station articles do
  not have a structured location claim. As of this writing the import
  produces 135 station records (out of thousands of call signs that appear
  in IPTV-org's channel names). This is intentional under the "never guess a
  city or state" rule: a smaller, correct dataset beats a denser, invented
  one. Stations absent from `data/us_tv_stations.json` keep their original
  channel name instead of getting a fabricated "CALLSIGN — City, ST".
- The `P131` tier is the coarsest and sometimes resolves to a county or metro
  area instead of a city proper (e.g. "Potter County" instead of "Amarillo").
  That's real Wikidata data, not a guess, but it means precision varies.

## EPG / XMLTV sources

The existing master playlist's `x-tvg-url` points at:

```
https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml
```

**This URL currently returns HTTP 404.** Verified directly (`curl -I`) on
2026-07-31. Investigating why led to the rest of this section.

| Source | URL | Call sign / city-state | Status |
|---|---|---|---|
| iptv-org/epg prebuilt guides (`iptv-org.github.io/epg/guides/**`) | n/a — no longer published | N/A | **Dead** — confirmed 404 |
| IPTV-org guide-source index (`api/guides.json`) | `https://iptv-org.github.io/api/guides.json` | Yes, per-channel-id site mapping | **Accepted** (as a coverage index, not a programme-data source) |
| tvtv.us / tvpassport.com grabbers | `iptv-org/epg` `sites/tvtv.us`, `sites/tvpassport.com` | Yes — local affiliate call signs, e.g. `WABCTV71.us` | **Rejected for direct use** (would require scraping their sites ourselves) |
| Community `GUIDES.md` mirrors (`worker-9dd4.onrender.com`, `StrangeDrVN/epg`) | listed in `iptv-org/epg/GUIDES.md` | Unknown / low coverage (2 and 466 channels respectively) | **Rejected** — unofficial, low coverage, no stability guarantee |
| zap2it.com / Gracenote-derived feeds | — | — | **Rejected** — ToS/licensing status unclear, not confirmed authorized for automated use |

### Why the current fallback is dead

`iptv-org/epg`'s own documentation states GitHub Actions that built and
published the pre-made `guides/**` XML files were disabled, and the project
now only ships grabber *code* — running it yourself produces a `guide.xml`
locally, it is no longer hosted centrally by IPTV-org. `GUIDES.md` lists two
community-run replacement mirrors, each covering a small fraction of channels
and run by individual GitHub users rather than IPTV-org itself, so neither
meets the "stable public legal source" bar for a production fallback.

### IPTV-org guide-source index (`api/guides.json`) — accepted, used for reporting only

This is IPTV-org's own already-public JSON file listing, for every channel id
it knows about, which grabber sites are configured to have a guide for it
(`{"channel": "WABCTV71.us", "site": "tvpassport.com", "site_id": "...",
"site_name": "ABC (WABC) New York, NY", ...}`). Filtered to U.S.
local-station-shaped ids and cached at `data/epg-guides-index.json` (see
`scripts/update_epg_data.py`).

We use this **only to report coverage** ("does a guide source exist for this
channel, and via which site?") — we do not fetch programme listings from
`tvpassport.com`/`tvtv.us` ourselves. Actually scraping those sites directly
would mean re-implementing (and re-triggering the ToS exposure of) grabbers
that are already part of the `iptv-org/epg` project; that's out of scope and
explicitly discouraged by the Phase 1 spec ("do not scrape thousands of
station pages" / "unauthorized scraping").

### Custom XMLTV decision

**Not generated this phase.** `epg/AndroidTVGuru.xml` requires real programme
listings from a legal, bulk-fetchable source; none was found (see above). The
`x-tvg-url` in `AndroidTVGuru.m3u` is left unchanged from Phase 0
(`https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml`), per the
"keep the existing customer-facing URL stable" instruction, even though it
currently 404s upstream — this is an IPTV-org-side outage/discontinuation,
not something introduced by this change, and switching to one of the
rejected alternatives above would trade a dead URL for an unstable or
ToS-risky one. This is tracked as a known limitation; see README.md and the
PR description for the recommended follow-up.
