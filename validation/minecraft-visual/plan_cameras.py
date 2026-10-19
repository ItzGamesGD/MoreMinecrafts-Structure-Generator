#!/usr/bin/env python3
"""Turn a runtime report into world-space camera positions for the native screenshot capture.

Cameras are authored in a piece's own template coordinates (looking from ``eye`` at ``target``)
and mapped through the recovered placement, so every view stays correct under any rotation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import assembly_probe as ap  # noqa: E402

CHAMBER = "main_chamber"


def aim(eye, target):
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return round(yaw, 1), round(pitch, 1)


def camera(name, placed, eye_local, target_local, note=""):
    """Eye (feet cell) and target in template-local coordinates, mapped through the placement."""
    eye = placed.world(tuple(int(v) for v in eye_local))
    target = placed.world(tuple(int(v) for v in target_local))
    return camera_abs(name, eye, target, note)


def camera_abs(name, feet_cell, target_cell, note=""):
    feet = (feet_cell[0] + 0.5, float(feet_cell[1]), feet_cell[2] + 0.5)
    yaw, pitch = aim((feet[0], feet[1] + 1.62, feet[2]), (target_cell[0] + 0.5, target_cell[1] + 0.5, target_cell[2] + 0.5))
    return {"name": name, "x": feet[0], "y": feet[1], "z": feet[2], "yaw": yaw, "pitch": pitch, "note": note,
            "feet_cell": list(feet_cell), "target_cell": list(target_cell)}


def occupancy(pieces):
    solid = {}
    for _piece, placed in pieces:
        for pos, state in placed.blocks().items():
            if not ap.passable(state):
                solid[pos] = state["id"]
    return solid


def check_clear(cams, solid, view_blocks=2):
    """Reject cameras whose body or first ``view_blocks`` of sight line sit inside masonry."""
    problems = []
    for cam in cams:
        if "commands" in cam:
            continue
        x, y, z = cam["feet_cell"]
        if (x, y, z) in solid or (x, y + 1, z) in solid:
            problems.append(f"{cam['name']}: camera body inside {solid.get((x, y, z)) or solid.get((x, y + 1, z))}")
            continue
        yaw, pitch = math.radians(cam["yaw"]), math.radians(cam["pitch"])
        direction = (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
        for step in range(1, view_blocks + 1):
            px, py, pz = (cam["x"] + direction[0] * step, cam["y"] + 1.62 + direction[1] * step, cam["z"] + direction[2] * step)
            cell = (math.floor(px), math.floor(py), math.floor(pz))
            if cell in solid:
                problems.append(f"{cam['name']}: sight line enters {solid[cell]} {step} block(s) ahead at {cell}")
                break
    if problems:
        raise SystemExit("camera placement problems:\n  " + "\n  ".join(problems))


def pieces_from_report(report, assembly_index=0):
    assembly = report["assemblies"][assembly_index]
    return assembly["pieces"]


def placed_pieces(templates, assembly):
    out = []
    for p in assembly["pieces"]:
        out.append((p, ap.Placed(templates[p["template"]], p["turns"], tuple(p["origin"]))))
    return out


def exterior_camera(name, pieces, note, offset=(-80, 46, -80)):
    los = [p.bbox()[0] for _piece, p in pieces]
    his = [p.bbox()[1] for _piece, p in pieces]
    lo = tuple(min(v[i] for v in los) for i in range(3))
    hi = tuple(max(v[i] for v in his) for i in range(3))
    center = tuple((lo[i] + hi[i]) // 2 for i in range(3))
    eye = (center[0] + offset[0], hi[1] + offset[1], center[2] + offset[2])
    return camera_abs(name, eye, (center[0], lo[1] + 4, center[2]), note)


def sg02_cameras(templates, assembly):
    pieces = placed_pieces(templates, assembly)
    chamber = pieces[0][1]
    cams = [
        camera("cavern-overview", chamber, (18, 1, 32), (23, 9, 6), "plaza, symmetrical stairs, north platform, rails"),
        camera("platform-lanes", chamber, (7, 9, 7), (36, 9, 7), "four-lane north platform, deepslate rails on plaza edge"),
        camera("stairs-and-rail", chamber, (17, 1, 22), (23, 4, 13), "deepslate brick stairs meeting the railed platform"),
        camera("rail-detail", chamber, (18, 9, 6), (23, 9, 9), "wall rail ends beside the open stair mouth"),
        camera("stair-landing", chamber, (23, 9, 6), (23, 6, 14), "looking down the stair run from the deck: flush final step at the mouth, rails either side"),
        camera("lower-door", chamber, (10, 1, 17), (8, 3, 0), "lower-level connection under the platform"),
        camera("upper-vestibule", chamber, (11, 9, 8), (11, 11, 0), "upper-level 5x5 vestibule from the gallery lane"),
        camera("undercroft", chamber, (12, 1, 19), (4, 3, 8), "open undercroft carrying the deck"),
    ]
    for piece, placed in pieces[1:]:
        if piece["template"].endswith("rooms/lower/stub") and not any(c["name"] == "lower-stub-interior" for c in cams):
            w, h, d = placed.template.size
            cams.append(camera("lower-stub-interior", placed, (w // 2, 1, 4), (w // 2, 2, d - 1), "reserved lower volume looking back at the cavern door"))
        if piece["template"].endswith("rooms/upper/stub") and not any(c["name"] == "upper-stub-interior" for c in cams):
            w, h, d = placed.template.size
            cams.append(camera("upper-stub-interior", placed, (w // 2, 1, 4), (w // 2, 5, d - 1), "reserved upper volume looking back at the cavern door"))
    cams.append(exterior_camera("exterior-reserved-volumes", pieces, "whole assembly: chamber, tunnels, 8 lower and 8 upper reserved volumes"))
    check_clear(cams, occupancy(pieces))
    return cams


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--stage", choices=("sg02", "sg03"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assembly", type=int, default=0)
    args = parser.parse_args()
    templates, _ = ap.load_pack(args.pack)
    report = json.loads(args.report.read_text())
    assembly = report["assemblies"][args.assembly]
    if args.stage == "sg02":
        cams = sg02_cameras(templates, assembly)
    else:
        import plan_cameras_sg03

        cams = plan_cameras_sg03.cameras(templates, assembly, report, ap, camera, placed_pieces)
        standalone = [(None, ap.Placed(templates[i], 0, tuple(o))) for i, o in report["standalone_origins"].items()]
        check_clear(cams, occupancy(placed_pieces(templates, assembly) + standalone))
        cams += plan_cameras_sg03.section_cameras(templates, assembly, ap, camera, placed_pieces)
    args.output.write_text(json.dumps(cams, indent=2) + "\n")
    print(f"{len(cams)} cameras -> {args.output}")


if __name__ == "__main__":
    main()
