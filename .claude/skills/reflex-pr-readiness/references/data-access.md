# Data access by runner

Two layers of data. The **git layer** (diff sizes, behind-main, stacks) needs
only anonymous git reads of the public repo and works everywhere. The
**review/CI layer** (merge box: mergeability, checks, reviews, threads) needs an
authenticated GitHub identity. Verify which you have before collecting anything,
and say on the board when the second layer is absent.

| Runner | Git layer | Review/CI layer | Identity check |
|---|---|---|---|
| Claude Code remote (claude.ai/code) | `git` via the session proxy; public reads always work | GitHub MCP (`mcp__github__*`) **only for repos attached to the session**. reflex-dev/reflex must be attached (pick it when creating the environment/session, or `add_repo` with push access; a read-only add does not unlock the API). `api.github.com` is 403'd at the egress proxy, so `gh`/curl do not work. | `mcp__github__get_me` → `login` |
| Cowork desktop | `git` in `mcp__workspace__bash` | Built-in browser (`mcp__Claude_Browser__*`) signed in as masenf. No `gh`, no GitHub MCP. | `document.querySelector('meta[name="user-login"]')?.content` |
| Local CLI / any box with `gh` | `git` | `gh api` (REST + GraphQL). `scripts/fetch_listing.sh` and `scripts/fetch_prstate.sh` do the work. | `gh api /user` |

## Claude Code remote: field mapping from the GitHub MCP

Load tools once: `ToolSearch select:mcp__github__get_me,mcp__github__list_pull_requests,mcp__github__pull_request_read,mcp__github__search_pull_requests,mcp__github__get_job_logs,mcp__github__actions_list`.

| Need | Call |
|---|---|
| Listing | `list_pull_requests(owner=reflex-dev, repo=reflex, state=open, perPage=100, page=N, fields=[number,title,draft,user,labels,created_at,updated_at,comments,head,mergeable_state])`. `author_association` is not in the list fields; fill it from `pull_request_read(get)` or `search_pull_requests(fields=[number,author_association])`. |
| Open counter | `search_pull_requests(query="repo:reflex-dev/reflex is:open", perPage=1)` → `total_count` |
| Mergeability | `pull_request_read(get)` → `mergeable`, `mergeable_state` (`dirty` = conflicts, `blocked` = missing review/checks, `behind` = update-branch offered, `unstable` = failing non-required check, `unknown` = re-fetch after a few seconds) |
| Checks | `pull_request_read(get_check_runs)` — names, status, conclusion. A run with everything `queued`/`action_required` and only the two AI reviewers complete is **"workflows awaiting approval"**: CI never ran. |
| Failing logs | `actions_list(list_workflow_runs, branch=<head_ref>)` then `get_job_logs(run_id, failed_only=true, return_content=true, tail_lines=300)` — fork branches need `actor`/head-repo context; fall back to the check's `details_url`. |
| Reviews | `pull_request_read(get_reviews)` — state, author, submitted_at, `author_association`. Counting approval = `APPROVED` from `MEMBER`/`OWNER`/`COLLABORATOR` on the current head (later commits do not dismiss in this repo unless configured; check `commit_id`). |
| Threads | `pull_request_read(get_review_comments)` — returns threads with `isResolved`. Any unresolved thread blocks merge, bot threads included. |
| Linked issue + filer | PR body `closes #N` / `fixes #N`, then `issue_read(get, N)` → `user.login`. |
| Delta | `search_pull_requests(query="repo:reflex-dev/reflex is:merged merged:>TS")`, `...is:closed is:unmerged closed:>TS`, `...created:>TS`. |

## Cowork: browser specifics

Everything in the original skill applies: `preview_start` a tab and keep it;
verify `meta[name=user-login]`; fetch listing pages in `javascript_tool` and
parse with `DOMParser` from `div[id^="issue_"]` (draft = `svg.octicon-git-pull-request-draft`);
never call `tabs_close`; tell subagents to open and keep their own tabs. The
merge box loads lazily and can show "All checks have passed / Update branch"
before settling into conflicts: re-read until settled.

## Search qualifiers: use, do not trust

`is:pr is:open draft:false` with `review:none|approved|changes-requested`,
`status:failure|success`, `sort:updated-asc`, `merged:>TS`, `created:>TS` are
fine for **finding candidates and computing the delta**. They are not
evidence: `status:success` has returned PRs with 11 failing checks and fork PRs
whose CI never ran; `review:approved` has missed counting approvals three
times. Only the merge box (or its API equivalent above) is authoritative.

## Bare repo for measurement

`scripts/prscan.sh` keeps `cache/repo.git` (gitignored). Set
`REFLEX_ALTERNATES=/path/to/reflex/.git/objects` if a clone exists nearby to
share objects. Fetches are chunked at 14 refs per call because tool calls have
a timeout ceiling and background processes do not survive between calls. On
some mounts deleting refs fails with stale `.lock` files: do not prune, filter
by `nondraft.txt` instead. `unable to unlink ... Operation not permitted`
warnings are harmless.
