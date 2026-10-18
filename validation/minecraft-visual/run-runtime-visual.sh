#!/usr/bin/env bash
set -euo pipefail
repo=$1
pack=$2
fixture="$repo/validation/minecraft-visual"
server_pid_file="$fixture/run/server.pid"
printf 'server-startup=NOT RUN\ndatapack-load=NOT RUN\ntemplate-placement=NOT RUN\njigsaw-placement=NOT RUN\nclient-startup=NOT RUN\nworld-join=NOT RUN\nplaza-screenshot=NOT RUN\nscreenshots=NOT RUN\n' > "$fixture/evidence/runtime-result.txt"
cleanup() {
  if [ -f "$server_pid_file" ]; then
    server_pid=$(cat "$server_pid_file")
    kill -- "-$server_pid" 2>/dev/null || kill "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Keep the server and its acceptance commands in the same Actions step as the client.
# GitHub Actions tears down background processes between steps.
bash "$fixture/run-acceptance.sh" "$repo" "$pack" --keep-server
bash "$fixture/capture-client.sh" "$repo"
