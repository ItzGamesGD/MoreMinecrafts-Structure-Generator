#!/usr/bin/env python3
"""Read-only ice_box_1 diagnostics. No Minecraft client or physics engine."""
from __future__ import annotations
from collections import deque
import hashlib
import json
import os
from pathlib import Path

import nbtlib
from mcbuild.render.views import build_contact_sheet
from mcbuild.export.schem import export_schem
from render_approved_ancient_followup import Candidate, ice_box, get_key, get_name

OUT = Path("out/ice-box-inspection")
DIRECTIONS = {"north": (0,0,-1), "south": (0,0,1),
              "west": (-1,0,0), "east": (1,0,0)}
HATCH = (11,4,4)
BASE = "7ffa4ec3877f585d4cb205ffed610c9b06a81910"
FULL = {"deepslate", "cobbled_deepslate", "polished_deepslate",
        "deepslate_bricks", "deepslate_tiles", "cracked_deepslate_bricks",
        "cracked_deepslate_tiles", "chiseled_deepslate", "reinforced_deepslate",
        "ice", "blue_ice", "packed_ice", "polished_basalt", "basalt",
        "smooth_basalt", "stone", "barrel", "note_block",
        "soul_soil"}
AIR = {"air", "cave_air", "void_air", "structure_void"}
# These fixtures have no entity collision; their presence is NOT activation proof.
NO_COLLISION = {"stone_pressure_plate", "lever"}

def plain(value):
    if isinstance(value, dict):
        return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)) or hasattr(value, "tolist"):
        return [plain(v) for v in value]
    if isinstance(value, str):
        return str(value)
    if isinstance(value, (int, float)):
        return int(value) if isinstance(value,int) else float(value)
    return str(value)

def dump(path, data):
    (OUT/path).write_text(json.dumps(data, indent=2, default=plain)+"\n")

def add(a,b):
    return tuple(x+y for x,y in zip(a,b))

class Geometry:
    """Conservative centered 0.6-wide, two-cell-high route model.
    Partial blocks other than ladders/open hatch and known non-colliding
    pressure plates/levers are conservatively obstacles. No jumping,
    swimming, crouching, diagonal corner cutting or external terrain assumed.
    Failed conservative paths are not a proof that all Minecraft routes fail.
    """
    def __init__(self, c):
        self.c = c
        self.size = c.size
        self.blocks = {p:plain(c.palette[int(b["state"])])
                       for p,b in c.positions.items()}
    def inside(self,p):
        return all(0<=v<s for v,s in zip(p,self.size))
    def state(self,p):
        state = self.blocks.get(p, {"Name":"minecraft:air"})
        if state["Name"] == "minecraft:jigsaw":
            # Use placed final state for geometry, retain original metadata below.
            final = str(self.c.positions[p].get("nbt",{}).get("final_state",""))
            if final:
                name = final.split("[",1)[0]
                return {"Name":name, "unparsed_final_state":final}
        return state
    def name(self,p):
        return self.state(p)["Name"].removeprefix("minecraft:")
    def props(self,p):
        return self.state(p).get("Properties",{})
    def clear(self,p,opened=False):
        if not self.inside(p):
            return False
        name = self.name(p)
        return (name in AIR or name in NO_COLLISION or name == "ladder" or
                (p==HATCH and opened))
    def blockers(self,p,opened=False):
        return [{"pos":q,"state":self.state(q)} for q in (p,add(p,(0,1,0)))
                if not self.clear(q,opened)]
    def ladder_valid(self,p):
        facing = self.props(p).get("facing")
        delta = DIRECTIONS.get(facing)
        support = add(p,tuple(-v for v in delta)) if delta else None
        return {"pos":p,"facing":facing,"support":support,
                "support_state":self.state(support) if support else None,
                "pass":bool(support and self.name(support) in FULL)}
    def node(self,p,opened):
        if self.blockers(p,opened):
            return False
        below = add(p,(0,-1,0))
        climb = (self.name(p)=="ladder" and self.ladder_valid(p)["pass"])
        hatch_climb = opened and p in (HATCH,add(HATCH,(0,1,0)))
        floor = self.name(below) in FULL or (below==HATCH and not opened)
        return climb or hatch_climb or floor
    def graph(self,opened):
        nodes = {(x,y,z) for x in range(self.size[0])
                 for y in range(self.size[1]-1) for z in range(self.size[2])
                 if self.node((x,y,z),opened)}
        edges = {}
        for p in nodes:
            near = [add(p,d) for d in DIRECTIONS.values()]
            # Vertical edges only inside supported ladder/hatch shaft.
            if p[0]==11 and p[2]==4:
                near += [add(p,(0,-1,0)),add(p,(0,1,0))]
            edges[p] = [q for q in near if q in nodes]
        return nodes, edges
    def search(self,start,edges,goals):
        parents = {p:None for p in start if p in edges}
        queue = deque(parents)
        end = None
        while queue:
            p = queue.popleft()
            if p in goals:
                end=p
                break
            for q in edges[p]:
                if q not in parents:
                    parents[q]=p
                    queue.append(q)
        path=[]
        while end is not None:
            path.append(end)
            end=parents[end]
        return list(reversed(path)), list(parents)

def snapshot(c):
    return {p:(get_key(c.palette[int(b["state"])]),plain(b.get("nbt",{})))
            for p,b in c.positions.items()}

def inspect(c,label):
    folder=OUT/label
    folder.mkdir(parents=True,exist_ok=True)
    g=Geometry(c)
    jigsaws=[{"pos":p,"state":plain(c.palette[int(b["state"])]),
              "nbt":plain(b.get("nbt",{}))}
             for p,b in c.positions.items() if c.get(p)=="jigsaw"]
    dump(Path(label)/"coordinate-map.json",{
        "size_xyz":c.size,"axis_convention":"+x=east,+z=south,+y=up; local unrotated",
        "blocks":[{"pos":p,"state":plain(c.palette[int(b["state"])]),
                   "nbt":plain(b.get("nbt",{}))}
                  for p,b in sorted(c.positions.items())],
        "missing_positions":"air in this template; external world terrain unknown",
        "jigsaws":jigsaws})
    ladder=[g.ladder_valid((11,y,4)) for y in (1,2,3)]
    results={"module":label,"jigsaws":jigsaws,"ladder":ladder,
             "trapdoor":{"pos":HATCH,"state":g.state(HATCH),
                         "opening_above_blockers":g.blockers((11,5,4)),
                         "iron_requires_redstone":True,
                         "activation_verified":False},
             "checks":{},"approaches":{}}
    containers=[p for p,b in c.positions.items()
                if c.get(p) in ("barrel","chest")]
    opened_nodes,opened_edges=g.graph(True)
    _,closed_edges=g.graph(False)
    container_access=[]
    for p in containers:
        adjacent=[add(p,d) for d in DIRECTIONS.values()]
        path,_=g.search([(11,1,4)],opened_edges,set(adjacent))
        container_access.append({"pos":p,"state":g.state(p),
            "inventory":plain(c.positions[p].get("nbt",{})),
            "adjacent_standing_positions":[q for q in adjacent if q in opened_nodes],
            "ladder_to_container_path":path,
            "lid_above":g.state(add(p,(0,1,0))),
            "pass":bool(path)})
    results["containers"]=container_access
    results["activation_fixtures"]=[{"pos":p,"state":g.state(p)}
        for p in c.positions if g.name(p) in NO_COLLISION]
    for face in DIRECTIONS:
        # Surface y=4 top => feet y=5; boundary sampling is explicit, not
        # evidence that a city street actually exists outside that boundary.
        boundary=[(x,5,z) for x in range(c.size[0]) for z in range(c.size[2])
                  if ((face=="north" and z==0) or (face=="south" and z==c.size[2]-1)
                      or (face=="west" and x==0) or (face=="east" and x==c.size[0]-1))]
        path,visited=g.search(boundary,opened_edges,{(11,1,4)})
        closed_path,_=g.search(boundary,closed_edges,{(11,5,4)})
        frontier=[]
        for p in visited:
            for d in DIRECTIONS.values():
                q=add(p,d)
                if g.inside(q) and q not in opened_nodes:
                    frontier.append({"from":p,"to":q,
                        "body_blockers":g.blockers(q,True),
                        "floor_state":g.state(add(q,(0,-1,0)))})
        results["approaches"][face]={"sampled_boundary_feet":boundary,
            "valid_starts":[p for p in boundary if p in opened_nodes],
            "closed_hatch_surface_path":closed_path,
            "open_hatch_to_ladder_path":path,
            "pass":bool(path),"reached":visited,"blocked_frontier":frontier}
    corridor=[(11,1,z) for z in range(4,11)]
    results["ladder_to_pantry_probe"]=[
        {"feet":p,"body_blockers":g.blockers(p,True),
         "floor_state":g.state(add(p,(0,-1,0))),"pass":g.node(p,True)}
        for p in corridor]
    results["entrance_direction_analysis"]={
        "street_face":"UNCONFIRMED: requires adjacent street template/placement context",
        "connector_evidence":jigsaws,
        "rule":"Jigsaw orientation and final_state are evidence, not a walkable street.",
        "surface_boundary_feet_y":5,
        "geometrically_reachable_faces":[f for f,v in results["approaches"].items() if v["pass"]]}
    results["checks"]={
        "dimensions_19_10_15":c.size==(19,10,15),
        "ladder_support":all(x["pass"] for x in ladder),
        "hatch_above_clear":not g.blockers((11,5,4)),
        "ladder_to_pantry_probe":all(g.node(p,True) for p in corridor),
        "surface_boundary_to_ladder_open_hatch":any(v["pass"] for v in results["approaches"].values()),
        "all_container_sides_reachable":all(v["pass"] for v in container_access),
        "iron_hatch_activation_verified":False}
    dump(Path(label)/"accessibility.json",results)
    c.root.save(folder/"inspection-snapshot.nbt",gzipped=True)
    reloaded=nbtlib.load(folder/"inspection-snapshot.nbt")
    assert reloaded==c.root, "NBT round trip changed data"
    grid=c.preview()
    export_schem(grid,str(folder/"visual-only.schem"))
    assert int(nbtlib.load(folder/"visual-only.schem")["Schematic"]["Version"])==3
    views=[{"yaw":i} for i in range(4)]
    for filename,rendergrid,specs in (
        ("exterior-four-directions.png",grid,views),
        ("top-down-roof.png",grid,[{"mode":"top-down"}])):
        img,labels,_=build_contact_sheet(rendergrid,specs)
        img.save(folder/filename)
    cutaway=grid.clone()
    detail=grid.clone()
    for (x,y,z),_ in list(grid.items()):
        if y>=4:
            cutaway.clear_block(x,y,z)
        if not (8<=x<=14 and 1<=z<=7):
            detail.clear_block(x,y,z)
    img,_,_=build_contact_sheet(cutaway,views)
    img.save(folder/"underground-cutaway.png")
    img,_,_=build_contact_sheet(detail,views)
    img.save(folder/"entrance-closeup.png")
    approach=grid.clone()
    for (x,y,z),_ in list(grid.items()):
        if y>=5:
            approach.clear_block(x,y,z)
    img,_,_=build_contact_sheet(approach,[{"mode":"top-down"}])
    img.save(folder/"top-down-surface-y4.png")
    return results

def model_self_test():
    # Algorithm checks only. Never described as Minecraft player-input testing.
    class Fixture:
        size=(19,10,15)
        positions={}
    g=Geometry(Fixture())
    g.blocks={(11,4,5):{"Name":"minecraft:polished_basalt"},
              (11,5,5):{"Name":"minecraft:stone_pressure_plate"}}
    assert g.node((11,5,5),False), "Pressure plates have no entity collision"
    g.blocks[(11,6,5)]={"Name":"minecraft:deepslate"}
    assert not g.node((11,5,5),False), "A full head obstruction must fail"
    g.blocks={(11,2,4):{"Name":"minecraft:ladder","Properties":{"facing":"north"}},
              (11,2,5):{"Name":"minecraft:deepslate"}}
    assert g.ladder_valid((11,2,4))["pass"]
    g.blocks.pop((11,2,5))
    assert not g.ladder_valid((11,2,4))["pass"], "Unsupported ladder must fail"
    g.blocks={HATCH:{"Name":"minecraft:iron_trapdoor"}}
    assert not g.clear(HATCH,False) and g.clear(HATCH,True)
    print("GEOMETRY_MODEL_SELF_TESTS=PASS (synthetic algorithm checks only)",flush=True)

def main():
    model_self_test()
    OUT.mkdir(parents=True,exist_ok=True)
    c=Candidate("ice_box_1")
    original=snapshot(c)
    inspect(c,"vanilla")
    # Reproduce ONLY the existing approved candidate, without new repairs.
    ice_box(c)
    c.verify()
    existing=inspect(c,"existing-candidate")
    original_jigsaws={p:v for p,v in original.items()
                      if v[0].split("[")[0]=="minecraft:jigsaw"}
    now=snapshot(c)
    assert all(now[p]==v for p,v in original_jigsaws.items())
    ice_positions=[p for p,v in original.items()
                   if v[0].split("[")[0] in ("minecraft:ice","minecraft:blue_ice","minecraft:packed_ice")]
    retained=[p for p in ice_positions if now[p]==original[p]]
    assert len(retained)>=0.8*len(ice_positions)
    report={
        "status":"INSPECTION_ONLY_PENDING_REVIEW",
        "base_sha":BASE,"inspection_commit":os.environ.get("GITHUB_SHA"),
        "source_url":c.url,"source_git_blob_sha":c.sha,
        "generator_sha256":hashlib.sha256(Path("tools/render_approved_ancient_followup.py").read_bytes()).hexdigest(),
        "jigsaws_unchanged":True,"ice_retained":len(retained),"ice_original":len(ice_positions),
        "candidate_reproduction":"Unchanged ice_box(Candidate('ice_box_1')); no barracks/small_statue calls",
        "geometry_model":Geometry.__doc__,
        "limitations":["No actual Minecraft client/player input.",
            "No external terrain or city placement/rotation verified.",
            "Conservative integer-height routes; partial shapes and stepping/jumping unresolved.",
            "Open hatch evaluated conditionally; no redstone circuit simulation.",
            "Barrel access means adjacent standing space; inventory interaction not tested.",
            "Cutaways are render copies, never structural edits."],
        "checks":existing["checks"]}
    dump(Path("summary.json"),report)
    lines=["# ice_box_1 inspection only","",
        "Automated geometry diagnostics; no Minecraft-client verification.",
        "The vanilla and existing candidate are compared, not a repaired before/after.",
        "","| Check | Result |","|---|---|"]
    lines += [f"| {key} | {'PASS' if value else 'FAIL / UNVERIFIED'} |"
              for key,value in existing["checks"].items()]
    (OUT/"README.md").write_text("\n".join(lines)+"\n")
    print("ICE_BOX_INSPECTION_SUMMARY="+json.dumps(report),flush=True)
    print("ICE_BOX_LADDER="+json.dumps(existing["ladder"]),flush=True)
    print("ICE_BOX_CORRIDOR="+json.dumps(existing["ladder_to_pantry_probe"]),flush=True)
    print("ICE_BOX_HATCH="+json.dumps(existing["trapdoor"]),flush=True)
    print("ICE_BOX_CONTROLS="+json.dumps(existing["activation_fixtures"]),flush=True)
    print("ICE_BOX_SURFACE_PATHS="+json.dumps({f:v["closed_hatch_surface_path"]
          for f,v in existing["approaches"].items()}),flush=True)
    print("ICE_BOX_APPROACHES="+json.dumps({f:{"pass":v["pass"],
          "valid_starts":v["valid_starts"],"path":v["open_hatch_to_ladder_path"]}
          for f,v in existing["approaches"].items()}),flush=True)
    # Keep geometry failures visible after artifacts exist. Redstone activation
    # remains explicitly unverified, rather than manufacturing a physics result.
    geometry_checks={k:v for k,v in existing["checks"].items()
                     if k!="iron_hatch_activation_verified"}
    assert all(geometry_checks.values()), "Geometry accessibility incomplete; review artifacts; do not repair in this PR"

if __name__=="__main__":
    main()
