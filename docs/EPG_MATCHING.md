# EPG matching

Implemented in `android_tv_guru/epg.py` (canonical package module;
`scripts/build_epg_source.py` is a thin CLI wrapper around it). See
`docs/DATA_SOURCES.md` for the source research.

## Match tiers (most to least confident)

1. **`manual_override`** — the channel id has an entry in
   `data/epg-overrides.json`. This file is empty by default; entries are only
   added after a human confirms the mapping, never generated automatically.
2. **`exact_channel_id`** (confidence: high) — the source's `xmltv_id`
   (stripped of any `@feed` suffix like `@HD`/`@East`) equals our published
   IPTV-org channel id exactly. Because both tvguide.com's and i.mjh.nz's
   channel lists already use IPTV-org channel ids as their `xmltv_id` where
   known, this tier alone accounts for essentially all matches in the current
   run (see `reports/epg-coverage.csv` for exact counts).
3. **`call_sign_in_name`** (confidence: medium) — only applied to i.mjh.nz
   entries that have *no* `xmltv_id` at all. We extract a call sign from our
   channel's own name (`android_tv_guru.callsigns`) and check whether that
   exact call sign appears as a whole word in the candidate source's display
   name (e.g. call sign `WABC` inside `"WABC ABC7 New York"`). A call sign
   must match as a complete token, never a substring — `KABC` does not match
   `"WKABCD Radio Network"` — and a shared network is never sufficient on its
   own (WABC's guide entry can never satisfy KABC's lookup).
4. **Unmatched** — everything else. Never guessed, never inferred from
   network/category alone.

Every matcher function in `android_tv_guru/epg.py` is a pure function over
already-loaded data — no network access happens during matching itself, only
during the (separate) fetch of source channel lists.

## Conflict detection

`find_conflict()` checks whether the channel's known station city (from
`data/us_tv_stations.json`, when we have it) appears as a substring in the
matched source's display name. A mismatch is written to
`reports/epg-conflicts.csv` for manual review — never auto-corrected, and
never computed at all when we don't have station data to compare against (no
station data = no conflict claim, since we can't verify one way or the
other). Example: `KQED92.us` (KQED2, San Jose) vs. our station record for
`KQED-TV` showing San Francisco would be flagged rather than silently
trusted either way.

## Reports

- `reports/epg-matches.csv` — `channel_id, call_sign, display_name, source,
  site, site_id, match_method, confidence, reason`
- `reports/epg-unmatched.csv` — `channel_id, call_sign, display_name, reason`
  — the full list of remaining unmatched channels.
- `reports/epg-conflicts.csv` — `channel_id, call_sign, matched_display_name,
  known_city, known_state, reason`
- `reports/epg-coverage.csv` — `metric, value`: `total_channels`,
  `matched_channels`, `unmatched_channels`, `conflicts`,
  `coverage_before_percent` (0.0 — the old guide URL was dead, so effective
  coverage was zero before this work), `coverage_after_percent`.

## Generating the actual guide

`android_tv_guru.epg.build_and_write()` (invoked by
`scripts/build_epg_source.py`) only produces `epg/grabber-input.channels.xml`
(the *input* to the grabber — which sources to fetch and what id/name to
label the result with) and the reports above; it makes no network calls to
any guide source's programme data itself, only to the source's channel *list*
files. Fetching real programme data is a separate step (`iptv-org/epg`'s
`grab` command, invoked by `.github/workflows/update-epg.yml`), and merging
the result into `AndroidTVGuru.xml`/`.xml.gz` is
`android_tv_guru.epg.merge_guides()` / `write_guide_outputs()` (wrapped by
`scripts/merge_epg.py`), which also:

- drops (and counts) any duplicate `<channel id>` across input files, keeping
  the first occurrence
- drops (and counts) any `<programme channel="...">` that doesn't reference a
  channel actually present in the merged output — this is what "broken guide
  generation" means and is directly covered by `tests/test_merge_epg.py`

## Pinned iptv-org/epg version

`.github/workflows/update-epg.yml` checks out `iptv-org/epg` at a **fixed
commit**, not a moving branch:

```
Pinned commit: 1344395e9edb2967782dcda55b66fbc757db5caa
Pinned on:     2026-07-31
Verified by:   running both the tvguide.com and i.mjh.nz (roku/pluto/pbs/
               plex/samsung/metv) grabbers at this exact commit and
               confirming real programme data was returned for all sources
               that completed (see docs/DATA_SOURCES.md and the PR
               description for exact counts).
```

**Why pinned:** `iptv-org/epg`'s site grabbers are actively maintained
against frequently-changing upstream APIs; tracking `master` means a bad
upstream change could silently break our nightly guide generation with no
way to know which commit last worked. Pinning means upgrades are a
deliberate, reviewed action.

**Update procedure:** to move to a newer commit, clone the tool, check out
the candidate commit, run the same grab commands documented below against a
small channel sample, confirm real programme data comes back for both
tvguide.com and i.mjh.nz, then update the `git checkout <sha>` line in
`.github/workflows/update-epg.yml` and this document's pinned-commit block
in the same PR.

## Regenerating locally

```sh
python3 scripts/update_station_data.py     # refresh data/us_tv_stations.json
python3 scripts/build_epg_source.py        # refresh reports/ and epg/grabber-input.channels.xml
git clone --filter=blob:none https://github.com/iptv-org/epg.git .epg-tool
cd .epg-tool
git checkout 1344395e9edb2967782dcda55b66fbc757db5caa
npm ci
npx tsx scripts/commands/epg/grab.ts --channels=../epg/grabber-input.channels.xml \
  --days=2 --output=../epg/raw-guide.xml
cd ..
python3 scripts/merge_epg.py epg/raw-guide.xml --output .
```
