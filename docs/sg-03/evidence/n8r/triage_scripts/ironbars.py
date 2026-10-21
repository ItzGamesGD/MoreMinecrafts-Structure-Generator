import json, sys
from pathlib import Path
N = Path("/home/user/MoreMinecrafts-Structure-Generator/validation/minecraft-visual/sg03-natural")
sys.path.insert(0, str(N))
from run_natural import STRUCT, ROT  # noqa
import assembly_probe as ap  # noqa
from world import World  # noqa
S = Path("/tmp/claude-0/-home-user-MoreMinecrafts-Structure-Generator/9b0fb163-9813-5d94-a639-ebb8df5b2921/scratchpad/n8/repro")
templates, _ = ap.load_pack(Path("/home/user/MoreMinecrafts-Structure-Generator/exports/sg-03/forgotten-underground-kingdom/datapack"))
w = World(S / "region")
for (cx, cz), pos in (((188, 52), (2949, -20, 841)), ((185, -90), (2901, -35, -1447)), ((522, -285), (8363, -33, -4573))):
    start = ((w.chunk(cx, cz).nbt.get("structures") or {}).get("starts") or {}).get(STRUCT)
    exp = None; inbox = []
    for child in start["Children"]:
        name = child["pool_element"]["location"]
        placed = ap.Placed(templates[name], ROT[child["rotation"]], tuple(child["BB"])[:3])
        blocks = placed.blocks(include_air=True)
        if pos in blocks: exp, owner, rot = blocks[pos], name.rsplit("/", 1)[-1], child["rotation"]; bb = child["BB"]
    act = w.state(*pos)
    print("SITE", (cx, cz), pos, owner, rot, "BB", bb)
    print("  expected", json.dumps(exp)); print("  actual  ", json.dumps(act))
    for label, d in (("N", (0, 0, -1)), ("S", (0, 0, 1)), ("W", (-1, 0, 0)), ("E", (1, 0, 0)), ("U", (0, 1, 0)), ("D", (0, -1, 0))):
        q = (pos[0] + d[0], pos[1] + d[1], pos[2] + d[2]); t = placed.blocks(include_air=True).get(q) if False else None
        # template expectation for neighbour from whichever piece contains it
        te = None
        for child in start["Children"]:
            nm = child["pool_element"]["location"]; pl = ap.Placed(templates[nm], ROT[child["rotation"]], tuple(child["BB"])[:3])
            b2 = pl.blocks(include_air=True)
            if q in b2: te = b2[q]
        a2 = w.state(*q)
        print(f"  {label} {q} expected={te['id'] if te else None} actual={a2['id']}", "" if (te and ap.state_matches(te, a2)) else "  <-- differs")
