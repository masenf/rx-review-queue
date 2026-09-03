# Cache data schema

Each run lives in `cache/runs/YYYY-MM-DD/` (append `-2`, `-3` for a second run
on the same day). Files are plain JSON so any agent, on any runner, can produce
and consume them. All timestamps are ISO-8601 UTC unless suffixed.

```
cache/
  repo.git/                 bare mirror of reflex-dev/reflex (gitignored, rebuilt by prscan.sh)
  runs/YYYY-MM-DD/
    listing.json            every open PR (drafts included) as enumerated from GitHub
    nondraft.txt            PR numbers to measure, one per line (derived from listing)
    measurements.json       git-derived figures, written by scripts/measure.py
    prstate/N.json          merge-box state per PR gathered from the API (optional per PR)
    report.json             the agent's verdicts; the only hand-authored file
    delta.json              output of scripts/delta.py (mechanical, pre-annotation)
    chat-summary.md         the short "what changed / needs attention" message posted to the user
```

## listing.json

```jsonc
{
  "fetched_at": "2026-09-03T14:02:11Z",
  "source": "rest" | "github-mcp" | "browser",
  "authenticated_as": "masenf",        // null => unauthenticated; the review/CI layer is then ABSENT
  "open_count": 61,                    // the repo's "N Open" counter; must equal prs.length
  "prs": [{
    "number": 7040, "title": "...", "draft": false,
    "author": "login", "author_association": "MEMBER|COLLABORATOR|CONTRIBUTOR|FIRST_TIME_CONTRIBUTOR|NONE",
    "labels": ["bug"], "created_at": "...", "updated_at": "...",
    "comments": 3,                     // null if the source doesn't give it
    "head_sha": "...", "head_ref": "branch", "head_repo": "owner/repo", "is_fork": true,
    "body_present": true
  }]
}
```

`author_association` is the API equivalent of the listing's role badge and is
what author-concentration counts are computed from. Never count authorship from
commit metadata: the head commit on many branches is authored "Claude".

## measurements.json (generated)

```jsonc
{
  "main": "<sha>", "main_date": "...", "listing_fetched_at": "...",
  "measured": 40, "missing_refs": [], "stacks": [[6901, 6902, 6903]],   // root -> tip
  "prs": { "7040": {
    "head": "<sha>", "merge_base": "<sha>",
    "files": 12, "insertions": 197, "deletions": 45,
    "commits_ahead": 1, "behind_main": 0,
    "buckets": {"python": 7, "unit_tests": 2, "config": 2, "markdown_other": 1},
    "bucket_paths": {"python": ["reflex/..."], ...},
    "flags": {
      "touches_components_py": false, "pyi_hashes_updated": false, "components_without_pyi_hash": false,
      "has_unit_tests": true, "has_real_docs": false,
      "has_fragment": false, "fragments_expected": 1, "fragment_numbers": [], "fragment_named_after_pr": false,
      "packages_touched": []
    },
    "contained_in": [], "contains": [],
    "parent_relative": null | {"parent": 6901, "files": 3, "insertions": 10, "deletions": 2, "commits": 1}
                            | {"parent": 6901, "note": "merge-bases differ; quote vs-main figures and label them"}
  }}
}
```

Buckets: `unit_tests` (tests/units/), `playwright` (tests/integration/tests_playwright/),
`selenium` (other tests/integration/), `benchmarks`, `tests_other`, `ci` (.github/), `pyi`
(*.pyi, pyi_hashes.json), `scripts`, `fragments` (news/, packages/*/news/), `docs`
(docs/**/*.md|mdx only), `frontend`, `python`, `config`, `changelog` (compiled CHANGELOG.md),
`markdown_other`, `other`.

## prstate/N.json

Produced by `scripts/fetch_prstate.sh N` (gh + GraphQL) or assembled by the agent from
GitHub MCP `pull_request_read` calls. Fields the renderer and the scoring rely on:

```jsonc
{
  "number": 7040, "fetched_at": "...", "head_sha": "...",
  "mergeable": "MERGEABLE|CONFLICTING|UNKNOWN",   // UNKNOWN => re-fetch; GitHub computes lazily
  "merge_state": "CLEAN|BLOCKED|BEHIND|DIRTY|UNSTABLE|HAS_HOOKS|UNKNOWN",
  "conflicting_files": [],                         // only from the merge box / attempted merge
  "update_branch_offered": true,
  "auto_merge": false,
  "review_decision": "APPROVED|CHANGES_REQUESTED|REVIEW_REQUIRED|null",
  "linked_issues": [{"number": 6990, "title": "...", "filed_by": "someone-else"}],
  "reviews": [{"by": "login", "state": "APPROVED", "at": "...", "can_push": true}],
  "counting_approval": true,        // an APPROVED review from someone with write access, on the current head
  "awaiting": ["reflex-dev/reflex-team"],
  "threads": {"total": 4, "unresolved": [{"by": "greptile-apps", "outdated": false, "first_comment": "..."}]},
  "checks": {
    "rollup": "SUCCESS|FAILURE|PENDING|null",
    "total": 110, "by_state": {"SUCCESS": 100, "FAILURE": 2, "PENDING": 8},
    "failing": ["unit-tests (windows, 3.11)"], "pending": ["..."]
  },
  "ci_never_ran": false,            // "N workflows awaiting approval": fork PR, CI gate never clicked
  "failing_job_findings": [          // from READING THE LOGS, not the check name
    {"check": "unit-tests (windows, 3.11)", "cause": "test in a file the PR does not touch; flaky on main too"}
  ],
  "outstanding_asks": [{"by": "masenf", "ask": "...", "addressed": false}],
  "body_has_repro": true,
  "recent_comments": [{"by": "...", "at": "...", "excerpt": "..."}],
  "days_waiting_on_maintainer": 6   // last author activity after the last maintainer comment
}
```

## report.json (hand-authored by the agent)

```jsonc
{
  "run": {"date": "2026-09-03", "started_at": "2026-09-03 07:05 PT", "runner": "claude-code-remote",
          "github_login": "masenf", "review_ci_layer": "present|absent", "session": "..."},
  "stats": {"open": 61, "nondraft": 40, "drafts": 21, "counting_approvals": 2, "fast_lane": 3,
            "one_fix_away": 9, "fork_ci_unrun": 5, "never_human_reviewed": 12},
  "attention": ["Plain-language bullets: what needs Masen today. Cheap unblocks first."],
  "top15": [{"number": 7040, "score": 8.5, "summary": "...", "evidence": ["..."],
             "blocker": "...", "whose_move": "maintainer|author", "chips": ["issue filed by other-user"],
             "override_reason": null}],
  "one_fix_away": {"maintainer": [{"number":..., "summary":..., "blocker":...}], "author": [...]},
  "fast_lane": [{"number":..., "summary": "why it is mergeable at a glance; real file list checked"}],
  "closure": [{"number":..., "summary":..., "keep_issue": 6812}],
  "stacks": [{"chain": [6901, 6902], "note": "..."}],          // optional; defaults to measurements.stacks
  "conflict_clusters": [{"prs": [7029, 7030], "files": ["reflex/x.py"], "note": "..."}],
  "structural": [{"number":..., "summary":...}],
  "patterns": [{"title": "Counting approvals repo-wide: 2", "detail": "..."}],
  "delta": {"previous_run": "2026-09-02", "merged": [7001], "closed": [{"number": 6950, "note": "..."}],
            "opened": [...], "entered_top15": [...], "left_top15": [...],
            "newly_blocked": [...], "newly_unblocked": [...], "draft_flips": [...]},
  "method": {"notes": ["..."], "audit_corrections": ["..."], "caveats": ["..."]}
}
```

Items in list fields may be a bare integer (PR number) or an object with
`number` plus `note`. Free text may contain `#1234`, which the renderer links.
