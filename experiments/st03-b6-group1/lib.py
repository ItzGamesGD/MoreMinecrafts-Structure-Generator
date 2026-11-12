"""Small authoring helpers shared by the ST-03 group-1 builds (B3-06). Cells are (x, y, z) -> (block id, {state}).

Local frame (same as House A): +x east, +z south, y=0 floor. Every building's door faces south (z = depth - 1).
Stairs: `facing` is the direction the stair ASCENDS toward (vanilla blockstate: facing=east has the raised half east),
so a roof slope that falls to the north uses facing=south.
"""

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
# raised quarter of an outer-corner stair (vanilla blockstates: base model = SE quarter, rotated by y)
_QUARTER = {
    ("east", "outer_right"): "SE", ("south", "outer_right"): "SW", ("west", "outer_right"): "NW",
    ("north", "outer_right"): "NE", ("east", "outer_left"): "NE", ("south", "outer_left"): "SE",
    ("west", "outer_left"): "SW", ("north", "outer_left"): "NW",
}  # fmt: skip


def corner_stair(quarter, prefer):
    """(facing, shape) of an outer stair whose single raised quarter is `quarter` (NE/NW/SE/SW)."""
    for (f, s), q in _QUARTER.items():
        if q == quarter and f in prefer:
            return f, s
    raise KeyError(quarter)


class G:
    def __init__(s, w, h, d):
        s.W, s.H, s.D, s.c = w, h, d, {}
        s.decor = set()  # cells that are decoration/detail only (placement variants may differ there, nowhere else)

    def d(s, x, y, z, block, **p):
        """put() for a decoration cell: recorded so the variant check can prove variants differ only in decoration."""
        s.put(x, y, z, block, **p)
        s.decor.add((x, y, z))

    def put(s, x, y, z, block, **p):
        assert 0 <= x < s.W and 0 <= y < s.H and 0 <= z < s.D, (x, y, z, block)
        s.c[(x, y, z)] = ("minecraft:" + block, {k: str(v).lower() for k, v in p.items()})

    def fill(s, x0, x1, y0, y1, z0, z1, block, **p):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    s.put(x, y, z, block, **p)

    def clear(s, x, y, z):
        s.c.pop((x, y, z), None)

    def stair(s, x, y, z, mat, facing, shape="straight", half="bottom"):
        s.put(x, y, z, mat + "_stairs", facing=facing, half=half, shape=shape)

    def door(s, x, y, z, mat, facing, hinge="left"):
        for half in ("lower", "upper"):
            s.put(
                x, y + (half == "upper"), z, mat + "_door",
                facing=facing, half=half, hinge=hinge, open=False, powered=False,
            )  # fmt: skip

    def shutter(s, x, y, z, outward, mat="spruce"):
        """Open trapdoor lying flat on the OUTER face of its cell. outward = direction of the exterior."""
        s.put(x, y, z, mat + "_trapdoor", facing=OPP[outward], half="bottom", open=True, powered=False)

    def bed(s, x, z, color, head):
        """Bed at floor level (y=1); head cell offset in direction `head` from the foot (x, z)."""
        dx, dz = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[head]
        s.put(x, 1, z, color + "_bed", facing=head, occupied=False, part="foot")
        s.put(x + dx, 1, z + dz, color + "_bed", facing=head, occupied=False, part="head")

    def gable_ew(s, eave, mat, ridge_block=None, trim=None):
        """Ridge along x, slopes along z (any odd depth). Returns roof height function h(z)."""
        d = s.D
        r = (d - 1) // 2
        h = lambda z: eave + min(z, d - 1 - z)
        for z in range(d):
            for x in range(s.W):
                if z == r:
                    s.put(x, h(z), z, *(ridge_block or ("dark_oak_log",)), **({"axis": "x"} if (ridge_block or ("dark_oak_log",))[0].endswith("_log") else {}))
                else:
                    s.stair(x, h(z), z, mat, "south" if z < r else "north")
        return h

    def hip(s, y0, mat, cap="dark_oak_planks"):
        """Pyramid hip roof on a square footprint (odd width = depth): rings of stairs, corner pieces, filled centre."""
        n = s.W
        assert s.D == n and n % 2 == 1
        k = 0
        while n - 2 * k >= 3:
            a, b, y = k, n - 1 - k, y0 + k
            for x in range(a, b + 1):
                for z in range(a, b + 1):
                    if not (x in (a, b) or z in (a, b)):
                        continue
                    nz, sz, wx, ex = z == a, z == b, x == a, x == b
                    if (nz or sz) and (wx or ex):
                        q = ("S" if nz else "N") + ("E" if wx else "W")  # raised quarter points to the roof centre
                        f, sh = corner_stair(q, ("north", "south", "east", "west"))
                        s.stair(x, y, z, mat, f, sh)
                    elif nz:
                        s.stair(x, y, z, mat, "south")
                    elif sz:
                        s.stair(x, y, z, mat, "north")
                    elif wx:
                        s.stair(x, y, z, mat, "east")
                    else:
                        s.stair(x, y, z, mat, "west")
            k += 1
        c = n // 2
        # innermost: centre cell(s) filled to the level of the last ring
        s.put(c, y0 + k - 1, c, cap)
        return y0 + k
