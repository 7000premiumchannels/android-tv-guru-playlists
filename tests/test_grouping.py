from android_tv_guru.grouping import GROUP_ORDER, determine_group, sort_key


def us_channel(**overrides):
    base = {
        "id": "TEST.us",
        "name": "WTST-TV",
        "network": "ABC",
        "owners": [],
        "country": "US",
        "categories": [],
        "is_nsfw": False,
    }
    base.update(overrides)
    return base


def test_local_network_requires_call_sign():
    # "ABC" alone is not a call sign, so this must NOT be classified local
    # even though the network field says ABC.
    channel = us_channel(id="ABC.us", name="ABC", network="ABC")
    assert determine_group(channel) != "US Local - ABC"


def test_local_network_with_call_sign_is_classified():
    channel = us_channel(id="WTSTTV71.us", name="WTST-TV 7.1", network="ABC")
    assert determine_group(channel) == "US Local - ABC"


def test_national_feed_denylist_forces_news_group():
    channel = us_channel(
        id="ABCNewsLive.us",
        name="ABC News Live",
        network="ABC",
        categories=["news"],
    )
    assert determine_group(channel) == "US News & Weather"


def test_national_feeds_without_callsign_names_never_classified_local():
    for name, categories in [
        ("CBS News 24/7", ["news"]),
        ("NBC News NOW", ["news"]),
        ("Fox Weather", ["weather"]),
        ("LiveNOW from FOX", ["news"]),
        ("Scripps News", ["news"]),
        ("NewsNation", ["news"]),
    ]:
        channel = us_channel(id=name.replace(" ", ""), name=name, categories=categories)
        group = determine_group(channel)
        assert not group.startswith("US Local -"), (name, group)


def test_category_group_takes_priority_over_spanish_keyword_for_us():
    channel = us_channel(id="Sp.us", name="Spanish Kids Network", network=None, categories=["kids"])
    assert determine_group(channel) == "Kids & Family"


def test_us_spanish_keyword_fallback():
    channel = us_channel(id="Sp2.us", name="Latino Variety Channel", network=None, categories=[])
    assert determine_group(channel) == "Spanish"


def test_non_us_spanish_country():
    channel = us_channel(id="X.mx", name="Some Channel", country="MX", network=None, categories=[])
    assert determine_group(channel) == "Spanish"


def test_non_us_african_country():
    channel = us_channel(id="X.ke", name="Some Channel", country="KE", network=None, categories=[])
    assert determine_group(channel) == "African & Caribbean"


def test_other_international_fallback():
    channel = us_channel(id="X.jp", name="Some Channel", country="JP", network=None, categories=[])
    assert determine_group(channel) == "Other International - JP"


def test_sort_key_orders_local_groups_before_other_international():
    key_abc = sort_key("US Local - ABC")
    key_intl = sort_key("Other International - FR")
    key_other_us = sort_key("Other US Public Channels")
    assert key_abc < key_other_us < key_intl


def test_sort_key_matches_declared_group_order():
    keys = [sort_key(g) for g in GROUP_ORDER]
    assert keys == sorted(keys)
