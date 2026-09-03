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
      commits(last:1){nodes{commit{
        statusCheckRollup{state contexts(first:150){totalCount nodes{
          ... on CheckRun{name status conclusion detailsUrl}
          ... on StatusContext{context state targetUrl}}}}}}}
    }
  }
}' -F owner="$OWNER" -F repo="$REPO" -F n="$N" | jq '
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
  checks: ($p.commits.nodes[0].commit.statusCheckRollup as $r | {
    rollup: $r.state,
    total: $r.contexts.totalCount,
    by_state: ([$r.contexts.nodes[] | (.conclusion // .state // .status)] | group_by(.) | map({(.[0]): length}) | add),
    failing: [$r.contexts.nodes[] | select((.conclusion // .state) as $s | $s == "FAILURE" or $s == "ERROR" or $s == "TIMED_OUT") | (.name // .context)],
    pending: [$r.contexts.nodes[] | select(.conclusion == null and (.state // "PENDING") == "PENDING" or .status == "QUEUED" or .status == "IN_PROGRESS" or .status == "WAITING") | (.name // .context)]
  }),
  recent_comments: [$p.comments.nodes[] | {by: .author.login, at: .createdAt, excerpt: .body[:160]}]
}'
