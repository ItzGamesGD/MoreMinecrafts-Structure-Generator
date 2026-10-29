"""Live load check on a real vanilla Minecraft server (the reference's version).

Loads the exported template through a datapack, places it with /place template, and tests
every cell with `execute if block` against the complete expected state (the source state
plus the reference defaults the converter filled in). As an independent
cross-check of the version handling it also places a "DataFixer probe": the same source
states written in the legacy Name/Properties layout and stamped with the *source*
DataVersion, so that the game's own DataFixer upgrades them. Both placements must match
cell for cell (`execute if blocks ... all`). Placement uses `strict` (knownShape), which is
how jigsaw world generation places pool elements.

This is vanilla server evidence. It does not start MoreMinecrafts-Beta (Fabric + mod), so it
does not replace a load test inside the MMB runtime.
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

from .convert import Config, load_reference, resolve_state
from .schem import parse_state, read_schematic

ORIGIN = (0, 0, 0)
PROBE_ORIGIN = (64, 0, 0)
LOG_ERRORS = re.compile(r"(Failed to load|Couldn't load|Error loading|Exception|Invalid|Unknown block)", re.I)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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


def run(config: Config, server_jar: Path, java: str, work: Path | None = None) -> dict:
    reference = load_reference(config.target)
    sha1 = hashlib.sha1(server_jar.read_bytes()).hexdigest()
    if sha1 != reference["server_jar_sha1"]:
        raise SystemExit(f"server jar sha1 {sha1} is not the reference jar {reference['server_jar_sha1']}")
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
    port = _free_port()
    server = Server(
        work / "server",
        server_jar,
        java,
        {
            "level-type": "minecraft:flat",
            "generate-structures": "false",
            "rcon.port": str(port),
            "server-port": str(_free_port()),
            "level-seed": "1",
        },
        datapack=pack,
    )
    result = {"minecraft_version": version["id"], "server_jar_sha1": sha1, "pack_format": pack_format}
    try:
        server.start()
        result["datapacks"] = server.cmd("datapack list enabled")
        x1 = max(ORIGIN[0], PROBE_ORIGIN[0]) + schem.size[0]
        server.cmd(f"forceload add -16 -16 {x1 + 16} {schem.size[2] + 16}")
        # `strict` sets StructurePlaceSettings.knownShape, as jigsaw worldgen (SinglePoolElement) does:
        # template states are placed as written, without neighbour shape updates.
        result["place"] = server.cmd(
            f"place template {config.structure_id} {ORIGIN[0]} {ORIGIN[1]} {ORIGIN[2]} none none 1 0 strict"
        )
        result["place_probe"] = server.cmd(
            f"place template {probe_id} {PROBE_ORIGIN[0]} {PROBE_ORIGIN[1]} {PROBE_ORIGIN[2]} none none 1 0 strict"
        )
        failures = []
        for index, palette_index in enumerate(schem.cells):
            x, y, z = schem.position(index)
            block_id, props = parse_state(schem.palette[palette_index])
            full, _ = resolve_state(block_id, props, reference)
            state = block_id + ("[" + ",".join(f"{k}={v}" for k, v in full) + "]" if full else "")
            reply = server.cmd(f"execute if block {ORIGIN[0] + x} {ORIGIN[1] + y} {ORIGIN[2] + z} {state}")
            if "passed" not in reply:
                failures.append({"pos": [x, y, z], "expected": state, "reply": reply})
        result["cells_tested"] = len(schem.cells)
        result["cell_failures"] = failures[:20]
        result["cell_failure_count"] = len(failures)
        end = [ORIGIN[i] + schem.size[i] - 1 for i in range(3)]
        result["dfu_probe_compare"] = server.cmd(
            f"execute if blocks {ORIGIN[0]} {ORIGIN[1]} {ORIGIN[2]} {end[0]} {end[1]} {end[2]} "
            f"{PROBE_ORIGIN[0]} {PROBE_ORIGIN[1]} {PROBE_ORIGIN[2]} all"
        )
    finally:
        server.stop()
    log = (work / "server" / "server.log").read_text(errors="replace")
    result["log_errors"] = [line for line in log.splitlines() if LOG_ERRORS.search(line)][:20]
    result["pack_loaded"] = "mmst_export_check" in result.get("datapacks", "")
    result["placed"] = result.get("place", "").startswith("Loaded template") and result.get(
        "place_probe", ""
    ).startswith("Loaded template")
    result["probe_matches"] = "passed" in result.get("dfu_probe_compare", "")
    ok = (
        result["pack_loaded"]
        and result["placed"]
        and result["cell_failure_count"] == 0
        and result["probe_matches"]
        and not result["log_errors"]
    )
    result["result"] = "PASS" if ok else "FAIL"
    return result
