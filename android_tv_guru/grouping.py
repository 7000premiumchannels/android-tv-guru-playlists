"""Group-title classification for channels.

Group priority (see docs/ARCHITECTURE.md):

US channels:
  1. US Local - <Network>   (only with a confidently identified local station)
  2. IPTV-org category group (news/weather, movies, kids, sports, music, religious)
  3. Spanish (name/network keyword heuristic)
  4. Other US Public Channels

Non-US channels:
  1. Spanish (country-code heuristic)
  2. African & Caribbean (country code)
  3. IPTV-org category group
  4. Other International - <country code>
"""

import re

from .callsigns import extract_callsign

NETWORK_PATTERNS = [
    ("ABC", re.compile(r"\bABC\b|American Broadcasting", re.I)),
    ("CBS", re.compile(r"\bCBS\b", re.I)),
    ("NBC", re.compile(r"\bNBC\b", re.I)),
    ("FOX", re.compile(r"\bFOX\b", re.I)),
    ("CW", re.compile(r"\bCW\b|The CW", re.I)),
    ("PBS", re.compile(r"\bPBS\b|Public Broadcasting", re.I)),
    ("Telemundo", re.compile(r"\bTelemundo\b", re.I)),
    ("Univision", re.compile(r"\bUnivision\b", re.I)),
]

# Explicit safety net: national streaming/news feeds that must never land in a
# "US Local - <Network>" group even though their network metadata says ABC/
# CBS/NBC/FOX. In practice the call-sign gate below already excludes these
# (their names/ids are not call-sign-shaped), but they are listed here by
# exact IPTV-org channel id so the exclusion is explicit and independently
# testable, per the Phase 1 spec.
NATIONAL_FEED_DENYLIST = {
    "ABCNewsLive.us",
    "CBSNews247.us",
    "NBCNewsNOW.us",
    "FoxWeather.us",
    "LiveNOWfromFOX.us",
    "ScrippsNews.us",
    "NewsNation.us",
}

CATEGORY_GROUPS = {
    "news": "US News & Weather",
    "weather": "US News & Weather",
    "movies": "Movies & Classic TV",
    "classic": "Movies & Classic TV",
    "series": "Movies & Classic TV",
    "kids": "Kids & Family",
    "family": "Kids & Family",
    "sports": "Sports & Highlights",
    "music": "Music",
    "religious": "Religious",
}

# IPTV-org's public API does not ship a languages.json, so "Spanish-language"
# is approximated:
#  - US channels: name/network/owners keyword matching (US_SPANISH_RE)
#  - non-US channels: country code membership (SPANISH_SPEAKING_COUNTRIES)
# This is a heuristic, not a real language field, and can misclassify a small
# number of channels (e.g. a bilingual or minority-language channel).
US_SPANISH_RE = re.compile(r"\bspanish\b|\bazteca\b|\blatino\b|\bhispan", re.I)

SPANISH_SPEAKING_COUNTRIES = {
    "ES",
    "MX", "AR", "BO", "CL", "CO", "CR", "CU", "DO", "EC", "SV",
    "GQ", "GT", "HN", "NI", "PA", "PY", "PE", "UY", "VE",
}

AFRICAN_COUNTRIES = {
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CM", "CV", "CF", "TD", "KM", "CD", "CG", "CI",
    "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR",
    "LY", "MG", "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN",
    "SC", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "ZM", "ZW",
}
CARIBBEAN_COUNTRIES = {
    "AG", "BS", "BB", "CU", "DM", "DO", "GD", "HT", "JM", "KN", "LC", "VC", "TT", "PR",
    "AW", "CW", "BQ", "KY", "TC", "VG", "VI", "GP", "MQ",
}

GROUP_ORDER = [
    "US Local - ABC",
    "US Local - CBS",
    "US Local - NBC",
    "US Local - FOX",
    "US Local - CW",
    "US Local - PBS",
    "US Local - Telemundo",
    "US Local - Univision",
    "US News & Weather",
    "Movies & Classic TV",
    "Kids & Family",
    "Sports & Highlights",
    "Music",
    "Religious",
    "Spanish",
    "African & Caribbean",
    "Other US Public Channels",
]
GROUP_ORDER_INDEX = {group: i for i, group in enumerate(GROUP_ORDER)}


def local_network_label(channel):
    """Return the network label ("ABC", "CBS", ...) for a confidently identified
    U.S. local station, or None if the channel should not be locally classified.

    Requires ALL of:
      1. country == "US"
      2. a syntactically valid broadcast call sign in the channel name
      3. the channel is not on the explicit national-feed denylist
      4. network affiliation is supported by IPTV-org's curated "network"
         field (checked first) or, failing that, the channel name/owners
    """
    if channel.get("country") != "US":
        return None
    if channel.get("id") in NATIONAL_FEED_DENYLIST:
        return None

    call_sign = extract_callsign(channel.get("name"))
    if call_sign is None:
        return None

    network_field = channel.get("network") or ""
    owners = " ".join(channel.get("owners") or [])
    name = channel.get("name") or ""

    # Prefer the curated network field alone (most reliable); only fall back
    # to name/owners text if the network field itself doesn't resolve.
    for label, pattern in NETWORK_PATTERNS:
        if pattern.search(network_field):
            return label

    text = f"{name} {network_field} {owners}"
    for label, pattern in NETWORK_PATTERNS:
        if pattern.search(text):
            return label

    return None


def determine_group(channel):
    country = channel.get("country")
    categories = channel.get("categories") or []

    if country == "US":
        network_label = local_network_label(channel)
        if network_label:
            return f"US Local - {network_label}"

        for category in categories:
            if category in CATEGORY_GROUPS:
                return CATEGORY_GROUPS[category]

        name = channel.get("name") or ""
        network_field = channel.get("network") or ""
        owners = " ".join(channel.get("owners") or [])
        if US_SPANISH_RE.search(f"{name} {network_field} {owners}"):
            return "Spanish"

        return "Other US Public Channels"

    if country in SPANISH_SPEAKING_COUNTRIES:
        return "Spanish"

    if country in AFRICAN_COUNTRIES or country in CARIBBEAN_COUNTRIES:
        return "African & Caribbean"

    for category in categories:
        if category in CATEGORY_GROUPS:
            return CATEGORY_GROUPS[category]

    return f"Other International - {country or 'XX'}"


def sort_key(group):
    if group in GROUP_ORDER_INDEX:
        return (0, GROUP_ORDER_INDEX[group], "")
    return (1, group, "")
