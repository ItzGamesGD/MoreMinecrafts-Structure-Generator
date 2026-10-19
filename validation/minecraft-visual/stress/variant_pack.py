#!/usr/bin/env python3
"""Copy the SG-01 datapack and change only the structure's generation ``step`` (experiment tool for SG-01-C F-2)."""
import argparse
import json
import shutil
from pathlib import Path

STEPS = ["raw_generation", "lakes", "local_modifications", "underground_structures", "surface_structures", "strongholds",
         "underground_ores", "underground_decoration", "fluid_springs", "vegetal_decoration", "top_layer_modification"]

p = argparse.ArgumentParser()
p.add_argument("--pack", type=Path, required=True)
p.add_argument("--step", choices=STEPS, required=True)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
shutil.rmtree(a.out, ignore_errors=True)
shutil.copytree(a.pack, a.out)
f = a.out / "data/moreminecrafts/worldgen/structure/forgotten_kingdom/central_cavern.json"
d = json.loads(f.read_text())
d["step"] = a.step
f.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
print(a.step, "index", STEPS.index(a.step))
