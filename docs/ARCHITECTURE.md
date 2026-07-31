# Architecture

## Package layout

```
android_tv_guru/
  callsigns.py   Syntactic U.S. call-sign extraction from a channel name.
                 No external data — a pure regex over FCC naming conventions.
  stations.py    Loads data/us_tv_stations.json; call sign -> city/state.
                 Missing entries are normal (partial coverage); callers must
                 fall back to the original channel name rather than guess.
  grouping.py    group-title classification: local network (requires a call
                 sign), IPTV-org category, Spanish/African & Caribbean
                 heuristics, "Other International - <cc>" fallback.
  epg.py         Conservative EPG-source matching + conflict detection over
                 IPTV-org's public guide-source index. No network access.
  playlists.py   Orchestration: fetch channels/streams/cities/subdivisions,
                 build Entry objects, write the master + category playlists,
                 write state playlists, run EPG matching, write reports.

scripts/
  update_station_data.py   Builds data/us_tv_stations.json from Wikidata.
  update_epg_data.py       Refreshes data/epg-guides-index.json from IPTV-org's
                            api/guides.json (filtered to local-station ids).

data/
  us_tv_stations.json      Station directory (see docs/DATA_SOURCES.md).
  epg-guides-index.json    Cached, filtered guide-source index.
  epg-overrides.json       Manual, human-reviewed EPG id overrides (empty by default).

reports/        Generated CSVs (epg-matches/unmatched/conflicts/source-coverage).
docs/           This file, DATA_SOURCES.md, EPG_MATCHING.md.
tests/          pytest suite; tests/fixtures/data holds small, hand-written
                fixture channels/streams/stations so tests run offline.

build_android_tv_guru_m3u-1.py   Thin compatibility entry point; calls
                                  android_tv_guru.playlists.main(). Kept so
                                  the GitHub Actions workflow and any existing
                                  bookmarks keep working unchanged.
```

## Data flow

```
channels.json ─┐
streams.json ──┼─▶ playlists.build_entries() ──▶ Entry objects
cities.json ────┤        │
subdivisions.json ┘      ├── grouping.determine_group()   (group-title)
                          ├── callsigns.extract_callsign() (call sign, US only)
                          └── stations.StationDirectory    (confident city/state,
                                                             else fall back to
                                                             the original name)

Entry objects ──▶ write_master_and_categories()  ──▶ AndroidTVGuru.m3u, playlists/*.m3u
             └──▶ write_state_playlists()         ──▶ playlists/US_Locals_All.m3u,
                                                        playlists/states/<State>.m3u
             └──▶ run_epg_matching() (epg.py + data/epg-guides-index.json)
                                                    ──▶ reports/epg-*.csv
```

## Design decisions worth knowing about

- **The call-sign gate is the primary conservative-classification mechanism.**
  A channel only lands in `US Local - <Network>` if its *name* is
  syntactically a real broadcast call sign (`android_tv_guru.callsigns`).
  National feeds like "ABC News Live" or "CBS Sports Network" don't look like
  call signs, so they're excluded by construction — the explicit
  `NATIONAL_FEED_DENYLIST` in `grouping.py` is a secondary, independently
  testable safety net, not the primary mechanism.
- **Display-name enrichment ("CALLSIGN — City, ST") never gates
  classification.** A channel can be `US Local - ABC` without a confident
  station match (it just keeps its original name); state playlists are the
  only outputs restricted to confidently matched stations, because sorting
  by state requires knowing the state.
- **Existing category playlists (`US_Networks.m3u`, `US_ABC.m3u`, etc.) are
  unchanged in shape** — same files, same filtering by group. Their *contents*
  shift because the conservative call-sign gate now excludes national feeds
  that Phase 0's looser name/network regex used to miscount as local (see the
  PR description for before/after counts).
- **No live stream-health probing.** Tests use small, hand-written JSON
  fixtures (`tests/fixtures/data/`) instead of hitting real stream URLs.
