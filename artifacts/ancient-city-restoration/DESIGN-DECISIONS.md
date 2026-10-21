# Ancient City restoration — owner design decisions

Project-level record of owner decisions. Each entry names the stage that raised the question, the decision and where
the evidence lives.

## Known accessibility issues — deferred (recorded in Stage 24-J)

Raised by Stage 24-I (`stage-24i/ENTRANCES.md`, Draft PR #33). These are **known accessibility issues, not resolved
defects**. No terrain-clearing feature is implemented and no house bounding box is enlarged for them; the Stage 24-I
roof protection is unchanged.

| seed | piece | issue | evidence | decision |
|---|---|---|---|---|
| 24005 | medium_ruin_1 #71 (NONE), door (-1348,-50,1029) | door blocked from the city path by 14 natural dripstone blocks (x -1349, y -50..-49, z 1029..1035) inside the neighbouring wall piece's box | survey, bot navigation: blocked | **Deferred to city connectivity work** |
| 24009 | large_ruin_1 #59 (CLOCKWISE_90), door (597,-50,551) | door blocked by 6 natural dripstone blocks (x 595..597, y -50..-49, z 550) inside the neighbouring wall piece's box | survey, bot navigation: blocked | **Deferred to city connectivity work** |
| 24015 | large_ruin_1 #55 (COUNTERCLOCKWISE_90), door (-272,-50,-154) | door opens onto a drop; no traversable connection within 14 blocks | survey | **Deferred to road, stair or walkway integration** |

Not authorised for these issues: a new terrain-clearing feature, a post-generation excavator, or enlarging a house box.
The Stage 24-I out-of-box overlay experiment remains evidence only (`stage-24i/experiment-entrance/`).

## Earlier decisions (for reference)

* Stage 24-G — functional protection of doors, ladders, beds, containers, railings and supports from vanilla decay.
* Stage 24-H — owner Option A: interior terrain clearance inside the piece box.
* Stage 24-I — roof cells over enclosed rooms protected from `block_rot`; exterior entrance clearance not delivered.
* Stage 24-J — watchtower appearance: alternatives prepared for review (`stage-24j/`); **no design chosen**, the approved
  tower NBTs are unchanged until the owner approves an option.
