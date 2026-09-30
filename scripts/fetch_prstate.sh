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
timeline_tmp=$(mktemp)
review_comments_tmp=$(mktemp)
threads_tmp=$(mktemp)
trap 'rm -f "$tmp" "$timeline_tmp" "$review_comments_tmp" "$threads_tmp"' EXIT

gh api graphql -f query='
query($owner:String!,$repo:String!,$n:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$n){
      number title isDraft state mergeable mergeStateStatus
      updatedAt
      author{login} authorAssociation
      headRepository{nameWithOwner}
      autoMergeRequest{enabledBy{login} mergeMethod}
      headRefOid baseRefName
      closingIssuesReferences(first:10){nodes{number title author{login}}}
      reviewDecision
      reviews(last:100){nodes{author{login} authorAssociation state submittedAt authorCanPushToRepository commit{oid}}}
      reviewRequests(first:20){nodes{requestedReviewer{... on User{login} ... on Team{slug}}}}
      reviewThreads(first:100){totalCount nodes{isResolved isOutdated comments(first:1){nodes{author{login} body createdAt}}}}
      comments(last:30){nodes{author{login} authorAssociation createdAt body}}
      commits(last:1){nodes{commit{oid committedDate statusCheckRollup{state}}}}
    }
  }
}' -F owner="$OWNER" -F repo="$REPO" -F n="$N" > "$tmp"

head_sha=$(jq -r '.data.repository.pullRequest.headRefOid' "$tmp")
thread_total=$(jq '.data.repository.pullRequest.reviewThreads.totalCount' "$tmp")
if [ "$thread_total" -gt 100 ]; then
  gh api graphql --paginate --slurp -f query='
  query($owner:String!,$repo:String!,$n:Int!,$endCursor:String){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$n){
        reviewThreads(first:100,after:$endCursor){
          nodes{isResolved isOutdated comments(first:1){nodes{author{login} body createdAt}}}
          pageInfo{hasNextPage endCursor}
        }
      }
    }
  }' -F owner="$OWNER" -F repo="$REPO" -F n="$N" |
    jq '[.[].data.repository.pullRequest.reviewThreads.nodes[]]' > "$threads_tmp"
else
  jq '.data.repository.pullRequest.reviewThreads.nodes' "$tmp" > "$threads_tmp"
fi
gh api --paginate "/repos/$OWNER/$REPO/issues/$N/timeline?per_page=100" | jq -s '[.[].[]]' > "$timeline_tmp"
gh api --paginate "/repos/$OWNER/$REPO/pulls/$N/comments?per_page=100" | jq -s '[.[].[]]' > "$review_comments_tmp"
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
    ,actions_total: ([$runs[] | select(.app.slug == "github-actions")] | length)
  }
')

jq --arg canonical "$OWNER/$REPO" --argjson checks "$checks" --slurpfile timeline "$timeline_tmp" --slurpfile review_comments "$review_comments_tmp" --slurpfile threads "$threads_tmp" '
def is_known_bot:
  . == null or test("^(greptile-apps|cubic-dev-ai|chatgpt-codex-connector|copilot-pull-request-reviewer|github-actions|github-advanced-security|codspeed|dependabot)(\\[bot\\])?$"; "i");
.data.repository.pullRequest as $p |
{
  number: $p.number,
  fetched_at: (now | todate),
  author_login: $p.author.login,
  author_association: $p.authorAssociation,
  head_repo: $p.headRepository.nameWithOwner,
  head_sha: $p.headRefOid,
  mergeable: $p.mergeable,                 # MERGEABLE | CONFLICTING | UNKNOWN (re-fetch if UNKNOWN)
  merge_state: $p.mergeStateStatus,        # CLEAN | BLOCKED | BEHIND | DIRTY | UNSTABLE | ...
  auto_merge: ($p.autoMergeRequest != null),
  review_decision: $p.reviewDecision,      # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | null
  linked_issues: [$p.closingIssuesReferences.nodes[] | {number, title, filed_by: .author.login}],
  reviews: [$p.reviews.nodes[] | {by: .author.login, association: .authorAssociation, state, at: .submittedAt, can_push: .authorCanPushToRepository, commit_id: .commit.oid}],
  counting_approval: any($p.reviews.nodes[];
    .state == "APPROVED" and
    .commit.oid == $p.headRefOid and
    .authorCanPushToRepository and
    .author.login != $p.author.login and
    ((.author.login | is_known_bot) | not)
  ),
  awaiting: [$p.reviewRequests.nodes[].requestedReviewer | (.login // .slug)],
  threads: {
    total: $p.reviewThreads.totalCount,
    unresolved: [$threads[0][] | select(.isResolved|not) | {by: .comments.nodes[0].author.login, outdated: .isOutdated, first_comment: (.comments.nodes[0].body[:200])}]
  },
  checks: ($checks + {rollup: ($p.commits.nodes[0].commit.statusCheckRollup.state // $checks.rollup)}),
  ci_never_ran: ($p.headRepository.nameWithOwner != $canonical and $checks.actions_total == 0),
  recent_comments: [$p.comments.nodes[] | {by: .author.login, association: .authorAssociation, at: .createdAt, excerpt: .body[:160]}],
  head_activity_at: (
    [$timeline[0][] |
      select(.event == "committed" or .event == "head_ref_force_pushed") |
      (.created_at // .committer.date // .author.date)] |
    map(select(. != null)) | max // $p.commits.nodes[0].commit.committedDate
  ),
  interaction_events: (
    ([
      $timeline[0][] |
      if .event == "commented" then
        {kind: "comment", by: .user.login, association: .author_association, at: .created_at}
      elif .event == "reviewed" then
        {kind: "review", by: .user.login, association: .author_association, at: .submitted_at, state: .state}
      else empty end
    ] + [
      $review_comments[0][] |
      {kind: "review_comment", by: .user.login, association: .author_association, at: .created_at}
    ]) |
    map(select(.by != null and .at != null)) |
    unique_by([.kind, .by, .at]) |
    sort_by(.at)
  )
}' "$tmp"
