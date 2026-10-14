#!/usr/bin/env python3
"""Three approved Ancient City candidates rebuilt in authentic Java 26.1.2 NBT.

Preserves all original jigsaw connectors and source block entity tags.
The candidate.nbt is the canonical output; preview .schem is visual only.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import nbtlib
from nbtlib import tag
from mcbuild.export.schem import export_schem
from mcbuild.palette import get_block, get_block_by_index
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid

from inspect_vanilla_ancient_nbt import load_template

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"out"/"ancient-city-followup"
MODULES=("barracks","ice_box_1","small_statue")
VIEWS=({"yaw":0},{"yaw":1},{"yaw":2},{"yaw":3})

def get_name(state):
    return str(state["Name"]).removeprefix("minecraft:")

def get_key(state):
    props=state.get("Properties")
    if not props:
        return str(state["Name"])
    return str(state["Name"])+"["+",".join(f"{k}={v}" for k,v in sorted(props.items()))+"]"

def state_from_key(key):
    if "[" in key:
        base, suffix=key.split("[",1)
        props=dict(piece.split("=",1) for piece in suffix.rstrip("]").split(","))
        return tag.Compound({"Name":tag.String("minecraft:"+base.removeprefix("minecraft:")),
                             "Properties":tag.Compound({k:tag.String(v) for k,v in props.items()})})
    return tag.Compound({"Name":tag.String("minecraft:"+key.removeprefix("minecraft:"))})

class Candidate:
    def __init__(self,name):
        self.name=name
        self.root,self.url,self.sha=load_template(name)
        self.size=tuple(int(i) for i in self.root["size"])
        self.palette=self.root["palette"]
        self.positions={tuple(map(int,b["pos"])):b for b in self.root["blocks"]}
        self.before={p:(get_key(self.palette[int(b["state"])]),str(b.get("nbt","")))
                     for p,b in self.positions.items()}
        self.indices={get_key(v):i for i,v in enumerate(self.palette)}
        self.original_ice=sum(1 for p in self.positions
                             if self.get(p) in ("ice","packed_ice","blue_ice"))
        self.protected={p for p in self.positions
                        if self.get(p) in ("jigsaw","chest","iron_trapdoor","ladder",
                                          "soul_fire","white_candle","note_block")}
        self.protected_snapshot={p:self.before[p] for p in self.protected}
        self.operations=Counter()

    def get(self,p):
        b=self.positions.get(tuple(p))
        return get_name(self.palette[int(b["state"])]) if b else "air"

    def set(self,x,y,z,key,category="placed",stock=None):
        p=(x,y,z)
        assert all(0<=v<hi for v,hi in zip(p,self.size)),(self.name,p,self.size)
        if p in self.protected:
            self.operations["protected_skipped"]+=1
            return False
        state=state_from_key(key)
        canonical=get_key(state)
        if canonical not in self.indices:
            self.indices[canonical]=len(self.palette)
            self.palette.append(state)
        index=self.indices[canonical]
        b=self.positions.get(p)
        if b is None:
            b=tag.Compound({"pos":tag.List[tag.Int](p),"state":tag.Int(index)})
            self.positions[p]=b
            self.root["blocks"].append(b)
        else:
            b["state"]=tag.Int(index)
            b.pop("nbt",None)
        if stock is not None:
            base=key.split("[",1)[0]
            assert base in ("barrel","chest")
            items=[tag.Compound({"Slot":tag.Byte(i),
                                 "id":tag.String("minecraft:"+item),
                                 "count":tag.Int(amount)})
                   for i,(item,amount) in enumerate(stock)]
            b["nbt"]=tag.Compound({"id":tag.String("minecraft:"+base),
                                   "Items":tag.List[tag.Compound](items)})
            self.operations["filled_food_or_equipment_containers"]+=1
        self.operations[category]+=1
        return True

    def carve(self,x,y,z):
        self.set(x,y,z,"air","carved")

    def verify(self):
        for p,original in self.protected_snapshot.items():
            b=self.positions[p]
            now=(get_key(self.palette[int(b["state"])]),str(b.get("nbt","")))
            assert now==original,(self.name,"Source connector or fixture changed",p)
        assert [int(v) for v in self.root["size"]]==list(self.size)
        assert sum(self.get(p)=="jigsaw" for p in self.protected)>=2
        if self.name=="barracks":
            assert self.get((8,4,8))=="spruce_trapdoor"
            for y in (1,2,3):assert self.get((8,y,8))=="ladder"
            assert self.get((10,3,10))=="jigsaw"
            assert self.get((4,4,15))==self.get((12,4,15))=="chest"
            assert self.get((4,1,5))=="barrel"
        elif self.name=="ice_box_1":
            assert self.get((11,4,4))=="iron_trapdoor"
            for y in (1,2,3):assert self.get((11,y,4))=="ladder"
            assert self.get((12,1,7))=="chest"
            ice_now=sum(self.get(p) in ("ice","packed_ice","blue_ice")
                        for p in self.positions)
            assert ice_now>=self.original_ice*0.8,(ice_now,self.original_ice)
            assert self.operations["filled_food_or_equipment_containers"]>=3
        elif self.name=="small_statue":
            assert all(get_key(self.palette[int(self.positions[p]["state"])])==a
                       for p,(a,_) in self.before.items())
            assert len(self.positions)-len(self.before)<=8

    def preview(self):
        grid=VoxelGrid()
        for p,b in self.positions.items():
            block=self.palette[int(b["state"])]
            if get_name(block) in ("air","jigsaw","structure_void"):
                continue
            grid.set(*p,get_block(get_key(block)).index)
        return grid

    def report(self):
        changed=sum(get_key(self.palette[int(self.positions[p]["state"])])!=before
                    for p,(before,_) in self.before.items())
        return {
            "module":self.name,"source":self.url,"source_git_blob_sha":self.sha,
            "dimensions_xyz":list(self.size),"original_count":len(self.before),
            "final_nbt_count":len(self.positions),"changed_original_positions":changed,
            "new_positions":len(self.positions)-len(self.before),
            "jigsaw_preserved":sum(self.get(p)=="jigsaw" for p in self.protected),
            "operations":dict(self.operations),
            "status":"NATIVE_NBT_CANDIDATE_PENDING_GAME_CLIENT_REVIEW",
        }

def barracks(r):
    assert r.size==(21,12,17)
    # y=4 upper surface; carve the *underground* at y=1..3 inside the source.
    for x in range(3,17):
        for z in range(3,14):
            for y in (1,2,3):r.carve(x,y,z)
            r.set(x,0,z,"polished_deepslate","basement_floor")
            if r.get((x,4,z))=="air":
                r.set(x,4,z,"deepslate_tiles","upper_ground_floor")
    # Four corner supports keep the original above-ground massing.
    for x in (3,16):
        for z in (3,13):
            for y in (1,2,3):
                r.set(x,y,z,"polished_basalt[axis=y]","supports")
    for x in range(4,16):
        for z in (3,13):r.set(x,1,z,"deepslate_bricks","wall_lining")
    for x,z,contents in (
        (4,5,[("iron_sword",3),("iron_axe",2),("shield",3)]),
        (5,5,[("bow",3),("crossbow",2),("arrow",64)]),
        (6,5,[("iron_helmet",2),("iron_chestplate",2)]),
        (14,11,[("iron_pickaxe",3),("iron_shovel",3)]),
        (15,11,[("iron_leggings",2),("iron_boots",2)]),
    ):
        r.set(x,1,z,"barrel[facing=up,open=false]","armory_storage",contents)
    for x,z,block in ((4,11,"smithing_table"),(5,11,"grindstone[face=floor,facing=north]"),
                      (6,11,"fletching_table"),(14,5,"anvil")):
        r.set(x,1,z,block,"armory_workstation")
    for x,z in ((5,9),(14,9)):
        r.set(x,3,z,"soul_lantern[hanging=true]","underground_light")
    # New one-block surface hatch/ladder into the new basement. No surface cellar.
    for y in (1,2,3):
        r.set(9,y,8,"deepslate_bricks","ladder_support")
        r.set(8,y,8,"ladder[facing=west]","basement_access")
    r.set(8,4,8,"spruce_trapdoor[facing=north,half=top,open=false,waterlogged=false]","hatch")
    # Modest courtyard armourer details (keep original shrines and chests).
    for x,z in ((5,4),(13,4)):
        r.set(x,5,z,"polished_deepslate_wall","upper_court_detail")
        r.set(x,6,z,"soul_lantern","upper_court_detail")
    r.set(11,5,5,"smithing_table","upper_workbench")
    r.set(12,5,5,"grindstone[face=floor,facing=north]","upper_workbench")

def ice_box(r):
    assert r.size==(19,10,15)
    # Interior pantry excavated next to ORIGINAL ladder (11,1..3,4).
    # Keep ice barriers, note blocks, original chest, hatch and all outer walls.
    for x in range(8,12):
        for z in range(6,11):
            for y in (1,2,3):r.carve(x,y,z)
            r.set(x,0,z,"polished_deepslate","pantry_floor")
    for z in range(5,10):
        for y in (1,2,3):r.carve(11,y,z)
    for x,z,contents in (
        (8,7,[("wheat",64),("wheat_seeds",32),("bread",16)]),
        (9,7,[("beef",32),("porkchop",24),("chicken",16)]),
        (10,7,[("mutton",24),("rabbit",8)]),
        (8,9,[("cod",32),("salmon",24)]),
        (9,9,[("potato",32),("carrot",32)]),
    ):
        r.set(x,1,z,"barrel[facing=up,open=false]","pantry_stock",contents)
    for x,z in ((8,6),(10,10)):
        r.set(x,3,z,"soul_lantern[hanging=true]","pantry_light")

    # Rebuild a compact roof over the cold pantry, without changing the
    # original exposed blue-ice blocks, access hatch or original jigsaws.
    for x in range(5,18):
        for z in range(1,14):
            rise=min(x-5,17-x)//3
            y=7+rise
            if r.get((x,y,z))=="air":
                facing="east" if x<=11 else "west"
                block="deepslate_tile_stairs[facing="+facing+",half=bottom]"
                r.set(x,y,z,block,"roof_restoration")
    for z in (2,12):
        for x in range(6,17):
            if r.get((x,6,z))=="air":
                r.set(x,6,z,"deepslate_bricks","upper_wall_restoration")
    for x,z in ((6,2),(16,2),(6,12),(16,12)):
        if r.get((x,5,z))=="air":
            r.set(x,5,z,"polished_basalt[axis=y]","roof_support")

def small_statue(r):
    assert r.size==(10,8,8)
    # No altered sculpture or candles: only fill two asymmetric corner gaps.
    for x,z in ((0,1),(0,6)):
        if r.get((x,1,z))=="air":
            r.set(x,1,z,"polished_deepslate","corner_restoration")

RESTORERS={"barracks":barracks,"ice_box_1":ice_box,"small_statue":small_statue}

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    reports=[]
    for name in MODULES:
        c=Candidate(name)
        RESTORERS[name](c)
        c.verify()
        out=OUTPUT/name
        out.mkdir(parents=True,exist_ok=True)
        c.root.save(out/"candidate.nbt",gzipped=True)
        reread=nbtlib.load(out/"candidate.nbt")
        assert [int(v) for v in reread["size"]]==list(c.size)
        assert len(reread["blocks"])==len(c.positions)
        grid=c.preview()
        assert len(grid)>100
        image,labels,stats=build_contact_sheet(grid,VIEWS)
        image.save(out/"render.png")
        export_schem(grid,str(out/"candidate.schem"))
        schem=nbtlib.load(out/"candidate.schem")["Schematic"]
        assert int(schem["Version"])==3
        report=c.report()
        report["preview_voxels"]=len(grid)
        report["views"]=labels
        report["render_stats"]=stats
        report["palette_counts"]=dict(Counter(get_block_by_index(i).mc_id for _,i in grid.items()))
        (out/"report.json").write_text(json.dumps(report,indent=2,default=str)+"\n")
        reports.append(report)
        print("OK",json.dumps({k:report[k] for k in (
            "module","dimensions_xyz","original_count","final_nbt_count",
            "changed_original_positions","new_positions","jigsaw_preserved","operations"
        )}),flush=True)
    (OUTPUT/"summary.json").write_text(json.dumps(reports,indent=2,default=str)+"\n")

if __name__=="__main__":
    main()
