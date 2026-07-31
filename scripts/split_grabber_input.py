#!/usr/bin/env python3
"""Workflow glue: split epg/grabber-input.channels.xml (produced by
android_tv_guru.epg.build_and_write, one combined file for all sources) into
one file per provider, so .github/workflows/update-epg.yml can grab each
provider in its own matrix job — isolating one provider's failure/slowness
from the others, and keeping any single grab well within a runner's memory
budget (see docs/DATA_SOURCES.md for why i.mjh.nz/Roku's source file alone is
~36MB).

This is pure workflow plumbing (an XML filter), not classification/matching
logic, so it stays a script rather than moving into android_tv_guru — the
canonical matching logic that produced the input file already lives in
android_tv_guru.epg.

Usage: split_grabber_input.py <provider> <input.xml> <output.xml>
  provider: tvguide | roku | pluto | pbs | plex | samsung | metv
"""

import sys
import xml.etree.ElementTree as ET

PROVIDER_RULES = {
    "tvguide": lambda site, site_id: site == "tvguide.com",
    "roku": lambda site, site_id: site == "i.mjh.nz" and site_id.startswith("Roku/"),
    "pluto": lambda site, site_id: site == "i.mjh.nz" and site_id.startswith("PlutoTV/"),
    "pbs": lambda site, site_id: site == "i.mjh.nz" and site_id.startswith("PBS/"),
    "plex": lambda site, site_id: site == "i.mjh.nz" and site_id.startswith("Plex/"),
    "samsung": lambda site, site_id: site == "i.mjh.nz" and site_id.startswith("SamsungTVPlus/"),
    "metv": lambda site, site_id: site == "i.mjh.nz" and site_id.startswith("MeTV/"),
}


def main():
    if len(sys.argv) != 4:
        print("Usage: split_grabber_input.py <provider> <input.xml> <output.xml>", file=sys.stderr)
        sys.exit(1)

    provider, input_path, output_path = sys.argv[1:4]
    rule = PROVIDER_RULES.get(provider)
    if rule is None:
        print(f"Unknown provider {provider!r}. Known: {sorted(PROVIDER_RULES)}", file=sys.stderr)
        sys.exit(1)

    root = ET.parse(input_path).getroot()
    kept = 0
    out_root = ET.Element("channels")
    for el in root.findall("channel"):
        if rule(el.get("site", ""), el.get("site_id", "")):
            out_root.append(el)
            kept += 1

    ET.ElementTree(out_root).write(output_path, encoding="unicode", xml_declaration=True)
    print(f"{provider}: {kept} channel(s) written to {output_path}")


if __name__ == "__main__":
    main()
