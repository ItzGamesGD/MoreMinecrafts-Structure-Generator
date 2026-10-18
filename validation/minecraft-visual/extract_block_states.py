#!/usr/bin/env python3
"""Compact the Minecraft 26.3 data-generator ``blocks.json`` report into block-states-26.3.json.

Regenerate the source report with:
  java -DbundlerMainClass=net.minecraft.data.Main -jar server.jar --reports --output out
and run:  extract_block_states.py out/reports/blocks.json block-states-26.3.json
Each entry: {"properties": {name: [values...]}, "default": {name: value}} (no entry for blocks without states).
"""
import json
import sys

report = json.load(open(sys.argv[1]))
compact = {}
for block_id, data in sorted(report.items()):
    props = data.get("properties", {})
    default = next((s.get("properties", {}) for s in data["states"] if s.get("default")), {})
    compact[block_id] = {"properties": props, "default": default} if props else {}
with open(sys.argv[2], "w") as out:
    json.dump(compact, out, separators=(",", ":"), sort_keys=True)
    out.write("\n")
print(f"{len(compact)} blocks -> {sys.argv[2]}")
