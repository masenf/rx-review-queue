# Publishing

## The board

`scripts/render.py cache/runs/<date>` builds `artifacts/index.html` from
`report.json` + `listing.json` + `measurements.json` + `prstate/*.json` using
`artifacts/template.html` (light mode, self-contained, PR numbers link to
GitHub, tabbed panes: Top 15 / One fix away / Fast lane / Close candidates /
Stacks / Since last run / Method & caveats). A dated copy goes to
`artifacts/history/`. Do not hand-edit `index.html`; fix the data or the
renderer.

If the board needs a new section, add it to `report.json`'s schema
(`cache/SCHEMA.md`) and to `render.py` in the same commit.

## The commit

```
git add cache/runs/<date> artifacts
git commit -m "run: <date> — <one-line headline, e.g. 3 merged, #7040 enters top 15>"
git push -u origin main
```

Push to `main`. Runs are append-only; never rewrite history in this repo.
If the push is rejected because another run pushed first, `git pull --rebase`
and push again; if the other run is for the same date, read its report and
merge findings rather than clobbering.

`artifacts/` on `main` is served by GitHub Pages (workflow in
`.github/workflows/pages.yml`, one-time setup: Settings → Pages → Source
"GitHub Actions"). Live URL: https://masenf.github.io/rx-review-queue/

Where the runner also offers a hosted artifact surface (Claude artifacts,
Cowork artifacts), publish the same `index.html` there for convenience; the
commit remains the record.

## The chat message

Write it to `cache/runs/<date>/chat-summary.md` and post it. Short and direct,
no preamble:

1. **Needs attention today** — cheap unblocks first (an unclicked workflow
   approval, an unresolved thread a bot already withdrew, a missing news
   fragment), then contributors waiting on a maintainer reply with day counts.
2. **Since last run** — merged, closed, newly opened, entered/left top 15,
   newly blocked/unblocked.
3. **Caveats** — anything absent (review/CI layer), audit corrections, PRs
   whose state could not be settled.

Link to the board.
