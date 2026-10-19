#!/usr/bin/env bash
# N7-A3 runner: one configuration, one site, one order, one repeat. Experimental; see docs/sg-03/n7a3-performance-compatibility.md.
# usage: n73_run.sh OUT_DIR CONFIG SEED CX CZ ORDER REPEAT [KEEP_WORLD=0|1] [BG_THREADS]
# CONFIG: V (vanilla jar, no module) | A (module, observe, no protection) | B (N7-A reach, enforce) |
#         C (N7-A2 refined precheck, enforce) | H (hybrid broad-phase, enforce) | HS (hybrid + shadow check)
# Requires SERVER_JAR (official 26.3 server.jar), SG_PACK (built SG-03 datapack folder), JAVA_HOME (JDK 25) on PATH.
set -euo pipefail
OUT="$1"; CONFIG="$2"; SEED="$3"; CX="$4"; CZ="$5"; ORDER="$6"; REP="$7"; KEEP="${8:-0}"; BG="${9:-}"
: "${SERVER_JAR:?set SERVER_JAR}"; : "${SG_PACK:?set SG_PACK}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
TAG="${CONFIG}_${SEED}_${CX}_${CZ}_${ORDER//:/-}_r${REP}"
ARGS=(--jar "$SERVER_JAR" --pack "$SG_PACK" --out "$OUT/$TAG" --seed "$SEED" --chunk "$CX" "$CZ" --order "$ORDER" --radius 5 --ticks 0 --port 40950)
[ "$KEEP" = 1 ] && ARGS+=(--keep-world)
if [ "$CONFIG" = V ]; then
  [ -n "$BG" ] && ARGS+=(--threads "$BG")
else
  ARGS+=(--fabric-project "$REPO/validation/fabric-protection-spike")
  case "$CONFIG" in
    A)  ARGS+=(--guard-mode observe --features none --refine off) ;;
    B)  ARGS+=(--guard-mode enforce --features both --refine off) ;;
    C)  ARGS+=(--guard-mode enforce --features both --refine precheck) ;;
    H)  ARGS+=(--guard-mode enforce --features both --refine hybrid) ;;
    HS) ARGS+=(--guard-mode enforce --features both --refine hybrid --shadow) ;;
    *) echo "unknown config $CONFIG" >&2; exit 2 ;;
  esac
  [ -n "$BG" ] && export SG01_BG_THREADS="$BG"
fi
mkdir -p "$OUT"
python3 "$REPO/validation/minecraft-visual/sg03-natural/collision_lab.py" "${ARGS[@]}" > "$OUT/$TAG.log" 2>&1
