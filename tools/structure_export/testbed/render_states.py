"""Offline isometric render of block states with mcbuild's renderer (vanilla blockstate models).

NOT a Minecraft client screenshot: it draws the states it is given with mcbuild's own model code,
so it only illustrates which connection states a placement holds. States come either from a
template .nbt or from a plot of a saved server world (as left by `live --work <dir>`):

    uv run --project vendor/mcbuild python tools/structure_export/testbed/render_states.py \
        --nbt <template.nbt> --out before.png
    uv run --project vendor/mcbuild python tools/structure_export/testbed/render_states.py \
        --world <work>/server/world --origin X Y Z --size W H L --out after.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor/mcbuild/src"))

from mcbuild.palette import get_block  # noqa: E402
from mcbuild.render.camera import render_isometric  # noqa: E402
from mcbuild.voxel import VoxelGrid  # noqa: E402

from tools.stage24c.mcserver import World  # noqa: E402
from tools.structure_export.convert import load_reference  # noqa: E402
from tools.structure_export.verify import plain, read_nbt  # noqa: E402


def from_nbt(path: Path) -> dict:
    data = plain(read_nbt(path)[1])
    palette = [_text(e["id"], e.get("properties", {})) for e in data["palette"]]
    return {tuple(b["pos"]): palette[b["state"]] for b in data["blocks"]}


def _text(block_id: str, props: dict) -> str:
    return block_id + ("[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]" if props else "")


def _entry(entry) -> str:
    # 26.3 chunk palettes: a bare id string for a block in its default state, else {id, properties};
    # nbtlib reads the strings of such a mixed list as compounds under an empty key.
    if not isinstance(entry, str) and "" in entry:
        entry = entry[""]
    if isinstance(entry, str):
        return _text(str(entry), load_reference("26.3")["blocks"][str(entry)]["default"])
    return _text(str(entry["id"]), {str(k): str(v) for k, v in entry.get("properties", {}).items()})


def _block(reader: World, x: int, y: int, z: int) -> str | None:
    chunk = reader.chunk(x >> 4, z >> 4)
    for section in chunk["sections"] if chunk else ():
        if int(section["Y"]) != y >> 4:
            continue
        states = section["block_states"]
        palette = states["palette"]
        if len(palette) == 1:
            return _entry(palette[0])
        bits = max(4, (len(palette) - 1).bit_length())
        per = 64 // bits
        i = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
        word = int(states["data"][i // per]) & 0xFFFFFFFFFFFFFFFF
        return _entry(palette[(word >> ((i % per) * bits)) & ((1 << bits) - 1)])
    return None


def from_world(world: Path, origin, size) -> dict:
    reader = World(world / "dimensions/minecraft/overworld")
    return {
        (x, y, z): _block(reader, origin[0] + x, origin[1] + y, origin[2] + z)
        for x in range(size[0])
        for y in range(size[1])
        for z in range(size[2])
    }


def render(states: dict, out: Path, yaw: int) -> None:
    grid = VoxelGrid()
    for (x, y, z), state in states.items():
        if state and not state.startswith("minecraft:air"):
            grid.set(x, y, z, get_block(state).index)
    render_isometric(grid, yaw=yaw, width=1000, height=1000).save(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--nbt", type=Path)
    parser.add_argument("--world", type=Path)
    parser.add_argument("--origin", type=int, nargs=3)
    parser.add_argument("--size", type=int, nargs=3)
    parser.add_argument("--yaw", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    states = from_nbt(args.nbt) if args.nbt else from_world(args.world, args.origin, args.size)
    render(states, args.out, args.yaw)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
