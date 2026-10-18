#!/usr/bin/env bash
# Download the official Minecraft 26.3 server jar and verify the SHA-1 published in Mojang's version manifest.
set -euo pipefail
dest=${1:?usage: fetch-server.sh DEST_JAR [VERSION]}
version=${2:-26.3}
manifest=$(curl -fsS https://piston-meta.mojang.com/mc/game/version_manifest_v2.json)
version_url=$(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); print(next(v["url"] for v in m["versions"] if v["id"]==sys.argv[2]))' "$manifest" "$version")
meta=$(curl -fsS "$version_url")
read -r url sha1 < <(python3 -c 'import json,sys; d=json.loads(sys.argv[1])["downloads"]["server"]; print(d["url"], d["sha1"])' "$meta")
curl -fsS -o "$dest" "$url"
echo "$sha1  $dest" | sha1sum -c -
