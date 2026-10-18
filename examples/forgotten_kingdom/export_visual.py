#!/usr/bin/env python3
"""Build a deterministic GLB and block-data-derived preview images from SG-01 NBT."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from structure_export.jigsaw import rotate_position
from structure_export.nbt import read_nbt

PACK = ROOT / "exports/sg-01/forgotten-underground-kingdom/datapack"
OUT = ROOT / "exports/sg-01/forgotten-underground-kingdom/visual"
BASE = "moreminecrafts:forgotten_kingdom/central_cavern"
DIRECTIONS = ("north", "east", "south", "west")
FACE_VECTORS = {"north": (0, 0, -1), "east": (1, 0, 0), "south": (0, 0, 1), "west": (-1, 0, 0)}
CONNECTORS = {
    "north": ((20, 1, 0), (2, 1, 14)),
    "east": ((40, 1, 20), (0, 1, 2)),
    "south": ((20, 1, 40), (2, 1, 0)),
    "west": ((0, 1, 20), (14, 1, 2)),
}
# Textures are copied from the vendored mcbuild vanilla texture set. Unavailable
# block variants use the closest named vanilla base texture below.
TEXTURE_ALIASES = {
    "deepslate_brick_wall": "deepslate_bricks",
    "stone_brick_stairs": "stone_bricks",
    "sea_lantern": "sea_lantern",
}
BLOCK_RGB = {
    "chiseled_tuff_bricks": (132, 125, 111),
    "deepslate_brick_wall": (74, 74, 78),
    "deepslate_bricks": (86, 85, 89),
    "deepslate_tiles": (67, 68, 74),
    "polished_deepslate": (78, 78, 83),
    "polished_deepslate_stairs": (78, 78, 83),
    "sea_lantern": (156, 221, 207),
    "stone_brick_stairs": (122, 120, 115),
    "tuff_bricks": (123, 116, 103),
}


def _load_templates() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    result, hashes = {}, {}
    for name in ("main_chamber", *(f"tunnel_{d}" for d in DIRECTIONS)):
        path = PACK / f"data/moreminecrafts/structure/forgotten_kingdom/central_cavern/{name}.nbt"
        raw = path.read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        result[name] = read_nbt(raw)["value"]
    return result, hashes


def _state(entry: dict[str, Any]) -> tuple[str, dict[str, str]]:
    return entry["id"].split(":", 1)[-1], entry.get("properties", {})


def _assembled_blocks(templates: dict[str, dict[str, Any]]) -> tuple[dict[tuple[int, int, int], tuple[str, dict[str, str]]], dict[str, Any]]:
    room = templates["main_chamber"]
    transforms = {"main_chamber": (0, 0, 0)}
    for direction, (parent_pos, child_pos) in CONNECTORS.items():
        # These four joins are authored without rotation. As in vanilla jigsaw assembly the child
        # connector sits in the cell in front of the parent connector, so tunnels are adjacent
        # to the chamber and never overlap it.
        front = FACE_VECTORS[direction]
        origin = tuple(parent_pos[i] + front[i] - child_pos[i] for i in range(3))
        transforms[f"tunnel_{direction}"] = origin
    blocks: dict[tuple[int, int, int], tuple[str, dict[str, str]]] = {}
    counts = Counter()
    for template_name, template in templates.items():
        origin = transforms[template_name]
        for block in template["blocks"]:
            state_name, props = _state(template["palette"][block["state"]])
            if state_name in {"air", "jigsaw"}:
                continue
            pos = tuple(block["pos"][i] + origin[i] for i in range(3))
            if pos in blocks:
                raise ValueError(f"Unexpected overlap between assembled templates at {pos}")
            blocks[pos] = (state_name, props)
            counts[state_name] += 1
    seam_report = {}
    for direction, (parent_pos, child_pos) in CONNECTORS.items():
        origin = transforms[f"tunnel_{direction}"]
        child_world = tuple(origin[i] + child_pos[i] for i in range(3))
        expected_child = tuple(parent_pos[i] + FACE_VECTORS[direction][i] for i in range(3))
        if child_world != expected_child:
            raise ValueError(f"{direction} connector seam mismatch: {expected_child} != {child_world}")
        seam_report[direction] = {"room_connector": list(parent_pos), "tunnel_connector_world": list(child_world),
                                  "tunnel_origin": list(origin), "rotation": "none"}
    return blocks, {"transforms": {k: list(v) for k, v in transforms.items()}, "seams": seam_report,
                    "block_counts": dict(sorted(counts.items()))}


def _texture_name(name: str) -> str:
    return TEXTURE_ALIASES.get(name, name)


def _build_atlas(material_names: list[str]) -> tuple[Image.Image, dict[str, tuple[float, float, float, float]], dict[str, str]]:
    tile, cols = 16, 4
    rows = math.ceil(len(material_names) / cols)
    atlas = Image.new("RGBA", (cols * tile, rows * tile), (128, 128, 128, 255))
    uv, used = {}, {}
    texture_dir = ROOT / "vendor/mcbuild/src/mcbuild/assets/textures/block"
    for idx, name in enumerate(material_names):
        candidate = texture_dir / f"{_texture_name(name)}.png"
        if not candidate.exists():
            candidate = texture_dir / "stone.png"
        if candidate.exists():
            im = Image.open(candidate).convert("RGBA").resize((tile, tile), Image.Resampling.NEAREST)
            used[name] = candidate.name
        else:
            im = Image.new("RGBA", (tile, tile), (*BLOCK_RGB.get(name, (128, 128, 128)), 255))
            used[name] = "flat-color fallback"
        col, row = idx % cols, idx // cols
        atlas.paste(im, (col * tile, row * tile))
        uv[name] = ((col * tile + 0.5) / atlas.width, (row * tile + 0.5) / atlas.height,
                    (col * tile + tile - 0.5) / atlas.width, (row * tile + tile - 0.5) / atlas.height)
    return atlas, uv, used


def _boxes_for_block(pos: tuple[int, int, int], name: str, props: dict[str, str], blocks: dict[tuple[int,int,int], tuple[str,dict[str,str]]]):
    x, y, z = pos
    if name == "stone_brick_stairs":
        facing = props.get("facing", "north")
        if facing == "north": hi = (x, y + 0.5, z + 0.5, x + 1, y + 1, z + 1)
        elif facing == "south": hi = (x, y + 0.5, z, x + 1, y + 1, z + 0.5)
        elif facing == "east": hi = (x, y + 0.5, z, x + 0.5, y + 1, z + 1)
        else: hi = (x + 0.5, y + 0.5, z, x + 1, y + 1, z + 1)
        return [(x,y,z,x+1,y+0.5,z+1), hi]
    if name == "deepslate_brick_wall":
        # Vanilla wall-like post with connected arms inferred from adjacent wall blocks.
        boxes = [(x+0.25,y,z+0.25,x+0.75,y+0.875,z+0.75)]
        for d, (dx,dz) in {"north":(0,-1),"south":(0,1),"west":(-1,0),"east":(1,0)}.items():
            neighbor = blocks.get((x+dx,y,z+dz))
            if neighbor and neighbor[0] == name:
                if d == "north": boxes.append((x+0.25,y+0.25,z,x+0.75,y+0.75,z+0.5))
                elif d == "south": boxes.append((x+0.25,y+0.25,z+0.5,x+0.75,y+0.75,z+1))
                elif d == "west": boxes.append((x,y+0.25,z+0.25,x+0.5,y+0.75,z+0.75))
                else: boxes.append((x+0.5,y+0.25,z+0.25,x+1,y+0.75,z+0.75))
        return boxes
    return [(x,y,z,x+1,y+1,z+1)]

# Every face winding is counter-clockwise when seen from outside. Coordinates are Y-up.
FACES = [
    ((0,0,-1), lambda a,b,c,d: [(a,b,c),(a,c,d)]),
]

def _face_quads(box):
    x0,y0,z0,x1,y1,z1=box
    return [
      ((0,0,-1), [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0)]),
      ((0,0,1), [(x1,y0,z1),(x0,y0,z1),(x0,y1,z1),(x1,y1,z1)]),
      ((-1,0,0), [(x0,y0,z1),(x0,y0,z0),(x0,y1,z0),(x0,y1,z1)]),
      ((1,0,0), [(x1,y0,z0),(x1,y0,z1),(x1,y1,z1),(x1,y1,z0)]),
      ((0,1,0), [(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)]),
      ((0,-1,0), [(x0,y0,z1),(x1,y0,z1),(x1,y0,z0),(x0,y0,z0)]),
    ]


def _build_geometry(blocks, uv_map):
    buckets = defaultdict(lambda: ([], [], []))
    full = {p for p,(n,_) in blocks.items() if n not in {"stone_brick_stairs","deepslate_brick_wall"}}
    for pos,(name,props) in blocks.items():
      for box in _boxes_for_block(pos,name,props,blocks):
        for normal,corners in _face_quads(box):
          # Cull a full block face against an adjacent full block; retain stair/wall overlaps.
          dx,dy,dz=normal
          adj=(pos[0]+dx,pos[1]+dy,pos[2]+dz)
          boundary=(box[0] == pos[0] if dx<0 else box[3] == pos[0]+1) if dx else ((box[1] == pos[1] if dy<0 else box[4] == pos[1]+1) if dy else (box[2] == pos[2] if dz<0 else box[5] == pos[2]+1))
          if boundary and pos in full and adj in full:
              continue
          verts, norms, uvs = buckets[name]
          a,b,c=corners[:3]
          cross=((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]),
                 (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]),
                 (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
          if sum(cross[k]*normal[k] for k in range(3)) < 0:
              corners=list(reversed(corners))
          u0,v0,u1,v1=uv_map[name]
          face_uv=[(u0,v1),(u1,v1),(u1,v0),(u0,v0)]
          for j in (0,1,2,0,2,3):
              verts.append(corners[j]); norms.append(normal); uvs.append(face_uv[j])
    return buckets


def _glb_write(path: Path, buckets, atlas: Image.Image):
    binbuf=bytearray(); views=[]; accessors=[]
    def add(data: bytes, target=None):
        while len(binbuf)%4: binbuf.append(0)
        off=len(binbuf); binbuf.extend(data)
        view={"buffer":0,"byteOffset":off,"byteLength":len(data)}
        if target: view["target"]=target
        views.append(view); return len(views)-1
    def accessor(view, component, count, typ, minimum=None, maximum=None):
        obj={"bufferView":view,"componentType":component,"count":count,"type":typ}
        if minimum is not None: obj["min"]=minimum
        if maximum is not None: obj["max"]=maximum
        accessors.append(obj); return len(accessors)-1
    names=sorted(buckets)
    atlasbuf=__import__('io').BytesIO(); atlas.save(atlasbuf,format='PNG',optimize=False)
    image_view=add(atlasbuf.getvalue())
    primitives=[]
    material_index={name:i for i,name in enumerate(names)}
    for name in names:
        verts,norms,uvs=buckets[name]
        if not verts: continue
        vdata=b"".join(struct.pack("<3f",*p) for p in verts)
        ndata=b"".join(struct.pack("<3f",*n) for n in norms)
        tdata=b"".join(struct.pack("<2f",*u) for u in uvs)
        vview=add(vdata,34962); nview=add(ndata,34962); tview=add(tdata,34962)
        count=len(verts)
        vmin=[min(p[i] for p in verts) for i in range(3)]; vmax=[max(p[i] for p in verts) for i in range(3)]
        va=accessor(vview,5126,count,"VEC3",vmin,vmax)
        na=accessor(nview,5126,count,"VEC3")
        ta=accessor(tview,5126,count,"VEC2")
        primitives.append({"attributes":{"POSITION":va,"NORMAL":na,"TEXCOORD_0":ta},"material":material_index[name],"mode":4})
    materials=[]
    for name in names:
        materials.append({"name":name,"pbrMetallicRoughness":{"baseColorFactor":[1,1,1,1],"metallicFactor":0,"roughnessFactor":1,"baseColorTexture":{"index":0}},"doubleSided":False})
    doc={"asset":{"version":"2.0","generator":"SG-01 deterministic NBT visual exporter"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0,"name":"SG-01 assembled NBT structure"}],"meshes":[{"name":"SG-01 blocks","primitives":primitives}],"materials":materials,"textures":[{"sampler":0,"source":0}],"samplers":[{"magFilter":9728,"minFilter":9728,"wrapS":33071,"wrapT":33071}],"images":[{"bufferView":image_view,"mimeType":"image/png","name":"mcbuild vanilla block texture atlas"}],"accessors":accessors,"bufferViews":views,"buffers":[{"byteLength":len(binbuf)}]}
    raw=json.dumps(doc,separators=(",",":"),sort_keys=True).encode()
    while len(raw)%4: raw+=b" "
    while len(binbuf)%4: binbuf.append(0)
    total=12+8+len(raw)+8+len(binbuf)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("wb") as f:
        f.write(struct.pack("<4sII",b"glTF",2,total)); f.write(struct.pack("<I4s",len(raw),b"JSON")); f.write(raw); f.write(struct.pack("<I4s",len(binbuf),b"BIN\x00")); f.write(binbuf)


def _read_glb(path):
    raw=path.read_bytes(); magic,ver,total=struct.unpack_from("<4sII",raw,0)
    if magic!=b"glTF" or ver!=2 or total!=len(raw): raise ValueError("Invalid GLB header")
    jlen,jtyp=struct.unpack_from("<I4s",raw,12); doc=json.loads(raw[20:20+jlen])
    boff=20+jlen; blen,btyp=struct.unpack_from("<I4s",raw,boff); binary=raw[boff+8:boff+8+blen]
    if btyp!=b"BIN\x00": raise ValueError("Missing GLB binary chunk")
    return doc,binary


def _validate_glb(doc, binary):
    if doc.get("asset", {}).get("version") != "2.0" or len(doc.get("scenes", [])) != 1:
        raise ValueError("GLB is missing its glTF 2.0 scene")
    if not doc.get("meshes") or not doc["meshes"][0].get("primitives"):
        raise ValueError("GLB has no mesh primitives")
    for view in doc["bufferViews"]:
        start=view.get("byteOffset",0); end=start+view["byteLength"]
        if start < 0 or end > len(binary): raise ValueError("GLB bufferView is outside its binary chunk")
    component_bytes={5121:1,5123:2,5125:4,5126:4}; type_components={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}
    for accessor in doc["accessors"]:
        view=doc["bufferViews"][accessor["bufferView"]]
        size=component_bytes[accessor["componentType"]]*type_components[accessor["type"]]
        stride=view.get("byteStride",size); start=view.get("byteOffset",0)+accessor.get("byteOffset",0)
        end=start+(accessor["count"]-1)*stride+size if accessor["count"] else start
        if end > view.get("byteOffset",0)+view["byteLength"]: raise ValueError("GLB accessor exceeds its bufferView")
    image=doc["images"][0]; view=doc["bufferViews"][image["bufferView"]]
    payload=binary[view.get("byteOffset",0):view.get("byteOffset",0)+view["byteLength"]]
    with Image.open(__import__('io').BytesIO(payload)) as decoded:
        if decoded.format != "PNG": raise ValueError("Embedded GLB atlas is not a PNG")


def _accessor(doc, binary, idx):
    a=doc["accessors"][idx]; v=doc["bufferViews"][a["bufferView"]]
    offsets={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}; n=offsets[a["type"]]
    fmt={5126:"f",5125:"I"}[a["componentType"]]
    size=struct.calcsize("<"+fmt*n); off=v.get("byteOffset",0)+a.get("byteOffset",0)
    return [struct.unpack_from("<"+fmt*n,binary,off+i*size) for i in range(a["count"])]


def _render_glb(path: Path, output: Path, *, view: str, cut_x: float|None=None, diag=False):
    doc,binary=_read_glb(path); tris=[]; mats=[]
    for mi,m in enumerate(doc["materials"]):
      rgb=BLOCK_RGB.get(m["name"],(125,125,125)); mats.append(rgb)
    for prim in doc["meshes"][0]["primitives"]:
      points=_accessor(doc,binary,prim["attributes"]["POSITION"]); material=prim["material"]
      for i in range(0,len(points),3):
        tri=points[i:i+3]
        if view in {"interior", "elevated"} and all(p[1] >= 16 for p in tri):
          continue
        if cut_x is not None:
          clipped=[]
          for j,p in enumerate(tri):
            q=tri[(j+1)%len(tri)]; pin=p[0] <= cut_x; qin=q[0] <= cut_x
            if pin: clipped.append(p)
            if pin != qin:
              t=(cut_x-p[0])/(q[0]-p[0]); clipped.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(3)))
          if len(clipped)<3: continue
          for j in range(1,len(clipped)-1): tris.append(([clipped[0],clipped[j],clipped[j+1]],material))
        else: tris.append((tri,material))
    width,height=1200,900; target=(20,7,20)
    cam_defs={
      "isometric":((100,90,115), (0,0,0)),
      "interior":((24,8,35),(20,4,20)),
      "elevated":((48,55,65),(20,5,20)),
      "top":((20,150,20),(20,0,20)),
      "section":((100,78,95),(15,5,20)),
    }
    eye,targ=cam_defs[view]
    direction=tuple(eye[i]-targ[i] for i in range(3)); ln=math.sqrt(sum(c*c for c in direction)); forward=tuple(c/ln for c in direction)
    right=(forward[2],0,-forward[0]); rn=math.sqrt(sum(c*c for c in right))
    if rn < 1e-8: right=(1,0,0); rn=1
    right=tuple(c/rn for c in right)
    up=(right[1]*forward[2]-right[2]*forward[1], right[2]*forward[0]-right[0]*forward[2], right[0]*forward[1]-right[1]*forward[0])
    def coords(p):
      d=tuple(p[i]-targ[i] for i in range(3))
      return sum(d[i]*right[i] for i in range(3)),sum(d[i]*up[i] for i in range(3)),sum(d[i]*forward[i] for i in range(3))
    projected=[]; bounds=[]
    for tri,mat in tris:
      cs=[coords(p) for p in tri]
      facing=(cs[1][0]-cs[0][0])*(cs[2][1]-cs[0][1])-(cs[1][1]-cs[0][1])*(cs[2][0]-cs[0][0])
      if facing <= 0: continue
      if all(c[2] > ln for c in cs): continue  # discard triangles behind the camera
      projected.append((sum(c[2] for c in cs)/3,cs,mat)); bounds.extend((c[0],c[1]) for c in cs)
    if not bounds: raise ValueError("No triangles to render")
    spanx=max(p[0] for p in bounds)-min(p[0] for p in bounds); spany=max(p[1] for p in bounds)-min(p[1] for p in bounds)
    scale=min((width-80)/spanx,(height-80)/spany)
    cx=(min(p[0] for p in bounds)+max(p[0] for p in bounds))/2; cy=(min(p[1] for p in bounds)+max(p[1] for p in bounds))/2
    img=Image.new("RGB",(width,height),(21,25,31)); draw=ImageDraw.Draw(img)
    light=(-0.4,0.85,-0.35); norm=math.sqrt(sum(x*x for x in light)); light=tuple(v/norm for v in light)
    for depth,cs,mat in sorted(projected,key=lambda item:item[0]):
      pts=[(width/2+(c[0]-cx)*scale,height/2-(c[1]-cy)*scale) for c in cs]
      n=( (cs[1][1]-cs[0][1])*(cs[2][2]-cs[0][2])-(cs[1][2]-cs[0][2])*(cs[2][1]-cs[0][1]),
          (cs[1][2]-cs[0][2])*(cs[2][0]-cs[0][0])-(cs[1][0]-cs[0][0])*(cs[2][2]-cs[0][2]),
          (cs[1][0]-cs[0][0])*(cs[2][1]-cs[0][1])-(cs[1][1]-cs[0][1])*(cs[2][0]-cs[0][0]))
      nl=math.sqrt(sum(c*c for c in n)) or 1; lum=max(0.42,0.60+0.38*abs(sum(n[i]/nl*light[i] for i in range(3))))
      base=mats[mat]; color=tuple(min(255,int(c*lum)) for c in base)
      draw.polygon(pts,fill=color)
    if diag:
      # Project exact connector seam block centers separately from the clean model.
      for direction,(room_pos,_) in CONNECTORS.items():
        origin=(0,0,0)
        # Project seam world center after global assembly; parent connectors are chamber coordinates.
        x,y,z=room_pos; px=width/2+(coords((x+.5,y+.5,z+.5))[0]-cx)*scale; py=height/2-(coords((x+.5,y+.5,z+.5))[1]-cy)*scale
        draw.ellipse((px-13,py-13,px+13,py+13),outline=(255,65,66),width=4)
        draw.text((px+14,py-10),direction.upper(),fill=(255,115,100),stroke_width=2,stroke_fill=(20,20,20))
    img.save(output,format="PNG",optimize=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output",type=Path,default=OUT); args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    templates, hashes=_load_templates(); blocks, report=_assembled_blocks(templates)
    names=sorted({name for name,_ in blocks.values()}); atlas,uv,texture_sources=_build_atlas(names)
    buckets=_build_geometry(blocks,uv)
    glb=args.output/"sg-01-central-cavern.glb"; _glb_write(glb,buckets,atlas)
    views=[("exterior-isometric.png","isometric",None),("interior-central-plaza.png","interior",None),
           ("elevated-balconies-supports.png","elevated",None),("top-down-overview.png","top",None),
           ("sectional-cutaway.png","section",20.5)]
    for filename,view,cut in views: _render_glb(glb,args.output/filename,view=view,cut_x=cut)
    _render_glb(glb,args.output/"jigsaw-connections-diagnostic.png",view="isometric",diag=True)
    # Verify that the GLB has a mesh and bounds matching assembled source block bounds.
    doc,binary=_read_glb(glb); _validate_glb(doc,binary); vertices=[]
    for prim in doc["meshes"][0]["primitives"]: vertices.extend(_accessor(doc,binary,prim["attributes"]["POSITION"]))
    model_bounds=[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)]
    grid_bounds=[[min(p[i] for p in blocks),max(p[i]+1 for p in blocks)] for i in range(3)]
    coordinate_state_digest=hashlib.sha256(json.dumps(
        [[list(p), name, props] for p,(name,props) in sorted(blocks.items())],
        separators=(",",":"),sort_keys=True).encode()).hexdigest()
    preview_names=[name for name,_,_ in views]+["jigsaw-connections-diagnostic.png"]
    report.update({"source_nbt_sha256":hashes,"assembled_coordinate_state_sha256":coordinate_state_digest,
                   "assembled_solid_block_count":len(blocks),"covered_block_position_count":len(blocks),
                   "glb_vertex_count":len(vertices),"glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
                   "glb_embeds_texture_atlas":True,"model_materials":names,
                   "preview_png_sha256":{name:hashlib.sha256((args.output/name).read_bytes()).hexdigest() for name in preview_names},
                   "glb_world_bounds":model_bounds,"source_block_bounds":grid_bounds,"glb_bytes":glb.stat().st_size,
                   "texture_sources":texture_sources,"limitations":["Texture atlas uses bundled mcbuild vanilla PNGs; deepslate_brick_wall maps to deepslate_bricks and stone_brick_stairs maps to stone_bricks.",
                   "Only SG-01's actual non-full block types are walls and stone-brick stairs. Wall connections are inferred from adjacent wall blocks.",
                   "Stair shape/facing is modeled; stair inner/outer corner state variants are represented as straight stair geometry.",
                   "Balcony wall neighbor/up and wall post states are approximated geometrically; no fences, slabs, entities, or mobs are present in the exported templates.",
                   "Preview rasterizer shades GLB triangles with representative block colors; the interactive GLB includes the block texture atlas."]})
    if model_bounds != grid_bounds: raise ValueError(f"GLB/source bounds mismatch: {model_bounds} != {grid_bounds}")
    report_path=args.output/"validation-report.json"; report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    for static_file in ("README.md", "index.html"):
        source=OUT/static_file; destination=args.output/static_file
        if source.exists() and source.resolve() != destination.resolve(): shutil.copyfile(source,destination)
    print(f"Wrote {glb} ({glb.stat().st_size} bytes), {len(blocks)} blocks, bounds {grid_bounds}")

if __name__=="__main__": main()
