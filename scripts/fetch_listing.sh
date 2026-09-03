#!/usr/bin/env bash
# Enumerate open PRs in reflex-dev/reflex via the GitHub REST API and write a
# listing.json (schema: cache/SCHEMA.md).
#
#   scripts/fetch_listing.sh cache/runs/YYYY-MM-DD/listing.json
#
# Uses `gh api` when the gh CLI is present and authenticated, otherwise curl
# with $GH_TOKEN / $GITHUB_TOKEN. If neither reaches api.github.com (some
# sandboxes 403 it at the egress proxy), the agent must build listing.json
# itself from the GitHub MCP `list_pull_requests` tool — see
# .claude/skills/reflex-pr-readiness/references/data-access.md.
set -euo pipefail
OUT="${1:?output path}"
OWNER=reflex-dev; REPO=reflex
TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"

api() { # api <path-with-query>
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh api -H "Accept: application/vnd.github+json" "$1"
  else
    [ -n "$TOKEN" ] || { echo "no gh auth and no GH_TOKEN" >&2; exit 3; }
    curl -fsS -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
      "https://api.github.com$1"
  fi
}

login=$(api /user | jq -r .login)
echo "authenticated as $login" >&2

tmp=$(mktemp)
page=1
: > "$tmp"
while :; do
  chunk=$(api "/repos/$OWNER/$REPO/pulls?state=open&per_page=100&sort=updated&direction=desc&page=$page")
  n=$(echo "$chunk" | jq length)
  echo "$chunk" | jq -c '.[]' >> "$tmp"
  [ "$n" -lt 100 ] && break
  page=$((page + 1))
done

open_count=$(api "/search/issues?q=repo:$OWNER/$REPO+is:pr+is:open&per_page=1" | jq .total_count)

jq -s --arg login "$login" --arg now "$(date -u +%FT%TZ)" --argjson open "$open_count" '
{
  fetched_at: $now,
  source: "rest",
  authenticated_as: $login,
  open_count: $open,
  prs: map({
    number, title, draft,
    author: .user.login,
    author_association,
    labels: [.labels[].name],
    created_at, updated_at,
    comments: null,
    head_sha: .head.sha,
    head_ref: .head.ref,
    head_repo: .head.repo.full_name,
    is_fork: (.head.repo.full_name != "\($OWNER)/\($REPO)"),
    body_present: ((.body // "") | length > 0)
  })
}' "$tmp" | sed "s/\\\\(\$OWNER)\/\\\\(\$REPO)/$OWNER\/$REPO/" > "$OUT"
rm -f "$tmp"

rows=$(jq '.prs | length' "$OUT")
echo "wrote $OUT: $rows rows, search says $open_count open" >&2
[ "$rows" = "$open_count" ] || echo "WARNING: row count != open counter; a merge may have landed mid-scrape. Re-run and reconcile." >&2
