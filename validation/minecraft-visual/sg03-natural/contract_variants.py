#!/usr/bin/env python3
"""N7-B protection-contract suite. Starts the module in its production configuration (no SG01_* behaviour settings) against disposable
copies of the REAL SG-03 content pack (which carries the production manifest) with one defect injected per case, and checks each case against
its expected outcome. The production pack itself is never modified. Cases cover missing / stale / unsupported / empty / invalid / conflicting protection data, an owner pack with an unsupported
declared format, additive extensions (valid, unresolvable, replace=true), an unrelated pack with an unsupported format (must NOT be rejected),
and reload scenarios (a reload that breaks the contract must be rejected loudly and keep the last validated set).
Environment: SG_PACK (the committed SG-03 datapack, exports/sg-03/forgotten-underground-kingdom/datapack), JAVA_HOME. Writes <out>/contract_variants.json (or contract_variants_rerun.json with --only).
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
SPIKE = REPO / "mod" / "sg-worldgen-protection"
CAVERN = "moreminecrafts:forgotten_kingdom/central_cavern"
MANIFEST = Path("data/moreminecrafts/sg_protection/manifest.json")
EXT_TAG = Path("data/moreminecrafts/tags/worldgen/structure/protected_extensions.json")
LEGACY_TAG = Path("data/moreminecrafts/tags/worldgen/structure/protected_from_overlays.json")  # N7-A tag: must have no effect in N7-B
CODES = ("MANIFEST_MISSING", "MANIFEST_CONFLICT", "MANIFEST_INVALID", "FORMAT_UNSUPPORTED", "MANIFEST_STALE", "MANIFEST_EMPTY", "REQUIRED_UNRESOLVED",
         "OWNER_PACK_INCOMPATIBLE", "GAME_VERSION_MISMATCH", "OWNERSHIP_MISMATCH", "EXTENSION_MALFORMED", "EXTENSION_UNRESOLVED")


def read_manifest(src: Path) -> dict:
    return json.loads((src / MANIFEST).read_text())


def make_pack(src: Path, dst: Path, manifest: dict | str | None = "keep", mcmeta_format: int | None = None) -> Path:
    """Copy of the real SG-03 pack. manifest: "keep" (the production manifest), None (removed), or replacement content."""
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    if manifest is None:
        (dst / MANIFEST).unlink()
    elif manifest != "keep":
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
    env = {"SG_PROTECTION_REPORT": str(report_path)}  # production configuration: no SG01_* behaviour settings
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
    result["log"] = [ln.split("]: ", 1)[-1][:420] for ln in log.splitlines()
                     if "protection contract" in ln or "SG protection" in ln or "rejected on reload" in ln or "SG_SPIKE protected" in ln][:8]
    result["codes"] = sorted({c for c in CODES if f"[{c}]" in log})
    if "Unbound values in registry" in log:
        result["codes"].append("VANILLA_TAG_LOAD_FAILURE")
    result["remedy_reported"] = "Remedy:" in log if result["outcome"] == "failed" and result["codes"] and result["codes"] != ["VANILLA_TAG_LOAD_FAILURE"] else None
    if report_path.exists():
        result["contract"] = json.loads(report_path.read_text()).get("contract")
    return result


def enable(srv, run_dir: Path, name: str, files: dict[str, str]) -> str:
    pack = extra_pack(run_dir / "world" / "datapacks" / name, files)
    srv.cmd("datapack list")
    out = srv.cmd(f'datapack enable "file/{pack.name}"')
    time.sleep(3)
    return out[:160]


def reload_conflict(srv, run_dir: Path) -> dict:
    """Valid start, then a second pack that also provides the manifest is enabled at runtime (triggers a reload)."""
    return {"command_reply": enable(srv, run_dir, "zz_conflict", {str(MANIFEST): json.dumps(read_manifest(run_dir / "world" / "datapacks" / "sg01"))})}


def reload_stale(srv, run_dir: Path) -> dict:
    """Valid start, then the owning pack's manifest becomes stale on disk and /reload runs."""
    path = run_dir / "world" / "datapacks" / "sg01" / MANIFEST
    path.write_text(json.dumps({**json.loads(path.read_text()), "revision": 0}))
    out = srv.cmd("reload")
    time.sleep(3)
    return {"command_reply": out[:160]}


def reload_manifest_removed(srv, run_dir: Path) -> dict:
    (run_dir / "world" / "datapacks" / "sg01" / MANIFEST).unlink()
    out = srv.cmd("reload")
    time.sleep(3)
    return {"command_reply": out[:160]}


def reload_extension_added(srv, run_dir: Path) -> dict:
    return {"command_reply": enable(srv, run_dir, "zz_extadd", {str(EXT_TAG): json.dumps({"values": ["minecraft:stronghold"]})})}


def reload_extension_replace(srv, run_dir: Path) -> dict:
    return {"command_reply": enable(srv, run_dir, "zz_extrep", {str(EXT_TAG): json.dumps({"replace": True, "values": ["minecraft:stronghold"]})})}


def reload_extension_malformed(srv, run_dir: Path) -> dict:
    return {"command_reply": enable(srv, run_dir, "zz_extbad", {str(EXT_TAG): "{oops"})}


def reload_extension_removed(srv, run_dir: Path) -> dict:
    out = srv.cmd('datapack disable "file/zz_ext"')
    time.sleep(3)
    return {"command_reply": out[:160]}


def contract_is(**want):
    """Checker for the contract state written at shutdown (the state in force after the last reload)."""
    def check(r: dict) -> bool:
        c = r.get("contract") or {}
        return all(c.get(k) == v for k, v in want.items())
    return check


def rejected(n, code=None):
    """n extension files were dropped as a whole (N7-C policy), optionally with this code."""
    def check(r: dict) -> bool:
        rej = (r.get("contract") or {}).get("rejected_extensions", [])
        return len(rej) == n and all(code in x for x in rej) if code else len(rej) == n
    return check


def warned(code):
    return lambda r: any(code in w for w in (r.get("contract") or {}).get("warnings", []))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--only", help="comma-separated case names to run (default: all)")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    src = Path(os.environ["SG_PACK"])
    base = read_manifest(src)
    w = a.out / "fixtures"
    ok = make_pack(src, w / "ok")
    ext = lambda name, values, **top: extra_pack(w / name, {str(EXT_TAG): json.dumps({**top, "values": values})})  # noqa: E731
    cases = [
        # name, pack, extras, expected outcome, expected code, after, extra check on the result
        ("production_valid", ok, [], "started", None, None, contract_is(required=1, extensions=0, format=1)),
        ("manifest_missing", make_pack(src, w / "nomanifest", None), [], "failed", "MANIFEST_MISSING", None, None),
        ("format_unsupported", make_pack(src, w / "fmt2", {**base, "format": 2}), [], "failed", "FORMAT_UNSUPPORTED", None, None),
        ("revision_stale", make_pack(src, w / "rev0", {**base, "revision": 0}), [], "failed", "MANIFEST_STALE", None, None),
        ("game_version_mismatch", make_pack(src, w / "mc", {**base, "minecraft": "26.2"}), [], "failed", "GAME_VERSION_MISMATCH", None, None),
        ("required_unresolved", make_pack(src, w / "unres", {**base, "structures": [CAVERN, "moreminecrafts:forgotten_kingdom/removed"]}), [], "failed", "REQUIRED_UNRESOLVED", None, None),
        ("manifest_empty", make_pack(src, w / "empty", {**base, "structures": []}), [], "failed", "MANIFEST_EMPTY", None, None),
        ("manifest_invalid_json", make_pack(src, w / "invalid", "{not json"), [], "failed", "MANIFEST_INVALID", None, None),
        ("manifest_duplicate_entry", make_pack(src, w / "dup", {**base, "structures": [CAVERN, CAVERN]}), [], "failed", "MANIFEST_INVALID", None, None),
        ("manifest_bad_entry", make_pack(src, w / "badentry", {**base, "structures": [CAVERN, 7]}), [], "failed", "MANIFEST_INVALID", None, None),
        ("manifest_no_structures_field", make_pack(src, w / "nostruct", {"format": 1, "revision": 1}), [], "failed", "MANIFEST_INVALID", None, None),
        ("owner_pack_format_999", make_pack(src, w / "owner999", mcmeta_format=999), [], "failed", "OWNER_PACK_INCOMPATIBLE", None, None),
        ("conflicting_provider", ok, [extra_pack(w / "zz_override", {str(MANIFEST): json.dumps(base)})], "failed", "MANIFEST_CONFLICT", None, None),
        # The manifest owner does not define the structure it lists (the SG pack defines it but ships no manifest here).
        ("ownership_mismatch", make_pack(src, w / "nomanifest2", None), [extra_pack(w / "zz_owner", {str(MANIFEST): json.dumps(base)})], "failed", "OWNERSHIP_MISMATCH", None, None),
        ("extension_valid", ok, [ext("zz_ext", ["minecraft:stronghold"])], "started", None, None, contract_is(required=1, extensions=1)),
        ("extension_optional_unresolved", ok, [ext("zz_extopt", [{"id": "thirdparty:not_installed", "required": False}])], "started", None, None,
         lambda r: warned("EXTENSION_OPTIONAL_UNRESOLVED")(r) and contract_is(extensions=0)(r)),
        # A required (default) entry for a structure that is not installed is refused by vanilla's own datapack loader before the module runs: loud, not silent.
        ("extension_required_unresolved", ok, [ext("zz_extbad", ["thirdparty:not_installed"])], "failed", "VANILLA_TAG_LOAD_FAILURE", None, None),
        # N7-C policy: an extension file that cannot be understood is dropped as a whole, loudly; the owner's protection is untouched.
        ("extension_replace_ignored", ok, [ext("zz_extrep", ["minecraft:stronghold"], replace=True)], "started", None, None,
         lambda r: warned("EXTENSION_REPLACE_IGNORED")(r) and contract_is(required=1, extensions=1)(r)),
        ("extension_malformed_json", ok, [extra_pack(w / "zz_extjson", {str(EXT_TAG): "{oops"})], "started", "EXTENSION_MALFORMED", None, lambda r: rejected(1, "EXTENSION_MALFORMED")(r) and contract_is(required=1, extensions=0)(r)),
        ("extension_bad_entry", ok, [ext("zz_extnum", ["minecraft:stronghold", 42])], "started", "EXTENSION_MALFORMED", None, lambda r: rejected(1, "EXTENSION_MALFORMED")(r) and contract_is(required=1, extensions=0)(r)),
        ("extension_tag_reference", ok, [ext("zz_exttag", ["#minecraft:village"])], "started", "EXTENSION_MALFORMED", None, lambda r: rejected(1, "EXTENSION_MALFORMED")(r) and contract_is(required=1, extensions=0)(r)),
        ("extension_malformed_isolated", ok, [extra_pack(w / "zz_extjson2", {str(EXT_TAG): "{oops"}), ext("zz_extgood", ["minecraft:stronghold"])], "started", "EXTENSION_MALFORMED", None,
         lambda r: rejected(1, "EXTENSION_MALFORMED")(r) and contract_is(required=1, extensions=1)(r)),
        ("extension_duplicates", ok, [ext("zz_ext1", ["minecraft:stronghold", CAVERN]), ext("zz_ext2", ["minecraft:stronghold"])], "started", None, None,
         lambda r: warned("EXTENSION_DUPLICATE")(r) and contract_is(extensions=1)(r)),
        # The N7-A tag is no longer read: replacing it neither helps nor hurts.
        ("legacy_tag_has_no_effect", ok, [extra_pack(w / "zz_legacy", {str(LEGACY_TAG): json.dumps({"replace": True, "values": ["minecraft:stronghold"]})})], "started", None, None,
         contract_is(required=1, extensions=0)),
        ("unrelated_pack_format_999", ok, [extra_pack(w / "zz_unrelated", {"data/other/function/x.mcfunction": "say hi"}, fmt=999)], "started", None, None, None),
        # Reload behaviour: a rejected reload keeps the last validated set and is loud; a valid reload takes effect.
        ("reload_conflict", ok, [], "started", None, reload_conflict, lambda r: (r["contract"] or {}).get("reload_rejections", 0) >= 1 and contract_is(required=1)(r)),
        ("reload_stale", make_pack(src, w / "reloadstale"), [], "started", None, reload_stale, lambda r: (r["contract"] or {}).get("reload_rejections", 0) >= 1 and contract_is(required=1)(r)),
        ("reload_manifest_removed", make_pack(src, w / "reloadrm"), [], "started", None, reload_manifest_removed,
         lambda r: (r["contract"] or {}).get("reload_rejections", 0) >= 1 and contract_is(required=1)(r)),
        ("reload_extension_replace", ok, [], "started", None, reload_extension_replace,
         lambda r: (r["contract"] or {}).get("reload_rejections", 0) == 0 and warned("EXTENSION_REPLACE_IGNORED")(r) and contract_is(extensions=1)(r)),
        ("reload_extension_malformed", ok, [], "started", "EXTENSION_MALFORMED", reload_extension_malformed,
         lambda r: (r["contract"] or {}).get("reload_rejections", 0) == 0 and rejected(1, "EXTENSION_MALFORMED")(r) and contract_is(required=1, extensions=0)(r)),
        ("reload_extension_added", ok, [], "started", None, reload_extension_added, lambda r: (r["contract"] or {}).get("reload_rejections", 0) == 0 and contract_is(extensions=1)(r)),
        ("reload_extension_removed", ok, [ext("zz_ext", ["minecraft:stronghold"])], "started", None, reload_extension_removed,
         lambda r: (r["contract"] or {}).get("reload_rejections", 0) == 0 and contract_is(extensions=0, required=1)(r)),
    ]
    results = []
    only = set(a.only.split(",")) if a.only else None
    for i, (name, pack, extras, want_outcome, want_code, after, check) in enumerate(cases):
        if only and name not in only:
            continue
        r = run(pack, name, a.out, 40980 + i, extras, after)
        r["expected_outcome"], r["expected_code"] = want_outcome, want_code
        got = r["outcome"] == want_outcome and (want_code is None or want_code in r["codes"])
        if r["outcome"] == "failed" and r["remedy_reported"] is False:
            got = False  # every module-reported failure must carry an actionable remedy
        if check is not None:
            got = got and bool(check(r))
        r["pass"] = got
        results.append(r)
        print(f"{name:32} {r['outcome']:8} codes={r['codes']} expected={want_outcome}/{want_code} {'PASS' if got else 'FAIL'}", flush=True)
    (a.out / ("contract_variants.json" if not only else "contract_variants_rerun.json")).write_text(json.dumps(results, indent=1) + "\n")
    print(f"{sum(r['pass'] for r in results)}/{len(results)} cases as expected")


if __name__ == "__main__":
    main()
