# 2026-08-28 (23:30 PT) — last run of the Cowork-hosted version

No data files survive from this run; the board lived in a Cowork artifact and
the measurements in a per-session sandbox. This note preserves the facts that
were quoted in the skill text so the first run in this repo has a baseline to
compare its delta pane against, and so it treats these as **partial**.

Known at that time (all figures are stale; re-verify everything):

- Counting approvals seen in merge boxes: **#6899** (also the only PR the
  `review:approved` search returned) and **#6963** ("Changes approved · 1
  approving review by reviewers with write access"). Earlier the same day
  **#6927** held one.
- **#6933** was current with main after the author pushed a main-merge at
  16:14:59 PT; the fact-check auditor had wrongly flagged it as 21 behind
  using a snapshot taken before that push.
- `status:success` returned 8 PRs of which only 2 were genuinely green; five
  were fork PRs with "N workflows awaiting approval" and one had passed only
  the two AI-reviewer checks. A PR with 11 failing checks appeared under
  `status:success`.
- Roughly a third of open PRs were drafts.
- Current PRs ran ~110 checks; older ones ~67.

The first run in this repo should say in its Method pane that the
"since last run" comparison is against this note, not against a full
listing, and list merged/closed/opened only where the API can establish
them (e.g. `merged:>2026-08-29T06:30:00Z`, `created:>2026-08-29T06:30:00Z`).
