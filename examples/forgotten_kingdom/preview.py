#!/usr/bin/env python3
"""Create layer and section ASCII evidence from the exported vanilla templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from structure_export.nbt import read_nbt

PACK = REPO_ROOT / "exports/sg-01/forgotten-underground-kingdom/datapack"
TEMPLATE_PATH = "data/moreminecrafts/structure/forgotten_kingdom/central_cavern/main_chamber.nbt"
GLYPHS = {
    "minecraft:air": ".",
    "minecraft:deepslate_tiles": "#",
    "minecraft:deepslate_bricks": "D",
    "minecraft:polished_deepslate": "P",
    "minecraft:tuff_bricks": "T",
    "minecraft:chiseled_tuff_bricks": "C",
    "minecraft:deepslate_brick_wall": "r",
    "minecraft:stone_brick_stairs": "S",
    "minecraft:sea_lantern": "L",
    "minecraft:jigsaw": "J",
}


def _read_template(path: Path) -> tuple[tuple[int, int, int], dict[tuple[int, int, int], str]]:
    template = read_nbt(path.read_bytes())["value"]
    size = tuple(template["size"])
    palette = template["palette"]
    blocks = {tuple(block["pos"]): palette[block["state"]]["Name"] for block in template["blocks"]}
    return size, blocks


def _glyph(block: str) -> str:
    if block.startswith("minecraft:stone_brick_stairs["):
        return "S"
    return GLYPHS.get(block, "?")


def top_layer(size: tuple[int, int, int], blocks: dict[tuple[int, int, int], str], y: int) -> str:
    sx, _, sz = size
    return "\n".join("".join(_glyph(blocks[(x, y, z)]) for x in range(sx)) for z in range(sz))


def x_section(size: tuple[int, int, int], blocks: dict[tuple[int, int, int], str], x: int) -> str:
    _, sy, sz = size
    return "\n".join("".join(_glyph(blocks[(x, y, z)]) for z in range(sz)) for y in reversed(range(sy)))


def z_section(size: tuple[int, int, int], blocks: dict[tuple[int, int, int], str], z: int) -> str:
    sx, sy, _ = size
    return "\n".join("".join(_glyph(blocks[(x, y, z)]) for x in range(sx)) for y in reversed(range(sy)))


def render(path: Path) -> str:
    size, blocks = _read_template(path)
    lines = [
        "# SG-01 central cavern — structural preview",
        "",
        "Generated from the exported NBT template. Minecraft client rendering is unavailable here.",
        "",
        "Glyphs: `.` air, `#` deepslate tile, `D` deepslate brick, `P` polished deepslate, `T` tuff brick,",
        "`C` chiseled tuff brick, `r` balcony rail, `S` stair, `L` sea lantern, `J` Jigsaw connector.",
        "Rows are north to south; columns are west to east. Four `J` connectors lead to the district tunnels.",
        "",
        f"Template dimensions: {size[0]} × {size[1]} × {size[2]} (X × Y × Z).",
    ]
    for y in (0, 1, 8, 15, 16):
        lines.extend(["", f"## Horizontal layer Y={y}", "", "```text", top_layer(size, blocks, y), "```"])
    lines.extend(["", "## North-to-south vertical section through X=20", "", "```text", x_section(size, blocks, 20), "```"])
    lines.extend(["", "## West-to-east vertical section through Z=20", "", "```text", z_section(size, blocks, 20), "```"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default=str(REPO_ROOT / "docs/sg-01/structural-evidence.md"))
    parser.add_argument("--pack", default=str(PACK))
    args = parser.parse_args()
    path = Path(args.pack) / TEMPLATE_PATH
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(path), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
