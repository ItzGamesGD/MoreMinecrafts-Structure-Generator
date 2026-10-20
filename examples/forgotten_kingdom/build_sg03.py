#!/usr/bin/env python3
"""Build the SG-03 pack: the SG-02 cavern with six modular rooms in the lower and upper pools."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kingdom_common import BASE, REPO_ROOT
import build_sg02 as sg02
from sg03_lower_rooms import LOWER_ROOMS
from sg03_upper_rooms import UPPER_ROOMS

DEFAULT_OUTPUT = REPO_ROOT / "exports/sg-03/forgotten-underground-kingdom/datapack"
LOWER_IDS = {name: f"{BASE}/rooms/lower/{name}" for name in LOWER_ROOMS}
UPPER_IDS = {name: f"{BASE}/rooms/upper/{name}" for name in UPPER_ROOMS}


def room_modules() -> dict:
    rooms = {LOWER_IDS[name]: builder() for name, builder in LOWER_ROOMS.items()}
    rooms.update({UPPER_IDS[name]: builder() for name, builder in UPPER_ROOMS.items()})
    return rooms


def build_templates():
    return sg02.build_templates(room_modules())


def validate_all(templates) -> dict:
    """Seam-validate every room against every connector of its kind (all four sides, both slots)."""
    results = {}
    for lower in LOWER_IDS.values():
        for key, value in sg02.validate_connections(templates, lower, next(iter(UPPER_IDS.values()))).items():
            if key.startswith("lower_"):
                results[(lower, key)] = value
    for upper in UPPER_IDS.values():
        for key, value in sg02.validate_connections(templates, next(iter(LOWER_IDS.values())), upper).items():
            if key.startswith("upper_"):
                results[(upper, key)] = value
    return results


def build_pack(output: Path | str) -> Path:
    templates = build_templates()
    validate_all(templates)
    return sg02.write_pack(
        output, templates, list(LOWER_IDS.values()), list(UPPER_IDS.values()),
        description="MoreMinecrafts Forgotten Underground Kingdom — SG-03 modular rooms",
        protection_manifest=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    print(build_pack(args.output))


if __name__ == "__main__":
    main()
