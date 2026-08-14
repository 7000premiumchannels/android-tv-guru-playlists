from pathlib import Path

import android_tv_guru.stations as stations_module
from android_tv_guru.stations import StationDirectory, state_name

FIXTURE = Path(__file__).parent / "fixtures" / "data" / "us_tv_stations.json"

# A trimmed real fragment of a RabbitEars state_search response: one genuine
# station row (WLNE-TV), plus a channel-sharing "tenant" sub-row (WPXQ-TV,
# sharing WLWC's transmitter) that must NOT be parsed as its own station —
# it doesn't have city/state cells immediately after its callsign link, only
# subchannel/network detail. See android_tv_guru.stations._RABBITEARS_ROW_RE.
_SAMPLE_STATE_HTML = """
<tr>
   <td>6</td>
   <td >24</td>
   <td><a href="market.php?request=station_search&callsign=22591#station"
      onclick="toggleStation('_66_22591'); return false;" title="Click to expand"><nobr>WLNE-TV</nobr></a></td>
   <td><nobr>NEW BEDFORD</nobr></td>
   <td>MA</td>
</tr>
<tr>
   <td>28</td>
   <td>17&nbsp;(G)</td>
   <td><a href="market.php?request=station_search&callsign=3978#station"><nobr>WLWC</nobr></a></td>
   <td><nobr>NEW BEDFORD</nobr></td>
   <td>MA</td>
</tr>
<tr>
   <td>08-1</td>
   <td></td>
   <td>31.3</td>
   <td></td>
   <td>1080i</td>
   <td></td>
   <td>DD5.1</td>
   <td>WYCN-LD</td>
   <td>Telemundo</td>
   <td>"Telemundo Providence"</td>
   <td><a href="market.php?request=station_search&callsign=50063#station">WPXQ-TV</a></td>
</tr>
<tr>
   <td>12</td>
   <td>7</td>
   <td><a href="market.php?request=station_search&callsign=47404#station"><nobr>WPRI-TV</nobr></a></td>
   <td><nobr>PROVIDENCE</nobr></td>
   <td>RI</td>
</tr>
<tr>
   <td>1</td>
   <td>5</td>
   <td><a href="market.php?request=station_search&callsign=99999#station"><nobr>CFTO-DT</nobr></a></td>
   <td><nobr>TORONTO</nobr></td>
   <td>ON</td>
</tr>
"""


def test_lookup_known_call_sign():
    directory = StationDirectory.load(FIXTURE)
    record = directory.lookup("WDIV-TV")
    assert record is not None
    assert record["city"] == "Detroit"
    assert record["state"] == "MI"


def test_lookup_unknown_call_sign_returns_none():
    directory = StationDirectory.load(FIXTURE)
    assert directory.lookup("KZZZ-TV") is None


def test_missing_file_yields_empty_directory():
    directory = StationDirectory.load(Path("/nonexistent/path.json"))
    assert len(directory) == 0
    assert directory.lookup("WDIV-TV") is None


def test_state_name_lookup():
    assert state_name("MI") == "Michigan"
    assert state_name("mi") == "Michigan"
    assert state_name(None) is None
    assert state_name("ZZ") is None


def test_rabbitears_row_regex_extracts_genuine_stations_only():
    matches = list(stations_module._RABBITEARS_ROW_RE.finditer(_SAMPLE_STATE_HTML))
    calls = {m.group("call") for m in matches}
    # WLNE-TV, WLWC, WPRI-TV: genuine station rows with their own city/state cells.
    assert {"WLNE-TV", "WLWC", "WPRI-TV"} <= calls
    # WPXQ-TV only appears inside a channel-sharing tenant sub-row (no
    # city/state cells immediately after its link) and must not be captured.
    assert "WPXQ-TV" not in calls
    # CFTO-DT is included by the regex itself (state filtering happens in
    # fetch_station_records_from_rabbitears, not the row regex).
    assert "CFTO-DT" in calls


def test_fetch_station_records_from_rabbitears_filters_and_normalizes(monkeypatch):
    monkeypatch.setattr(stations_module, "_RABBITEARS_STATES", ["RI"])
    monkeypatch.setattr(stations_module, "_fetch_rabbitears_state_page", lambda state: _SAMPLE_STATE_HTML)

    records = stations_module.fetch_station_records_from_rabbitears(log=lambda *a: None, delay=0.0)
    by_call = {r["call_sign"]: r for r in records}

    assert by_call["WLNE-TV"]["city"] == "New Bedford"
    assert by_call["WLNE-TV"]["state"] == "MA"
    assert by_call["WLNE-TV"]["source"] == "rabbitears"
    assert by_call["WPRI-TV"]["city"] == "Providence"

    # Channel-sharing tenant row never produces a bogus record.
    assert "WPXQ-TV" not in by_call
    # Non-U.S. spillover (Toronto, ON) is discarded, never guessed as a U.S. station.
    assert "CFTO-DT" not in by_call


def test_build_station_directory_merges_rabbitears_over_wikidata(tmp_path, monkeypatch):
    monkeypatch.setattr(
        stations_module, "fetch_station_records_from_wikidata",
        lambda log=print: [
            {
                "call_sign": "WLNE-TV", "normalized_call_sign": "WLNE-TV", "city": "Stale Wikidata City",
                "state": "MA", "facility_id": None, "service_type": "full_power", "status": "active",
                "source": "wikidata", "last_updated": "2020-01-01",
            },
            {
                "call_sign": "KZZZ-TV", "normalized_call_sign": "KZZZ-TV", "city": "Wikidata Only City",
                "state": "CA", "facility_id": None, "service_type": "full_power", "status": "active",
                "source": "wikidata", "last_updated": "2020-01-01",
            },
        ],
    )
    monkeypatch.setattr(
        stations_module, "fetch_station_records_from_rabbitears",
        lambda log=print: [
            {
                "call_sign": "WLNE-TV", "normalized_call_sign": "WLNE-TV", "city": "New Bedford",
                "state": "MA", "facility_id": "22591", "service_type": "full_power", "status": "active",
                "source": "rabbitears", "last_updated": "2026-08-14",
            },
        ],
    )

    out_path = tmp_path / "us_tv_stations.json"
    count = stations_module.build_station_directory(path=out_path, log=lambda *a: None)
    assert count == 2

    directory = StationDirectory.load(out_path)
    # RabbitEars wins on overlap (fresher, denser source).
    assert directory.lookup("WLNE-TV")["city"] == "New Bedford"
    assert directory.lookup("WLNE-TV")["source"] == "rabbitears"
    # Wikidata-only stations are preserved as a gap-filling fallback.
    assert directory.lookup("KZZZ-TV")["city"] == "Wikidata Only City"
