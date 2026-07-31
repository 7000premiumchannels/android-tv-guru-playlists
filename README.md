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

Coverage is partial by design: our station directory is built from Wikidata
(CC0-licensed, queried in bulk), not the full FCC license database — see
`docs/DATA_SOURCES.md` for why, and what would need to change to get full
coverage.

## EPG limitations

The `x-tvg-url` header in every playlist points at:

```
https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml
```

**As of 2026-07-31, this URL returns HTTP 404.** IPTV-org disabled the
GitHub Actions job that built and published pre-made guide XML files; see
`docs/DATA_SOURCES.md` and `docs/EPG_MATCHING.md` for the full investigation
and why we didn't replace it with an unofficial/low-coverage mirror or a
self-hosted feed this phase. Practically: players that fetch this URL for
program-guide data will get nothing back until IPTV-org restores hosting (or
a future phase ships a real replacement); channel playback itself is
unaffected.

We do report, per local station, whether a legal public guide source is
*known* to exist for it (without switching your guide feed) — see
`reports/epg-*.csv` after a build, and `docs/EPG_MATCHING.md`.

## Player compatibility caveats

- `group-title` values are used for on-screen categorization; not all IPTV
  players group channels visually the same way.
- Some IPTV-org streams are geo-restricted or occasionally offline — this
  project does not currently probe stream health (Phase 1 explicitly
  excludes live stream-health probing), so a listed channel may still fail
  to play in your region/player.
- State playlist filenames with a space (e.g. `New York.m3u`) need
  URL-encoding (`%20`) when referenced directly as a URL in some players.

## Legal/public limitation

Only publicly listed IPTV-org channel/stream data is used. We do not add
subscription-only, private, credentialed, DRM-bypassed, or pirated streams,
and NSFW channels (`is_nsfw`) are always excluded.

## Development

```
pip install pytest
python3 -m pytest tests/
python3 build_android_tv_guru_m3u-1.py
```

See `docs/ARCHITECTURE.md` for the package layout and data flow.
