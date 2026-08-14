# android-tv-guru-playlists

Public M3U playlists for Android TV Guru, built from
[IPTV-org](https://github.com/iptv-org)'s public, legal channel/stream data.
Nothing here is subscription-only, DRM-bypassed, pirated, or credentialed —
if IPTV-org doesn't list it as a public stream, it isn't in these playlists.

## Master playlist

```
https://raw.githubusercontent.com/7000premiumchannels/android-tv-guru-playlists/main/AndroidTVGuru.m3u
```

This is the full playlist: every valid, non-NSFW, publicly listed IPTV-org
stream, deduplicated by URL, organized with `group-title`. It is regenerated
daily by `.github/workflows/update-playlist.yml` and never intentionally
drops channels outside a specific category.

## Category and network playlists

`playlists/*.m3u` — same header/format as the master, filtered to one
category each (`US_ABC.m3u`, `Movies_Classic_TV.m3u`, `Spanish.m3u`, etc.).

## Local station playlists (state-level)

- `playlists/US_Locals_All.m3u` — every confidently identified U.S. local
  station (any network), sorted by network, then state, then city, then call
  sign.
- `playlists/states/<State>.m3u` — one file per U.S. state, e.g.
  `playlists/states/Texas.m3u`, `playlists/states/New York.m3u`
  (raw URL: `.../main/playlists/states/New%20York.m3u` — URL-encode the space).

**These are restricted to "confidently matched" stations only** — a channel
whose name is a real broadcast call sign *and* whose city/state we found in
`data/us_tv_stations.json`. Everything else still appears in the master
playlist and the network/category files above, just without a state
placement, because we never guess a station's city or state.

### Local station naming

When a station is confidently matched:

```
CALLSIGN — City, ST
```

e.g. `WDIV-TV — Detroit, MI`. When it isn't, the original IPTV-org channel
name is used unchanged (e.g. `KABC-TV 7.1`) — never a guessed city/state.

Coverage is partial by design: our station directory is built primarily from
RabbitEars.info's per-state station listings (~6,970 call signs), with
Wikidata (CC0-licensed, queried in bulk) filling any remaining gap, not the
full FCC license database — see `docs/DATA_SOURCES.md` for why, and what
would need to change to get full coverage.

## EPG (program guide)

The `x-tvg-url` in every playlist points at:

```
https://raw.githubusercontent.com/7000premiumchannels/android-tv-guru-playlists/main/AndroidTVGuru.xml.gz
```

### Why this exists

The previous guide URL
(`https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml`) started
returning HTTP 404 — IPTV-org discontinued centrally hosting pre-built guide
files. That URL is now retired; nothing in this repo's production path
references it anymore (see `docs/DATA_SOURCES.md` for the historical
record). We build and host our own guide instead, in this repository, from
legal public sources.

### Sources used

- **tvguide.com** — grabbed via [iptv-org/epg](https://github.com/iptv-org/epg)
  (public-domain/Unlicense open-source tool, pinned to a tested commit — see
  `docs/EPG_MATCHING.md`). Covers national/cable networks. The same source
  our playlist's guide URL already referenced before it went dead.
- **i.mjh.nz** (Roku, Pluto TV, PBS, Plex, Samsung TV Plus, MeTV) — a
  third-party public GitHub project run by an independent developer
  (`matthuisman`) that mirrors data derived from these free, ad-supported
  streaming platforms' apps. Roku Channel in particular rebroadcasts real
  U.S. local TV affiliates with real EPG data, which is the only path to
  local-station guide coverage we found that doesn't involve scraping a
  commercial listings aggregator. **This is not an official source from
  Roku/Pluto/PBS/Plex/Samsung**, and its redistribution terms are not
  formally documented — see `docs/DATA_SOURCES.md` for the full, honest
  evaluation (owner, license status, what "official" would and wouldn't
  mean here, and the sources we rejected and why: direct scraping of
  commercial listings sites, paid Schedules Direct/Gracenote data, informal
  community mirrors).

Subscription-only i.mjh.nz providers (Foxtel, Kayo, Sky, DStv, Binge, etc.)
are intentionally excluded.

### Coverage

See `reports/epg-coverage.csv` for the exact current numbers, and
`reports/epg-unmatched.csv` for the complete list of channels still without
a guide. Every match is either an exact channel-id match against a source's
own channel list, or (for i.mjh.nz entries with no id filled in) an exact
call-sign match — never a guess, and never inferred from a shared network
alone. See `docs/EPG_MATCHING.md` for the full matching rules.

### How AndroidTVGuru.xml.gz is generated

```
android_tv_guru/stations.py (RabbitEars + Wikidata importer) -> data/us_tv_stations.json (used only for conflict checks)
android_tv_guru/epg.py (source matching)         -> epg/grabber-input.channels.xml + reports/epg-*.csv
iptv-org/epg `grab` command (pinned commit)       -> raw per-source XMLTV
android_tv_guru/epg.py (merge)                    -> AndroidTVGuru.xml + AndroidTVGuru.xml.gz
```

`scripts/update_station_data.py`, `scripts/build_epg_source.py`, and
`scripts/merge_epg.py` are thin command-line wrappers around the
`android_tv_guru` package (see `docs/ARCHITECTURE.md`). Automated by
`.github/workflows/update-epg.yml`, which runs after the playlist workflow
so the channel universe it matches against is current.

### Regenerating it yourself

```sh
python3 scripts/update_station_data.py
python3 scripts/build_epg_source.py
git clone --filter=blob:none https://github.com/iptv-org/epg.git .epg-tool
cd .epg-tool && git checkout <pinned commit — see docs/EPG_MATCHING.md> && npm ci
npx tsx scripts/commands/epg/grab.ts --channels=../epg/grabber-input.channels.xml --days=2 --output=../epg/raw-guide.xml
cd ..
python3 scripts/merge_epg.py epg/raw-guide.xml --output .
```

### Player compatibility caveats

- `group-title` values are used for on-screen categorization; not all IPTV
  players group channels visually the same way.
- Some IPTV-org streams are geo-restricted or occasionally offline — this
  project does not currently probe stream health, so a listed channel may
  still fail to play in your region/player.
- State playlist filenames with a space (e.g. `New York.m3u`) need
  URL-encoding (`%20`) when referenced directly as a URL in some players.
- `AndroidTVGuru.xml.gz` currently covers a minority of published channels
  (national/cable networks plus a limited set of local affiliates carried on
  Roku Channel). Channels without a guide entry will still play — they just
  won't show program information in players that rely on the EPG.

## Legal/public limitation

Only publicly listed, legally accessible data is used for both the playlist
and the guide: no subscription-only, private, credentialed, DRM-bypassed, or
pirated streams or guide data, and NSFW channels (`is_nsfw`) are always
excluded.

## Development

```
pip install pytest
python3 -m pytest tests/
python3 build_android_tv_guru_m3u-1.py
```

See `docs/ARCHITECTURE.md` for the package layout and data flow.
