"""Hand-written, evidence-backed descriptive text for the gallery (all claims trace to Stage 24-B/24-C evidence)."""

DESIGN = {
    "large_ruin_1": ["Broad courtyard house: room wings wrap a 5×5 open-to-sky light court.", "Two beds, barrel, crafting table, four soul lanterns.", "Entrance: spruce door in the west wall; flat deepslate-tile roof with the open court."],
    "medium_ruin_1": ["Compact single-storey house: common room plus sleeping room.", "One bed, barrel, crafting table, two lanterns, bench and table slabs.", "Entrance: spruce door in the west wall; flat tile roof."],
    "medium_ruin_2": ["Partial two-storey house (height 5 → 8, owner-approved): the east half carries an upper bedroom over the ground-floor private room.", "Four-step stair run east from the family hall to a 2-high doorway in the upper west wall; upper bedroom with bed and storage barrel.", "Ground floor: bed, kitchen workstation, storage barrel, dining slabs."],
    "small_ruin_1": ["Single room with a sleeping alcove and a work corner.", "Low gable edge stairs on the long roof edges, one blue-glass slit window.", "One bed, one barrel."],
    "small_ruin_2": ["Micro home (8×5×4): one bed on the open north row, a clear central aisle, barrel set into the south wall.", "Compact functionality over decoration; one lantern."],
    "sauna_1": ["Public bathhouse restored from the original shell: both original basins (43 water blocks), original stairs and rims, three original loot chests, five jigsaws.", "Added: changing benches, resting benches, candles, wall-top soul lanterns and a tile canopy over the south reception.", "Owner-provisional change: the cracked-brick head block at (11,2,33) was removed to connect reception and bath circulation."],
    "large_pillar_1": ["Large watchtower: hollow 2×2 shaft inside a 6×6 ring, 2-high entrance tunnel in the west face.", "13-block ladder on a polished-basalt spine with three landings; 2×2 observation deck at y=14 enclosed by the retained parapet ring."],
    "medium_pillar_1": ["Medium watchtower: guard room around the retained central spine (original skull kept), east-side 8-block ladder, 5×6 observation deck.", "Parapet: 18 polished-deepslate wall segments on the deck edge (added in Stage 24-C)."],
}

LIMITS = {
    "large_ruin_1": ["Flat tile roof; low silhouette differentiation from the other flat-roofed houses (V1, owner decision).", "Vanilla processors remove ~5 % of lanterns and some blocks when generated (V5)."],
    "medium_ruin_1": ["Flat tile roof (V1).", "One generated piece in sampled seed 24005 was buried in a dripstone cave (vanilla terrain adaptation, same for the original).", "1 of 52 generated doors was removed by vanilla rot (V5)."],
    "medium_ruin_2": ["Two flat roof levels (V1); the stair opening is a small roof hole (skylight) over the stairs.", "Height 8 verified in 20 generated pieces with no bounding-box overlap (Stage 24-C)."],
    "small_ruin_1": ["Flat roof with gable-edge stairs only (V1)."],
    "small_ruin_2": ["Very small footprint: the interior is a 6×2 room; the bed was moved in Stage 24-C because it was obstructed by wall blocks."],
    "sauna_1": ["Opening at (11,2,33) awaits visual approval (V4).", "Only 9 generated sauna pieces sampled in 24 cities.", "Water containment and chest loot verified live; visual character of the benches/canopy is owner-pending."],
    "large_pillar_1": ["Deck ring uses rot-eligible deepslate: a hole in the 2-thick ring is unlikely but was not probed under real generation.", "Ladder repaired in Stage 24-C (it did not reach the deck in PR #10)."],
    "medium_pillar_1": ["Deck had no edge protection in PR #10; fixed in Stage 24-C.", "East ladder kept (not relocated): it climbs ground-to-deck in 3.6 s in the simulated-player test."],
}

STATUS = ["CODE VERIFIED", "GEOMETRY VERIFIED", "VISUAL PENDING", "LIVE PASS (server + simulated player; real client PENDING)", "WORLDGEN PASS", "OWNER REVIEW PENDING"]

QUESTIONS = {
    "V1": ("Roof differentiation (large_ruin_1 vs medium_ruin_2 vs other houses)", ["Keep flat roofs", "Differentiate roofs (describe)", "Needs discussion"]),
    "V2": ("Partial second floor presentation (medium_ruin_2)", ["Accept as is", "Change presentation (describe)", "Needs discussion"]),
    "V3": ("Watchtower silhouettes (large_pillar_1 vs medium_pillar_1)", ["Accept both", "Change large tower", "Change medium tower", "Needs discussion"]),
    "V4": ("Sauna reception opening at (11,2,33)", ["Keep opening", "Revert (restore the block)", "Alter the opening (describe)", "Needs discussion"]),
    "V5": ("Vanilla degradation of generated buildings", ["Keep vanilla degradation", "Protect critical blocks (door/ladder/lantern)", "Needs discussion"]),
}
