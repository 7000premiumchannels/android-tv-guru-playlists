import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import android_tv_guru.epg as epg_module
import merge_epg


def write_guide(path, channels, programmes):
    lines = ["<tv>"]
    for cid, name in channels:
        lines.append(f'<channel id="{cid}"><display-name>{name}</display-name></channel>')
    for cid, start, stop, title in programmes:
        lines.append(f'<programme start="{start}" stop="{stop}" channel="{cid}"><title>{title}</title></programme>')
    lines.append("</tv>")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_merge_combines_channels_and_programmes(tmp_path):
    a = tmp_path / "a.xml"
    b = tmp_path / "b.xml"
    write_guide(a, [("ABC.us", "ABC")], [("ABC.us", "20260101000000 +0000", "20260101003000 +0000", "Show A")])
    write_guide(b, [("CBS.us", "CBS")], [("CBS.us", "20260101000000 +0000", "20260101003000 +0000", "Show B")])

    tv, stats = epg_module.merge_guides([a, b])

    assert stats["channel_count"] == 2
    assert stats["programme_count"] == 2
    assert stats["duplicate_channels_dropped"] == 0
    assert stats["orphan_programmes_dropped"] == 0


def test_merge_drops_duplicate_channel_ids_keeping_first_file():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        first = d / "first.xml"
        second = d / "second.xml"
        write_guide(first, [("ABC.us", "ABC (preferred source)")], [])
        write_guide(second, [("ABC.us", "ABC (lower priority source)")], [])

        tv, stats = epg_module.merge_guides([first, second])

        assert stats["channel_count"] == 1
        assert stats["duplicate_channels_dropped"] == 1
        display_name = tv.find("channel").find("display-name").text
        assert display_name == "ABC (preferred source)"


def test_merge_drops_orphan_programmes_referencing_missing_channel(tmp_path):
    path = tmp_path / "guide.xml"
    write_guide(
        path,
        [("ABC.us", "ABC")],
        [
            ("ABC.us", "20260101000000 +0000", "20260101003000 +0000", "Real show"),
            ("GHOST.us", "20260101000000 +0000", "20260101003000 +0000", "Orphan show"),
        ],
    )

    tv, stats = epg_module.merge_guides([path])

    assert stats["channel_count"] == 1
    assert stats["programme_count"] == 1
    assert stats["orphan_programmes_dropped"] == 1


def test_merge_skips_unparseable_file_without_crashing(tmp_path):
    good = tmp_path / "good.xml"
    broken = tmp_path / "broken.xml"
    write_guide(good, [("ABC.us", "ABC")], [])
    broken.write_text("<tv><channel id='unterminated>", encoding="utf-8")

    tv, stats = epg_module.merge_guides([broken, good])

    assert stats["channel_count"] == 1


def test_write_outputs_produces_valid_xml_and_gzip(tmp_path):
    a = tmp_path / "a.xml"
    write_guide(a, [("ABC.us", "ABC")], [("ABC.us", "20260101000000 +0000", "20260101003000 +0000", "Show A")])

    tv, _stats = epg_module.merge_guides([a])
    out_dir = tmp_path / "out"
    xml_path, gz_path = epg_module.write_guide_outputs(tv, out_dir)

    assert xml_path.exists()
    assert gz_path.exists()

    # The XML file must parse cleanly (this is the "broken guide generation" check).
    parsed = ET.parse(xml_path).getroot()
    assert parsed.tag == "tv"
    assert len(parsed.findall("channel")) == 1

    import gzip

    with gzip.open(gz_path, "rt", encoding="utf-8") as fh:
        gz_content = fh.read()
    assert gz_content == xml_path.read_text(encoding="utf-8")


def test_no_duplicate_channel_ids_in_merged_output(tmp_path):
    a = tmp_path / "a.xml"
    b = tmp_path / "b.xml"
    write_guide(a, [("ABC.us", "ABC one")], [])
    write_guide(b, [("ABC.us", "ABC two"), ("CBS.us", "CBS")], [])

    tv, _stats = epg_module.merge_guides([a, b])
    ids = [c.get("id") for c in tv.findall("channel")]
    assert len(ids) == len(set(ids))


def test_cli_refuses_empty_merge(tmp_path, monkeypatch, capsys):
    broken = tmp_path / "broken.xml"
    broken.write_text("<tv><channel id='unterminated>", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["merge_epg.py", str(broken), "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        merge_epg.main()
    assert exc.value.code == 1
    assert "0 channels" in capsys.readouterr().err
    assert not (tmp_path / "AndroidTVGuru.xml").exists()


def test_cli_refuses_guide_with_channels_but_no_programmes(tmp_path, monkeypatch, capsys):
    # Simulate a previously-published guide with real programme data...
    previous = [("ABC.us", "ABC"), ("CBS.us", "CBS")]
    prev_tv = _build_tv(previous)
    prev_channel = prev_tv.find("channel")
    import xml.etree.ElementTree as ET_

    programme = ET_.SubElement(
        prev_tv, "programme",
        {"start": "20260101000000 +0000", "stop": "20260101003000 +0000", "channel": prev_channel.get("id")},
    )
    ET_.SubElement(programme, "title").text = "Show A"
    epg_module.write_guide_outputs(prev_tv, tmp_path)

    # ...then a new grab that got the channel list but zero programme data
    # for any of them (e.g. every programme fetch failed/timed out).
    channels_only_input = tmp_path / "channels_only.xml"
    write_guide(channels_only_input, previous, [])

    monkeypatch.setattr("sys.argv", ["merge_epg.py", str(channels_only_input), "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        merge_epg.main()
    assert exc.value.code == 1
    assert "0 programmes" in capsys.readouterr().err

    # The previously-good file (with real programme data) must survive untouched.
    assert len(ET.parse(tmp_path / "AndroidTVGuru.xml").getroot().findall("programme")) == 1


def test_cli_refuses_degraded_guide_against_previous(tmp_path, monkeypatch, capsys):
    # Simulate a previously-published guide with 10 channels...
    previous = [(f"CH{i}.us", f"Channel {i}") for i in range(10)]
    prev_tv = _build_tv(previous)
    epg_module.write_guide_outputs(prev_tv, tmp_path)

    # ...then a new grab that only found 2 of them (severely degraded, but not
    # empty, and with real programme data so this test isolates the
    # degraded-channel-count check from the separate zero-programme check).
    degraded_input = tmp_path / "degraded.xml"
    write_guide(
        degraded_input, previous[:2],
        [("CH0.us", "20260101000000 +0000", "20260101003000 +0000", "Show A")],
    )

    monkeypatch.setattr("sys.argv", ["merge_epg.py", str(degraded_input), "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        merge_epg.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "down from 10 previously" in err

    # The previously-good file must not have been overwritten.
    assert len(ET.parse(tmp_path / "AndroidTVGuru.xml").getroot().findall("channel")) == 10


def _build_tv(channels):
    import xml.etree.ElementTree as ET

    tv = ET.Element("tv")
    for cid, name in channels:
        channel_el = ET.SubElement(tv, "channel", {"id": cid})
        ET.SubElement(channel_el, "display-name").text = name
    return tv
