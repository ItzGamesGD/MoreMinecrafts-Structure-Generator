"""Stage 24-K: integrate the owner-approved watchtower designs into the production templates and rebuild the derived data.

1. `final-candidates/`: the eight approved templates. Six are byte-identical copies of the Stage 24-F files;
   large_pillar_1 and medium_pillar_1 are byte-identical copies of the approved Stage 24-J Option A candidates.
2. `derived-24g/`, `derived-24h/`, `derived-24i/`: the unchanged Stage 24-G (functional protection), 24-H (interior
   clearance) and 24-I (roof protection) builders run on those templates. `derived-24i/datapack` is the production pack.
3. `DERIVATION-DIFF.json`: what changed against the Stage 24-I derived data (must be nothing for the six untouched
   modules).
"""
from __future__ import annotations

import filecmp
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24c.common import MODULES  # noqa: E402
from tools.stage24k import rebase  # noqa: E402

ROOT, AR, K = rebase.ROOT, rebase.AR, rebase.K
D24F = AR / "stage-24f/final-candidates"
D24J = AR / "stage-24j"
APPROVED = {"large_pillar_1": D24J / "proposals/large_pillar_1/A/candidate.nbt",
            "medium_pillar_1": D24J / "proposals/medium_pillar_1/A/candidate.nbt"}
STRUCT = "data/minecraft/structure/ancient_city/structures/{m}.nbt"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def assemble(out: Path = K / "final-candidates"):
    shutil.rmtree(out, ignore_errors=True)
    sources = {}
    for m in MODULES:
        src = APPROVED.get(m, D24F / m / "restored.nbt")
        dst = out / m / "restored.nbt"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        sources[m] = {"source": src.relative_to(ROOT).as_posix(), "sha256": sha(dst),
                      "byte_identical_to_stage24f": filecmp.cmp(dst, D24F / m / "restored.nbt", shallow=False)}
    (out / "SHA256SUMS").write_text("".join(f"{sources[m]['sha256']}  {m}/restored.nbt\n" for m in MODULES))
    (out.parent / "SOURCES.json").write_text(json.dumps(sources, indent=1) + "\n")
    return sources


def derive():
    from tools.stage24g import build as G
    from tools.stage24h import build as H
    from tools.stage24i import build as I
    rebase.activate()
    out = {}
    out["g"] = G.build(K / "derived-24g", K / "final-candidates")
    out["h"] = H.build(K / "derived-24h")
    out["i"] = I.build(K / "derived-24i")
    return out


def diff_derived():
    """Compare the rebuilt derived data with the Stage 24-I ones, per module."""
    def load(p):
        return json.loads(p.read_text())
    old = {"protection": load(AR / "stage-24g/protection/protected-cells.json"), "mask": load(AR / "stage-24h/mask/interior-masks.json"),
           "roof": load(AR / "stage-24i/roof/roof-cells.json")}
    new = {"protection": load(K / "derived-24g/protection/protected-cells.json"), "mask": load(K / "derived-24h/mask/interior-masks.json"),
           "roof": load(K / "derived-24i/roof/roof-cells.json")}
    res = {}
    for m in MODULES:
        r = {}
        po, pn = {tuple(e["pos"]): e for e in old["protection"][m]["protected"]}, {tuple(e["pos"]): e for e in new["protection"][m]["protected"]}
        r["protected_cells"] = {"old": len(po), "new": len(pn), "identical": old["protection"][m] == new["protection"][m],
                                "removed": sorted(f"{list(p)} {','.join(po[p]['roles'])} {po[p]['state'].split('[')[0]}" for p in po.keys() - pn.keys()),
                                "added": sorted(f"{list(p)} {','.join(pn[p]['roles'])} {pn[p]['state'].split('[')[0]}" for p in pn.keys() - po.keys()),
                                "role_changed": sorted(f"{list(p)} {po[p]['roles']}->{pn[p]['roles']}" for p in po.keys() & pn.keys() if po[p]["roles"] != pn[p]["roles"])}
        mo = {tuple(c): k for k, v in old["mask"][m]["cleared"].items() for c in v}
        mn = {tuple(c): k for k, v in new["mask"][m]["cleared"].items() for c in v}
        r["mask"] = {"old": len(mo), "new": len(mn), "identical": old["mask"][m] == new["mask"][m],
                     "removed": sorted(f"{list(p)} {mo[p]}" for p in mo.keys() - mn.keys()),
                     "added": sorted(f"{list(p)} {mn[p]}" for p in mn.keys() - mo.keys())}
        r["roof"] = {"old": len(old["roof"][m]["roof_cells"]), "new": len(new["roof"][m]["roof_cells"]), "identical": old["roof"][m] == new["roof"][m]}
        res[m] = r
    pk_old, pk_new = AR / "stage-24i/datapack", K / "derived-24i/datapack"
    files = {}
    for f in sorted(p.relative_to(pk_new) for p in pk_new.rglob("*") if p.is_file()):
        o = pk_old / f
        files[f.as_posix()] = "new" if not o.exists() else ("identical" if filecmp.cmp(o, pk_new / f, shallow=False) else "differs")
    for f in sorted(p.relative_to(pk_old) for p in pk_old.rglob("*") if p.is_file()):
        if not (pk_new / f).exists():
            files[f.as_posix()] = "removed"
    res["_pack_files_vs_stage24i"] = {k: v for k, v in files.items() if v != "identical"}
    res["_pack_files_identical"] = sum(1 for v in files.values() if v == "identical")
    return res


def write_inventory_with_roof():
    """Stage 24-G protected-cell inventory plus the Stage 24-I roof cells (the inventory the survival and replay checks use)."""
    inv = json.loads((K / "derived-24g/protection/protected-cells.json").read_text())
    roofs = json.loads((K / "derived-24i/roof/roof-cells.json").read_text())
    for m in MODULES:
        inv[m]["protected"] += [{"pos": e["pos"], "state": e["state"], "roles": ["roof"], "why": ["Stage 24-I roof over an enclosed room"],
                                 "rottable": True, "overlay": True} for e in roofs[m]["roof_cells"]]
        inv[m]["overlay"] += [{"pos": e["pos"], "state": e["state"]} for e in roofs[m]["roof_cells"]]
    p = K / "derived-24i/roof/protected-cells-with-roof.json"
    p.write_text(json.dumps(inv, indent=1) + "\n")
    return p


def main():
    src = assemble()
    derive()
    write_inventory_with_roof()
    d = diff_derived()
    (K / "DERIVATION-DIFF.json").write_text(json.dumps(d, indent=1) + "\n")
    for m in MODULES:
        print(m, "byte-identical to 24-F:", src[m]["byte_identical_to_stage24f"], "| protected", d[m]["protected_cells"]["old"], "->", d[m]["protected_cells"]["new"],
              "| mask", d[m]["mask"]["old"], "->", d[m]["mask"]["new"], "| roof", d[m]["roof"]["old"], "->", d[m]["roof"]["new"])
    print("pack files that differ from Stage 24-I:", d["_pack_files_vs_stage24i"])


if __name__ == "__main__":
    main()
