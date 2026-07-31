#!/usr/bin/env python3
"""Merge per-source XMLTV guide fragments (produced by the iptv-org/epg
grabber, one file per source/provider) into a single AndroidTVGuru.xml, plus
a gzip-compressed AndroidTVGuru.xml.gz for hosting.

Usage:
    python3 scripts/merge_epg.py /tmp/guides/*.xml --output epg

Guards against exactly the failure modes Phase 1.5 tests must cover:
  - duplicate <channel id="..."> across input files (first file wins, in the
    order given on the command line; later duplicates are dropped and
    counted, never silently overwritten in a way that could pick a worse
    source)
  - <programme channel="..."> referencing a channel id that didn't make it
    into the merged channel set (dropped, counted — a "broken guide" would
    reference channels that don't exist)
"""

import gzip
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def merge(paths):
    channels = {}  # id -> Element
    programmes = []
    duplicate_channels = 0
    orphan_programmes = 0

    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            print(f"  WARNING: skipping unparseable file {path}: {exc}", file=sys.stderr)
            continue

        for channel_el in root.findall("channel"):
            cid = channel_el.get("id")
            if not cid:
                continue
            if cid in channels:
                duplicate_channels += 1
                continue
            channels[cid] = channel_el

        for programme_el in root.findall("programme"):
            programmes.append(programme_el)

    kept_programmes = []
    for p in programmes:
        if p.get("channel") in channels:
            kept_programmes.append(p)
        else:
            orphan_programmes += 1

    tv = ET.Element("tv")
    for cid in sorted(channels):
        tv.append(channels[cid])
    for p in kept_programmes:
        tv.append(p)

    return tv, {
        "input_files": len(paths),
        "channel_count": len(channels),
        "programme_count": len(kept_programmes),
        "duplicate_channels_dropped": duplicate_channels,
        "orphan_programmes_dropped": orphan_programmes,
    }


def write_outputs(tv_element, out_dir: Path, basename: str = "AndroidTVGuru"):
    out_dir.mkdir(parents=True, exist_ok=True)
    xml_path = out_dir / f"{basename}.xml"
    gz_path = out_dir / f"{basename}.xml.gz"

    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tv_element, encoding="utf-8")
    xml_path.write_bytes(xml_bytes)
    with gzip.open(gz_path, "wb") as fh:
        fh.write(xml_bytes)

    return xml_path, gz_path


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: merge_epg.py <input.xml> [<input.xml> ...] [--output DIR]", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(".")
    if "--output" in args:
        idx = args.index("--output")
        output_dir = Path(args[idx + 1])
        del args[idx : idx + 2]

    paths = [Path(a) for a in args]
    missing = [p for p in paths if not p.exists()]
    if missing:
        print(f"Input file(s) not found: {missing}", file=sys.stderr)
        sys.exit(1)

    tv, stats = merge(paths)
    xml_path, gz_path = write_outputs(tv, output_dir)

    print(f"Merged {stats['input_files']} source file(s):")
    print(f"  channels: {stats['channel_count']}")
    print(f"  programmes: {stats['programme_count']}")
    print(f"  duplicate channel ids dropped: {stats['duplicate_channels_dropped']}")
    print(f"  orphan programmes dropped: {stats['orphan_programmes_dropped']}")
    print(f"Wrote {xml_path} and {gz_path}")


if __name__ == "__main__":
    main()
