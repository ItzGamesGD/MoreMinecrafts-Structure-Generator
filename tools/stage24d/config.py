"""Per-module camera / cutaway configuration for the Stage 24-D gallery (coordinates are NBT-local x,y,z)."""
from __future__ import annotations

# front_az: camera azimuth of the entrance side (0=camera south, 90=east, 180=north, 270=west)
CFG = {
    "large_ruin_1": dict(front_az=270, entry=(0, 1, 7), fig=((-2, 1, 7), 90),
        floors=[("Floor plan — floor and furniture (y ≤ 1)", 1), ("Ground floor — walls and fittings, roof removed (y ≤ 3)", 3)],
        dollhouse=3, section=[{"axis": "z", "lt": 8}], section_az=200),
    "medium_ruin_1": dict(front_az=270, entry=(0, 1, 6), fig=((-2, 1, 6), 90),
        floors=[("Floor plan — floor and furniture (y ≤ 1)", 1), ("Ground floor — walls and fittings, roof removed (y ≤ 3)", 3)],
        dollhouse=3, section=[{"axis": "z", "lt": 6}], section_az=200),
    "medium_ruin_2": dict(front_az=270, entry=(0, 1, 5), fig=((-2, 1, 5), 90),
        floors=[("Ground floor plan (y ≤ 1)", 1), ("Ground floor walls — upper storey removed (y ≤ 3)", 3),
                ("Upper floor plan — floor and furniture (y ≤ 5)", 5), ("Upper room — walls, roof removed (y ≤ 6)", 6)],
        dollhouse=6, section=[{"axis": "z", "lt": 5}], section_az=200),
    "small_ruin_1": dict(front_az=270, entry=(0, 1, 3), fig=((-2, 1, 3), 90),
        floors=[("Floor plan — floor and furniture (y ≤ 1)", 1), ("Ground floor — walls and fittings, roof removed (y ≤ 3)", 3)],
        dollhouse=3, section=[{"axis": "z", "lt": 4}], section_az=200),
    "small_ruin_2": dict(front_az=270, entry=(0, 1, 2), fig=((-2, 1, 2), 90),
        floors=[("Floor plan — floor and furniture (y ≤ 1)", 1), ("Ground floor — walls and fittings, roof removed (y ≤ 3)", 3)],
        dollhouse=3, section=[{"axis": "z", "lt": 2}], section_az=200),
    "sauna_1": dict(front_az=0, entry=(13, 1, 36), fig=((13, 1, 38), 180),
        floors=[("Floor level — basins, benches, chests (y ≤ 1)", 1), ("Walls and fittings (y ≤ 3)", 3),
                ("Raised plunge basin level (y ≤ 5)", 5), ("Everything below the reception canopy (y ≤ 7)", 7)],
        dollhouse=7, section=[{"axis": "x", "lt": 14}], section_az=250),
    "large_pillar_1": dict(front_az=270, entry=(0, 2, 2), fig=((-2, 1, 2), 90),
        floors=[("Entrance level (y ≤ 1)", 1), ("First landing (y ≤ 5)", 5), ("Second landing (y ≤ 9)", 9), ("Observation deck (y ≤ 13)", 13)],
        dollhouse=13, section=[{"axis": "z", "lt": 2}], section_az=180),
    "medium_pillar_1": dict(front_az=180, entry=(3, 1, 0), fig=((3, 1, -2), 0),
        floors=[("Guard-room floor (y ≤ 1)", 1), ("Guard room — walls (y ≤ 4)", 4), ("Observation deck and parapet (y ≤ 9)", 9)],
        dollhouse=8, section=[{"axis": "z", "lt": 3}], section_az=180),
}
HOUSES = ["large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2"]
REFERENCE_HOMES = ["chamber_1", "chamber_2", "chamber_3", "tall_ruin_2", "tall_ruin_4"]
