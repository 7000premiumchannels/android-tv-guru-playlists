# Tennessee Local TV Stream Audit

**Status: COMPLETE.** No production file was modified. See the Final Summary
and Safe Candidates sections at the end for the bottom line.

**Scope:** find additional legitimate, publicly accessible Tennessee local TV
streams for Android TV Guru, beyond what IPTV-org already provides. This is a
diagnosis/research pass only — **no production file has been modified.**
`AndroidTVGuru.m3u`, the category playlists, and the playlist builder are
untouched throughout this audit.

**Methodology summary:**
- Station identity/ownership facts are drawn from Wikipedia's ["List of
  television stations in Tennessee"](https://en.wikipedia.org/wiki/List_of_television_stations_in_Tennessee)
  (which itself cites RabbitEars market listings) and cross-checked against
  RabbitEars where noted.
- IPTV-org state (existing stream Y/N) is read fresh from
  `https://iptv-org.github.io/api/channels.json` and `streams.json`.
- Candidate stream URLs are checked with lightweight HTTP requests only
  (HEAD/small ranged GET on manifests) — no substantial video is downloaded,
  per the task's verification protocol.
- No authentication, DRM, geo-restriction, or signed-URL protection is
  bypassed at any point.

---

## 1. Full station inventory

The user's task listed **31 stations** across 6 markets. Cross-checked
against Wikipedia's authoritative Tennessee station list, **Tennessee has 42
full-power stations**, plus one Tri-Cities-market station (WCYB) that is
Virginia-licensed and therefore outside Wikipedia's TN-specific list but
serves the same DMA and was already in the user's list (43 stations total
between the two lists). That leaves **12 additional legitimate full-power TN
stations not in the original list** (marked `NEW` below): WDSI-TV, WKPT-TV,
WKNX-TV, WVLR, WPXK-TV, WTWV, WPXX-TV, WCTE, WHTN, WJFB, WPGD-TV, and WNAB
(Nashville, Roar — not actually in the user's original list, corrected after
an initial mis-tally; WNPX, which *was* in the user's list, is marked `Yes`
below).

| Market | Call sign | Ch. | Affiliation | Licensed city | In user's list? |
|---|---|---|---|---|---|
| Chattanooga | WRCB | 3 | NBC | Chattanooga | Yes |
| Chattanooga | WTVC | 9 | ABC (Fox on .2) | Chattanooga | Yes |
| Chattanooga | WDEF-TV | 12 | CBS | Chattanooga | Yes |
| Chattanooga | WTCI | 45 | PBS | Chattanooga | Yes |
| Chattanooga | WFLI-TV | 53 | CW (MyNetworkTV on .2) | Cleveland, TN | Yes |
| Chattanooga | WDSI-TV | 61 | True Crime Network | Chattanooga | **NEW** |
| Jackson | WBBJ-TV | 7 | ABC (CBS on .3) | Jackson | Yes |
| Jackson | WLJT | 11 | PBS | Lexington, TN | Yes |
| Jackson | WJKT | 16 | Fox | Jackson | Yes |
| Tri-Cities | WETP-TV | 2 | PBS (satellite of WKOP-TV) | Sneedville, TN | Yes |
| Tri-Cities | WJHL-TV | 11 | CBS (ABC on .2) | Johnson City | Yes |
| Tri-Cities | WKPT-TV | 19 | Cozi TV | Kingsport | **NEW** |
| Tri-Cities | WEMT | 39 | Fox | Greeneville, TN | Yes |
| Tri-Cities | WCYB-TV | 5 | NBC (CW on .2, Fox on .3) | Bristol, **VA** | Yes (VA-licensed, TN-market) |
| Knoxville | WATE-TV | 6 | ABC | Knoxville | Yes |
| Knoxville | WKNX-TV | 7 | Independent | Knoxville | **NEW** |
| Knoxville | WVLT-TV | 8 | CBS (MyNetworkTV on .2) | Knoxville | Yes |
| Knoxville | WBIR-TV | 10 | NBC | Knoxville | Yes |
| Knoxville | WKOP-TV | 15 | PBS | Knoxville | Yes |
| Knoxville | WBXX-TV | 20 | CW | Crossville, TN | Yes |
| Knoxville | WTNZ | 43 | Fox | Knoxville | Yes |
| Knoxville | WVLR | 48 | CTN (religious) | Tazewell, TN | **NEW** |
| Knoxville | WPXK-TV | 54 | Ion Television | Jellico, TN | **NEW** |
| Memphis | WREG-TV | 3 | CBS | Memphis | Yes |
| Memphis | WMC-TV | 5 | NBC | Memphis | Yes |
| Memphis | WKNO | 10 | PBS | Memphis | Yes |
| Memphis | WHBQ-TV | 13 | Fox | Memphis | Yes |
| Memphis | WTWV | 23 | Religious independent | Memphis | **NEW** |
| Memphis | WATN-TV | 24 | ABC | Memphis | Yes |
| Memphis | WLMT | 30 | CW | Memphis | Yes |
| Memphis | WPXX-TV | 50 | Ion Television | Memphis | **NEW** |
| Nashville | WKRN-TV | 2 | ABC | Nashville | Yes |
| Nashville | WSMV-TV | 4 | NBC | Nashville | Yes |
| Nashville | WTVF | 5 | CBS | Nashville | Yes |
| Nashville | WNPT | 8 | PBS | Nashville | Yes |
| Nashville | WZTV | 17 | Fox (CW on .2) | Nashville | Yes |
| Nashville | WCTE | 22 | PBS | Cookeville, TN | **NEW** |
| Nashville | WNPX-TV | 28 | Ion Television | Franklin, TN | Yes |
| Nashville | WUXP-TV | 30 | MyNetworkTV | Nashville | Yes |
| Nashville | WHTN | 39 | CTN (religious) | Murfreesboro, TN | **NEW** |
| Nashville | WJFB | 44 | MeTV | Lebanon, TN | **NEW** |
| Nashville | WPGD-TV | 50 | TBN (religious) | Hendersonville, TN | **NEW** |
| Nashville | WNAB | 58 | Roar | Nashville | **NEW** |

Sources:
- [List of television stations in Tennessee — Wikipedia](https://en.wikipedia.org/wiki/List_of_television_stations_in_Tennessee)

---

## 2. IPTV-org baseline (fresh pull, this session)

Confirms and extends the prior session's finding. All 31 originally-listed
stations exist as channel entries in IPTV-org's `channels.json`. Of those,
**3 already have a working stream** (all already correctly represented in
Android TV Guru today):

| Call sign | Market | Network | IPTV-org channel id | Stream? | Currently in Android TV Guru? |
|---|---|---|---|---|---|
| WHBQ-TV | Memphis | Fox | WHBQTV131.us | Yes | Yes — `US Local - FOX`, "WHBQ-TV — Memphis, TN" |
| WDEF-TV | Chattanooga | CBS | WDEFTV121.us | Yes | Yes — `US Local - CBS`, "WDEF-TV — Chattanooga, TN" |
| WBBJ-TV | Jackson | ABC | WBBJTV71.us | Yes | Yes — `US Local - ABC`, "WBBJ-TV — Jackson, TN" (newly confirmed this session; not called out in the prior audit) |

Every other subchannel of every other originally-listed call sign has
**no stream** in IPTV-org's `streams.json` (verified per-subchannel, not just
the primary `.1`).

### IPTV-org state for the 12 additional (`NEW`) stations

All 12 exist as channel entries in IPTV-org's `channels.json`. **None have a
stream** (checked every subchannel of each):

| Call sign | Market | Affiliation | IPTV-org channel ids exist? | Any subchannel has a stream? |
|---|---|---|---|---|
| WDSI-TV | Chattanooga | True Crime Network | Yes (61.1, 61.2) | No |
| WKPT-TV | Tri-Cities | Cozi TV | Yes (both `-CD` and `-TV` id variants, 19.1–19.4) | No |
| WKNX-TV | Knoxville | Independent | Yes (7.1–7.3) | No |
| WVLR | Knoxville | CTN (religious) | Yes (48.1–48.4) | No |
| WPXK-TV | Knoxville | Ion Television | Yes (54.1–54.6) | No |
| WTWV | Memphis | TCT (religious) | Yes (34.1, DT2) | No |
| WPXX-TV | Memphis | Ion Television | Yes (50.1–50.9) | No |
| WCTE | Nashville (Cookeville) | PBS | Yes (22.1–22.4) | No |
| WHTN | Nashville (Murfreesboro) | CTN (religious) | Yes (39.1, 39.3–39.5, DT2) | No |
| WJFB | Nashville (Lebanon) | MeTV | Yes (44.1–44.7, LP1, LP2) | No |
| WPGD-TV | Nashville (Hendersonville) | TBN (religious) | Yes (50.1–50.5) | No |
| WNAB | Nashville | Roar | Yes (58.1, DT2, DT3) | No |

**Running total so far: 43 stations investigated (42 TN-licensed + WCYB), 3
already have a working stream via IPTV-org, all 3 already correctly
represented in Android TV Guru. 40 stations still need a stream — this is
what sections 3+ investigate from sources beyond IPTV-org.**

*(Checkpoint: IPTV-org baseline complete for all 43 stations.)*

---

## 3. FAST platforms (Pluto TV, Roku Channel, Plex, Samsung TV Plus, Local Now)

| Platform | Method | Result |
|---|---|---|
| **Pluto TV** | Fetched Pluto's public channel API (`api.pluto.tv/v2/channels`, 433 channels, no auth needed) and searched every channel name for any of the 31 target call signs or "Nashville"/"Memphis"/"Knoxville"/"Chattanooga"/"Tennessee". | **Zero matches.** Pluto TV carries no Tennessee-affiliated local channel. Consistent with Pluto's catalog being national/syndicated content, not local broadcast simulcasts. |
| **i.mjh.nz (Roku/Plex/Samsung TV Plus/PBS mirror)** | Checked the actual files i.mjh.nz publishes for these providers (already a vetted source in this project's EPG pipeline). | **Not applicable as a stream source** — confirmed i.mjh.nz only republishes EPG *programme schedule* XML for these platforms, not playable stream URLs. Useful for guide data (already used), not for finding new streams. |
| **Samsung TV Plus** | Searched for an official public channel-list API. | **No official public API exists.** Only unofficial, reverse-engineered community tools were found (e.g. a GitHub project that scrapes Samsung TV Plus internals). Per the task's instruction to avoid unclear-authorization sources, this was **not pursued** as a stream source. |
| **Plex (Live TV / Plex Free)** | Same category as Samsung TV Plus — Plex's live-channel catalog isn't a documented public API; would require either the Plex app's authenticated API or unofficial scraping. **Not pursued** for the same reason. |
| **Local Now** (Allen Media Group/Weather Group FAST app — not Scripps-owned, despite carrying some Scripps diginets) | Found via web search that Local Now has a per-station channel page pattern `localnow.com/channels/epg-<callsign>`. Tested all 31 original-list call signs directly (plus WNAB from the additional-stations list, as a spot check). All returned HTTP 200, but a control test against a deliberately bogus slug **also** returned HTTP 200 at an identical 19,596-byte page size — Local Now's router returns 200 for everything (client-side SPA routing), so raw status code is not evidence of a real channel. Compared actual page sizes instead. | **Only WTVF (Nashville, CBS, Scripps-owned) is real** — its page is a fully-hydrated 1.33MB payload, versus the generic 19.6KB "not found" shell for every other call sign tested. No other TN station checked is on Local Now. |

### Local Now / WTVF — investigated in detail, rejected

- URL: `https://localnow.com/channels/epg-wtvf`
- Channel branding: "WTVF Channel5 News Nashville" — **this is explicitly a news-branded channel, not the full CBS broadcast simulcast** (WTVF is Nashville's CBS affiliate; Local Now's own branding calls it a news product). Per the task's full-channel-vs-news-stream distinction, even if usable this would be classified `LOCAL NEWS STREAM`, not `FULL BROADCAST SIMULCAST`.
- **DRM: strong evidence of FairPlay DRM via DRMtoday.** The page's `Content-Security-Policy` header explicitly allowlists `skd://drmtoday` in `connect-src` — `skd://` is Apple's FairPlay Streaming key-delivery URL scheme, and DRMtoday is a commercial DRM licensing service. This is standard, deliberate content-protection infrastructure, not an oversight.
- No `.m3u8`/`.mpd` URL was found in the static page payload (stream is loaded via an authenticated client-side session, consistent with DRM-gated playback).
- **Classification: Category F (DRM-protected). Not a safe candidate**, and per the task's explicit instruction, no DRM bypass was attempted.

*(Checkpoint: Section 3 FAST-platform check complete.)*

---

## 4. NewsON

NewsON (`newson.us`, corporate site `corporate.newson.us`) is a dedicated
local-news aggregator with a genuine public web player (not app-only) —
found via [Cord Cutters News' NewsON channel list](https://cordcuttersnews.com/newson-channel-list-154-stations/)
and [NewsON's own corporate channel list](https://corporate.newson.us/newson-channel-list/).

**Tennessee stations on NewsON:** WTVF, WZTV (Nashville), WHBQ, WATN
(Memphis), WBIR (Knoxville), WDEF, WTVC (Chattanooga), WCYB (Tri-Cities),
WBBJ (Jackson) — 9 stations.

### Technical investigation (WTVC, station id 174, used as the representative case)

- Page: `https://www.newson.us/stationDetails/174` — a SvelteKit app that
  server-renders by prefetching `https://newson-api.triple-it.nl/v5api/detail/station/174?platformType=website`.
- Queried that API endpoint directly (the same public endpoint the page
  itself calls — not a bypass). Response confirms `"stationType": "news"`
  and `"stationGroup": "Sinclair"`, and the only playable content exposed is
  **VOD**: `previous-newscasts-row`, `news-clips-row`,
  `related-sports-videos-row` — individual, on-demand video segments
  ("Good Morning Chattanooga," "NewsChannel 9 at 11," etc.), each with a
  fixed `duration` and `airDate`. **No live/24-7 stream field is present in
  this response at all.**
- The page also references `https://auth.newson.us`, indicating any live
  "watch now" feature is gated behind an authenticated session — **not
  pursued**, per the task's instruction not to bypass authentication.

**Conclusion: NewsON is VOD-only via its public, unauthenticated web API.**
It's a real, legitimate, publicly-accessible source for individual local
news clips, but does not expose a persistent live channel stream suitable
for an M3U entry (an M3U entry needs one stable URL that's always "on";
NewsON's public surface is a catalog of finite-length clips with no live
member). **Not a safe candidate for any of the 9 TN stations it lists,
for this reason** — not because of DRM/auth/geo-restriction on a live
stream, but because no live stream is exposed publicly at all.

*(Checkpoint: Section 4 NewsON complete.)*

---

## 5. PBS station streams

All 7 Tennessee PBS stations (WNPT Nashville, WKNO Memphis, WKOP Knoxville,
WTCI Chattanooga, WETP Tri-Cities [satellite of WKOP], WCTE Cookeville,
WLJT Jackson/Lexington) use PBS's standard, shared "station video portal"
template — a per-station subdomain (`video.<callsign>.org`) that is
consistent across virtually all PBS member stations nationwide, not a
station-specific build.

### Technical investigation (WNPT and WKNO, checked in full; generalized to the rest)

- `https://video.wnpt.org/livestream/` and `https://video.wkno.org/livestream/`
  both embed the identical shared PBS national infrastructure:
  - The visible player is an iframe to `player.pbs.org/ga-livestream-partnerplayer/?station_id=<uuid>` — PBS's own hosted player, not a raw stream URL.
  - WKNO's page additionally exposes explicit DRM license-server URLs directly
    in its embedded config: `fairplay_license`, `widevine_license`, and
    `playready_license`, all served from `proxy.drm.pbs.org`, plus a
    FairPlay certificate URL at `static.drm.pbs.org/fairplay-cert`.
  - WNPT's `ga_live_stream_url` (the "general audience"/main-channel feed)
    literally resolves to `static.drm.pbs.org/v1/channel/livestream-update-needed-ga/index.m3u8`
    — checked directly: **HTTP 404**. That URL slug is a placeholder PBS's
    system shows before a station's live feed is fully provisioned, so
    WNPT's main channel isn't even live-enabled at the platform level right
    now, independent of the DRM question.
  - A third embedded URL, `kids_live_stream_url`
    (`livestream.pbskids.org/out/v1/<id>/est.m3u8` — the shared national PBS
    Kids feed, not a WNPT-specific stream) was checked directly with and
    without a `Referer` header matching the real page: **HTTP 403 both
    times**, confirming it requires a real authenticated player session, not
    just basic hotlink/referer protection.
- **Conclusion: PBS's national livestream platform is DRM-protected
  (Category F) and, for at least WNPT, also currently unprovisioned for a
  live main-channel feed at all.** Since this is shared, centrally-run PBS
  infrastructure (not a per-station custom build), this conclusion is
  extended with high confidence to the other 5 TN PBS stations
  (WKOP, WTCI, WETP, WCTE, WLJT) without repeating the full manifest-level
  verification for each — same platform, same DRM vendor contracts. **None
  are safe candidates.**

*(Checkpoint: Section 5 PBS complete.)*

---

## 6. Station-group corporate platforms and ownership

Ownership established (via Wikipedia, cross-checked against station "About"
pages) for routing to the right corporate platform:

| Call sign | Market | Owner |
|---|---|---|
| WKRN-TV | Nashville | Nexstar Media Group |
| WSMV-TV | Nashville | Gray Media |
| WTVF | Nashville | E.W. Scripps |
| WZTV | Nashville | Sinclair Broadcast Group |
| WATN-TV, WLMT | Memphis | Tegna (duopoly) |
| WHBQ-TV | Memphis | Imagicomm Communications (already has an IPTV-org stream) |
| WATE-TV | Knoxville | Nexstar Media Group |
| WVLT-TV | Knoxville | Gray Media |
| WBIR-TV | Knoxville | Tegna |
| WRCB | Chattanooga | Sarkes Tarzian, Inc. (independent) |
| WTVC, WFLI-TV | Chattanooga/Cleveland | Sinclair Broadcast Group |
| WDEF-TV | Chattanooga | Media General/Gray-affiliated (already has an IPTV-org stream) |
| WJHL-TV | Tri-Cities | Nexstar Media Group |
| WCYB-TV, WEMT | Tri-Cities/Greeneville | Sinclair Broadcast Group |
| WBBJ-TV | Jackson | Independent (already has an IPTV-org stream) |
| WJKT | Jackson | Nexstar Media Group |

### STIRR (Sinclair's FAST app)

Sinclair owns WZTV (Nashville), WTVC + WFLI-TV (Chattanooga), WCYB-TV + WEMT
(Tri-Cities) — 5 of our target stations. STIRR (`stirr.com`) is Sinclair's
consumer FAST platform; per [Cord Cutters News](https://cordcuttersnews.com/stirr-adds-six-new-stirr-city-channels-for-local-coverage/),
"STIRR Cities" is relaunching with local-news partner content in 200+
markets. **Inconclusive by design, not by omission:** STIRR's site
(`stirr.com/lists/91`, `stirr.com/contentLists/9/stirr-cities`) is a fully
client-side-rendered SPA built on the "Vodlix" white-label streaming
platform (confirmed via its JS asset paths) with no channel data present in
the static HTML at all. Determining actual Tennessee coverage would require
executing the page's JavaScript (a headless browser), which is outside the
lightweight-HTTP-only verification approach used throughout this audit.
**Not resolved either way — flagged for follow-up if this is worth pursuing
further, rather than guessed at.**

### Very Local (Tegna)

Checked whether Tegna operates a platform called "Very Local" (as
speculated going in). **It does not appear to exist as a current Tegna
product** — Tegna's own brands page (`tegna.com/brands/`) lists Premion
(a CTV ad platform, not a viewer-facing app), True Crime Network, and Quest
TV, with no mention of "Very Local." No further action taken on this lead.

### NewsON and Haystack News — both confirmed VOD-clip aggregators, not live-stream platforms

In addition to NewsON (Section 4), checked **Haystack News**
(`haystack.tv/channel/wkrn`, explicitly named in the task's source list):
confirmed to show individual pre-recorded news segments (56 seconds to
3+ minutes each), not a persistent live channel. This is the same pattern
as NewsON. **Neither platform exposes a live, persistent stream URL
suitable for an M3U entry**, for any station — this is a structural
property of what these two aggregators are (on-demand clip libraries), not
a station-by-station access restriction.

### Official station websites — bot-protected

Checked WKRN's own live-stream page directly
(`wkrn.com/what-to-watch/watch-news-2-live/`, Nexstar-owned): blocked by
**PerimeterX bot protection** (`px-captcha` challenge page, HTTP 403) before
any player or stream data could be reached. This is a legitimate,
deliberate anti-automation measure — not attempted to bypass, per the
task's instructions. Practically relevant even setting aside the "don't
bypass" rule: a URL that's only reachable through an interactive browser
session defeats the purpose of an M3U entry anyway, since a player app
needs to fetch the manifest directly and periodically, the same way a
scraper would.

### Gray Media (Quickplay video CMS)

Checked WSMV (Nashville, NBC, Gray-owned) directly: `wsmv.com/livestream/`
loads (HTTP 200), and its video infrastructure runs on Gray's "Quickplay"
video CMS (`api.graycms.quickplay.com` — confirmed via image-CDN asset
URLs on the page). Same result as STIRR: **no stream URL, player config, or
video API call is present in the static HTML** — the live player is loaded
by client-side JavaScript after page load, which a plain HTTP request
doesn't execute. Same architecture is shared across all Gray-owned stations
(WSMV Nashville, WVLT Knoxville), so this is a per-vendor finding, not
per-station. **Inconclusive without headless-browser execution** — not
resolved either way, not guessed at.

### Nexstar (WKRN) — confirmed bot-protected (see above)

### Independent stations (Sarkes Tarzian's WRCB)

Checked whether an independently-owned station (not part of the five major
groups) might have simpler, more directly-accessible infrastructure. WRCB
(Chattanooga NBC, Sarkes Tarzian) redirects to `local3news.com`, a
TownNews/"TNCMS" platform (a newspaper CMS also used by some smaller TV
station groups) with a `/livestream/` page. That page returned **HTTP 429
(rate-limited)** on the second request in this session; per the task's
"minimal requests only" instruction, this was not retried immediately.
**Inconclusive — not investigated further in this pass.**

### Religious broadcaster network (CTN — WVLR, WHTN's national network)

Checked whether CTN (Christian Television Network, the national network
carried by WVLR Knoxville-market and WHTN Nashville-market) has a simpler,
more directly accessible stream, on the theory that smaller/nonprofit
broadcasters sometimes run lighter infrastructure than the major
commercial groups. `ctntelevision.com` (a domain surfaced by search)
**does not resolve at all** (DNS failure) — likely a stale/third-party
listing. The real domain, `ctnonline.com`, loads fine but its
"Ways to Watch" page contains **no stream URL, iframe, or player config**
in the static HTML — same JS-rendering barrier as STIRR/Gray. Also worth
noting: even if found, a CTN stream would be the **national CTN network
feed**, not a WVLR- or WHTN-specific local stream (these stations mostly
retransmit CTN's national schedule) — would need to be labeled
accordingly, not attributed to the local station. **Inconclusive, not
pursued further.**

*(Checkpoint: Section 6 complete — the JS-rendering barrier (STIRR, Gray,
CTN) and bot-protection barrier (Nexstar) both mean several platforms could
not be fully resolved via lightweight HTTP-only checks; none were
force-bypassed.)*

---

## 7. EPG check

**No safe candidates were identified in this audit (see Section 8), so
there is nothing new requiring an EPG match.**

For context, the EPG status of the 3 stations already correctly represented
in Android TV Guru (via IPTV-org) was checked directly against the current
`AndroidTVGuru.xml`:

| Call sign | EPG channel id present in `AndroidTVGuru.xml`? | Programme data? |
|---|---|---|
| WHBQ-TV (Memphis, Fox) | No | None |
| WDEF-TV (Chattanooga, CBS) | No | None |
| WBBJ-TV (Jackson, ABC) | No | None |

None of the three currently have EPG programme data — consistent with the
project's existing, previously-documented EPG coverage limitation (roughly
10% of the full channel universe; the EPG matching pipeline's sources —
tvguide.com and i.mjh.nz's Roku/Pluto/PBS/Plex/Samsung mirrors — don't carry
these smaller-market Tennessee affiliates). This is a pre-existing, separate
gap from this audit's scope and is not something this audit's findings
change.

---

## 8. SAFE CANDIDATES FOR ADDITION

**None.**

Every candidate source investigated in this audit falls into one of these
buckets, none of which meet the "Category A: stable, direct, non-DRM,
non-authenticated, suitable for M3U" bar:

- **Category F (DRM-protected):** Local Now (WTVF, Nashville) and PBS's
  national video-portal infrastructure (all 7 TN PBS stations).
- **Not a live stream at all (VOD-clip libraries):** NewsON (9 TN stations)
  and Haystack News (checked for WKRN) — both are on-demand clip
  aggregators with no persistent live channel exposed via their public web
  surface.
- **Category E (authentication-required) / bot-protected, not attempted to
  bypass:** WKRN's own live-stream page (PerimeterX challenge).
- **Inconclusive (JS-rendered, no stream data reachable via static HTTP
  requests, not pursued via headless-browser automation):** STIRR
  (Sinclair — WZTV, WTVC, WFLI-TV, WCYB-TV, WEMT), Gray Media's Quickplay
  CMS (WSMV, WVLT), CTN's national site, and WRCB's `local3news.com`
  livestream page (also rate-limited on the one request attempted).
- **No FAST-platform presence found at all:** Pluto TV (checked all 433
  channels directly — zero Tennessee matches), Samsung TV Plus and Plex
  (no official public API exists for either; unofficial/reverse-engineered
  access was deliberately not used).
- **No streaming platform called "Very Local" appears to exist** under
  Tegna currently (contrary to the initial research hypothesis).

**Every genuinely open, verifiable, non-DRM, non-authenticated direct
stream found in this entire audit was already the 3 stations IPTV-org
already provides** (WHBQ-TV, WDEF-TV, WBBJ-TV) — all already correctly
represented in Android TV Guru before this audit began.

---

## Final Summary

- **Tennessee stations investigated: 43** (42 Tennessee-licensed full-power
  stations per Wikipedia's authoritative list, plus WCYB-TV — Virginia-
  licensed but serving the Tri-Cities Tennessee market and included in the
  user's original list).
  - 31 were in the user's original list (30 Tennessee-licensed + WCYB); **12
    additional legitimate full-power stations were identified and audited**
    (WDSI-TV, WKPT-TV, WKNX-TV, WVLR, WPXK-TV, WTWV, WPXX-TV, WCTE, WHTN,
    WJFB, WPGD-TV, WNAB — see Section 1's full inventory table).
- **Stations already represented in Android TV Guru: 3** — WHBQ-TV (Fox,
  Memphis), WDEF-TV (CBS, Chattanooga), WBBJ-TV (ABC, Jackson). All three
  via IPTV-org, all three correctly classified and named.
- **Additional full broadcast simulcast streams found: 0.**
- **Additional local-news-only streams found (any type): 0** that meet
  the "stable, direct, non-DRM, non-authenticated" bar. Local-news-branded
  content *does* exist for these markets on Local Now (1 station, DRM),
  NewsON (9 stations, VOD-only, no live), and Haystack (checked 1 station,
  VOD-only) — found, investigated, and correctly excluded, not overlooked.
- **Additional PBS/public streams found: 0.** All 7 TN PBS stations use
  PBS's shared, DRM-protected national video-portal platform.
- **Candidates rejected:** Local Now/WTVF (DRM), PBS national platform × 7
  stations (DRM, and WNPT's live feed isn't even provisioned), NewsON × 9
  stations (VOD-only), Haystack/WKRN (VOD-only), WKRN's own site
  (bot-protected).
- **Candidates left inconclusive (not rejected, not confirmed — would need
  headless-browser-based follow-up to resolve, which was out of scope for
  this lightweight-HTTP-only audit):** STIRR (5 Sinclair-owned TN
  stations), Gray Media's Quickplay platform (WSMV, WVLT), CTN's national
  site, WRCB/local3news.com.
- **Safe candidates recommended for addition: 0.**
- **Safe candidates with working EPG: 0** (none exist to check).
- **Stations for which no legitimate direct stream could be found via any
  source in this audit: all 40 stations without an existing IPTV-org
  stream** (every target station except WHBQ-TV, WDEF-TV, WBBJ-TV) —
  though for several of these (the STIRR/Gray/CTN/WRCB group above), "not
  found" reflects the limits of static-HTTP-only investigation, not a
  confirmed absence.

**Bottom line:** this audit did not find any new stream meeting the
task's Category A safety bar. The most concrete, actionable next step
this audit surfaced isn't a new stream to add — it's that **four
distinct platforms (STIRR, Gray Media/Quickplay, CTN, WRCB/local3news)
remain genuinely unresolved** because their content loads via
client-side JavaScript that a lightweight HTTP client can't execute.
Resolving those would require either a headless-browser-based follow-up
pass or manually inspecting the network traffic of a real browser
session — a reasonable next step if this is worth pursuing further, and
explicitly outside what this pass attempted.

No streams were added. `AndroidTVGuru.m3u`, the category playlists, and
`android_tv_guru/playlists.py` remain untouched.
