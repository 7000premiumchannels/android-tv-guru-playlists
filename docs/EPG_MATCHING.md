# EPG matching

See `docs/DATA_SOURCES.md` for the source research this design is based on.
This document covers the matching rules, report formats, and the reasoning
behind not switching to a custom XMLTV feed in Phase 1.

## What this phase does and does not do

- **Does not** change the `tvg-id` we publish for any channel. We always use
  the IPTV-org channel id (unchanged from Phase 0).
- **Does not** fetch programme listings from any third-party guide site
  (tvpassport.com, tvtv.us, etc.) — see `docs/DATA_SOURCES.md` for why.
- **Does** report, per U.S. local station, whether a known EPG source exists
  for its exact channel id, using IPTV-org's own public guide-source index
  (`api/guides.json`, cached at `data/epg-guides-index.json`).
- **Does** support a manual override file (`data/epg-overrides.json`) for
  human-reviewed exceptions, and flag city-mismatch conflicts for review.

## Match tiers (most to least confident)

1. **`manual_override`** — the channel id has an entry in
   `data/epg-overrides.json`. This file is empty by default; entries are only
   added after a human confirms the mapping, never generated automatically.
2. **`exact_channel_id`** — the channel id appears verbatim as a `channel` key
   in the IPTV-org guide-source index, meaning at least one grabber site is
   already configured with a guide for this exact channel. Because IPTV-org's
   local-station channel ids already are the call sign (e.g. `WABCTV71.us`),
   this tier is simultaneously an exact call-sign match — there is no
   separate "match by call sign against a different id" tier, since that
   would require guessing an id, which we don't do.
3. **`unmatched`** — no override and no index entry. Left alone; never
   inferred from a shared network (WABC is never matched using KABC's guide
   entry just because both are ABC).

Every matcher call in `android_tv_guru/epg.py` is a pure function over
already-loaded data — no network access happens during matching itself, only
during the (separate) refresh of `data/epg-guides-index.json`.

## Conflict detection

`find_conflicts()` compares the city embedded in a guide source's
`site_name` (e.g. "ABC (KABC) Los Angeles, CA HD") against the channel's
known city from `data/us_tv_stations.json`. A mismatch is reported, not
auto-corrected — e.g. `KQED92.us` (KQED2, San Jose) vs. our station record
for `KQED92.us` showing San Francisco is flagged for manual review rather
than silently trusted either way. If we have no station data for a channel,
no conflict check runs — we never guess a conflict we can't verify.

## Reports

Running the builder writes four CSVs to `reports/`, scoped to channels
classified into a `US Local - <Network>` group (see
`android_tv_guru/playlists.py::run_epg_matching`):

- `epg-matches.csv` — every non-unmatched result, with `channel_id,
  call_sign, display_name, city, state, original_tvg_id, selected_epg_id,
  source_name, match_method, confidence, reason`.
- `epg-unmatched.csv` — same columns, `match_method == unmatched` only.
- `epg-conflicts.csv` — `channel_id, site, site_name, known_city,
  known_state, reason`.
- `epg-source-coverage.csv` — `source_name, channel_count`, an aggregate
  count of matches per guide source (plus an `unmatched` row), useful for
  answering "how many local stations have some guide coverage, and from
  where?"

## Why AndroidTVGuru.m3u keeps its current `x-tvg-url`

The Phase 1 spec's gate for switching to a custom XMLTV feed is: it validates,
every selected tvg-id exists in it, tests pass, coverage beats the existing
fallback, and there are no cross-market mismatches. We did not build a custom
feed with real programme data this phase (no legal bulk programme-data source
was found — see `docs/DATA_SOURCES.md`), so that gate can't be evaluated, and
the header stays exactly as it was in Phase 0. Separately, and worth flagging
loudly: that existing fallback URL currently 404s upstream (IPTV-org
discontinued hosting pre-built guides). That is an external outage, not
something this change causes or can safely paper over by pointing at an
unofficial/low-coverage mirror instead. See the PR description for the
recommended next step.
