#!/usr/bin/env bash
# Download the official Minecraft server jar and verify the SHA-1 published in Mojang's version manifest.
set -euo pipefail
dest=${1:?usage: fetch-server.sh DEST_JAR [VERSION]}
version=${2:-26.3}
tmp=$(mktemp -d)
curl -fsS https://piston-meta.mojang.com/mc/game/version_manifest_v2.json -o "$tmp/manifest.json"
version_url=$(python3 -c 'import json,sys; print(next(v["url"] for v in json.load(open(sys.argv[1]))["versions"] if v["id"]==sys.argv[2]))' "$tmp/manifest.json" "$version")
curl -fsS "$version_url" -o "$tmp/version.json"
read -r url sha1 < <(python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))["downloads"]["server"]; print(d["url"], d["sha1"])' "$tmp/version.json")
curl -fsS -o "$dest" "$url"
echo "$sha1  $dest" | sha1sum -c -
