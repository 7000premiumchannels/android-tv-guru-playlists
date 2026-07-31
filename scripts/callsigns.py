"""Extraction of U.S. broadcast television call signs from channel names.

Standalone module for the Phase 1.5 EPG pipeline (kept separate from
build_android_tv_guru_m3u-1.py so nothing about playlist generation changes).

IPTV-org's channels.json does not carry a dedicated call-sign field, but for
the large majority of U.S. terrestrial stations and their digital
sub-channels, the channel "name" is (or begins with) the FCC call sign
itself, e.g.:

    "KABC-TV 7.1"   -> call sign KABC-TV, sub-channel 7.1
    "WABC-TV"       -> call sign WABC-TV
    "K30FZ-D 4.1"   -> low-power/translator call sign K30FZ-D, sub-channel 4.1
    "ABC News Live" -> not a call sign (national streaming feed)

This module only performs syntactic recognition of that convention — no
external data is consulted, so it is safe to use standalone.
"""

import re
from dataclasses import dataclass
from typing import Optional

_STANDARD_CALL = r"[KW][A-Z]{2,3}"
_STANDARD_SUFFIX = r"(?:-TV|-DT|-CD|-LD|-LP)"
_TRANSLATOR_CALL = r"[KW]\d{2}[A-Z]{2}"
_TRANSLATOR_SUFFIX = r"(?:-D)"
_SUBCHANNEL = r"(?:[\s-]?\d{1,2}(?:\.\d{1,2})?)?"

CALLSIGN_RE = re.compile(
    rf"^(?P<call>{_STANDARD_CALL}|{_TRANSLATOR_CALL})"
    rf"(?P<suffix>{_STANDARD_SUFFIX}|{_TRANSLATOR_SUFFIX})?"
    rf"{_SUBCHANNEL}$"
)

_LOW_POWER_SUFFIXES = {"-LD", "-LP", "-CD", "-D"}


@dataclass(frozen=True)
class CallSign:
    raw: str
    call_sign: str
    normalized_call_sign: str
    suffix: Optional[str]
    is_low_power: bool


def extract_callsign(name: Optional[str]) -> Optional[CallSign]:
    if not name:
        return None

    candidate = name.strip()
    match = CALLSIGN_RE.match(candidate)
    if not match:
        return None

    call = match.group("call").upper()
    suffix = match.group("suffix")
    suffix = suffix.upper() if suffix else None

    normalized = call + suffix if suffix else call
    is_low_power = bool(re.match(_TRANSLATOR_CALL + "$", call)) or suffix in _LOW_POWER_SUFFIXES

    return CallSign(
        raw=candidate,
        call_sign=call,
        normalized_call_sign=normalized,
        suffix=suffix,
        is_low_power=is_low_power,
    )
