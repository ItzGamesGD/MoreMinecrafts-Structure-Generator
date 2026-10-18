#!/usr/bin/env bash
# Regenerate the local patch series from the pristine upstream tree and the current vendor tree.
#
#   usage: vendor/patches/make-patch.sh <pristine-upstream-dir> <output.patch>
#
# Only files git would track (tracked, or untracked and not ignored) are included, so build
# outputs such as mod/build and __pycache__ never end up in a patch. The generated UPSTREAM.md
# and UPSTREAM_COMMIT files are excluded: the sync workflow writes them from the pin.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(git -C "$here" rev-parse --show-toplevel)"
pristine="$1"
out_patch="$2"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# 1. Pristine side: a git repo whose first commit is the unmodified upstream tree.
mkdir "$work/base"
cp -a "$pristine"/. "$work/base"/
rm -rf "$work/base/.git"
rm -f "$work/base/UPSTREAM.md" "$work/base/UPSTREAM_COMMIT"  # generated metadata, excluded from both sides
git -C "$work/base" init -q
git -C "$work/base" add -A
git -C "$work/base" -c user.name=patch -c user.email=patch@localhost commit -q -m pristine

# 2. Current side: the files git tracks for vendor/mcbuild, minus generated metadata.
mkdir "$work/current"
(cd "$repo_root" && git ls-files -co --exclude-standard vendor/mcbuild) |
  grep -v -E '(^|/)(UPSTREAM\.md|UPSTREAM_COMMIT)$' |
  while IFS= read -r path; do
    rel="${path#vendor/mcbuild/}"
    if [ -f "$repo_root/$path" ]; then
      mkdir -p "$work/current/$(dirname "$rel")"
      cp -p "$repo_root/$path" "$work/current/$rel"
    fi
  done

# 3. Replace the pristine work tree with the current file set and diff the two.
find "$work/base" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a "$work/current"/. "$work/base"/
git -C "$work/base" add -A
git -C "$work/base" diff --cached --binary > "$out_patch"
echo "wrote $out_patch ($(grep -c '^diff --git' "$out_patch") file(s))"
