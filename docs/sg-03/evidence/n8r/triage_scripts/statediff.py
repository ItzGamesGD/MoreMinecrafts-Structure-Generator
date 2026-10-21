import json, sys
from collections import Counter
from pathlib import Path
N = Path("/home/user/MoreMinecrafts-Structure-Generator/validation/minecraft-visual/sg03-natural")
sys.path.insert(0, str(N))
from run_natural import STRUCT, inspect, ROT  # noqa
import assembly_probe as ap  # noqa
from world import World  # noqa
S = Path("/tmp/claude-0/-home-user-MoreMinecrafts-Structure-Generator/9b0fb163-9813-5d94-a639-ebb8df5b2921/scratchpad/n8r")
templates, _ = ap.load_pack(Path("/home/user/MoreMinecrafts-Structure-Generator/exports/sg-03/forgotten-underground-kingdom/datapack"))
sites = json.load(open(S / "det/vA/soak.json"))["sites"][:24]
for arm in ("vA", "vB", "control", "write"):
    w = World(S / "det" / arm / "region"); tot = Counter(); samples = []
    for cx, cz in sites:
        ch = w.chunk(cx, cz); start = ((ch.nbt.get("structures") or {}).get(STRUCT) if False else ((ch.nbt.get("structures") or {}).get("starts") or {}).get(STRUCT)) if ch else None
        if not start: continue
        for child in start["Children"]:
            name = child["pool_element"]["location"]
            if name not in templates or child.get("rotation") not in ROT: continue
            placed = ap.Placed(templates[name], ROT[child["rotation"]], tuple(child["BB"])[:3])
            for pos, exp in placed.blocks(include_air=False).items():
                act = w.state(*pos)
                if ap.state_matches(exp, act): continue
                tot["state_only" if exp["id"] == act["id"] else "id_change"] += 1
                if exp["id"] == act["id"] and len(samples) < 6: samples.append({"site": [cx, cz], "pos": list(pos), "piece": name.rsplit("/", 1)[-1], "expected": exp, "actual": act})
    print(arm, dict(tot)); [print("  ", json.dumps(s)) for s in samples]
