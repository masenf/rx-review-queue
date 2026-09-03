---
name: reflex-pr-readiness
description: Weekday review-readiness triage of open non-draft PRs in reflex-dev/reflex. Ranks PRs by how close they are to merging, publishes the board to artifacts/index.html, and commits the run data to this repo. Runner-agnostic; needs an authenticated GitHub data source plus git.
---

Assess which open pull requests in **reflex-dev/reflex** are most ready for
review and merging, update the board in `artifacts/index.html`, commit the
run's data under `cache/runs/<date>/`, push, and report what changed.

The run has no memory except this repository. Everything needed is here:

- `references/data-access.md` — how to reach GitHub from each runner (Claude
  Code remote, Cowork, local CLI) and which fields substitute for the merge box.
- `references/traps.md` — every way this task has produced a wrong board so
  far. Read it before collecting data, not after.
- `references/scoring.md` — the ranking rubric and bucket definitions.
- `references/publishing.md` — the board, the commit, the chat message.
- `cache/SCHEMA.md` — the JSON files you read and write.

Budget: about 60 non-draft PRs, ~110 checks each. Parallelise the per-PR
state gathering with subagents in batches of 5–6; do the listing, git
measurement, scoring and publishing yourself.

## Step 0 — Establish access first

1. Decide today's run directory: `RUN=cache/runs/$(date -u +%F)`; if it already
   exists with a `report.json`, another run happened today. **Do not race
   it**: read it, and either stop (if it is fresh) or write to `${RUN}-2`.
2. Pick a GitHub data source per `references/data-access.md` and **verify the
   identity** it is authenticated as. The expected login is **masenf**. Record
   it in `report.json → run.github_login`.
3. If no authenticated source is available, say so plainly, still do the git
   measurement layer, and mark `run.review_ci_layer = "absent"` on the board.
   An unauthenticated view silently loses draft flags, role badges and every
   merge-box detail and produces a board that looks fine and is wrong.
4. `scripts/prscan.sh fetch-main` — creates `cache/repo.git` if needed and
   refreshes `origin/main`. No credentials required.

## Step 1 — Enumerate open PRs → `$RUN/listing.json`

Collect **every** open PR, drafts included: number, title, author,
`author_association` (the role badge), draft flag, labels, timestamps, comment
count, head SHA, fork or not. Use `scripts/fetch_listing.sh` where the REST
API is reachable; otherwise page through the GitHub MCP `list_pull_requests`
tool (perPage 100, `fields` without `body`) and write the same schema.

Cross-check `prs.length` against the repo's open-PR counter. A difference of
one or two means a merge landed mid-scrape: re-read and reconcile, do not guess.

**Exclude drafts from all ranking.** Write the non-draft numbers to
`$RUN/nondraft.txt`. Note drafts whose titles self-identify ("DO NOT MERGE",
"wip") and, separately, drafts pushed in the last week: those are live work,
never closure candidates.

## Step 2 — Measure real diffs → `$RUN/measurements.json`

Do not trust PR descriptions about what changed. Measure it:

```
scripts/prscan.sh fetch-from $RUN/nondraft.txt     # chunked, resumable
scripts/measure.py $RUN/listing.json -o $RUN/measurements.json
```

Per PR this yields files / insertions / deletions / commits ahead / **commits
behind today's main** / path buckets / fragment expectations / stack
membership, computed from `merge-base(origin/main, pr)..pr`. Every number is
recomputed on every run; behind-main figures copied forward are the single most
common historical error. Read `references/traps.md § Bucketing` before
interpreting buckets: markdown is not docs, per-package fragments are required
not duplicated, fragments named after an issue number are correct.

## Step 3 — Per-PR review and CI state → `$RUN/prstate/N.json`

For every non-draft PR gather what the **merge box** would show: mergeability
and conflicting files, check rollup with the **names** of failing and pending
checks, whether CI ever ran (fork PRs: "N workflows awaiting approval"), review
decision, each approval with date and whether the reviewer has write access
(a **counting** approval), changes-requested and whether dismissed, unresolved
review threads and who opened them, reviewers still awaiting, linked issue and
**who filed it**, whether the body has concrete repro steps, and the substance
of each outstanding ask with whether it was addressed.

**Read the failing job logs**, not just the check name. This has repeatedly
changed the verdict (one missing news fragment behind three red checks; a
"flake" that was the PR's own docs page failing to build; a windows-only unit
failure in a file the PR does not touch). Write what you found to
`failing_job_findings`.

Use `scripts/fetch_prstate.sh N` where `gh` works; otherwise assemble the same
JSON from the GitHub MCP `pull_request_read` methods (`get`, `get_reviews`,
`get_review_comments`, `get_check_runs`, `get_comments`) and `get_job_logs`.
Delegate in batches of 5–6 PRs per subagent. Each subagent gets: the data-source
instructions, the schema, the trap list in `references/traps.md § Merge box`,
and the exact list of numbers. Tell it to write files, not prose.

## Step 4 — Score and bucket → `$RUN/report.json`

Rank by **how close each PR is to merging if a maintainer looks at it today**,
per `references/scoring.md`. Keep the ranking monotonic in its own score; if
you override, say why on the card (`override_reason`).

Produce, in `report.json`:

- **top15** — ranked, with evidence and the specific thing standing in the way.
- **one_fix_away** — a single identified blocker each, grouped by whose move it
  is (`maintainer` / `author`). Where CI never ran, the workflow-approval click
  *is* the blocker: put those in `fast_lane` or `one_fix_away.maintainer`, and
  do not also claim a code finding as "the one fix".
- **fast_lane** — mergeable at a glance. Verify "docs-only" against the real
  file list in `measurements.json`.
- **closure** — too broad, too niche, or abandoned. Stale PR but legitimate
  issue → "close the PR, keep issue #N" (`keep_issue`). Never an actively
  pushed draft.
- **stacks / conflict_clusters / structural** — chains from `measurements.stacks`
  with notes; PRs fighting over the same files.
- **patterns** — counting approvals repo-wide (from merge boxes, never from
  search), PRs never human-reviewed, contributors pinging into silence with day
  counts, fork PRs with unrun CI, fragment problems, author concentration
  (from `author_association` in the listing, never from commit authorship).
- **delta** — start from `scripts/delta.py $RUN`, then annotate merged vs closed
  from the API (`is:pr merged:>PREV_RUN_TS`, `created:>PREV_RUN_TS`).
- **attention** — the bullets that lead the chat message: cheap unblocks first
  (an unclicked workflow approval, an unresolved thread a bot already withdrew,
  a missing news fragment), then contributors waiting on a maintainer reply.
- **stats** — the header tiles. They must agree with the tab counts.

## Step 5 — Verify

Run **one adversarial fact-check subagent** over `report.json` with access to
`$RUN/` and `cache/repo.git`, instructed to hunt for errors, not confirm. It
must check: every numeric claim against `merge-base(main,pr)..pr`; every draft
flag, author and title against `listing.json`; every cited SHA resolves and is
an ancestor of the PR it is attributed to; author-concentration arithmetic;
open/merged/closed reconciliation against the previous run; stat tiles vs tab
counts vs card counts; group totals that should sum; and any claim asserted as
fact the data cannot support.

**Judge its findings.** Git figures and API figures are taken minutes apart;
a PR pushed in that window makes them disagree and the auditor will call it an
error. When audit and API disagree, **re-fetch that PR** before changing
anything. Fix what is genuinely wrong and list the corrections in
`method.audit_corrections`.

## Step 6 — Publish

```
scripts/render.py $RUN            # -> artifacts/index.html + artifacts/history/<date>.html
```

Write the chat summary to `$RUN/chat-summary.md`, then commit `cache/runs/<date>/`
and `artifacts/` to **main** and push (`references/publishing.md`). If a
Claude artifact or other hosted surface is available on this runner, publish
`artifacts/index.html` there too, but the commit is the record.

Then report in chat, concisely and without preamble: **lead with what needs
Masen's attention today**, then what changed since the previous run: merged,
closed, newly opened, moved into or out of the top 15, newly blocked or
unblocked.
