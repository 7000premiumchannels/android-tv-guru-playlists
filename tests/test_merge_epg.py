import xml.etree.ElementTree as ET
from pathlib import Path

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

    tv, stats = merge_epg.merge([a, b])

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

        tv, stats = merge_epg.merge([first, second])

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

    tv, stats = merge_epg.merge([path])

    assert stats["channel_count"] == 1
    assert stats["programme_count"] == 1
    assert stats["orphan_programmes_dropped"] == 1


def test_merge_skips_unparseable_file_without_crashing(tmp_path):
    good = tmp_path / "good.xml"
    broken = tmp_path / "broken.xml"
    write_guide(good, [("ABC.us", "ABC")], [])
    broken.write_text("<tv><channel id='unterminated>", encoding="utf-8")

    tv, stats = merge_epg.merge([broken, good])

    assert stats["channel_count"] == 1


def test_write_outputs_produces_valid_xml_and_gzip(tmp_path):
    a = tmp_path / "a.xml"
    write_guide(a, [("ABC.us", "ABC")], [("ABC.us", "20260101000000 +0000", "20260101003000 +0000", "Show A")])

    tv, _stats = merge_epg.merge([a])
    out_dir = tmp_path / "out"
    xml_path, gz_path = merge_epg.write_outputs(tv, out_dir)

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

    tv, _stats = merge_epg.merge([a, b])
    ids = [c.get("id") for c in tv.findall("channel")]
    assert len(ids) == len(set(ids))
