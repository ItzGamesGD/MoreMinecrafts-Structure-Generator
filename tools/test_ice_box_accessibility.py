#!/usr/bin/env python3
"""Regression and delivery checks for the Ancient City ice box."""
from __future__ import annotations
from collections import deque
import ast
import subprocess
import json
import math
from pathlib import Path
from PIL import Image

import nbtlib
from mcbuild.export.schem import export_schem
from inspect_ice_box_accessibility import Candidate, Geometry, inspect
from render_approved_ancient_followup import get_key, get_name, ice_box

OUT=Path("out/ice-box-inspection")
BASE="7ffa4ec3877f585d4cb205ffed610c9b06a81910"

def state(c,p):
    b=c.positions.get(p)
    return c.palette[int(b["state"])] if b else None

def name(c,p):
    s=state(c,p)
    return get_name(s).removeprefix("minecraft:") if s else "air"

def props(c,p):
    s=state(c,p)
    return {str(k):str(v) for k,v in s.get("Properties",{}).items()} if s else {}

def redstone_model(c, plate_pressed: bool, lever_on: bool) -> bool:
    """Static vanilla-neighbor-power model; this does not run Minecraft redstone."""
    hatch=(11,4,4)
    plate=(11,5,5)
    plate_support=(11,4,5)
    lever=(11,3,3)
    lever_support=(11,4,3)
    plate_ok=(name(c,plate)=="stone_pressure_plate"
              and name(c,plate_support)=="polished_basalt"
              and sum(abs(a-b) for a,b in zip(plate_support,hatch))==1)
    lever_ok=(name(c,lever)=="lever"
              and props(c,lever).get("face")=="ceiling"
              and name(c,lever_support)=="deepslate_tiles"
              and sum(abs(a-b) for a,b in zip(lever_support,hatch))==1)
    assert name(c,hatch)=="iron_trapdoor"
    return (plate_pressed and plate_ok) or (lever_on and lever_ok)

def reachable_lever_position(c):
    g=Geometry(c)
    _,edges=g.graph(True)
    # Explicit BFS because a distance-reach node need not be the first goal.
    start=(11,1,4)
    if start not in edges:return []
    seen={start}; q=deque([start]); parent={start:None}; goal=None
    while q:
        p=q.popleft()
        eye=(p[0]+0.5,p[1]+1.62,p[2]+0.5)
        lever=(11.5,3.5,3.5)
        if math.dist(eye,lever)<=4.5:
            goal=p;break
        for n in edges[p]:
            if n not in seen:
                seen.add(n);parent[n]=p;q.append(n)
    route=[]
    while goal is not None:
        route.append(goal);goal=parent[goal]
    return list(reversed(route))

def main():
    source=Candidate("ice_box_1")
    source_snapshot=dict(source.before)
    source_jigsaws={p:v for p,v in source_snapshot.items()
                    if v[0].split("[",1)[0]=="minecraft:jigsaw"}
    source_ice={p:v for p,v in source_snapshot.items()
                if v[0].split("[",1)[0] in
                ("minecraft:ice","minecraft:packed_ice","minecraft:blue_ice")}
    source_contents={p:v for p,v in source_snapshot.items()
                     if v[0].split("[",1)[0] in ("minecraft:barrel","minecraft:chest")}

    # Reproduce the exact base-branch ice_box function as the before image.
    baseline_source=subprocess.check_output(
        ["git","show",f"{BASE}:tools/render_approved_ancient_followup.py"],text=True)
    tree=ast.parse(baseline_source)
    old_function=next(n for n in tree.body
                      if isinstance(n,ast.FunctionDef) and n.name=="ice_box")
    namespace={}
    exec(compile(ast.fix_missing_locations(ast.Module(
        body=[old_function],type_ignores=[])), "<base ice_box>", "exec"),namespace)
    broken=Candidate("ice_box_1")
    namespace["ice_box"](broken)
    baseline_containers={
        p:(get_key(broken.palette[int(b["state"])]),str(b.get("nbt","")))
        for p,b in broken.positions.items()
        if get_key(broken.palette[int(b["state"])]).split("[",1)[0]
           in ("minecraft:barrel","minecraft:chest")
    }
    before=inspect(broken,"before-repair")
    assert not before["checks"]["ladder_support"], before["checks"]
    assert not before["checks"]["surface_boundary_to_ladder_open_hatch"], before["checks"]

    c=Candidate("ice_box_1")
    ice_box(c)
    candidate_containers={
        p:(get_key(c.palette[int(b["state"])]),str(b.get("nbt","")))
        for p,b in c.positions.items()
        if get_key(c.palette[int(b["state"])]).split("[",1)[0]
           in ("minecraft:barrel","minecraft:chest")
    }
    assert candidate_containers==baseline_containers,(
        "food container positions, states, or block entities changed",
        baseline_containers,candidate_containers)
    c.verify()
    result=inspect(c,"repaired-candidate")

    # Candidate invariants: dimensions, exact jigsaw and protected fixtures,
    # every original ice state and original food-storage block entity survive.
    assert c.size==(19,10,15)
    assert len(source_jigsaws)==3
    assert all(c.before[p]==v for p,v in source_jigsaws.items())
    assert all((get_key(c.palette[int(c.positions[p]["state"])]),
                str(c.positions[p].get("nbt","")))==v
               for p,v in c.protected_snapshot.items())
    assert all((get_key(c.palette[int(c.positions[p]["state"])]),
                str(c.positions[p].get("nbt","")))==v
               for p,v in source_ice.items())
    assert all((get_key(c.palette[int(c.positions[p]["state"])]),
                str(c.positions[p].get("nbt","")))==v
               for p,v in source_contents.items())

    # Ladder support, unblocked turn into x=10, and continuous player-sized route.
    assert result["checks"]["ladder_support"], result["ladder"]
    assert all(c.get((11,y,5))=="polished_basalt" for y in (1,2,3))
    west_route=[(11,1,4),(10,1,4),(10,1,5),(10,1,6),(11,1,6)]
    g=Geometry(c)
    assert all(g.node(p,True) for p in west_route),west_route
    east=result["approaches"]["east"]
    assert east["closed_hatch_surface_path"], "East surface approach to closed hatch is blocked"
    assert east["open_hatch_to_ladder_path"], "Open hatch to supported ladder route is blocked"
    assert result["checks"]["surface_boundary_to_ladder_open_hatch"]
    assert result["checks"]["all_container_sides_reachable"]

    # The original iron hatch remains, with operable original controls. This is
    # a static neighbor-power simulation, not an MC redstone/client simulation.
    assert c.get((11,4,4))=="iron_trapdoor"
    assert name(c,(11,5,5))=="stone_pressure_plate"
    assert name(c,(11,3,3))=="lever"
    states={(False,False):False,(True,False):True,
            (False,True):True,(True,True):True}
    assert all(redstone_model(c,p,l)==opened
               for (p,l),opened in states.items())
    assert result["approaches"]["east"]["reached"]
    assert reachable_lever_position(c), "No basement route to a lever-use position"

    # Distinctive restrained threshold, cold accents and side lighting.
    for x in (10,12):
        assert c.get((x,5,4))=="deepslate_bricks"
        assert c.get((x,6,4))=="blue_ice"
        assert c.get((x,5,5))=="soul_lantern"
    assert result["checks"]["hatch_above_clear"]

    # Side-by-side renders use the exact base function and repaired function.
    before_image=Image.open(OUT/"before-repair"/"exterior-four-directions.png").convert("RGB")
    after_image=Image.open(OUT/"repaired-candidate"/"exterior-four-directions.png").convert("RGB")
    comparison=Image.new("RGB",(before_image.width+after_image.width,before_image.height),(24,24,28))
    comparison.paste(before_image,(0,0));comparison.paste(after_image,(before_image.width,0))
    comparison.save(OUT/"before-after-exterior.png")

    # Export native NBT and visual schematic, then reload both.
    out=OUT/"repaired-candidate"
    out.mkdir(parents=True,exist_ok=True)
    c.root.save(out/"candidate.nbt",gzipped=True)
    reread=nbtlib.load(out/"candidate.nbt")
    assert reread==c.root
    grid=c.preview()
    export_schem(grid,str(out/"candidate.schem"))
    schem=nbtlib.load(out/"candidate.schem")["Schematic"]
    assert int(schem["Version"])==3

    summary={
        "status":"REPAIRED_CANDIDATE_STATIC_VALIDATION_PASSED",
        "dimensions_xyz":list(c.size),
        "jigsaws_preserved":len(source_jigsaws),
        "original_ice_positions_preserved":len(source_ice),
        "original_container_positions_and_nbt_preserved":len(source_contents),
        "candidate_food_container_count_and_nbt_preserved":len(baseline_containers),
        "original_iron_trapdoor_preserved":True,
        "ladder_support_positions":[[11,y,5] for y in (1,2,3)],
        "west_passage":west_route,
        "surface_to_hatch":east["closed_hatch_surface_path"],
        "surface_through_open_hatch_to_ladder":east["open_hatch_to_ladder_path"],
        "container_access":result["containers"],
        "controls":{
            "surface_pressure_plate":[11,5,5],
            "plate_power_block":[11,4,5],
            "inside_lever":[11,3,3],
            "lever_power_block":[11,4,3],
            "hatch":[11,4,4],
            "signal_state_simulation":{f"plate={p},lever={l}":redstone_model(c,p,l)
                                       for p,l in states},
            "inside_lever_use_route":reachable_lever_position(c),
            "classification":"static vanilla adjacency model and geometry-based reach distance; no in-game interaction",
        },
        "entrance_markers":[
            {"pos":[x,5,4],"block":"deepslate_bricks"} for x in (10,12)
        ]+[{"pos":[x,6,4],"block":"blue_ice"} for x in (10,12)]
         +[{"pos":[x,5,5],"block":"soul_lantern"} for x in (10,12)],
        "actual_minecraft_client_gameplay":"NOT TESTED",
        "before_repair_checks":before["checks"],
        "automated_checks":result["checks"],
    }
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    lines=["# ice_box_1 repair validation","",
           "Static geometry and redstone adjacency checks; actual Minecraft gameplay NOT TESTED.","",
           "| Check | Result |","|---|---|"]
    lines += [f"| {k} | {'PASS' if v else 'FAIL'} |"
              for k,v in result["checks"].items()]
    lines += ["| Iron hatch signal states | PASS (static model) |",
              "| NBT export and reload | PASS |",
              "| Sponge v3 schematic export and reload | PASS |",
              "| Client survival interactions | NOT TESTED |"]
    (OUT/"README.md").write_text("\n".join(lines)+"\n")
    print("ICE_BOX_REPAIR_SUMMARY="+json.dumps(summary,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
