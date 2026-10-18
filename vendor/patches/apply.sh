#!/usr/bin/env bash
# Build vendor/mcbuild from a pristine upstream checkout plus the local patch series.
#
#   usage: vendor/patches/apply.sh <pristine-upstream-dir> <output-dir>
#
# Every patch in vendor/patches/mcbuild/ is applied in lexical order. `git apply --check` runs
# before each real apply, and any failure aborts with a non-zero exit so CI fails. Nothing is
# applied partially: the output directory is rebuilt from scratch on every run.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
pristine="$1"
out="$2"

if [ ! -d "$pristine" ]; then
  echo "error: pristine upstream directory not found: $pristine" >&2
  exit 1
fi

rm -rf "$out"
mkdir -p "$out"
cp -a "$pristine"/. "$out"/
rm -rf "$out/.git"
rm -f "$out/UPSTREAM.md" "$out/UPSTREAM_COMMIT"

# Record the pin from the pristine checkout itself, so the metadata cannot disagree with the source.
if [ -d "$pristine/.git" ]; then
  sha="$(git -C "$pristine" rev-parse HEAD)"
  printf '%s\n' "$sha" > "$out/UPSTREAM_COMMIT"
  printf '# Vendored mcbuild\n\nSource: https://github.com/harrynull/mcbuild\n\nUpstream commit: %s\n\nLocal security patches: vendor/patches/mcbuild/ (see vendor/patches/mcbuild/README.md).\n' "$sha" > "$out/UPSTREAM.md"
fi

shopt -s nullglob
patches=("$here"/mcbuild/*.patch)
if [ "${#patches[@]}" -eq 0 ]; then
  echo "error: no patches found in $here/mcbuild" >&2
  exit 1
fi

for patch in "${patches[@]}"; do
  echo "applying $(basename "$patch")"
  (
    cd "$out"
    git apply --check --whitespace=nowarn -p1 "$patch"
    git apply --whitespace=nowarn -p1 "$patch"
  )
done
echo "applied ${#patches[@]} patch(es) to $out"
