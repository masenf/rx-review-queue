# cache/

Persistent state between runs. The skill has no memory; this directory is it.

- `runs/<date>/` — one directory per run: the scraped listing, git measurements,
  per-PR merge-box state, the agent's `report.json`, and the chat summary.
  Committed, so the next run (on any machine) can compute "what changed".
- `repo.git/` — bare mirror of reflex-dev/reflex used for diff measurement.
  **Gitignored.** Rebuilt in seconds by `scripts/prscan.sh fetch-main`; the
  repo is public so no credentials are needed.
- `SCHEMA.md` — the shape of every file above.

Keep old runs. They are small and the delta pane depends on them. If a run
was aborted, leave a `ABORTED.md` in its directory saying why rather than
deleting it, so the next run does not treat it as a valid baseline.
