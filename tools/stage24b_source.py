"""Stage 24-B source provenance and baseline manifest utilities."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen

import nbtlib

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "049c791ad8e7255d15c30f66774f427a343522e5"
SOURCE_COMMIT = "bb6d6451fb5fff54d3930fd8bf19d81200f00e6d"
SOURCE_ROOT = "data/minecraft/structure/ancient_city/structures"
STAGE_ROOT = Path("artifacts/ancient-city-restoration/stage-24a")
MODULES = {
    "large_ruin_1": {"size": [17, 5, 17], "sha1": "3ce04aa7cd68ab706ed7e7910cbf8453f090fb39", "entry": {"face": "west", "pos": [0, 0, 7]}},
    "medium_ruin_1": {"size": [8, 5, 13], "sha1": "c476ea76624d25ac483f723c55ef39695ac86aee", "entry": {"face": "west", "pos": [0, 0, 6]}},
    "medium_ruin_2": {"size": [16, 5, 11], "sha1": "0f8b01b7aff4bd43c8e5ecc18292940ca648bf03", "entry": {"face": "west", "pos": [0, 0, 5]}},
    "small_ruin_1": {"size": [7, 5, 8], "sha1": "b1b9c2ac7c4b06a1a80e53adf4dd4fd706f2a799", "entry": {"face": "west", "pos": [0, 0, 3]}},
    "small_ruin_2": {"size": [8, 5, 4], "sha1": "34d14f95c92675e6d97d212baf88e84c4f506fbd", "entry": {"face": "west", "pos": [0, 0, 2]}},
    "sauna_1": {"size": [29, 10, 37], "sha1": "ef56d35f13f3acb8d62095ccc2f7e85d58d253b1", "entry": {"face": "south", "pos": [13, 1, 36]}},
    "large_pillar_1": {"size": [6, 15, 6], "sha1": "4d619829f48909054996945d01a77d949946e678", "entry": {"face": "west", "pos": [0, 1, 2]}},
    "medium_pillar_1": {"size": [7, 11, 8], "sha1": "38ece3d8a57c9fed3f2a050ffd21b5b636121bbe", "entry": {"face": "south", "pos": [3, 1, 0]}},
}


def plain(value):
    if hasattr(value, "items"):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def verify_source_bytes(module: str, data: bytes) -> str:
    if module not in MODULES:
        raise KeyError(f"Unknown Stage 24-B module: {module}")
    actual = git_blob_sha1(data)
    expected = MODULES[module]["sha1"]
    if actual != expected:
        raise ValueError(f"{module} source blob SHA mismatch: expected {expected}, got {actual}")
    return actual


def download_original(module: str) -> tuple[bytes, str]:
    relative = f"{SOURCE_ROOT}/{module}.nbt"
    url = f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/{SOURCE_COMMIT}/{relative}"
    request = Request(url, headers={"User-Agent": "MoreMinecrafts-Stage24B-Source-Validator"})
    data = urlopen(request, timeout=60).read()
    verify_source_bytes(module, data)
    return data, url


def load_original(module: str):
    data, url = download_original(module)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{module}.nbt"
        path.write_bytes(data)
        return nbtlib.load(path), url, git_blob_sha1(data)


def block_key(state) -> str:
    name = str(state["Name"])
    props = state.get("Properties")
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


def _source_details(module: str, root, url: str, sha: str, design: str, report: dict) -> dict:
    source_size = [int(v) for v in root["size"]]
    expected = MODULES[module]["size"]
    if source_size != expected or report.get("size_xyz") != expected:
        raise ValueError(f"{module} source/design baseline dimension drift: {source_size}, expected {expected}")
    if report.get("source_blob_sha1") != sha or report.get("source_blob_sha1") != MODULES[module]["sha1"]:
        raise ValueError(f"{module} Stage 24-A source-inspection SHA does not match pinned source")

    palette = root["palette"]
    counts = Counter()
    jigsaws = []
    block_entities = []
    foundations = []
    protected_counts = Counter()
    for item in root["blocks"]:
        pos = [int(v) for v in item["pos"]]
        state = palette[int(item["state"])]
        key = block_key(state)
        counts[key.split("[", 1)[0]] += 1
        if pos[1] == 0:
            foundations.append({"pos": pos, "state": key})
        if key.split("[", 1)[0] == "minecraft:jigsaw":
            jigsaws.append({"pos": pos, "state": key, "nbt": plain(item.get("nbt", {}))})
        if "nbt" in item:
            block_entities.append({"pos": pos, "state": key, "nbt": plain(item["nbt"])})
        if module == "sauna_1" and key.split("[", 1)[0] in ("minecraft:water", "minecraft:chest", "minecraft:deepslate_tile_stairs", "minecraft:deepslate_brick_slab", "minecraft:deepslate_tile_slab"):
            protected_counts[key.split("[", 1)[0]] += 1
        if module == "medium_pillar_1" and key.split("[", 1)[0] == "minecraft:skeleton_skull":
            protected_counts[key.split("[", 1)[0]] += 1
    for key in ("minecraft:water", "minecraft:chest", "minecraft:deepslate_tile_stairs"):
        if module == "sauna_1":
            expected_count = {"minecraft:water": 43, "minecraft:chest": 3, "minecraft:deepslate_tile_stairs": 86}[key]
            if protected_counts[key] != expected_count:
                raise ValueError(f"sauna_1 protected {key} count drift: {protected_counts[key]} != {expected_count}")
    expected_jigsaws = {"sauna_1": 5, "large_pillar_1": 1, "medium_pillar_1": 2}.get(module, 1)
    if len(jigsaws) != expected_jigsaws:
        raise ValueError(f"{module} jigsaw count drift: {len(jigsaws)} != {expected_jigsaws}")
    return {
        "source_url": url,
        "source_verified": True,
        "source_blob_sha1": sha,
        "original_dimensions_xyz": source_size,
        "block_count": len(root["blocks"]),
        "palette_counts": dict(sorted(counts.items())),
        "entry_candidate": MODULES[module]["entry"],
        "foundation_blocks": foundations,
        "jigsaws": jigsaws,
        "block_entities": block_entities,
        "protected_counts": dict(protected_counts),
        "approved_design_sha256": hashlib.sha256(design.encode()).hexdigest(),
        "stage24a_report_sha1": report["source_blob_sha1"],
    }


def build_baseline_manifest(repo_root: Path = ROOT, output: Path | None = None) -> dict:
    actual_root = Path(repo_root)
    baseline_object = subprocess.run(
        ["git", "-C", str(actual_root), "cat-file", "-e", f"{BASELINE_SHA}^{{commit}}"],
        text=True, capture_output=True,
    )
    if baseline_object.returncode != 0:
        raise ValueError(f"Approved Stage 24-A baseline commit is missing: {BASELINE_SHA}")
    merge_base = subprocess.run(
        ["git", "-C", str(actual_root), "merge-base", "HEAD", BASELINE_SHA],
        text=True, capture_output=True, check=True,
    ).stdout.strip()
    if merge_base != BASELINE_SHA:
        raise ValueError(f"HEAD does not descend from the verified Stage 24-A baseline {BASELINE_SHA}")
    base = actual_root / STAGE_ROOT
    modules = {}
    for module in MODULES:
        design_path = base / "designs" / f"{module}.md"
        report_path = base / "source-inspection" / module / "source.json"
        if not design_path.is_file() or not report_path.is_file():
            raise FileNotFoundError(f"Approved Stage 24-A design/report pair missing for {module}")
        design = design_path.read_text(encoding="utf-8")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("verified") is not True:
            raise ValueError(f"Stage 24-A source report is not verified: {module}")
        root, url, sha = load_original(module)
        modules[module] = _source_details(module, root, url, sha, design, report)
    manifest = {
        "stage": "24-B",
        "baseline_commit": BASELINE_SHA,
        "source_repository": "InventivetalentDev/minecraft-assets",
        "source_commit": SOURCE_COMMIT,
        "source_path": SOURCE_ROOT,
        "expected_modules": list(MODULES),
        "modules": modules,
        "implementation_dimensions_xyz": {name: ([16, 8, 11] if name == "medium_ruin_2" else MODULES[name]["size"]) for name in MODULES},
        "status": "SOURCE_BASELINE_VERIFIED",
    }
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    target = ROOT / "artifacts" / "ancient-city-restoration" / "stage-24b" / "baseline.json"
    doc = build_baseline_manifest(output=target)
    print(json.dumps({name: {"size": info["original_dimensions_xyz"], "sha1": info["source_blob_sha1"]} for name, info in doc["modules"].items()}, indent=2))
