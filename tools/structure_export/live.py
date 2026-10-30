"""Live load check on a real vanilla Minecraft server (the reference's version).

Everything below is decided by the game, not by converter code:

1. Load. The exported template, placed with `/place template ... strict` (knownShape and update
   flag 16, as jigsaw world generation places pool elements), must hold exactly the states written
   in the .nbt, tested cell by cell with `execute if block`.
2. Version handling. A "DataFixer probe" (the same source states in the legacy Name/Properties layout,
   stamped with the *source* DataVersion, so the game's own DataFixer upgrades them) placed strict must
   hold the source states completed with the 26.3 defaults. This probe is also the "before" picture:
   it is what the source generates with defaulted connections (the PR #46 output).
3. Connections, the oracle. On a strict copy of the export, every connecting block (wall, fence,
   pane/bars, fence gate) is re-set with a non-strict `/setblock <pos> <source state>`: the game runs
   Block.updateFromNeighbourShapes on it and then re-applies the properties the source states
   (BlockInput.place), which is exactly what the converter claims to have precomputed. The copy must
   still equal an untouched strict copy (`execute if blocks ... all`); a block the game would connect
   differently changes. Done for all four rotations, so rotation and coordinates are covered too.
4. Normal placement. The export placed without `strict` (the game updates every placed block's shape)
   must equal the strict placement except where the source states a connection property that vanilla
   would compute differently (the converter keeps stated properties; the report lists them). The
   uncorrected probe placed without `strict` is compared too, for the before/after picture.

This is vanilla server evidence. It does not start MoreMinecrafts-Beta (Fabric + mod), so it does
not replace a load test inside the MMB runtime.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import shutil
import socket
import tempfile
import zipfile
from pathlib import Path

import nbtlib
from nbtlib.tag import Compound, Int, List, String

from tools.stage24c.mcserver import Server

from .connectivity import Rules, load_connectivity
from .convert import Config, convert, load_reference, resolve_state
from .schem import parse_state, read_schematic
from .verify import plain, read_nbt

LOG_PROBLEMS = re.compile(
    r"(/WARN\]|/ERROR\]|Failed to load|Couldn't load|Error loading|Exception|Unknown block)", re.I
)
# The offline-mode banner that every server with online-mode=false prints (four WARN lines), and the
# tick-lag notice that force-loading the test plots can cause (performance only, not content).
LOG_EXPECTED = re.compile(
    r"OFFLINE/INSECURE MODE|make no attempt to authenticate|ability for hackers to connect"
    r"|set \"online-mode\" to \"true\"|Can't keep up! Is the server overloaded\?"
)
# Superflat with an explicit layer list; an empty generator-settings logs "No key layers" at ERROR.
FLAT = {
    "layers": [
        {"block": "minecraft:bedrock", "height": 1},
        {"block": "minecraft:dirt", "height": 2},
        {"block": "minecraft:grass_block", "height": 1},
    ],
    "biome": "minecraft:plains",
}
ROTATIONS = ("none", "clockwise_90", "180", "counterclockwise_90")
# Rotation.rotate(Direction) for the horizontal directions
TURN = {
    "none": {d: d for d in ("north", "east", "south", "west")},
    "clockwise_90": {"north": "east", "east": "south", "south": "west", "west": "north"},
    "180": {"north": "south", "east": "west", "south": "north", "west": "east"},
    "counterclockwise_90": {"north": "west", "west": "south", "south": "east", "east": "north"},
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def transform(pos, rotation: str) -> tuple[int, int, int]:
    """StructureTemplate.transform with pivot (0, 0, 0) and no mirror."""
    x, y, z = pos
    return {"none": (x, y, z), "clockwise_90": (-z, y, x), "180": (-x, y, -z), "counterclockwise_90": (z, y, -x)}[
        rotation
    ]


def rotate_props(props: dict[str, str], rotation: str) -> dict[str, str]:
    """BlockState.rotate for the properties walls, fences, panes/bars and fence gates carry."""
    turn = TURN[rotation]
    out = {}
    for key, value in props.items():
        if key in turn:
            out[turn[key]] = value
        elif key == "facing":
            out[key] = turn[value]
        else:
            out[key] = value
    return out


def _text(block_id: str, props: dict[str, str]) -> str:
    return block_id + ("[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]" if props else "")


def _legacy_probe(config: Config) -> bytes:
    """The source states as an old-layout template at the source DataVersion (game upgrades it)."""
    schem = read_schematic(config.source)
    palette, lookup, blocks = [], {}, []
    for index, palette_index in enumerate(schem.cells):
        text = schem.palette[palette_index]
        block_id, props = parse_state(text)
        if config.air == "omit" and block_id == "minecraft:air":
            continue
        if text not in lookup:
            lookup[text] = len(palette)
            entry = Compound({"Name": String(block_id)})
            if props:
                entry["Properties"] = Compound({k: String(v) for k, v in props.items()})
            palette.append(entry)
        blocks.append(Compound({"pos": List[Int](schem.position(index)), "state": Int(lookup[text])}))
    root = nbtlib.File(
        {
            "DataVersion": Int(schem.data_version),
            "size": List[Int](schem.size),
            "palette": List[Compound](palette),
            "blocks": List[Compound](blocks),
            "entities": List[Compound]([]),
        },
        root_name="",
    )
    buffer = io.BytesIO()
    root.write(buffer)
    return gzip.compress(buffer.getvalue(), mtime=0)


def _template_cells(path: Path) -> dict[tuple[int, int, int], tuple[str, dict[str, str]]]:
    _, root = read_nbt(path)
    data = plain(root)
    palette = [(e["id"], e.get("properties", {})) for e in data["palette"]]
    return {tuple(b["pos"]): palette[b["state"]] for b in data["blocks"]}


class Layout:
    """Separate plots for each placement, far enough apart that no two placements touch."""

    def __init__(self, size: tuple[int, int, int]):
        self.size = size
        self.span = max(size[0], size[2])
        self.gap = 2 * self.span + 3  # a rotated copy reaches `span` either way from its origin

    def origin(self, column: int, row: int) -> tuple[int, int, int]:
        return (column * self.gap + self.span + 1, 0, row * self.gap + self.span + 1)

    def box(self, origin, rotation: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        corners = [
            transform((x, y, z), rotation)
            for x in (0, self.size[0] - 1)
            for y in (0, self.size[1] - 1)
            for z in (0, self.size[2] - 1)
        ]
        lo = tuple(min(c[i] for c in corners) + origin[i] for i in range(3))
        hi = tuple(max(c[i] for c in corners) + origin[i] for i in range(3))
        return lo, hi

    def extent(self, columns: int, rows: int) -> tuple[int, int, int, int]:
        return (0, 0, columns * self.gap - 1, rows * self.gap - 1)


def _at(origin, pos, rotation):
    t = transform(pos, rotation)
    return tuple(origin[i] + t[i] for i in range(3))


def run(config: Config, server_jar: Path, java: str, work: Path | None = None) -> dict:
    reference = load_reference(config.target)
    rules = Rules(load_connectivity(config.target))
    sha1 = hashlib.sha1(server_jar.read_bytes()).hexdigest()
    if sha1 != reference["server_jar_sha1"]:
        raise SystemExit(f"server jar sha1 {sha1} is not the reference jar {reference['server_jar_sha1']}")
    exported = convert(config)
    if not config.nbt_path.is_file() or config.nbt_path.read_bytes() != exported.nbt:
        raise SystemExit(f"{config.nbt_path} is not the current conversion; run `convert` first")
    with zipfile.ZipFile(server_jar) as z:
        version = json.loads(z.read("version.json"))
    namespace, name = config.structure_id.split(":", 1)
    probe_id = f"{namespace}:{name}__dfu_probe"
    work = Path(work or tempfile.mkdtemp(prefix="mmst-live-"))
    pack = work / "mmst_export_check"
    if pack.exists():
        shutil.rmtree(pack)
    pack_format = [version["pack_version"]["data_major"], version["pack_version"]["data_minor"]]
    (pack / "data" / namespace / "structure").mkdir(parents=True)
    (pack / "pack.mcmeta").write_text(
        json.dumps(
            {
                "pack": {
                    "description": "MM-ST structure export live check",
                    "min_format": pack_format,
                    "max_format": pack_format,
                }
            }
        )
    )
    target = pack / "data" / namespace / "structure" / f"{name}.nbt"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(config.nbt_path, target)
    (target.parent / f"{Path(name).name}__dfu_probe.nbt").write_bytes(_legacy_probe(config))

    schem = read_schematic(config.source)
    template = _template_cells(config.nbt_path)
    source = {}  # pos -> (block_id, stated props, complete default state text)
    for index, palette_index in enumerate(schem.cells):
        block_id, props = parse_state(schem.palette[palette_index])
        if config.air == "omit" and block_id == "minecraft:air":
            continue
        full, _ = resolve_state(block_id, props, reference)
        source[schem.position(index)] = (block_id, props, _text(block_id, dict(full)))
    connecting = sorted(p for p in template if rules.kind(template[p][0]) is not None)
    stated_differs = {tuple(d["pos"]) for d in exported.report["connectivity"]["explicit_differs_from_vanilla"]}

    layout = Layout(schem.size)
    port = _free_port()
    server = Server(
        work / "server",
        server_jar,
        java,
        {
            "level-type": "minecraft:flat",
            "generator-settings": json.dumps(FLAT, separators=(",", ":")),
            "generate-structures": "false",
            "rcon.port": str(port),
            "server-port": str(_free_port()),
            "level-seed": "1",
        },
        datapack=pack,
    )
    result: dict = {"minecraft_version": version["id"], "server_jar_sha1": sha1, "pack_format": pack_format}

    def place(template_id, origin, rotation, strict):
        mode = " strict" if strict else ""
        reply = server.cmd(
            f"place template {template_id} {origin[0]} {origin[1]} {origin[2]} {rotation} none 1 0{mode}"
        )
        if not reply.startswith("Loaded template"):
            raise RuntimeError(f"place {template_id} {rotation}{mode}: {reply}")
        return reply

    def same(a, b, rotation, positions=None):
        """Positions (template frame) where placement a differs from placement b."""
        if positions is None:
            lo_a, hi_a = layout.box(a, rotation)
            lo_b, _ = layout.box(b, rotation)
            reply = server.cmd("execute if blocks {} {} {} {} {} {} {} {} {} all".format(*lo_a, *hi_a, *lo_b))
            if "passed" in reply:
                return []
            positions = [schem.position(i) for i in range(len(schem.cells))]
        out = []
        for pos in positions:
            pa, pb = _at(a, pos, rotation), _at(b, pos, rotation)
            if "passed" not in server.cmd("execute if blocks {} {} {} {} {} {} {} {} {} all".format(*pa, *pa, *pb)):
                out.append(list(pos))
        return out

    def recompute(origin, rotation) -> list:
        """Non-strict /setblock of each connecting block's source state; positions the game changed."""
        changed = []
        for pos in connecting:
            block_id, stated, _ = source[pos]
            at = _at(origin, pos, rotation)
            reply = server.cmd("setblock {} {} {} {}".format(*at, _text(block_id, rotate_props(stated, rotation))))
            if reply.startswith("Changed the block"):
                changed.append(list(pos))
        return changed

    def cell_test(origin, expected: dict) -> list:
        failures = []
        for pos, state in sorted(expected.items()):
            x, y, z = (origin[i] + pos[i] for i in range(3))
            reply = server.cmd(f"execute if block {x} {y} {z} {state}")
            if "passed" not in reply:
                failures.append({"pos": list(pos), "expected": state, "reply": reply})
        return failures

    try:
        server.start()
        result["datapacks"] = server.cmd("datapack list enabled")
        x0, z0, x1, z1 = layout.extent(5, len(ROTATIONS))
        result["forceload"] = server.cmd(f"forceload add {x0} {z0} {x1} {z1}")

        # 1 + 2: load and version handling (rotation none)
        export_at, probe_at = layout.origin(0, 0), layout.origin(3, 0)
        place(config.structure_id, export_at, "none", True)
        place(probe_id, probe_at, "none", True)
        failures = cell_test(export_at, {p: _text(*template[p]) for p in template})
        result["load"] = {"cells_tested": len(template), "failure_count": len(failures), "failures": failures[:20]}
        failures = cell_test(probe_at, {p: s[2] for p, s in source.items()})
        result["dfu_probe"] = {"cells_tested": len(source), "failure_count": len(failures), "failures": failures[:20]}
        result["before_after"] = {
            "cells_changed_by_correction": len(same(export_at, probe_at, "none")),
            "corrected_blocks_in_report": exported.report["connectivity"]["corrected_blocks"],
        }
        # Negative control: the same oracle run on the uncorrected placement must change it, and the
        # game's own result must then equal the converter's (a /setblock also shape-updates neighbours,
        # so fewer blocks may report a change than were corrected).
        changed = recompute(probe_at, "none")
        result["oracle_negative_control"] = {
            "setblock_changed_on_uncorrected": len(changed),
            "uncorrected_after_game_recompute_vs_export_diff": same(probe_at, export_at, "none"),
        }

        # 3 + 4 for every rotation
        result["rotations"] = {}
        for row, rotation in enumerate(ROTATIONS):
            oracle, pristine, normal = layout.origin(0, row), layout.origin(1, row), layout.origin(2, row)
            probe_normal = layout.origin(4, row)
            if row:  # row 0 already holds the strict export at layout.origin(0, 0)
                place(config.structure_id, oracle, rotation, True)
            place(config.structure_id, pristine, rotation, True)
            place(config.structure_id, normal, rotation, False)
            place(probe_id, probe_normal, rotation, False)
            changed_by_game = recompute(oracle, rotation)
            oracle_diff = same(oracle, pristine, rotation)
            normal_diff = same(normal, pristine, rotation)
            probe_normal_diff = same(probe_normal, pristine, rotation)
            unexpected = [p for p in normal_diff if tuple(p) not in stated_differs]
            result["rotations"][rotation] = {
                "connecting_blocks_reset_by_setblock": len(connecting),
                "setblock_changed": changed_by_game,
                "oracle_vs_strict_diff": oracle_diff,
                "normal_vs_strict_diff": normal_diff,
                "normal_vs_strict_unexpected": unexpected,
                "uncorrected_normal_vs_corrected_strict_diff": probe_normal_diff,
                "pass": not changed_by_game and not oracle_diff and not unexpected,
            }
    finally:
        server.stop()
    log = (work / "server" / "server.log").read_text(errors="replace")
    lines = [line for line in log.splitlines() if LOG_PROBLEMS.search(line)]
    result["log_expected"] = [line for line in lines if LOG_EXPECTED.search(line)]
    result["log_problems"] = [line for line in lines if not LOG_EXPECTED.search(line)][:40]
    result["pack_loaded"] = "mmst_export_check" in result.get("datapacks", "")
    ok = (
        result["pack_loaded"]
        and result.get("load", {}).get("failure_count") == 0
        and result.get("dfu_probe", {}).get("failure_count") == 0
        and result.get("before_after", {}).get("cells_changed_by_correction")
        == result.get("before_after", {}).get("corrected_blocks_in_report")
        and bool(result.get("oracle_negative_control", {}).get("setblock_changed_on_uncorrected"))
        == bool(result.get("before_after", {}).get("corrected_blocks_in_report"))
        and result.get("oracle_negative_control", {}).get("uncorrected_after_game_recompute_vs_export_diff") == []
        and len(result.get("rotations", {})) == len(ROTATIONS)
        and all(r["pass"] for r in result["rotations"].values())
        and not result["log_problems"]
    )
    result["result"] = "PASS" if ok else "FAIL"
    return result
