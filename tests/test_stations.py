from pathlib import Path

from android_tv_guru.stations import StationDirectory, state_name

FIXTURE = Path(__file__).parent / "fixtures" / "data" / "us_tv_stations.json"


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
