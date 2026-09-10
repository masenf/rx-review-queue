#!/usr/bin/env bash
# Pull the "merge box" for one PR from the GitHub API into a JSON document
# (schema: cache/SCHEMA.md, prstate). Requires the gh CLI (uses GraphQL for
# review-thread resolution, which REST does not expose).
#
#   scripts/fetch_prstate.sh N > cache/runs/YYYY-MM-DD/prstate/N.json
#
# Without gh, the agent gathers the same fields with the GitHub MCP tool
# pull_request_read (methods get / get_reviews / get_review_comments /
# get_check_runs / get_comments) — see references/data-access.md.
set -euo pipefail
N="${1:?pr number}"
OWNER=reflex-dev; REPO=reflex

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

gh api graphql -f query='
query($owner:String!,$repo:String!,$n:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$n){
      number title isDraft state mergeable mergeStateStatus
      author{login} authorAssociation
      autoMergeRequest{enabledBy{login} mergeMethod}
      headRefOid baseRefName
      closingIssuesReferences(first:10){nodes{number title author{login}}}
      reviewDecision
      reviews(last:50){nodes{author{login} state submittedAt authorCanPushToRepository}}
      reviewRequests(first:20){nodes{requestedReviewer{... on User{login} ... on Team{slug}}}}
      reviewThreads(first:100){totalCount nodes{isResolved isOutdated comments(first:1){nodes{author{login} body createdAt}}}}
      comments(last:30){nodes{author{login} createdAt body}}
      commits(last:1){nodes{commit{statusCheckRollup{state}}}}
    }
  }
}' -F owner="$OWNER" -F repo="$REPO" -F n="$N" > "$tmp"

head_sha=$(jq -r '.data.repository.pullRequest.headRefOid' "$tmp")
checks=$(gh api --paginate "/repos/$OWNER/$REPO/commits/$head_sha/check-runs?per_page=100" | jq -s '
  [.[].check_runs[]] as $runs |
  def norm:
    if . == null then null
    else ascii_upcase | gsub("-"; "_")
    end;
  def state_of($r): (($r.conclusion // $r.status) | norm);
  def is_failing($s): ["FAILURE", "ERROR", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"] | index($s);
  def is_pending($r):
    ($r.conclusion == null) or
    ((($r.status // "") | ascii_downcase) | IN("queued", "in_progress", "waiting", "requested", "pending"));
  {
    rollup: (
      if ($runs | length) == 0 then null
      elif any($runs[]; is_failing(state_of(.))) then "FAILURE"
      elif any($runs[]; is_pending(.)) then "PENDING"
      else "SUCCESS"
      end
    ),
    total: ($runs | length),
    by_state: ([$runs[] | state_of(.)] | group_by(.) | map({(.[0]): length}) | add // {}),
    failing: [$runs[] | select(is_failing(state_of(.))) | .name],
    pending: [$runs[] | select(is_pending(.)) | .name]
  }
')

jq --argjson checks "$checks" '
.data.repository.pullRequest as $p |
{
  number: $p.number,
  fetched_at: (now | todate),
  head_sha: $p.headRefOid,
  mergeable: $p.mergeable,                 # MERGEABLE | CONFLICTING | UNKNOWN (re-fetch if UNKNOWN)
  merge_state: $p.mergeStateStatus,        # CLEAN | BLOCKED | BEHIND | DIRTY | UNSTABLE | ...
  auto_merge: ($p.autoMergeRequest != null),
  review_decision: $p.reviewDecision,      # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | null
  linked_issues: [$p.closingIssuesReferences.nodes[] | {number, title, filed_by: .author.login}],
  reviews: [$p.reviews.nodes[] | {by: .author.login, state, at: .submittedAt, can_push: .authorCanPushToRepository}],
  awaiting: [$p.reviewRequests.nodes[].requestedReviewer | (.login // .slug)],
  threads: {
    total: $p.reviewThreads.totalCount,
    unresolved: [$p.reviewThreads.nodes[] | select(.isResolved|not) | {by: .comments.nodes[0].author.login, outdated: .isOutdated, first_comment: (.comments.nodes[0].body[:200])}]
  },
  checks: ($checks + {rollup: ($p.commits.nodes[0].commit.statusCheckRollup.state // $checks.rollup)}),
  recent_comments: [$p.comments.nodes[] | {by: .author.login, at: .createdAt, excerpt: .body[:160]}]
}' "$tmp"
