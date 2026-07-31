# android-tv-guru-playlists
Public m3u Playlist for Android TV Guru

## Master playlist

```
https://raw.githubusercontent.com/7000premiumchannels/android-tv-guru-playlists/main/AndroidTVGuru.m3u
```

Regenerated daily by `.github/workflows/update-playlist.yml` from IPTV-org's
public channel/stream data. See `playlists/` for per-category filtered
versions.

## EPG (program guide)

The `x-tvg-url` in `AndroidTVGuru.m3u` points at:

```
https://raw.githubusercontent.com/7000premiumchannels/android-tv-guru-playlists/main/AndroidTVGuru.xml.gz
```

### Why this exists

The previous guide URL (`iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml`)
started returning HTTP 404 — IPTV-org discontinued centrally hosting
pre-built guide files. Rather than leave a dead URL in place, we now build
and host our own guide, in this repository, from legal public sources.

### Sources used

- **tvguide.com** — grabbed via [iptv-org/epg](https://github.com/iptv-org/epg)
  (public-domain/Unlicense open-source tool). Covers national/cable
  networks. The same source our playlist's guide URL already referenced.
- **i.mjh.nz** (Roku, Pluto TV, PBS, Plex, Samsung TV Plus, MeTV) — mirrors
  of these free, ad-supported streaming platforms' own official app APIs,
  openly published on GitHub. Roku Channel in particular rebroadcasts real
  U.S. local TV affiliates with real EPG data, which is the only legal path
  to local-station guide coverage we found — see `docs/DATA_SOURCES.md` for
  the full evaluation (including sources we rejected and why: direct
  scraping of commercial listings sites, paid Schedules Direct/Gracenote
  data, informal community mirrors).

Subscription-only i.mjh.nz providers (Foxtel, Kayo, Sky, DStv, Binge, etc.)
are intentionally excluded.

### Coverage

See `reports/epg-coverage.csv` for the exact current numbers. As of the last
run: 10,509 unique published channel ids, 1,028 matched to a legal EPG
source (9.78%), 0 conflicts flagged for review. Coverage before this change
was effectively 0% (the old guide URL was dead). Every match is either an
exact channel-id match against a source's own channel list, or (for
i.mjh.nz entries with no id filled in) an exact call-sign match — never a
guess, and never inferred from a shared network alone. See
`docs/EPG_MATCHING.md` for the full matching rules and
`reports/epg-unmatched.csv` for the complete list of channels still without
a guide.

### How AndroidTVGuru.xml.gz is generated

```
scripts/update_station_data.py   ->  data/us_tv_stations.json (Wikidata; used only for conflict checks)
scripts/build_epg_source.py      ->  epg/grabber-input.channels.xml + reports/epg-*.csv
iptv-org/epg `grab` command      ->  raw per-source XMLTV
scripts/merge_epg.py             ->  AndroidTVGuru.xml + AndroidTVGuru.xml.gz
```

Automated daily by `.github/workflows/update-epg.yml`, which runs after the
playlist workflow so the channel universe it matches against is current.

### Regenerating it yourself

```sh
python3 scripts/update_station_data.py
python3 scripts/build_epg_source.py
git clone --depth 1 -b master https://github.com/iptv-org/epg.git .epg-tool
cd .epg-tool && npm ci
npx tsx scripts/commands/epg/grab.ts --channels=../epg/grabber-input.channels.xml --days=2 --output=../epg/raw-guide.xml
cd ..
python3 scripts/merge_epg.py epg/raw-guide.xml --output .
```

### Player compatibility caveat

`AndroidTVGuru.xml.gz` currently covers ~10% of published channels
(national/cable networks plus a limited set of local affiliates carried on
Roku Channel). Channels without a guide entry will still play — they just
won't show program information in players that rely on the EPG.

## Legal/public limitation

Only publicly listed, legally accessible data is used for both the playlist
and the guide: no subscription-only, private, credentialed, DRM-bypassed, or
pirated streams or guide data, and NSFW channels are always excluded.

## Development

```
pip install pytest
python3 -m pytest tests/
```
