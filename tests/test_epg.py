from android_tv_guru.epg import (
    build_guide_index,
    find_conflicts,
    match_channel,
)


def test_exact_channel_id_match_is_high_confidence():
    guide_index = build_guide_index(
        [{"channel": "WABCTV71.us", "site": "tvpassport.com", "site_name": "ABC (WABC) New York, NY"}]
    )
    match = match_channel(
        channel_id="WABCTV71.us",
        call_sign="WABC-TV",
        display_name="WABC-TV — New York, NY",
        station={"city": "New York", "state": "NY"},
        guide_index=guide_index,
        overrides={},
    )
    assert match.match_method == "exact_channel_id"
    assert match.confidence == "high"
    assert match.selected_epg_id == "WABCTV71.us"


def test_manual_override_takes_precedence_over_index_match():
    guide_index = build_guide_index(
        [{"channel": "WABCTV71.us", "site": "tvpassport.com", "site_name": "ABC (WABC) New York, NY"}]
    )
    overrides = {"WABCTV71.us": "WABC.us@override"}
    match = match_channel(
        channel_id="WABCTV71.us",
        call_sign="WABC-TV",
        display_name="WABC-TV — New York, NY",
        station={"city": "New York", "state": "NY"},
        guide_index=guide_index,
        overrides=overrides,
    )
    assert match.match_method == "manual_override"
    assert match.selected_epg_id == "WABC.us@override"


def test_no_shared_network_matching():
    # WABC and KABC share a network (ABC) but not a channel id; KABC must
    # never be matched off of WABC's guide-index entry.
    guide_index = build_guide_index(
        [{"channel": "WABCTV71.us", "site": "tvpassport.com", "site_name": "ABC (WABC) New York, NY"}]
    )
    match = match_channel(
        channel_id="KABCTV71.us",
        call_sign="KABC-TV",
        display_name="KABC-TV 7.1",
        station=None,
        guide_index=guide_index,
        overrides={},
    )
    assert match.match_method == "unmatched"
    assert match.selected_epg_id is None


def test_source_priority_prefers_tvguide_over_others():
    guide_index = build_guide_index(
        [
            {"channel": "WABCTV71.us", "site": "ontvtonight.com", "site_name": "WABC HDTV"},
            {"channel": "WABCTV71.us", "site": "tvguide.com", "site_name": "WABC"},
        ]
    )
    match = match_channel(
        channel_id="WABCTV71.us",
        call_sign="WABC-TV",
        display_name="WABC-TV — New York, NY",
        station=None,
        guide_index=guide_index,
        overrides={},
    )
    assert match.source_name == "tvguide.com"


def test_conflict_detection_flags_city_mismatch():
    rows = [{"channel": "KQED92.us", "site": "tvtv.us", "site_name": "PBS Plus (KQED2) San Jose, CA"}]
    station = {"city": "San Francisco", "state": "CA"}
    conflicts = find_conflicts("KQED92.us", rows, station)
    assert len(conflicts) == 1
    assert conflicts[0]["known_city"] == "San Francisco"


def test_no_conflict_when_cities_agree():
    rows = [{"channel": "WABCTV71.us", "site": "tvpassport.com", "site_name": "ABC (WABC) New York, NY"}]
    station = {"city": "New York", "state": "NY"}
    conflicts = find_conflicts("WABCTV71.us", rows, station)
    assert conflicts == []


def test_no_conflict_check_without_station_data():
    # We never guess a conflict we can't verify against known station data.
    rows = [{"channel": "X.us", "site": "tvtv.us", "site_name": "Somewhere, ZZ"}]
    assert find_conflicts("X.us", rows, None) == []
