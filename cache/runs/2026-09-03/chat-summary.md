# Reflex PR readiness — 2026-09-03 (first run in rx-review-queue)

Board: https://masenf.github.io/rx-review-queue/ (artifacts/index.html; data in cache/runs/2026-09-03/)

## Needs attention today

Cheap unblocks first:

- **#7037** is approved, green and clean. Merge it; that shrinks **#7019**, which then only needs a re-approve (Farhan's approval was reset by the main-merge push).
- **Five fork PRs are waiting only on "Approve workflows"**: #7004 (fixes #6955, filed by Farhan), #6861 (fixes #6860), #6876 (fixes #6874), #6813, and the one-file docs fix #6875 (fixes #6816). On #7004 the greptile fragment thread is half right: the issue-named reflex-base fragment is fine, but the PR also added a root news/7004.bugfix.md for a package it does not touch.
- **Two stale "changes requested" reviews** from Farhan survive pushes that addressed them: #7006 (react-moment 2.0.2) and #6968 (click_element utility, which fixes the Selenium flake currently failing #7015). Re-review or dismiss.
- **harsh21234i has three green, unreviewed fixes for issues you filed**: #7008 (#6974), #7016 (#6975), #7035 (#7028, one cubic P1 thread open). No human has looked at any of them.
- **#6996** closes your #6983 and is green; the only open item is your #6469-overlap ask, which the head commit appears to address.
- **#6812** (hybrid property): you reviewed positively on Aug 27 but never approved; the head has only moved by a main merge.

Contributors waiting on a maintainer reply:

- **#6841**: your Aug 14 finding (patch breaks computed vars in shared state that depend on root state) is unanswered, but the author's Aug 20 question pinged "@mansef" (typo), so you were never notified. 14 days.
- Decisions parked: **#6815** (hard ValueError for non-uppercase env vars vs a deprecation window; 5 days), **#6768** (you said "holding off" Jul 30).
- Zero maintainer contact: **#6929** (6 days since its last push, green fix), **#6930/#6932** (5 days since their last pushes, now conflicting), **#6770** (38 days, pinged @reflex-dev), **#6813** (34 days), **#6490** (100 days), **#6553** (105 days).
- **#6116** (orjson): the author declared it blocked on #6933, which merged Sep 2. Tell benedikt-bartscher it is unblocked; it needs a rebase and the engineio import fix.

## Since last run (baseline: Aug 28 23:30 PT notes, not a full listing)

- **Merged (19)**: #7039, #7031, #7030, #7029, #7027, #7025, #7021, #7018, #7014, #7012, #7011, #7010, #7009, #7005, #7001 (during this scan), #6995, #6961, #6947, #6933.
- **Closed unmerged (1)**: #7020.
- **Newly opened, still open (12)**: #7040, #7038, #7037, #7036, #7035, #7033, #7019, #7016, #7015, #7008, #7007, #7006.
- **Counting approvals**: 3 (#7037, #7038, #6898, all Farhan). The Aug 28 approvals are gone: #6963 and #6927 closed Aug 28; #6899's approval was dismissed by a later push.
- **Newly unblocked**: #6116 (its blocker #6933 merged).
- Top-15 entered/left cannot be computed against a notes-only baseline; tomorrow's run will have a real one.

## Caveats

- Review/CI layer present (GitHub MCP as masenf). api.github.com unreachable from the sandbox; head SHAs came from git ls-remote.
- #7001 merged mid-scrape and was dropped from the listing (91 open, 64 non-draft, 27 drafts).
- The MCP does not expose the `mergeable` boolean; conflicts are derived from `mergeable_state=dirty`.
- Four merge-box subagents were killed by a spend-limit 429 but all 64 files were on disk and validated.
- #7036's head was pushed five minutes before the scan; only the AI reviewers had run, so it is not counted as "CI never ran".
- Closure list (9) includes three of Farhan's own stale branches (#6563, #6597, #6468) and four contributor PRs whose issues stay open (#6553 → #6514, #6126 → #5669, #6125 → #5830, #5430 → #5418).
- Fact-check corrected 6 errors and 3 day-count/wording issues before publishing (report.json → method.audit_corrections).
