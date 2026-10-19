#!/usr/bin/env bash
# N7-A2 experiment matrix (experimental; see docs/sg-03/n7a2-guard-validation.md). Runs collision_lab.py against the Fabric spike.
# usage: n72_matrix.sh OUT_DIR ARM [ARM...]    ARM in: M0 A B C D M1 M2 O K F
# Requires: SERVER_JAR (official 26.3 server.jar), SG_PACK (built SG-03 datapack folder), JAVA_HOME (JDK 25) on PATH.
set -euo pipefail
OUT="$1"; shift
: "${SERVER_JAR:?set SERVER_JAR to the official 26.3 server.jar}"
: "${SG_PACK:?set SG_PACK to the built SG-03 datapack folder}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
SITES=("173 -19 15 s173a" "173 -18 36 s173b" "42 4 13 s42a" "42 6 -19 s42b")
ORDERS=("rowmajor" "rowmajor_rev" "colmajor" "colmajor_rev" "spiral_out" "spiral_in" "random:1" "random:2")

# arm -> guard-mode features fixture refine oracle
arm_args() {
  case "$1" in
    A) echo "observe both none off off" ;;      # vanilla baseline: observe only, nothing cancelled
    B) echo "enforce geode none off off" ;;     # geode guard only
    C) echo "enforce both none off off" ;;      # N7-A reach, both hooks enforced
    D) echo "enforce both none precheck off" ;; # refined monster guard, both hooks enforced
    M0) echo "observe both no_geode off off" ;; # geode fixture, monster room unguarded (causal baseline)
    M1) echo "enforce monster_room no_geode off off" ;;
    M2) echo "enforce monster_room no_geode precheck off" ;;
    O) echo "enforce geode none off monster_room" ;; # oracle: monster room unguarded, outcome classified
    K) echo "enforce geode none off monster_room" ;;
    F) echo "enforce both none off off" ;;      # fault injection, see FAULT env
    *) echo "unknown arm $1" >&2; exit 2 ;;
  esac
}

for ARM in "$@"; do
  read -r GM FE FX RF OR <<<"$(arm_args "$ARM")"
  for site in "${SITES[@]}"; do set -- $site; SEED=$1; CX=$2; CZ=$3; NAME=$4
    for ORD in "${ORDERS[@]}"; do
      T="${ORD//:/-}"
      if [ "$ARM" = F ]; then
        for FAULT in out_of_range status_too_high missing_start; do
          TAG="F_${FAULT}_${NAME}_${T}"
          [ "$NAME" = s173b ] && [ "$T" = spiral_out ] || continue
          python3 "$REPO/validation/minecraft-visual/sg03-natural/collision_lab.py" --jar "$SERVER_JAR" --pack "$SG_PACK" --out "$OUT/$TAG" \
            --seed "$SEED" --chunk "$CX" "$CZ" --order "$ORD" --radius 5 --fabric-project "$REPO/validation/fabric-protection-spike" \
            --guard-mode "$GM" --features "$FE" --fixture "$FX" --refine "$RF" --oracle "$OR" --fault "$FAULT" > "$OUT/$TAG.log" 2>&1
        done
        continue
      fi
      TAG="${ARM}_${NAME}_${T}"
      python3 "$REPO/validation/minecraft-visual/sg03-natural/collision_lab.py" --jar "$SERVER_JAR" --pack "$SG_PACK" --out "$OUT/$TAG" \
        --seed "$SEED" --chunk "$CX" "$CZ" --order "$ORD" --radius 5 --fabric-project "$REPO/validation/fabric-protection-spike" \
        --guard-mode "$GM" --features "$FE" --fixture "$FX" --refine "$RF" --oracle "$OR" > "$OUT/$TAG.log" 2>&1
    done
  done
done
