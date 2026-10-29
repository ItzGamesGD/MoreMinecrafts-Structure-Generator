"""Read-only comparison of an exported template with a MoreMinecrafts-Beta checkout.

Nothing in the MMB checkout is written. Checks:
1. the checkout is at the expected commit (if given);
2. the template's NBT schema (root keys, tag types, palette/block entry keys, DataVersion)
   matches every structure template MMB already ships;
3. MMB's own template loader (`template_info` in scripts/structures/sky_islands/validate.py)
   accepts it: bounds, duplicate positions and palette lookups;
4. its datapack-relative path is the one MMB's template pools resolve for its id.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from .verify import read_nbt

TEMPLATE_DIR = "src/main/resources/data/moreminecrafts/structure"


def _signature(path: Path) -> dict:
    _, root = read_nbt(path)
    r = root.value
    palette_keys, block_keys = set(), set()
    for entry in r["palette"].value:
        palette_keys |= set(entry.value)
    for entry in r["blocks"].value:
        block_keys |= set(entry.value)
    return {
        "root": {k: (v.type, v.element) for k, v in r.items() if k != "entities"},
        "data_version": r["DataVersion"].value,
        "palette_keys": palette_keys,
        "block_keys": block_keys,
    }


def _mmb_template_info(mmb: Path):
    script = mmb / "scripts/structures/sky_islands/validate.py"
    spec = importlib.util.spec_from_file_location("mmb_sky_islands_validate", script)
    module = importlib.util.module_from_spec(spec)
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # leave no __pycache__ in MMB
    try:
        spec.loader.exec_module(module)  # module level only defines helpers; main() is not run
    finally:
        sys.dont_write_bytecode = previous
    return module


def check(nbt_path: Path, structure_id: str, datapack: Path, mmb: Path, expect_commit: str | None) -> dict:
    head = subprocess.run(
        ["git", "-C", str(mmb), "rev-parse", "HEAD", "HEAD^{tree}"], capture_output=True, text=True, check=True
    ).stdout.split()
    if expect_commit and head[0] != expect_commit:
        raise SystemExit(f"MMB checkout is at {head[0]}, expected {expect_commit}")
    dirty = subprocess.run(
        ["git", "-C", str(mmb), "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout.strip()

    references = sorted((mmb / TEMPLATE_DIR).rglob("*.nbt"))
    if not references:
        raise SystemExit(f"no MMB templates under {TEMPLATE_DIR}")
    ours = _signature(nbt_path)
    problems = []
    for ref in references:
        theirs = _signature(ref)
        if theirs["root"] != ours["root"]:
            problems.append(f"root tag types differ from {ref.relative_to(mmb)}: {theirs['root']} vs {ours['root']}")
        if theirs["data_version"] != ours["data_version"]:
            problems.append(f"DataVersion {ours['data_version']} != {theirs['data_version']} in {ref.relative_to(mmb)}")
    mmb_palette_keys = set().union(*(_signature(r)["palette_keys"] for r in references))
    mmb_block_keys = set().union(*(_signature(r)["block_keys"] for r in references))
    if not ours["palette_keys"] <= mmb_palette_keys:
        problems.append(f"palette keys {sorted(ours['palette_keys'] - mmb_palette_keys)} unused by MMB templates")
    if not ours["block_keys"] <= mmb_block_keys:
        problems.append(f"block keys {sorted(ours['block_keys'] - mmb_block_keys)} unused by MMB templates")

    module = _mmb_template_info(mmb)
    size, blocks = module.template_info(nbt_path)
    problems += [f"MMB template_info: {f}" for f in module.failures]

    namespace, name = structure_id.split(":", 1)
    relative = nbt_path.relative_to(datapack).as_posix()
    expected_relative = f"data/{namespace}/structure/{name}.nbt"
    if relative != expected_relative:
        problems.append(f"datapack path {relative} != {expected_relative}")
    if namespace != "moreminecrafts":
        problems.append(f"namespace {namespace!r} is not MMB's 'moreminecrafts'")
    if problems:
        raise SystemExit("MMB compatibility check FAILED:\n - " + "\n - ".join(problems))
    return {
        "mmb_commit": head[0],
        "mmb_tree": head[1],
        "mmb_worktree_clean": not dirty,
        "reference_templates": len(references),
        "data_version": ours["data_version"],
        "mmb_template_info": {"size": list(size), "blocks": len(blocks)},
        "mmb_resource_path": f"src/main/resources/{expected_relative}",
        "result": "PASS",
    }
