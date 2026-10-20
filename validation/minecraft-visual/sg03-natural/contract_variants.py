#!/usr/bin/env python3
"""N7-A4 protection-contract experiment. Starts the module in manifest mode (SG01_PROTECTION=manifest) against fixture datapacks and checks
each case against its expected outcome. Fixtures are disposable copies of the SG datapack plus a TEST-ONLY manifest; the production pack is
never modified. Cases cover missing / stale / unsupported / empty / invalid / conflicting protection data, an owner pack with an unsupported
declared format, additive extensions (valid, unresolvable, replace=true), an unrelated pack with an unsupported format (must NOT be rejected),
and reload scenarios (a reload that breaks the contract must be rejected loudly and keep the last validated set).
Environment: SG_PACK (built SG-03 datapack folder), JAVA_HOME. Writes <out>/contract_variants.json.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from world import Server  # noqa: E402

REPO = HERE.parents[2]
SPIKE = REPO / "validation" / "fabric-protection-spike"
CAVERN = "moreminecrafts:forgotten_kingdom/central_cavern"
MANIFEST = Path("data/moreminecrafts/sg_protection/manifest.json")
EXT_TAG = Path("data/moreminecrafts/tags/worldgen/structure/protected_extensions.json")
LEGACY_TAG = Path("data/moreminecrafts/tags/worldgen/structure/protected_from_overlays.json")


def good_manifest(**over) -> dict:
    m = {"format": 1, "revision": 1, "structures": [CAVERN]}
    m.update(over)
    return m


def make_pack(src: Path, dst: Path, manifest: dict | str | None, mcmeta_format: int | None = None) -> Path:
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    if manifest is not None:
        (dst / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
        (dst / MANIFEST).write_text(manifest if isinstance(manifest, str) else json.dumps(manifest))
    if mcmeta_format is not None:
        meta = json.loads((dst / "pack.mcmeta").read_text())
        meta["pack"]["min_format"] = meta["pack"]["max_format"] = mcmeta_format
        (dst / "pack.mcmeta").write_text(json.dumps(meta))
    return dst


def extra_pack(dst: Path, files: dict[str, str], fmt: int = 121) -> Path:
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    (dst / "pack.mcmeta").write_text(json.dumps({"pack": {"description": dst.name, "min_format": fmt, "max_format": fmt}}))
    for rel, content in files.items():
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_text(content)
    return dst


def run(pack: Path, name: str, out: Path, port: int, extras: list[Path], after=None) -> dict:
    run_dir = (SPIKE / "run" / "server").resolve()
    shutil.rmtree(run_dir, ignore_errors=True)
    (run_dir / "world" / "datapacks").mkdir(parents=True)
    for e in extras:
        shutil.copytree(e, run_dir / "world" / "datapacks" / e.name)
    report_path = (out / f"{name}.report.json").resolve()
    report_path.unlink(missing_ok=True)
    env = {"SG01_PROTECTION": "manifest", "SG01_GUARD_MODE": "enforce", "SG01_FEATURES": "both", "SG01_REFINE": "hybrid", "SG01_SPIKE_REPORT": str(report_path)}
    result: dict = {"case": name}
    try:
        srv = Server("java", None, run_dir, 173, pack, port=port, launcher=["./gradlew", "--no-daemon", "runServer"], launcher_cwd=SPIKE,
                     start_timeout=240, env=env)
        result["outcome"] = "started"
        if after is not None:
            result["after"] = after(srv, run_dir)
        srv.stop()
    except RuntimeError as e:
        result["outcome"] = "failed"
        result["error_tail"] = str(e)[-300:]
    log = (run_dir / "server.log").read_text(errors="replace") if (run_dir / "server.log").exists() else ""
    if (run_dir / "server.log").exists():
        shutil.copy2(run_dir / "server.log", out / f"{name}.log")
    result["log"] = [ln.split("]: ", 1)[-1][:300] for ln in log.splitlines()
                     if "protection contract" in ln or "SG protection" in ln or "rejected on reload" in ln or "SG_SPIKE protected" in ln][:8]
    result["codes"] = sorted({c for c in ("MANIFEST_MISSING", "MANIFEST_CONFLICT", "MANIFEST_INVALID", "FORMAT_UNSUPPORTED", "MANIFEST_STALE", "MANIFEST_EMPTY",
                                          "REQUIRED_UNRESOLVED", "OWNER_PACK_INCOMPATIBLE") if c in log})
    if report_path.exists():
        result["contract"] = json.loads(report_path.read_text()).get("contract")
    return result


def reload_conflict(srv, run_dir: Path) -> dict:
    """Valid start, then a second pack that also provides the manifest is enabled at runtime (triggers a reload)."""
    evil = extra_pack(run_dir / "world" / "datapacks" / "zz_conflict", {str(MANIFEST): json.dumps(good_manifest())})
    srv.cmd("datapack list")
    out = srv.cmd(f'datapack enable "file/{evil.name}"')
    time.sleep(3)
    return {"command_reply": out[:160]}


def reload_stale(srv, run_dir: Path) -> dict:
    """Valid start, then the owning pack's manifest becomes stale on disk and /reload runs."""
    (run_dir / "world" / "datapacks" / "sg01" / MANIFEST).write_text(json.dumps(good_manifest(revision=0)))
    out = srv.cmd("reload")
    time.sleep(3)
    return {"command_reply": out[:160]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    src = Path(os.environ["SG_PACK"])
    w = a.out / "fixtures"
    ok = make_pack(src, w / "ok", good_manifest())
    cases = [
        # name, pack, extras, expectation (outcome, code or None), after
        ("valid", ok, [], ("started", None), None),
        ("manifest_missing", make_pack(src, w / "nomanifest", None), [], ("failed", "MANIFEST_MISSING"), None),
        ("format_unsupported", make_pack(src, w / "fmt2", good_manifest(format=2)), [], ("failed", "FORMAT_UNSUPPORTED"), None),
        ("revision_stale", make_pack(src, w / "rev0", good_manifest(revision=0)), [], ("failed", "MANIFEST_STALE"), None),
        ("required_unresolved", make_pack(src, w / "unres", good_manifest(structures=[CAVERN, "moreminecrafts:forgotten_kingdom/removed"])), [], ("failed", "REQUIRED_UNRESOLVED"), None),
        ("manifest_empty", make_pack(src, w / "empty", good_manifest(structures=[])), [], ("failed", "MANIFEST_EMPTY"), None),
        ("manifest_invalid", make_pack(src, w / "invalid", "{not json"), [], ("failed", "MANIFEST_INVALID"), None),
        ("owner_pack_format_999", make_pack(src, w / "owner999", good_manifest(), mcmeta_format=999), [], ("failed", "OWNER_PACK_INCOMPATIBLE"), None),
        ("conflicting_provider", ok, [extra_pack(w / "zz_override", {str(MANIFEST): json.dumps(good_manifest(structures=[CAVERN]))})], ("failed", "MANIFEST_CONFLICT"), None),
        ("extension_valid", ok, [extra_pack(w / "zz_ext", {str(EXT_TAG): json.dumps({"values": ["minecraft:stronghold"]})})], ("started", None), None),
        ("extension_unresolvable", ok, [extra_pack(w / "zz_extbad", {str(EXT_TAG): json.dumps({"values": ["thirdparty:not_installed"]})})], ("started", None), None),
        ("extension_replace_empty", ok, [extra_pack(w / "zz_extrep", {str(EXT_TAG): json.dumps({"replace": True, "values": []})})], ("started", None), None),
        ("legacy_tag_replaced_to_empty", ok, [extra_pack(w / "zz_legacy", {str(LEGACY_TAG): json.dumps({"replace": True, "values": []})})], ("started", None), None),
        ("unrelated_pack_format_999", ok, [extra_pack(w / "zz_unrelated", {"data/other/function/x.mcfunction": "say hi"}, fmt=999)], ("started", None), None),
        ("reload_conflict", ok, [], ("started", None), reload_conflict),
        ("reload_stale", make_pack(src, w / "reloadstale", good_manifest()), [], ("started", None), reload_stale),
    ]
    results = []
    for i, (name, pack, extras, (want_outcome, want_code), after) in enumerate(cases):
        r = run(pack, name, a.out, 40980 + i, extras, after)
        r["expected_outcome"], r["expected_code"] = want_outcome, want_code
        got = r["outcome"] == want_outcome and (want_code is None or want_code in r["codes"])
        if name.startswith("reload_"):
            got = got and bool(r.get("contract")) and r["contract"].get("reload_rejections", 0) >= 1
        r["pass"] = got
        results.append(r)
        print(f"{name:32} {r['outcome']:8} codes={r['codes']} expected={want_outcome}/{want_code} {'PASS' if got else 'FAIL'}", flush=True)
    (a.out / "contract_variants.json").write_text(json.dumps(results, indent=1) + "\n")
    print(f"{sum(r['pass'] for r in results)}/{len(results)} cases as expected")


if __name__ == "__main__":
    main()
