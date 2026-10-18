"""SG-03 camera plan: cavern with connections, entrances, every room interior, and a multi-level section."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples/forgotten_kingdom"))
from kingdom_common import LOWER_U, UPPER_U  # noqa: E402
from sg02_cavern import side_xz  # noqa: E402

ROOM_VIEWS = {
    # name: [(label, feet-cell, target-cell)] in the room's own template coordinates
    "storage_room": [("a-aisle", (6, 1, 14), (6, 3, 3)), ("b-corner", (2, 1, 14), (10, 2, 4)), ("c-stash", (6, 3, 3), (6, 2, 15))],
    "guard_room": [("a-hall", (7, 1, 8), (7, 3, 1)), ("b-watch-step", (7, 3, 2), (7, 3, 11)), ("c-armoury", (10, 1, 6), (1, 3, 3))],
    "residence_ruin": [("a-hall", (7, 1, 16), (7, 3, 8)), ("b-bedroom", (7, 1, 6), (7, 2, 15)), ("c-hearth", (10, 1, 12), (3, 2, 8))],
    "grand_hall": [("a-nave", (11, 1, 28), (11, 7, 3)), ("b-gallery", (3, 7, 19), (3, 10, 2)), ("c-dais", (11, 4, 5), (11, 6, 28))],
    "barracks_hall": [("a-mess", (10, 1, 24), (10, 4, 12)), ("b-bunks-and-stair", (10, 1, 20), (2, 5, 15)), ("d-mezzanine", (10, 1, 22), (10, 7, 9)), ("c-armoury", (10, 1, 8), (17, 2, 3))],
    "trial_chamber": [("a-entry", (11, 1, 26), (11, 3, 10)), ("b-ledge", (2, 3, 12), (16, 1, 16)), ("c-alcove", (11, 3, 6), (11, 2, 24))],
}


def cameras(templates, assembly, report, ap, camera, placed_pieces):
    pieces = placed_pieces(templates, assembly)
    chamber = pieces[0][1]
    cams = []
    # Cavern with the new connections visible: lower doors under the platform, upper vestibules above.
    cams.append(camera("cavern-lower-doors", chamber, (10, 1, 20), (10, 6, 2), "plaza view under the north platform: lower-level doorway at slot a"))
    cams.append(camera("cavern-upper-vestibules", chamber, (30, 9, 7), (11, 11, 2), "north deck lane: the upper vestibule opening in the gallery-back masonry"))
    cams.append(camera("cavern-overview", chamber, (18, 1, 32), (23, 9, 6), "plaza, stairs, north platform"))
    seen_lower = seen_upper = False
    for piece, placed in pieces[1:]:
        slot = piece["slot"] or ""
        name = piece["template"].rsplit("/", 1)[-1]
        if "/rooms/lower/" in piece["template"] and not seen_lower:
            side, letter = slot.rsplit("_link_", 1)[-1].split("_")
            u = LOWER_U[0 if letter == "a" else 1]
            x, z = side_xz(side, u, 11)
            tx, tz = side_xz(side, u, 0)
            cams.append(camera(f"lower-entrance-{name}", chamber, (x, 1, z), (tx, 3, tz), f"lower slot {side}/{letter}: {name}"))
            seen_lower = True
        if "/rooms/upper/" in piece["template"] and not seen_upper:
            side, letter = slot.rsplit("_link_", 1)[-1].split("_")
            u = UPPER_U[0 if letter == "a" else 1]
            x, z = side_xz(side, u, 7)
            tx, tz = side_xz(side, u, 0)
            cams.append(camera(f"upper-entrance-{name}", chamber, (x, 9, z), (tx, 11, tz), f"upper slot {side}/{letter}: {name}"))
            seen_upper = True
    # Interior of every module: from the standalone, verified template placements. The standalone
    # doorways (and their still-present jigsaw blocks) are plugged in the evidence world first so the
    # views read as sealed rooms rather than as voids.
    plugs = []
    for template_id, origin in report["standalone_origins"].items():
        name = template_id.rsplit("/", 1)[-1]
        if name not in ROOM_VIEWS:
            continue
        w, h, d = templates[template_id].size
        half = 1 if "/lower/" in template_id else 2
        ox, oy, oz = origin
        plugs.append(f"fill {ox + w // 2 - half - 1} {oy + 1} {oz + d - 1} {ox + w // 2 + half + 1} {oy + 5} {oz + d - 1} minecraft:polished_deepslate")
    cams.append({"commands": plugs})
    for template_id, origin in report["standalone_origins"].items():
        name = template_id.rsplit("/", 1)[-1]
        if name not in ROOM_VIEWS:
            continue
        standalone = ap.Placed(templates[template_id], 0, tuple(origin))
        kind = "lower" if "/lower/" in template_id else "upper"
        for label, feet, target in ROOM_VIEWS[name]:
            cams.append(camera(f"{kind}-{name}-{label}", standalone, feet, target, f"{name} interior"))
    return cams


def section_cameras(templates, assembly, ap, camera, placed_pieces):
    """Cut the evidence world through the north slot stack (local x=10) and view the multi-level section."""
    pieces = placed_pieces(templates, assembly)
    chamber = pieces[0][1]
    lo = tuple(min(p.bbox()[0][i] for _piece, p in pieces) for i in range(3))
    hi = tuple(max(p.bbox()[1][i] for _piece, p in pieces) for i in range(3))
    # local box x>=10 over the whole assembly extent, mapped to world and axis-aligned
    far = 120
    corners = [chamber.world((x, y, z)) for x in (10, 10 + far) for y in (0, 40) for z in (-90, 130)]
    cmin = tuple(min(c[i] for c in corners) for i in range(3))
    cmax = tuple(max(c[i] for c in corners) for i in range(3))
    cmin = (cmin[0], lo[1] - 1, cmin[2])
    cmax = (cmax[0], hi[1] + 2, cmax[2])
    commands = []
    step = 24
    for x in range(cmin[0], cmax[0] + 1, step):
        for y in range(cmin[1], cmax[1] + 1, step):
            for z in range(cmin[2], cmax[2] + 1, step):
                commands.append(f"fill {x} {y} {z} {min(x + step - 1, cmax[0])} {min(y + step - 1, cmax[1])} {min(z + step - 1, cmax[2])} minecraft:air")
    # The cut removes local x>=10; the cut face looks toward local +x. Place cameras on that side.
    cams = [{"commands": commands}]
    cams.append(camera("section-multilevel", chamber, (44, 14, 8), (10, 9, 8), "vertical section through the north lower/upper stack (evidence world cut at local x=10)"))
    cams.append(camera("elevated-separation", chamber, (34, 30, -26), (6, 8, 4), "elevated oblique view of the cut: lower band, upper band, tunnels and chamber"))
    return cams
