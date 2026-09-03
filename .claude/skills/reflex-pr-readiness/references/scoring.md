# Scoring rubric

The question for every non-draft PR: **if a maintainer looks at it today, how
close is it to merging?** Score 0–10, then bucket. The score is a
communication device, not a formula to hide behind: every card must carry the
evidence and the single most important thing in the way.

## Signals

| Signal | Weight | Notes |
|---|---|---|
| CI genuinely green on the current head | +2 | "Workflows awaiting approval" is 0, not green. Read logs for any red. |
| No conflicts, or only "Update branch" needed | +1 | Behind-main is a light penalty (−0.5 past ~40 commits), never a blocker. |
| No unresolved review threads | +1 | Any unresolved thread, bot included, blocks merge. Rebutted bot threads: note "one click". |
| Counting approval on current head | +2 | Write-access reviewer. Non-counting approval: +0.5. |
| Changes-requested outstanding, not dismissed | −2 | If the asks were addressed in later commits, −0.5 and say "re-review needed". |
| Tests added / updated for the change | +1 | `unit_tests` or `playwright` bucket non-empty, and relevant. |
| Docs where the change is user-visible | +0.5 | Real docs bucket, not fragments. Missing where clearly needed: −0.5. |
| News fragment(s) present as expected | +0.5 | `fragments_expected` met. Missing: −0.5 and it is usually the "one fix". |
| Tight scope: one identifiable problem | +1 | Sprawling or mixed-concern diffs: −1. |
| **Bug fix whose linked issue was filed by someone other than the author** | +1.5 | The rarest, most decision-relevant signal. Capture the filer on the card. |
| Feature with no issue / self-filed issue | −1 | |
| Over-narrow feature or niche use case | −1 | Candidate for closure if also stale. |
| Author is a first-time contributor with unrun CI | 0 | Not their fault; the approval click is the maintainer's move. |
| Stale: no author activity > 60 days and asks outstanding | −2 | Closure candidate unless the issue is legitimate. |

## Buckets

- **Top 15** — highest scores, monotonic. Each card: evidence bullets, blocker,
  whose move.
- **One fix away** — exactly one identified blocker. Group by `maintainer`
  (approve workflows, resolve a withdrawn bot thread, click Update branch,
  dismiss a stale review) vs `author` (add fragment, fix one test, rebase).
- **Fast lane** — mergeable at a glance: green, no threads, trivially reviewable
  (docs-only verified against the file list, one-line fixes, dependency bumps
  with green CI).
- **Close candidates** — too broad, too niche, abandoned. If the issue is
  legitimate: "close the PR, keep issue #N".
- **Stacks / structural** — chains, conflict clusters, duplicate PRs
  (identical stats vs main are a strong hint), PRs that should be split.

## Patterns to always report

1. Counting approvals repo-wide, by PR number, from merge boxes.
2. PRs never reviewed by a human (only bots).
3. Contributors waiting on a maintainer reply, with day counts.
4. Fork PRs whose CI never ran.
5. Fragment problems (missing, wrong package).
6. Author concentration: top authors by open non-draft count, from
   `author_association`/login in the listing.
