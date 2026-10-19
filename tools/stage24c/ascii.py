"""ASCII layer dumps of an NBT (debug/evidence)."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from tools.stage24c.common import *

SYM = {"air": ".", "ladder": "H", "jigsaw": "J", "water": "~", "soul_lantern": "L", "skeleton_skull": "S", "chest": "C",
       "barrel": "B", "bed": "b", "iron_door": "D", "oak_door": "D", "trapdoor": "T", "stairs": "^", "slab": "_", "fence": "|",
       "wall": "#", "campfire": "F", "furnace": "f", "stone_button": "o", "torch": "t"}

def sym(st):
    n = st.split("[")[0].replace("minecraft:", "")
    if n == "air": return "."
    if n.endswith("_stairs"): return "^"
    for k, v in SYM.items():
        if k in n: return v
    return "X"

def dump(m, root=None, ys=None):
    r = load_nbt((root or S24B) / m / "restored.nbt") if not hasattr(root, "keys") else root
    b = blocks_of(r); sx, sy, sz = (int(v) for v in r["size"])
    for y in (ys if ys is not None else range(sy)):
        print(f"--- {m} y={y}  (rows=z, cols=x)")
        for z in range(sz):
            print("".join(sym(b[(x, y, z)][0]) if (x, y, z) in b else " " for x in range(sx)))

if __name__ == "__main__":
    dump(sys.argv[1], ys=[int(a) for a in sys.argv[2:]] or None)
