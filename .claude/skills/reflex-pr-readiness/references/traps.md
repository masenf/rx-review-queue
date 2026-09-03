# Traps: every way this board has been wrong

Read before collecting. Add to this file whenever a run finds a new one; it is
the memory the job otherwise lacks.

## Authentication
- An unauthenticated GitHub view drops draft badges, role badges and every
  merge-box detail, and still renders a plausible board. Verify identity first
  and treat the review/CI layer as **absent**, not uncertain, if it fails.

## Listing
- Page text of the PR list drops draft and role badges; read the DOM or the API.
- Row count vs the "N Open" counter differing by one or two means a merge landed
  mid-scrape. Re-read and reconcile.
- Count author concentration from the role badge / `author_association`, not
  from commit metadata: the head commit is authored "Claude" on many branches.

## Search qualifiers
- `status:success` returned 8 PRs; 2 were green. Five were fork PRs with "N
  workflows awaiting approval" (no test workflow ever ran), one had passed two
  AI-reviewer checks only, and a PR with 11 failing checks appeared under it.
- `review:approved` has missed counting approvals on three separate runs
  (#6927 on Aug 28 15:30, #6963 on Aug 28 23:30, while returning only #6899).
  **Never state "N approvals repo-wide" from search.** Read merge boxes.
- An approval from a reviewer without write access does not satisfy CODEOWNERS
  (`reflex-dev/reflex-team`). Distinguish "has an approval" from "has a
  counting approval".

## Git measurement
- **Recompute against today's main.** Main moves 20+ commits between runs;
  behind-main figures copied forward are the single most common error.
- Counting `.md` files does not measure documentation. Changelog fragments are
  markdown. Real docs are `docs/**/*.md|mdx`. PRs labelled `documentation`
  routinely ship only Python.
- Fragments live in `news/` and `packages/*/news/`. Per-package fragments are
  **required**: a PR touching `reflex/` and two packages needs three. Never
  report per-package duplication as a collision.
- Fragments named after a **different** number than the PR are usually correct:
  towncrier's `issue_format` resolves to `/issues/{issue}`, so naming by the
  linked issue is the convention.
- `**/components/*.py` changed without `pyi_hashes.json` is worth flagging
  only when CI is unverified. On recent runs every such PR passed CI; the
  heuristic over-flags.
- Stacked PRs: a head that is an ancestor of another PR cannot merge
  independently and its vs-main diff includes all ancestors. Quote a
  parent-relative diff only when parent and child share a merge-base;
  otherwise quote vs-main and label it.
- Compiled `CHANGELOG.md` edits mark release/backport PRs, not docs work.

## Merge box / API state
- **Bot summary comments go stale.** greptile has posted "5/5, safe to merge"
  on unmergeable PRs, on PRs with red checks, and on PRs with open maintainer
  objections, and "not safe to merge" over a finding it had already withdrawn.
  Verify against commit sequence and thread state, never summaries.
- **PR bodies drift from their code**; several have no body beyond a bot
  banner. Trust the diff.
- The merge box loads lazily (more so in the built-in browser) and can show
  "All checks have passed / Update branch" before settling into conflicts.
  Re-read until settled; via the API, `mergeable: null/UNKNOWN` means re-fetch.
  Fork PRs awaiting workflow approval may never settle their mergeability line.
- **"N workflows awaiting approval"** means CI has *never run*: common on fork
  PRs from first-time contributors, who cannot fix it. Not green, not passing.
  Expect ~106 checks "pending" behind the gate with only two bot reviewers green.
- Check totals are not comparable across PRs: current PRs run ~110 checks,
  older ones ~67. A low success count can mean an old run, not a narrow one.
- "Auto-merge enabled" does not mean it will fire; verify the required
  contexts have actually reported.
- GitHub treats **any** unresolved review thread as a hard merge blocker,
  including bot threads the author already rebutted. Call those out: they are
  a click, not a code change.
- Read failing job logs. Historical verdict flips: three failures → one
  missing towncrier fragment; "flaky" → the PR's own new docs page failing to
  build; a failing Lighthouse job → a `bun` download network error; a
  windows-only unit failure → in a file the PR does not touch.

## Scoring / presentation
- Where CI never ran, the workflow-approval click is the binding blocker; do
  not also claim a code finding as "the one fix".
- Keep the ranking monotonic in its own score; explain overrides on the card.
- Stat tiles must equal tab counts must equal card counts.
- Never put actively pushed drafts in closure candidates.

## Fact-check
- Git and merge-box figures are taken minutes apart. On Aug 28 23:30 the
  auditor flagged "#6933 is 21 behind, not current"; the author had pushed a
  main-merge at 16:14:59 PT inside the fetch window. Re-fetch before changing
  the board when audit and live data disagree.

## Runner
- Cowork: never `tabs_close`; leave a tab open; subagents default to cleaning
  up tabs, so tell them not to. `gh` and the API were unreachable there.
- Claude Code remote: the GitHub MCP only covers repos attached to the
  session; `api.github.com` is 403'd at the proxy. Without reflex-dev/reflex
  attached, only the git layer is available.
- Background processes do not survive between tool calls; chunk fetches.
