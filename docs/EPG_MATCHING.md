# EPG matching (Phase 1.5)

Implemented in `scripts/build_epg_source.py`. See `docs/DATA_SOURCES.md` for
the source research.

## Matching tiers

1. **`exact_channel_id`** (confidence: high) — the source's `xmltv_id`
   (stripped of any `@feed` suffix like `@HD`/`@East`) equals our published
   IPTV-org channel id exactly. Because both tvguide.com's and i.mjh.nz's
   channel lists already use IPTV-org channel ids as their `xmltv_id` where
   known, this tier alone accounts for all 1,028 matches in the current run.
2. **`call_sign_in_name`** (confidence: medium) — only applied to i.mjh.nz
   entries that have *no* `xmltv_id` at all. We extract a call sign from our
   channel's own name (`scripts/callsigns.py`) and check whether that exact
   call sign appears as a whole word in the candidate source's display name
   (e.g. call sign `WABC` inside `"WABC ABC7 New York"`). A call sign must
   match as a complete token, never a substring — `KABC` does not match
   `"WKABCD Radio Network"` — and a shared network is never sufficient on its
   own (WABC's guide entry can never satisfy KABC's lookup). In the current
   dataset this tier contributed 0 matches (verified deliberately, not a
   bug): the local-affiliate call signs in our published playlist and the
   local-affiliate names i.mjh.nz exposes with no `xmltv_id` simply don't
   overlap in this snapshot — see `docs/DATA_SOURCES.md` for why real local
   coverage is capped by what Roku Channel actually carries.
3. **Unmatched** — everything else. Never guessed, never inferred from
   network/category alone.

## Conflict detection

For any match where we also have Wikidata station data for the call sign
(`data/us_tv_stations.json`), we check whether the station's known city
appears as a substring in the matched source's display name. A mismatch is
written to `reports/epg-conflicts.csv` for manual review — never
auto-corrected, and never computed at all when we don't have station data to
compare against (no station data = no conflict claim, since we can't verify
one way or the other).

## Reports

- `reports/epg-matches.csv` — `channel_id, call_sign, display_name, source,
  site, site_id, match_method, confidence, reason`
- `reports/epg-unmatched.csv` — `channel_id, call_sign, display_name, reason`
  — this is the full list of remaining unmatched channels.
- `reports/epg-conflicts.csv` — `channel_id, call_sign, matched_display_name,
  known_city, known_state, reason`
- `reports/epg-coverage.csv` — `metric, value`: `total_channels`,
  `matched_channels`, `unmatched_channels`, `conflicts`,
  `coverage_before_percent` (0.0 — the old URL was dead, so effective
  coverage was zero), `coverage_after_percent`.

## Generating the actual guide

`scripts/build_epg_source.py` only produces `epg/grabber-input.channels.xml`
(the *input* to the grabber — which sources to fetch and what id/name to
label the result with) and the reports above; it makes no network calls to
any guide source itself, only to IPTV-org's own channel-list files. Fetching
real programme data is a separate step (`iptv-org/epg`'s grab command,
invoked by `.github/workflows/update-epg.yml`), and merging the result into
`AndroidTVGuru.xml`/`.xml.gz` is `scripts/merge_epg.py`, which also:

- drops (and counts) any duplicate `<channel id>` across input files, keeping
  the first occurrence
- drops (and counts) any `<programme channel="...">` that doesn't reference a
  channel actually present in the merged output — this is what "broken guide
  generation" means and is directly covered by
  `tests/test_merge_epg.py`

## Regenerating locally

```sh
python3 scripts/update_station_data.py     # refresh data/us_tv_stations.json
python3 scripts/build_epg_source.py        # refresh reports/ and epg/grabber-input.channels.xml
git clone --depth 1 -b master https://github.com/iptv-org/epg.git .epg-tool
cd .epg-tool && npm ci
npx tsx scripts/commands/epg/grab.ts --channels=../epg/grabber-input.channels.xml \
  --days=2 --output=../epg/raw-guide.xml
cd ..
python3 scripts/merge_epg.py epg/raw-guide.xml --output .
```
