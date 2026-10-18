#!/usr/bin/env bash

mark_stage() {
  local name=$1 verdict=$2 result_file=$3
  local replacement="$name=$verdict"
  if grep -Eq "^${name}=" "$result_file"; then
    sed -i "s/^${name}=.*/${replacement}/" "$result_file"
  else
    printf '%s\n' "$replacement" >> "$result_file"
  fi
}
