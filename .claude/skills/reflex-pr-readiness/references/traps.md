# Traps: every way this board has been wrong

Read before collecting. Add to this file whenever a run finds a new one; it is
the memory the job otherwise lacks.

## Authentication
- An unauthenticated GitHub view drops draft badges, role badges and every
  merge-box detail, and still renders a plausible board. Verify identity first
  and treat the review/CI layer as **absent**, not uncertain, if it fails.

## Listing
- Page text of the PR list drops draft and role badges; read the DOM or the API.
- Sep 3: the listing page returned 92 rows and the search counter said 91
  two minutes later; #7001 had merged at 18:40:32Z between the two calls.
  Confirm the odd one out with `pull_request_read(get)` and drop it; then
  re-fetch main before measuring, or every behind-main figure is off by one.
- `search_pull_requests(... is:closed is:unmerged closed:>TS)` returned 0
  although #7020 was closed unmerged in the window. Recover closed-unmerged
  PRs from the `created:>TS` list (state closed, absent from `is:merged`)
  and confirm each with `issue_read`.
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
- Don't regex git's English conflict messages to extract file paths — the
  wording varies by conflict type (`CONFLICT (content): Merge conflict in
  <path>` has no trailing period; `CONFLICT (modify/delete): <path> deleted
  in ... and modified in ...` doesn't match a content-conflict regex at all)
  and each new shape silently drops files instead of erroring. Sep 4: a
  trailing-period assumption missed 5 PRs' conflicts entirely; the fix for
  that still missed #5430's and #6723's modify/delete conflicts. Parse
  `git merge-tree --write-tree`'s own staged-entry lines instead: the tree-OID
  line, then one `<mode> <sha> <stage>\t<path>` line per conflicted path up to
  the first blank line — every conflict type lands there regardless of the
  prose that follows.

## Merge box / API state
- The GitHub MCP `pull_request_read(get)` does **not** return the
  `mergeable` boolean. Derive it from `mergeable_state`: `dirty` =
  conflicts, `unknown` = re-fetch once, anything else = no conflicts. Do not
  write UNKNOWN for a PR whose state is `blocked`.
- A head pushed minutes before the scan shows only the two AI-reviewer check
  runs and looks exactly like "workflows awaiting approval" (#7036, pushed
  18:35Z, scanned 18:41Z). Check the head push time before flagging
  `ci_never_ran` on a non-first-timer.
- Stacked PRs whose base is another branch report `mergeable_state: clean`
  even when only the benchmark workflow ran on the head (Alek99's July perf
  stack). CLEAN is relative to the base branch and says nothing about unit
  tests, pre-commit or changelog: list which workflows actually ran.
- `CHANGES_REQUESTED` survives the pushes that address it (#7006, #6968 on
  Sep 3). Report it as "stale changes-requested: dismiss or re-review", a
  maintainer click, not an author blocker.
- Greptile flags a fragment named after the linked issue as "release note
  links wrong PR" (#7004). Issue-naming resolves through towncrier's issue
  link, but check the *count* too: #7004 also carried a root
  `news/7004.bugfix.md` for a package it does not touch. Read the fragment
  paths against `packages_touched` before calling the thread a false alarm.
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
- A `DISMISSED` review is not automatically a live objection or automatically
  stale — read the ordering. #6917 (Sep 4): masenf's own Aug 31 review was
  self-dismissed by masenf on Sep 3, immediately followed by the author
  addressing every thread and a fresh masenf `APPROVED` on the new head.
  Stopping at "there's a DISMISSED entry" misreads a completed, fully-resolved
  approval as still-contested. Read the full ordered review timeline, not the
  presence of any one state.

## Incremental runs
- From the second run on, a PR whose `listing.updated_at` is unchanged since
  the last run genuinely has no new comments/reviews/threads/checks — safe to
  carry its prstate forward. But **mergeable/conflicting_files can change with
  zero activity on the PR itself**: main moving is enough. Sep 4: #7019
  merging flipped 5 untouched PRs from clean to conflicting overnight.
  Recompute mergeable/conflicting_files (cheap: local `git merge-tree`) and
  days_waiting_on_maintainer fresh for every PR, every run, regardless of
  updated_at. As an integrity check, re-fetch check-runs for any carried-forward
  PR that was non-green last run and confirm it matches before trusting the rest.
- Recompute a since-merged PR's own diff against its real merge commit
  (`diff --stat <first-parent>..<merge-commit>`) before citing its size in
  prose — don't reuse the last pre-merge measurement. #7019 was stacked on
  unmerged #7037 the day before (36 files, including #7037's), and shrank to
  its true 33-file contribution once #7037 landed first. Same root cause as
  "recompute against today's main," applied to something that already merged.
- Run `scripts/delta.py` only after `report.json` exists for the run. Run
  before, and its entered_top15/left_top15 silently compute against an empty
  current-top15 (`entered_top15: []`, `left_top15: <all of yesterday's>`) with
  no error. If a delta looks like nothing entered and everything left the
  top 15, re-run it — don't trust it.

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
- Claude Code remote: background subagents die with a spend-limit 429 and
  report "failed" even after writing most of their files. Check which
  `prstate/N.json` exist and validate them (number, head SHA vs listing)
  before re-running anything; on Sep 3 all 64 files were on disk despite
  four "failed" batches.
- `scripts/render.py` and `scripts/delta.py` were committed without the
  executable bit; run them as `python3 scripts/render.py` if the bit is lost.
- Cowork: never `tabs_close`; leave a tab open; subagents default to cleaning
  up tabs, so tell them not to. `gh` and the API were unreachable there.
- Claude Code remote: the GitHub MCP only covers repos attached to the
  session; `api.github.com` is 403'd at the proxy. Without reflex-dev/reflex
  attached, only the git layer is available.
- Background processes do not survive between tool calls; chunk fetches.
