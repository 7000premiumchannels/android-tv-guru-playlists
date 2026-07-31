"""Lookup of U.S. TV station city/state by call sign.

Backed by data/us_tv_stations.json (see scripts/update_station_data.py for how
that file is produced, and docs/DATA_SOURCES.md for the source decision).
Coverage is intentionally partial — see that script's docstring. A missing
lookup is not an error; callers should fall back to the original channel name.
"""

import json
from pathlib import Path
from typing import Dict, Optional

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "us_tv_stations.json"

US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin",
    "WY": "Wyoming", "DC": "District of Columbia",
}


class StationDirectory:
    def __init__(self, records):
        self._by_call_sign: Dict[str, dict] = {r["normalized_call_sign"]: r for r in records}

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "StationDirectory":
        if not path.exists():
            return cls([])
        records = json.loads(path.read_text(encoding="utf-8"))
        return cls(records)

    def lookup(self, normalized_call_sign: str) -> Optional[dict]:
        return self._by_call_sign.get(normalized_call_sign)

    def __len__(self):
        return len(self._by_call_sign)


def state_name(state_code: Optional[str]) -> Optional[str]:
    if not state_code:
        return None
    return US_STATE_NAMES.get(state_code.upper())
