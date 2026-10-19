"""Build traversal legs (in world coordinates) for a generated SG-01 from its recorded pieces, any rotation."""
from __future__ import annotations

from analysis import PIECE_TEMPLATE, ROT, piece_cells

CENTER = 20  # chamber local centre column (41 wide)


def chamber_transform(start: dict, templates: dict):
    """Return (local -> world) mapping for the main chamber, including its recorded rotation."""
    child = next(c for c in start["Children"] if PIECE_TEMPLATE[c["pool_element"]["location"]] == "main_chamber")
    template = templates["main_chamber"]
    world = {tuple(b["pos"]): pos for b, (pos, _s) in zip(template["blocks"], piece_cells(template, child["BB"], ROT[child["rotation"]]))}
    return lambda x, y, z: world[(x, y, z)]


def legs_for_site(start: dict, templates: dict, tag: str) -> list[tuple[str, tuple, tuple, int]]:
    w = chamber_transform(start, templates)
    plaza = w(CENTER, 1, CENTER)
    legs = []

    def leg(name, a, b, timeout=900):
        legs.append((f"{tag}:{name}", a, b, timeout))

    # (local door cell just inside the chamber, tunnel far-end entrance cell) per direction
    doors = {"north": (CENTER, 1, 1), "east": (39, 1, CENTER), "south": (CENTER, 1, 39), "west": (1, 1, CENTER)}
    far = {  # tunnel far-end aperture cell (feet level), via chamber-local extension of the tunnel length (15) past the door plane
        "north": (CENTER, 1, -14), "east": (54, 1, CENTER), "south": (CENTER, 1, 54), "west": (-14, 1, CENTER)}
    # Far-end cells are outside the chamber template, so derive them from the tunnel pieces instead.
    for child in start["Children"]:
        name = PIECE_TEMPLATE[child["pool_element"]["location"]]
        if name == "main_chamber":
            continue
        direction = name.split("_", 1)[1]
        bb = child["BB"]
        cx, cz = (bb[0] + bb[3]) // 2, (bb[2] + bb[5]) // 2
        # the end of the tunnel farthest from the chamber centre
        plaza_x, _py, plaza_z = plaza
        ends = ([(bb[0], cz), (bb[3], cz)] if bb[3] - bb[0] > bb[5] - bb[2] else [(cx, bb[2]), (cx, bb[5])])
        ex, ez = max(ends, key=lambda e: abs(e[0] - plaza_x) + abs(e[1] - plaza_z))
        far[direction] = (ex, bb[1] + 1, ez)
    # outbound waypoints within follow-range: entrance -> chamber door -> plaza centre
    for d in ("north", "east", "south", "west"):
        door = w(*doors[d])
        leg(f"entrance_{d}_to_door", far[d], door)
        leg(f"door_{d}_to_plaza", door, plaza)
    for d in ("north", "east", "south", "west"):
        door = w(*doors[d])
        leg(f"plaza_to_door_{d}", plaza, door)
        leg(f"door_{d}_to_entrance", door, far[d])
    # stair runs: plaza -> stair foot -> ring landing (feet y = ring floor 8 + 1)
    foot = {"north": (CENTER, 1, 15), "south": (CENTER, 1, 25), "east": (25, 1, CENTER), "west": (15, 1, CENTER)}
    top = {"north": (CENTER, 9, 5), "south": (CENTER, 9, 35), "east": (35, 9, CENTER), "west": (5, 9, CENTER)}
    for d in ("north", "east", "south", "west"):
        leg(f"plaza_to_stair_foot_{d}", plaza, w(*foot[d]))
        leg(f"stair_{d}_up_to_ring", w(*foot[d]), w(*top[d]))
        leg(f"stair_{d}_down_to_foot", w(*top[d]), w(*foot[d]))
    # full lap of the elevated ring in 15-block legs (keeps every leg inside mob pathfinding range)
    lap = [(CENTER, 5), (35, 5), (35, CENTER), (35, 35), (CENTER, 35), (5, 35), (5, CENTER), (5, 5), (CENTER, 5)]
    for i in range(len(lap) - 1):
        leg(f"ring_lap_{i}", w(lap[i][0], 9, lap[i][1]), w(lap[i + 1][0], 9, lap[i + 1][1]))
    # outward probes: a goal 6 blocks beyond each tunnel mouth. Inside solid rock it must NOT be reachable; it only
    # passes where natural cave space actually continues past the aperture.
    for d in ("north", "east", "south", "west"):
        fx, fy, fz = far[d]
        dx, dz = fx - plaza[0], fz - plaza[2]
        ux, uz = ((1 if dx > 0 else -1), 0) if abs(dx) > abs(dz) else (0, (1 if dz > 0 else -1))
        leg(f"outward_probe_{d}", far[d], (fx + 6 * ux, fy, fz + 6 * uz), 240)
    return legs
