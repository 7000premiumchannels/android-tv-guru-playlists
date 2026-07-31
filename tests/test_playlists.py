import json
from pathlib import Path

from android_tv_guru.playlists import (
    LOCAL_GROUPS,
    build_entries,
    is_valid_stream_url,
    write_master_and_categories,
    write_state_playlists,
)
from android_tv_guru.stations import StationDirectory

FIXTURES = Path(__file__).parent / "fixtures" / "data"


def load_fixture_entries():
    channels = json.loads((FIXTURES / "channels.json").read_text())
    streams = json.loads((FIXTURES / "streams.json").read_text())
    stations = StationDirectory.load(FIXTURES / "us_tv_stations.json")
    return build_entries(channels, streams, stations)


def test_nsfw_channel_excluded():
    entries = load_fixture_entries()
    assert all(e.channel_id != "NSFWChannel.us" for e in entries)


def test_invalid_scheme_excluded():
    entries = load_fixture_entries()
    assert all(e.channel_id != "SomeCA.ca" for e in entries)


def test_orphan_stream_without_channel_id_excluded():
    entries = load_fixture_entries()
    urls = [e.url for e in entries]
    assert "https://example.com/orphan.m3u8" not in urls


def test_exact_url_deduplication():
    entries = load_fixture_entries()
    wcbs_entries = [e for e in entries if e.channel_id == "WCBSTV21.us"]
    # streams.json fixture lists the same WCBS URL twice; only one entry should remain.
    assert len(wcbs_entries) == 1


def test_national_feed_not_classified_local():
    entries = load_fixture_entries()
    abc_news = next(e for e in entries if e.channel_id == "ABCNewsLive.us")
    assert abc_news.group == "US News & Weather"


def test_confident_match_gets_callsign_city_state_name():
    entries = load_fixture_entries()
    wabc = next(e for e in entries if e.channel_id == "WABCTV71.us")
    assert wabc.station_confident is True
    assert wabc.display_name == "WABC-TV — New York, NY"
    assert wabc.group == "US Local - ABC"


def test_unmatched_station_falls_back_to_original_name():
    entries = load_fixture_entries()
    kabc = next(e for e in entries if e.channel_id == "KABCTV71.us")
    assert kabc.station_confident is False
    # Never guess a city/state -> original channel name is retained verbatim.
    assert kabc.display_name == "KABC-TV 7.1"


def test_no_wabc_kabc_cross_market_bleed():
    entries = load_fixture_entries()
    wabc = next(e for e in entries if e.channel_id == "WABCTV71.us")
    kabc = next(e for e in entries if e.channel_id == "KABCTV71.us")
    assert wabc.state_code == "NY"
    assert kabc.state_code is None
    assert "New York" not in kabc.display_name
    assert "NY" not in kabc.display_name


def test_is_valid_stream_url():
    assert is_valid_stream_url("https://example.com/a.m3u8") is True
    assert is_valid_stream_url("http://example.com/a.m3u8") is True
    assert is_valid_stream_url("ftp://example.com/a.m3u8") is False
    assert is_valid_stream_url("not a url") is False
    assert is_valid_stream_url("") is False
    assert is_valid_stream_url(None) is False


def test_m3u_block_formatting():
    entries = load_fixture_entries()
    wabc = next(e for e in entries if e.channel_id == "WABCTV71.us")
    block = wabc.m3u_block()
    lines = block.splitlines()
    assert lines[0].startswith("#EXTINF:-1 ")
    assert 'tvg-id="WABCTV71.us"' in lines[0]
    assert 'group-title="US Local - ABC"' in lines[0]
    assert lines[0].endswith(",WABC-TV — New York, NY")
    assert lines[1] == "https://example.com/wabc.m3u8"


def test_master_and_category_outputs(tmp_path, monkeypatch):
    import android_tv_guru.playlists as playlists_module

    monkeypatch.setattr(playlists_module, "OUT", tmp_path / "AndroidTVGuru.m3u")
    monkeypatch.setattr(playlists_module, "PLAYLISTS_DIR", tmp_path / "playlists")

    entries = load_fixture_entries()
    ordered = write_master_and_categories(entries)

    master_text = (tmp_path / "AndroidTVGuru.m3u").read_text()
    assert master_text.startswith(
        '#EXTM3U x-tvg-url="https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml"\n'
    )
    # group ordering: ABC locals must appear before CBS locals, which must
    # appear before Spanish/African & Caribbean entries in the file.
    abc_pos = master_text.index("US Local - ABC")
    cbs_pos = master_text.index("US Local - CBS")
    spanish_pos = master_text.index('group-title="Spanish"')
    african_pos = master_text.index("African & Caribbean")
    assert abc_pos < cbs_pos < spanish_pos < african_pos

    us_abc_file = tmp_path / "playlists" / "US_ABC.m3u"
    assert us_abc_file.exists()
    us_abc_text = us_abc_file.read_text()
    assert "WABC-TV" in us_abc_text
    assert "WCBS-TV" not in us_abc_text

    assert len(ordered) == len(entries)


def test_state_playlist_filtering(tmp_path, monkeypatch):
    import android_tv_guru.playlists as playlists_module

    states_dir = tmp_path / "playlists" / "states"
    monkeypatch.setattr(playlists_module, "STATES_DIR", states_dir)

    entries = load_fixture_entries()
    confident_locals, by_state = write_state_playlists(entries)

    # Only confidently matched local stations (WABC-TV, WDIV-TV) qualify.
    confident_ids = {e.channel_id for e in confident_locals}
    assert confident_ids == {"WABCTV71.us", "WDIVTV41.us"}

    ny_text = (states_dir / "New York.m3u").read_text()
    assert "WABC-TV" in ny_text
    assert "WDIV-TV" not in ny_text
    assert 'group-title="US Local - ABC - New York"' in ny_text

    mi_text = (states_dir / "Michigan.m3u").read_text()
    assert "WDIV-TV" in mi_text
    assert "WABC-TV" not in mi_text

    # A state with no confidently matched stations still gets a (empty) file.
    ca_text = (states_dir / "California.m3u").read_text()
    assert ca_text == (
        '#EXTM3U x-tvg-url="https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml"\n'
    )

    all_locals_text = (states_dir.parent / "US_Locals_All.m3u").read_text()
    assert "WABC-TV" in all_locals_text
    assert "WDIV-TV" in all_locals_text
    assert "KABC-TV" not in all_locals_text
