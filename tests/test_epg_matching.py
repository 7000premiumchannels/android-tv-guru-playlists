from callsigns import extract_callsign

import build_epg_source as epg


def test_base_id_and_feed_strips_suffix():
    assert epg.base_id_and_feed("WABCTV71.us@HD") == ("WABCTV71.us", "HD")


def test_base_id_and_feed_no_suffix():
    assert epg.base_id_and_feed("CookingChannel.us") == ("CookingChannel.us", "")


def test_base_id_and_feed_empty():
    assert epg.base_id_and_feed("") == (None, None)
    assert epg.base_id_and_feed(None) == (None, None)


def test_pick_best_prefers_source_priority():
    rows = [
        {"source": "i.mjh.nz/pluto", "feed": "", "site": "i.mjh.nz", "site_id": "x"},
        {"source": "tvguide.com", "feed": "", "site": "tvguide.com", "site_id": "y"},
    ]
    best = epg.pick_best(rows)
    assert best["source"] == "tvguide.com"  # earlier in SOURCE_PRIORITY


def test_pick_best_prefers_feed_priority_within_same_source():
    rows = [
        {"source": "tvguide.com", "feed": "West", "site": "tvguide.com", "site_id": "a"},
        {"source": "tvguide.com", "feed": "East", "site": "tvguide.com", "site_id": "b"},
        {"source": "tvguide.com", "feed": "HD", "site": "tvguide.com", "site_id": "c"},
    ]
    best = epg.pick_best(rows)
    assert best["feed"] == "HD"  # HD ranks before East/West in FEED_PRIORITY


def test_build_exact_index_groups_by_base_id():
    rows = [
        {"source": "tvguide.com", "site": "tvguide.com", "site_id": "1", "xmltv_id": "ABC.us@East"},
        {"source": "tvguide.com", "site": "tvguide.com", "site_id": "2", "xmltv_id": "ABC.us@West"},
        {"source": "tvguide.com", "site": "tvguide.com", "site_id": "3", "xmltv_id": ""},
    ]
    index = epg.build_exact_index(rows)
    assert set(index.keys()) == {"ABC.us"}
    assert len(index["ABC.us"]) == 2


def test_build_name_index_only_keeps_empty_xmltv_id():
    rows = [
        {"xmltv_id": "ABC.us", "display_name": "ABC"},
        {"xmltv_id": "", "display_name": "Some Unmapped Channel"},
    ]
    index = epg.build_name_index(rows)
    assert len(index) == 1
    assert index[0]["display_name"] == "Some Unmapped Channel"


def test_name_contains_call_sign_matches_whole_word():
    call_sign = extract_callsign("WABC-TV")
    assert epg.name_contains_call_sign("WABC ABC7 New York", call_sign) is True


def test_name_contains_call_sign_rejects_substring_only():
    # "KABC" must not match inside an unrelated token like "WKABCD".
    call_sign = extract_callsign("KABC-TV")
    assert epg.name_contains_call_sign("WKABCD Radio Network", call_sign) is False


def test_name_contains_call_sign_no_shared_network_false_positive():
    # WABC and KABC share a network (ABC) but are different stations; a name
    # index lookup for one must never satisfy the other by accident.
    wabc = extract_callsign("WABC-TV")
    assert epg.name_contains_call_sign("KABC ABC7 Los Angeles", wabc) is False


def test_find_conflict_flags_city_mismatch():
    call_sign = extract_callsign("KQED-TV")
    stations = {"KQED-TV": {"city": "San Francisco", "state": "CA"}}
    conflict = epg.find_conflict("KQED92.us", call_sign, "PBS Plus (KQED2) San Jose, CA", stations)
    assert conflict is not None
    assert conflict["known_city"] == "San Francisco"


def test_find_conflict_no_conflict_when_city_matches():
    call_sign = extract_callsign("WABC-TV")
    stations = {"WABC-TV": {"city": "New York", "state": "NY"}}
    conflict = epg.find_conflict("WABCTV71.us", call_sign, "WABC ABC7 New York", stations)
    assert conflict is None


def test_find_conflict_none_without_station_data():
    call_sign = extract_callsign("WABC-TV")
    conflict = epg.find_conflict("WABCTV71.us", call_sign, "Some Name", {})
    assert conflict is None


def test_find_conflict_none_without_call_sign():
    assert epg.find_conflict("X.us", None, "Some Name", {"WABC-TV": {"city": "NY", "state": "NY"}}) is None
