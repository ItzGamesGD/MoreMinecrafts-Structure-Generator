#!/usr/bin/env python3
"""Read-only triage: classify cells inside piece boxes that differ between two worlds (24 det sites)."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
N = Path("/home/user/MoreMinecrafts-Structure-Generator/validation/minecraft-visual/sg03-natural")
sys.path.insert(0, str(N))
from run_natural import STRUCT, ROT  # noqa
import assembly_probe as ap  # noqa
from world import World  # noqa
S = Path("/tmp/claude-0/-home-user-MoreMinecrafts-Structure-Generator/9b0fb163-9813-5d94-a639-ebb8df5b2921/scratchpad/n8r")
PACK = Path("/home/user/MoreMinecrafts-Structure-Generator/exports/sg-03/forgotten-underground-kingdom/datapack")
templates, _ = ap.load_pack(PACK)
CRIT = ("trial_spawner", "vault", "chest", "barrel", "door", "spawner", "ominous", "lectern", "decorated_pot", "stairs", "ladder", "trapdoor", "button", "lever", "rail", "iron_bars")
def key(st): return st["id"]
def props(st): return {k: v for k, v in st.items() if k != "id"}
ref_name, oth_name = sys.argv[1], sys.argv[2]
ref, oth = World(S / "det" / ref_name / "region"), World(S / "det" / oth_name / "region")
sites = json.load(open(S / "det" / "vA" / "soak.json"))["sites"][:24]
by_piece, by_trans, by_exp, crit, state_only = Counter(), Counter(), Counter(), Counter(), Counter()
samples = defaultdict(list); per_site = {}
for cx, cz in sites:
    ch = ref.chunk(cx, cz); start = ((ch.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT) if ch else None
    if not start: continue
    n = 0
    for child in start["Children"]:
        name = child["pool_element"]["location"]; leaf = name.rsplit("/", 1)[-1]
        if name not in templates or child.get("rotation") not in ROT: continue
        placed = ap.Placed(templates[name], ROT[child["rotation"]], tuple(child["BB"])[:3])
        for pos, exp in placed.blocks(include_air=True).items():
            a, b = ref.state(*pos), oth.state(*pos)
            if a == b: continue
            n += 1
            kind = "state_only" if a["id"] == b["id"] else "id_change"
            by_piece[leaf] += 1; by_trans[(a["id"], b["id"])] += 1
            e = exp["id"]
            by_exp[("tmpl_air" if e in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air") else "tmpl_solid", "ref_matches" if ap.state_matches(exp, a) else "ref_differs", "oth_matches" if ap.state_matches(exp, b) else "oth_differs")] += 1
            if kind == "state_only": state_only[a["id"]] += 1
            direction = "vanilla_damaged" if (ap.state_matches(exp, b) and not ap.state_matches(exp, a)) else ("other_damaged" if (ap.state_matches(exp, a) and not ap.state_matches(exp, b)) else "both_differ")
            for c in CRIT:
                if c in a["id"] or c in b["id"] or c in e:
                    crit[(c, kind, direction)] += 1
            if leaf in ("tunnel_west", "residence_ruin") or "stairs" in e or "iron_bars" in e:
                if len(samples[("PATH", leaf, direction)]) < 6: samples[("PATH", leaf, direction)].append({"site": [cx, cz], "pos": list(pos), "tmpl": e, "ref": a["id"], "oth": b["id"]})
            if len(samples[(a["id"], b["id"])]) < 2: samples[(a["id"], b["id"])].append({"site": [cx, cz], "pos": list(pos), "piece": leaf, "tmpl": exp, "ref": a, "oth": b})
    per_site[f"{cx},{cz}"] = n
out = {"ref": ref_name, "other": oth_name, "total": sum(per_site.values()), "per_site": per_site,
       "by_piece": by_piece.most_common(), "by_transition": [[list(k), v] for k, v in by_trans.most_common(25)],
       "template_relation": [[list(k), v] for k, v in by_exp.most_common()], "state_only_by_block": state_only.most_common(15),
       "critical_ids": [[list(k), v] for k, v in sorted(crit.items())],
       "samples": [{"trans": list(k), "ex": v} for k, v in list(samples.items())]}
Path(S.parent / "triage" / f"boxdiff_{ref_name}_{oth_name}.json").write_text(json.dumps(out, indent=1, default=str))
print(ref_name, oth_name, "total", out["total"]); print("by_piece", out["by_piece"][:8]); print("trans", out["by_transition"][:8])
print("relation", out["template_relation"]); print("critical", out["critical_ids"]); print("state_only", out["state_only_by_block"][:6])
