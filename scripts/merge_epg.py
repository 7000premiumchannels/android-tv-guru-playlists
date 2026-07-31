#!/usr/bin/env python3
"""Thin CLI wrapper: merge grabbed per-source XMLTV fragments into
AndroidTVGuru.xml / AndroidTVGuru.xml.gz.

Usage:
    python3 scripts/merge_epg.py <input.xml> [<input.xml> ...] [--output DIR]

The real implementation (android_tv_guru.epg.merge_guides /
write_guide_outputs) lives in the package — see docs/EPG_MATCHING.md.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from android_tv_guru.epg import merge_guides, write_guide_outputs  # noqa: E402

# A new guide with fewer than this fraction of the previous guide's channel
# count is treated as degraded (e.g. most grab jobs failed/timed out) and
# refused, same as an outright-empty guide — never silently publish a guide
# that regressed this badly over the last known-good one.
MIN_CHANNEL_RETENTION = 0.5


def _previous_channel_count(basename: str, output_dir: Path) -> int:
    xml_path = output_dir / f"{basename}.xml"
    if not xml_path.exists():
        return 0
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return 0
    return len(root.findall("channel"))


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

    requested = [Path(a) for a in args]
    paths = [p for p in requested if p.exists()]
    missing = [p for p in requested if p not in paths]
    if missing:
        # A missing input (e.g. one matrix grab job failed to produce its
        # fragment artifact) is not fatal here — we merge whatever did show
        # up. Include the previously-committed AndroidTVGuru.xml as one of
        # the inputs (lowest priority, last in the list) so a provider that
        # fails THIS run still falls back to its last-known-good data
        # instead of vanishing from the guide entirely.
        print(f"WARNING: input file(s) not found, skipping: {missing}", file=sys.stderr)

    if not paths:
        print("No input files available to merge; nothing to do.", file=sys.stderr)
        sys.exit(1)

    tv, stats = merge_guides(paths)

    if stats["channel_count"] == 0:
        # Refuse to write an empty guide over a previously-good one — this
        # is the "don't erase the last known good production guide" guard.
        print("ERROR: merge produced 0 channels; refusing to write output.", file=sys.stderr)
        sys.exit(1)

    previous_count = _previous_channel_count("AndroidTVGuru", output_dir)
    if previous_count > 0 and stats["channel_count"] < previous_count * MIN_CHANNEL_RETENTION:
        # Refuse a severely degraded guide too (e.g. most grab jobs failed) —
        # not empty, but bad enough that publishing it would be worse than
        # keeping the last known-good guide.
        print(
            f"ERROR: merge produced only {stats['channel_count']} channels, "
            f"down from {previous_count} previously (< {int(MIN_CHANNEL_RETENTION * 100)}% retained); "
            "refusing to write output.",
            file=sys.stderr,
        )
        sys.exit(1)

    xml_path, gz_path = write_guide_outputs(tv, output_dir)

    print(f"Merged {stats['input_files']} source file(s):")
    print(f"  channels: {stats['channel_count']}")
    print(f"  programmes: {stats['programme_count']}")
    print(f"  duplicate channel ids dropped: {stats['duplicate_channels_dropped']}")
    print(f"  orphan programmes dropped: {stats['orphan_programmes_dropped']}")
    print(f"Wrote {xml_path} and {gz_path}")


if __name__ == "__main__":
    main()
