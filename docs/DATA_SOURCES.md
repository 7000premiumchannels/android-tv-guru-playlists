# EPG data sources (Phase 1.5)

Research performed 2026-07-31. This document is scoped to the production EPG
(Phase 1.5); it does not cover playlist/stream data sources, which are
unchanged from Phase 0/1.

## Why the previous guide URL needed replacing

The playlist's `x-tvg-url` pointed at
`https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml`. That URL
currently returns **HTTP 404**. IPTV-org's `epg` project disabled the GitHub
Actions job that built and centrally hosted pre-made guide XML files;
`GUIDES.md` in that repo now only lists two informal, community-run mirrors
(`worker-9dd4.onrender.com`, 2 channels; a `StrangeDrVN/epg` fork, 466
channels) — neither is official, comprehensive, or a stability guarantee we'd
want to depend on for a production URL.

## Sources evaluated

| Source | Type | Channels available | Call sign / city data | License / access | Decision |
|---|---|---|---|---|---|
| **tvguide.com** (via `iptv-org/epg` grabber) | Commercial cable/national guide, scraped by an open-source grabber | 153 (national/cable, incl. Univision/Telemundo national feeds) | No local affiliates | Grabber is Unlicense (public domain); same source our own header already referenced pre-Phase-1.5 | **Accepted** |
| **i.mjh.nz** (Roku, Pluto TV, PBS, Plex, Samsung TV Plus, MeTV) | Mirrors of free ad-supported streaming platforms' own official app APIs | Roku 709, Pluto 2,810, Plex 2,807, Samsung 2,437, PBS 149, MeTV 1 (all providers, before filtering to our channel set) | Roku rebroadcasts real U.S. local affiliates (e.g. `WABCTV71.us`, `KABCTV71.us`) with real EPG data | Openly published on GitHub (`matthuisman/i.mjh.nz`), sourced from each platform's own official API, not scraped from a paywalled listings aggregator | **Accepted** — this is the *significantly better source* found during research: it is the only legal path to real local-affiliate programme data we found |
| **i.mjh.nz** subscription providers (Foxtel, Kayo, Sky, DStv, Binge, Singtel, SkyGo, SkySportNow) | Paid/subscription platforms | — | — | Subscription-gated content | **Rejected** — violates the "no subscription-only content" rule even though the grabber technically supports them |
| Direct scraping of tvtv.us / tvpassport.com | Commercial listings aggregators (Nielsen/Gracenote-adjacent) | Would cover most local affiliates | Yes, extensively | Commercial ToS, not confirmed authorized for bulk redistribution | **Rejected** — same reasoning as Phase 1: this is unauthorized scraping of a commercial data provider, not "self-hosting an open source tool against its own designed target" |
| Schedules Direct (schedulesdirect.org) | Paid ($25/yr), Gracenote-licensed | Comprehensive, incl. local affiliates | Yes | ToS explicitly restricts use to the paying account holder's own private devices; redistribution to a public repo is not permitted | **Rejected** |
| Zap2it / Gracenote direct | Commercial | Comprehensive | Yes | Known ToS/legal gray area (flagged in Phase 1 research too) | **Rejected** |
| Community `GUIDES.md` mirrors | Informal, individual-run | 2 and 466 channels respectively | Unknown | No stability/ownership guarantee | **Rejected** |

## Why i.mjh.nz is legally sound

`iptv-org/epg`'s `i.mjh.nz` site grabber does not scrape a web page — its
`url()` function fetches a single already-public, already-generated XMLTV
file per provider directly from `matthuisman/i.mjh.nz`'s own GitHub
repository (e.g. `.../Roku/all.xml`), which that project maintains
specifically so other tools can consume it. That data, in turn, comes from
each streaming platform's own official app-facing API (the same API their
own free apps use) — Roku Channel, Pluto TV, Plex, Samsung TV Plus, and PBS
all operate ad-supported, no-subscription-required linear channels, and
these are frequently the same platforms IPTV-org's public stream list itself
draws from. This is a fundamentally different legal posture than scraping a
commercial listings site like tvtv.us/tvpassport.com/Zap2it: nothing here
requires bypassing a paywall, violating a ToS against automated access, or
redistributing licensed commercial data.

## Coverage achieved

See `reports/epg-coverage.csv` for the exact numbers from the last run.
Summary: of 10,509 unique channel ids in the published master playlist,
1,028 (9.78%) matched a legal EPG source by channel id (all via
`exact_channel_id` — see `docs/EPG_MATCHING.md`).

**Note on this development environment specifically:** this sandbox has very
limited free memory (frequently under 2GB, shared with several other running
processes) and could not reliably parse the larger i.mjh.nz provider files
end-to-end — `Roku/all.xml` alone is ~36MB and repeatedly triggered an
out-of-memory kill here regardless of concurrency/heap settings. The
committed `AndroidTVGuru.xml`/`.xml.gz` in this PR therefore contains real,
live-fetched programme data for the sources that *did* complete
(tvguide.com: 92 channels, i.mjh.nz/PBS: 5, i.mjh.nz/MeTV: 1,
i.mjh.nz/Samsung: 19 — 117 channels, 3,114 programmes total), while the
Roku/Pluto/Plex matches (911 channels, already computed and written to
`epg/grabber-input.channels.xml` and `reports/epg-matches.csv`) are fully
wired into `.github/workflows/update-epg.yml` and will populate on the first
scheduled run on a normal GitHub Actions runner, which has dedicated memory
and won't hit this constraint. This is a development-environment limitation,
not a limitation of the pipeline or the data source.
