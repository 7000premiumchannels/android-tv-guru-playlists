# Data sources

This document records every public data source investigated across Phase 1
(station data for local-station classification/naming) and Phase 1.5
(production EPG), whether each was accepted, and why. Research was performed
2026-07-31; the "known stability and legal limitations" notes below should be
re-checked periodically since third-party terms can change.

## Base channel/stream data (unchanged since Phase 0)

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

Used for local-station display naming (`CALLSIGN — City, ST`) and, in
Phase 1.5, as a cross-check for EPG match conflicts. Implemented in
`android_tv_guru/stations.py`.

| Source | Coverage | Call sign | City/state | License | Status |
|---|---|---|---|---|---|
| **FCC LMS Public Database Files** | Full — the authoritative source | Yes | Yes | Public domain (U.S. government work) | **Rejected — not fetchable from this environment** |
| **RabbitEars.info (per-state search)** | Dense (~6,970 call signs resolved) | Yes | Yes | No formal license; explicit `robots.txt` permission for automated access (see below) | **Accepted — primary source** |
| **Wikidata (SPARQL)** | Partial (~135 call signs resolved) | Yes (via item label) | Yes (via P1408/P159/P131) | CC0 | **Accepted — supplementary, fills any RabbitEars gap** |

### FCC LMS Public Database Files — attempted twice, still not usable

URL: `https://enterpriseefiling.fcc.gov/dataentry/public/tv/lmsDatabase.html`
(a single bulk zip download, per `catalog.data.gov/dataset/lms-public-database-files`).
This is the preferred, authoritative source. What was tried:

- **2026-07-31:** direct fetch of the LMS database page returned HTTP 403
  (Akamai bot protection), with a browser-like User-Agent. The
  `catalog.data.gov` listing page for the same dataset loads but is a
  JavaScript-rendered SPA with no static download link in the HTML.
- **2026-08-14, re-attempted per a request to rule out a UA-specific block:**
  tried a realistic Chrome User-Agent plus full browser `Accept`/
  `Accept-Language` headers against several distinct endpoints —
  `enterpriseefiling.fcc.gov/dataentry/public/tv/lmsDatabase.html`,
  `www.fcc.gov/media/television/tv-query`, `publicfiles.fcc.gov`, and a
  legacy `transition.fcc.gov` CDBS bulk-data path. All either 403'd directly
  from Akamai (`server: AkamaiGHost`) or, in `publicfiles.fcc.gov`'s case,
  returned an empty body behind an Akamai Bot Manager JS-challenge cookie
  exchange (`_abck`/`bm_sz`/`dtCookie`) that a plain HTTP client can't pass.
  **Decisive evidence it's a wholesale, domain-level IP block rather than a
  URL- or header-specific one:** even `www.fcc.gov/robots.txt` — a static,
  trivial file with no bot-protection rationale — returned Akamai's "Access
  Denied" from this environment. No User-Agent or endpoint choice changes
  that outcome.

**Decision:** still do not implement a direct FCC importer. Instead, use
RabbitEars.info (below), which republishes the same underlying FCC
city-of-license data with far denser coverage than the Wikidata fallback.
The importer interface stays schema-stable
(`android_tv_guru.stations.build_station_directory`) so a direct FCC
importer could still replace or supplement either source later without
touching any other module.

### RabbitEars.info — accepted, primary source

- **Owner/operator:** an independent DX/broadcast-engineering hobbyist site
  (`rabbitears.info`), unaffiliated with the FCC or any broadcaster; run
  since 2008.
- **URL pattern:** `https://www.rabbitears.info/search.php?request=state_search&state=XX`
  — one request per U.S. state/territory (55 total: 50 states + DC + PR +
  GU + VI + AS + MP), returning every station whose Nielsen market touches
  that state, grouped by market, as plain server-rendered HTML (no
  JavaScript execution needed).
- **License / permission:** no formal license or ToS statement covering bulk
  reuse of the data was found. However, `rabbitears.info/robots.txt`
  explicitly names `ClaudeBot` with a `Crawl-delay: 5` directive (and no
  `Disallow` for the pages used here) — a clear, machine-readable grant of
  automated access at that rate, which this importer honors as a strict
  minimum delay between requests (`fetch_station_records_from_rabbitears`'s
  `delay` parameter, default 5.0s). This is a one-time/periodic bulk import
  (55 requests total, ~5 minutes), not a continuous crawl.
- **What the data is:** each station row shows its FCC call sign, city of
  license, and licensing state, plus (via the same link) its FCC facility
  ID — the same fields the (unreachable) FCC LMS database would provide.
  The site's own station-detail view attributes "network data" to the FCC
  and links to FCC repack-check tools per station, consistent with this
  being sourced from FCC licensing records rather than independently
  compiled.
- **Coverage:** ~6,970 unique call signs resolved (2026-08-14), roughly 50x
  Wikidata's ~135 — a large majority of the call signs that appear in
  IPTV-org's U.S. channel names, including full-power, Class A, and
  low-power/translator stations.
- **Known limitation:** ~90 rows use a low-power/translator call-sign
  pattern (`K`/`W` + 2-digit channel + **3** letters, e.g. `K13AAE-D`) that
  `android_tv_guru.callsigns.extract_callsign()` doesn't currently recognize
  (its translator pattern only matches a 2-letter suffix). These are
  correctly and silently dropped under the "never guess" rule rather than
  forced through — call-sign syntax recognition is shared, general-purpose
  logic used well beyond station lookup (classification, EPG matching), so
  widening it was treated as a separate, out-of-scope change from this data
  source swap; expanding `_TRANSLATOR_CALL`'s pattern would recover them.
- **Parsing approach:** each state page can run to several megabytes of
  old-style, loosely-closed HTML; a full DOM parse (BeautifulSoup) of a
  file that size is slow enough to matter at 55-file scale, so
  `android_tv_guru.stations._RABBITEARS_ROW_RE` uses a targeted regex over
  the one row shape a genuine station listing has — verified to produce
  identical results to a BeautifulSoup parse on a sample state, and
  verified to correctly skip the HTML's channel-sharing "tenant" sub-rows
  (a station relaying another's transmitter has its own row shape with no
  city/state cells immediately following its call-sign link).
- **Non-U.S. market spillover:** a state search's market grouping
  occasionally includes bordering Canadian or Mexican stations (Nielsen
  DMAs cross borders in a few cases). Each row's own reported state is
  checked against the U.S. state/territory list and discarded if it isn't
  one (verified: Ontario, Baja California, Sonora, and several other
  non-U.S. codes appear in raw output and are correctly filtered).

### Wikidata — accepted, supplementary

- **Owner/operator:** Wikimedia Foundation (Wikidata is a Wikimedia project).
- **URL:** `https://query.wikidata.org/sparql` (public SPARQL endpoint).
- **License:** CC0 (public domain dedication) — Wikidata's data is explicitly
  released for unrestricted reuse, including commercial and redistribution
  use, per Wikidata's own terms.
- **Access method:** one bulk query per location property (`P1408` "licensed
  to broadcast to", `P159` "headquarters location", `P131` "located in the
  administrative territorial entity", in that priority order), not
  per-station scraping.
- **Role since RabbitEars was added:** `build_station_directory()` now
  fetches both sources and merges them, with RabbitEars winning on any call
  sign both resolve (denser, more current); Wikidata's ~135 records only
  matter for whatever handful of call signs RabbitEars doesn't cover.

Details (unchanged from the original Wikidata-only implementation):
- Call sign: derived from the Wikidata item label, validated through
  `android_tv_guru.callsigns.extract_callsign()`, so a malformed/non-call-sign
  label is dropped rather than guessed.
- City/state: from the location property chain, `wdt:P300` (ISO 3166-2 code)
  gives a two-letter state.
- FCC Facility ID: `wdt:P1400`, present on some records.
- The `P131` tier is the coarsest and sometimes resolves to a county or metro
  area instead of a city proper (e.g. "Potter County" instead of "Amarillo").
  That's real Wikidata data, not a guess, but it means precision varies.

## EPG / XMLTV sources

### The retired guide URL — historical record only

The master playlist's `x-tvg-url` used to point at
`https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml`. **That URL
returns HTTP 404** (verified directly with `curl -I` on 2026-07-31) and is
retired from every production code path in this repository — it does not
appear in `AndroidTVGuru.m3u`'s header, any workflow, or any script.
`iptv-org/epg`'s own documentation states the GitHub Actions job that built
and centrally published pre-made `guides/**` XML files was disabled; the
project now only ships grabber *code*, and its `GUIDES.md` lists two
informal, individually-run replacement mirrors (`worker-9dd4.onrender.com`,
2 channels; a `StrangeDrVN/epg` fork, 466 channels) — neither meets a
"stable public source" bar for a production URL, so neither is used. This
history is kept here only as context for why a self-hosted guide exists at
all.

### Sources used to build the current guide

| Source | Type | Owner / repository | Channels available (raw, before filtering to our list) | License / redistribution | Decision |
|---|---|---|---|---|---|
| **tvguide.com** (via `iptv-org/epg` grabber) | Commercial cable/national guide, fetched by an open-source grabber | Grabber tool: `iptv-org/epg` (GitHub org `iptv-org`); underlying data: TV Guide Magazine / Red Ventures | 153 (national/cable, incl. Univision/Telemundo national feeds) | Grabber code is Unlicense (public domain); the underlying tvguide.com data itself is **not** separately licensed to us — we rely on the same access pattern IPTV-org's own project has used for years | **Accepted** |
| **i.mjh.nz** (Roku, Pluto TV, PBS, Plex, Samsung TV Plus, MeTV) | Public third-party aggregator/mirror | Independently run by GitHub user `matthuisman` (`github.com/matthuisman/i.mjh.nz`); not affiliated with Roku/Pluto/PBS/Plex/Samsung | Roku 709, Pluto 2,810, Plex 2,807, Samsung 2,437, PBS 149, MeTV 1 (all providers) | See "About i.mjh.nz" below — no explicit license file or redistribution grant found in the repository; treated as a public mirror, not an official or clearly-licensed feed | **Accepted, with caveats documented below** |
| i.mjh.nz subscription providers (Foxtel, Kayo, Sky, DStv, Binge, Singtel, SkyGo, SkySportNow) | Paid/subscription platforms | Same repository as above | — | Subscription-gated content | **Rejected** — violates the "no subscription-only content" rule even though the grabber technically supports them |
| Direct scraping of tvtv.us / tvpassport.com | Commercial listings aggregators (Nielsen/Gracenote-adjacent) | Commercial companies | Would cover most local affiliates | Commercial ToS; not confirmed authorized for bulk redistribution | **Rejected** |
| Schedules Direct (schedulesdirect.org) | Paid ($25/yr), Gracenote-licensed | Schedules Direct LLC | Comprehensive, incl. local affiliates | ToS explicitly restricts use to the paying account holder's own private devices; redistribution to a public repo is not permitted | **Rejected** |
| Zap2it / Gracenote direct | Commercial | Gracenote (Nielsen) | Comprehensive | Known ToS/legal gray area | **Rejected** |
| IPTV-org guide-source index (`api/guides.json`) | Coverage index (not programme data) | `iptv-org` | Per-channel-id site mapping | Same license as other IPTV-org API files (public, used elsewhere in this project) | **Superseded** — an earlier revision of this pipeline used this purely as a coverage index; the current pipeline fetches real channel lists directly from tvguide.com/i.mjh.nz instead, which is a strict improvement (it drives actual programme data, not just a coverage claim), so the separate index and its cache file were retired to avoid maintaining two matching systems |
| Community `GUIDES.md` mirrors | Informal, individual-run | Various GitHub users | 2 and 466 channels respectively | No stability/ownership guarantee | **Rejected** |

### About i.mjh.nz — accurate description

`i.mjh.nz` (repository: `github.com/matthuisman/i.mjh.nz`) is a **public
third-party aggregator/mirror**, run and maintained by one independent
developer, not by Roku, Pluto TV, PBS, Plex, Samsung, or any streaming
platform. We have **not** found a published license file or explicit
redistribution grant in that repository, and we make no claim that it is an
"official" source.

What we can say concretely, based on inspecting the `iptv-org/epg` grabber
code for this site (`sites/i.mjh.nz/i.mjh.nz.config.js`):
- The grabber's `url()` function fetches a single XMLTV file per provider
  (e.g. `.../Roku/all.xml`) directly from `matthuisman/i.mjh.nz`'s own GitHub
  repository — a static file already published on GitHub, not a scrape of a
  live web page requiring us to bypass any access control.
- The project's stated purpose (per its structure and its adoption by
  `iptv-org/epg` and numerous other public projects that consume it, e.g.
  various Pluto/Roku/Plex playlist generators on GitHub) is to make this data
  available for exactly this kind of downstream consumption, but this is an
  inference from common practice and third-party usage, **not** a documented
  license grant we can point to.
- Where the underlying programme data ultimately comes from (Roku Channel,
  Pluto TV, PBS, Plex, Samsung TV Plus app APIs) is stated by the project's
  own file/path naming, not independently verified by us against each
  platform's own developer documentation.

**Known limitations, stated plainly:**
- No formal license or terms-of-use document was found for `i.mjh.nz` itself.
- We cannot claim legal certainty that redistributing this data (even
  further downstream, as part of our own guide file) is unambiguously
  authorized by the platforms whose data it mirrors.
- Stability is not contractually guaranteed — it is one individual's project.
  If it goes offline or changes format, our EPG generation for Roku/Pluto/
  PBS/Plex/Samsung/MeTV channels would need to be re-evaluated.
- This is nonetheless the least-risky path we found to real local-affiliate
  programme data: it does not require bypassing a paywall or an access
  control on a commercial listings aggregator, and it does not involve a
  paid service whose ToS explicitly forbids redistribution (unlike Schedules
  Direct). We are transparent that "least-risky available option" is not the
  same claim as "confirmed fully licensed."

### Custom XMLTV guide — status

A real `AndroidTVGuru.xml`/`AndroidTVGuru.xml.gz` is generated and hosted
from this repository (`android_tv_guru/epg.py`, driven by
`.github/workflows/update-epg.yml`), combining tvguide.com and the free
(non-subscription) i.mjh.nz providers. See `docs/EPG_MATCHING.md` for the
matching rules and `reports/epg-coverage.csv` for current coverage numbers.
The iptv-org/epg grabber tool itself is pinned to a specific, tested commit
rather than tracking a moving branch — see `docs/EPG_MATCHING.md` for the
pinned SHA and update procedure.
