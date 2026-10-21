#!/usr/bin/env bash
# N7-A3 runner: one configuration, one site, one order, one repeat. Experimental; see docs/sg-03/n7a3-performance-compatibility.md.
# usage: n73_run.sh OUT_DIR CONFIG SEED CX CZ ORDER REPEAT [KEEP_WORLD=0|1] [BG_THREADS]
# CONFIG: RG (N7-C injected geode drift) | R (injected monster-room precheck drift) | P (N7-B production configuration) | F (N7-B simulated drift, box fallback) | V (vanilla jar, no module) | A (module, observe, no protection) | B (N7-A reach, enforce) |
#         C (N7-A2 refined precheck, enforce) | H (hybrid broad-phase, enforce) | HS (hybrid + shadow check)
# RADIUS (default 5) sets the loaded area; SG01_EXTRA_MODS (optional) adds mod jars for compatibility runs.
# Requires SERVER_JAR (official 26.3 server.jar), SG_PACK (built SG-03 datapack folder), JAVA_HOME (JDK 25) on PATH.
set -euo pipefail
OUT="$1"; CONFIG="$2"; SEED="$3"; CX="$4"; CZ="$5"; ORDER="$6"; REP="$7"; KEEP="${8:-0}"; BG="${9:-}"
: "${SERVER_JAR:?set SERVER_JAR}"; : "${SG_PACK:?set SG_PACK}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
TAG="${CONFIG}_${SEED}_${CX}_${CZ}_${ORDER//:/-}_r${REP}"
ARGS=(--jar "$SERVER_JAR" --pack "$SG_PACK" --out "$OUT/$TAG" --seed "$SEED" --chunk "$CX" "$CZ" --order "$ORDER" --radius "${RADIUS:-5}" --settle "${SETTLE:-0}" --ticks 0 --port 40950)
[ "$KEEP" = 1 ] && ARGS+=(--keep-world)
[ "${FREEZE:-0}" = 1 ] && ARGS+=(--freeze)
if [ "$CONFIG" = V ]; then
  [ -n "$BG" ] && ARGS+=(--threads "$BG")
else
  ARGS+=(--fabric-project "$REPO/mod/sg-worldgen-protection")
  case "$CONFIG" in
    A)  ARGS+=(--guard-mode observe --features none --refine off) ;;
    B)  ARGS+=(--guard-mode enforce --features both --refine off) ;;
    C)  ARGS+=(--guard-mode enforce --features both --refine precheck) ;;
    H)  ARGS+=(--guard-mode enforce --features both --refine hybrid) ;;
    HS) ARGS+=(--guard-mode enforce --features both --refine hybrid --shadow) ;;
    P)  ARGS+=(--production) ;;
    PJ) ARGS+=(--production --production-jar) ;;  # N7-D: the built production jar, loaded as a jar
    PE) ARGS+=(--production --stale-lab-env) ;;  # N7-D: production artifact with every lab variable exported: all must be ignored          # N7-B: production configuration, no lab settings
    R)  ARGS+=(--guard-mode enforce --features both --refine hybrid --fault precheck_blind) ;;  # N7-B: injected drift the startup check cannot see -> runtime watch
    F)  ARGS+=(--guard-mode enforce --features both --refine hybrid --lab-fingerprint-break ${BREAK:-both}) ;;  # N7-C: simulated vanilla change -> zone guard
    Z)  ARGS+=(--guard-mode enforce --features both --refine hybrid --fault zone_probe) ;;  # N7-D: adversarial probe of the 3x3 write-zone boundary
    X)  ARGS+=(--guard-mode enforce --features both --refine hybrid --lab-foreign ${FOREIGN:-both}) ;;  # N7-D: inert foreign transformer on the vanilla class -> must go to zone
    RN) ARGS+=(--guard-mode enforce --features both --refine hybrid --fault precheck_blind_near) ;;  # N7-D: replica wrong only where a protected piece is near (passes calibration)
    O)  ARGS+=(--guard-mode enforce --features both --refine hybrid --oracle monster_room) ;;  # oracle: vanilla unguarded, replica vs reality
    RNB) ARGS+=(--guard-mode enforce --features both --refine off --fault precheck_blind_near) ;;  # N7-E: the N7-D damage scenario under the production box decision
    RB) ARGS+=(--guard-mode enforce --features both --refine off --fault box_shrunk) ;;  # N7-E: module believes a smaller footprint than vanilla has
    RG) ARGS+=(--guard-mode enforce --features both --refine hybrid --fault geode_shrunk) ;;  # N7-C: injected geode bound drift
    *) echo "unknown config $CONFIG" >&2; exit 2 ;;
  esac
  [ -n "$BG" ] && export SG01_BG_THREADS="$BG"
fi
mkdir -p "$OUT"
python3 "$REPO/validation/minecraft-visual/sg03-natural/collision_lab.py" "${ARGS[@]}" > "$OUT/$TAG.log" 2>&1
