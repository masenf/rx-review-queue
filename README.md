# rx-review-queue

Weekday review-readiness triage for open pull requests in
[reflex-dev/reflex](https://github.com/reflex-dev/reflex). An agent pointed at
this repository ranks the open non-draft PRs by how close they are to merging,
publishes a tabbed board, and commits the run's data back here so the next run
can say what changed.

This replaces a Cowork-hosted scheduled skill that was tied to one desktop.
Everything it needs now lives in the repo: the procedure, the hard-won list of
ways the board has been wrong, the scripts, the cached data, and the board.

- **Board:** `artifacts/index.html` (served at https://masenf.github.io/rx-review-queue/ once Pages is enabled)
- **Procedure:** `.claude/skills/reflex-pr-readiness/SKILL.md`
- **Data:** `cache/runs/<date>/` (schema in `cache/SCHEMA.md`)

## Running it

Any Claude agent with git and an authenticated GitHub identity (masenf):

> Run the `reflex-pr-readiness` skill in this repo.

The skill is self-contained. Three runners are documented in
`.claude/skills/reflex-pr-readiness/references/data-access.md`:

| Runner | Requirement |
|---|---|
| Claude Code remote (claude.ai/code) | Environment with **both** `masenf/rx-review-queue` and `reflex-dev/reflex` attached, so the GitHub MCP can read reflex PRs. Without reflex attached only the git layer works. |
| Cowork desktop | Built-in browser signed in to GitHub as masenf. |
| Local / any box with `gh` | `gh auth login` as masenf, Python 3.11+, git. |

### Scheduling on Claude Code remote

Create a Routine that starts a fresh session each weekday morning in an
environment with both repos attached, with the prompt:

> Run the `reflex-pr-readiness` skill in masenf/rx-review-queue. Commit the run data and board to main and push. Then report what needs attention today and what changed since the last run.

Cron for 07:00 Pacific on weekdays is `0 14 * * 1-5` (UTC, PDT) or `0 15 * * 1-5` (PST).

## Layout

```
.claude/skills/reflex-pr-readiness/   the skill: SKILL.md + references/
scripts/
  prscan.sh          bare mirror of reflex; fetch main + PR heads (chunked, resumable)
  fetch_listing.sh   open-PR listing via REST (gh or GH_TOKEN) -> listing.json
  fetch_prstate.sh   merge-box state for one PR via gh GraphQL -> prstate/N.json
  measure.py         diff figures, buckets, fragment checks, stack detection -> measurements.json
  delta.py           mechanical diff against the previous run
  render.py          report.json + data -> artifacts/index.html
artifacts/
  template.html      stylesheet and page skeleton
  index.html         latest board
  history/           one board per run
cache/
  SCHEMA.md          JSON shapes
  runs/<date>/       per-run data (committed)
  repo.git/          bare mirror (gitignored)
```

## Manual pipeline

```bash
RUN=cache/runs/$(date -u +%F); mkdir -p $RUN/prstate
scripts/prscan.sh fetch-main
scripts/fetch_listing.sh $RUN/listing.json                     # needs gh or GH_TOKEN
jq -r '.prs[] | select(.draft|not) | .number' $RUN/listing.json > $RUN/nondraft.txt
scripts/prscan.sh fetch-from $RUN/nondraft.txt
scripts/measure.py $RUN/listing.json -o $RUN/measurements.json
for n in $(cat $RUN/nondraft.txt); do scripts/fetch_prstate.sh $n > $RUN/prstate/$n.json; done
scripts/delta.py $RUN > $RUN/delta.json
# ... the agent writes $RUN/report.json (schema: cache/SCHEMA.md) ...
scripts/render.py $RUN
git add $RUN artifacts && git commit -m "run: $(date -u +%F)" && git push -u origin main
```

The judgment (ranking, blockers, patterns) is the agent's and lives in
`report.json`. The scripts only measure and render.
