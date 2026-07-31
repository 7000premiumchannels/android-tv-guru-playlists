from callsigns import extract_callsign


def test_bare_call_sign():
    result = extract_callsign("WABC")
    assert result.normalized_call_sign == "WABC"


def test_hyphenated_tv_suffix():
    result = extract_callsign("WABC-TV")
    assert result.normalized_call_sign == "WABC-TV"


def test_k_call_sign_with_subchannel():
    result = extract_callsign("KABC-TV 7.1")
    assert result.call_sign == "KABC"
    assert result.normalized_call_sign == "KABC-TV"


def test_digital_suffix():
    assert extract_callsign("KABC-DT").normalized_call_sign == "KABC-DT"


def test_low_power_translator():
    result = extract_callsign("K30FZ-D 4.1")
    assert result.normalized_call_sign == "K30FZ-D"
    assert result.is_low_power is True


def test_invalid_names_return_none():
    for name in ["", None, "Local News Channel", "West", "Discovery Channel"]:
        assert extract_callsign(name) is None


def test_national_channel_names_are_not_call_signs():
    for name in ["ABC News Live", "CBS News 24/7", "NBC News NOW", "Fox Weather", "NewsNation"]:
        assert extract_callsign(name) is None, name
