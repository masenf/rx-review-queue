#!/usr/bin/env bash
# Maintain a bare mirror of reflex-dev/reflex under cache/repo.git and fetch
# main plus PR heads into it. Pure git; needs no GitHub credentials (the
# repo is public).
#
#   scripts/prscan.sh init                 create cache/repo.git if missing
#   scripts/prscan.sh fetch-main           refresh refs/remotes/origin/main
#   scripts/prscan.sh fetch-prs N [N...]   fetch refs/pull/N/head -> refs/pr/N
#   scripts/prscan.sh fetch-from FILE      same, numbers read from FILE (one per line)
#
# fetch-prs / fetch-from chunk the refspecs (CHUNK, default 14) so a single
# git invocation stays well under a tool-call timeout ceiling. Re-run the
# same command to resume; already-fetched refs are cheap no-ops.
#
# Optional: REFLEX_ALTERNATES=/path/to/reflex/.git/objects makes the first
# fetch far faster by sharing objects with an existing clone.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$ROOT/cache/repo.git"
REMOTE_URL="${REFLEX_REMOTE_URL:-https://github.com/reflex-dev/reflex.git}"
CHUNK="${CHUNK:-14}"

g() { git --git-dir="$REPO" "$@"; }

cmd_init() {
  if [ -d "$REPO" ]; then
    echo "repo.git exists at $REPO"
  else
    git init --bare -q "$REPO"
    g remote add origin "$REMOTE_URL"
    echo "created $REPO"
  fi
  if [ -n "${REFLEX_ALTERNATES:-}" ] && [ -d "$REFLEX_ALTERNATES" ]; then
    mkdir -p "$REPO/objects/info"
    grep -qxF "$REFLEX_ALTERNATES" "$REPO/objects/info/alternates" 2>/dev/null \
      || echo "$REFLEX_ALTERNATES" >> "$REPO/objects/info/alternates"
    echo "alternates -> $REFLEX_ALTERNATES"
  fi
}

cmd_fetch_main() {
  cmd_init >/dev/null
  # `unable to unlink ... Operation not permitted` on some mounts is harmless.
  g fetch -q origin "+refs/heads/main:refs/remotes/origin/main" 2>&1 | grep -v 'unable to unlink' || true
  echo "origin/main = $(g rev-parse --short refs/remotes/origin/main)"
}

fetch_numbers() {
  cmd_init >/dev/null
  local nums=("$@") i=0 specs=()
  while [ $i -lt ${#nums[@]} ]; do
    specs=()
    for n in "${nums[@]:$i:$CHUNK}"; do
      specs+=("+refs/pull/$n/head:refs/pr/$n")
    done
    g fetch -q origin "${specs[@]}" 2>&1 | grep -v 'unable to unlink' || true
    echo "fetched ${nums[*]:$i:$CHUNK}"
    i=$((i + CHUNK))
  done
}

case "${1:-}" in
  init) cmd_init ;;
  fetch-main) cmd_fetch_main ;;
  fetch-prs) shift; fetch_numbers "$@" ;;
  fetch-from) shift; mapfile -t nums < <(grep -Eo '^[0-9]+' "$1"); fetch_numbers "${nums[@]}" ;;
  *) sed -n '2,20p' "$0"; exit 2 ;;
esac
