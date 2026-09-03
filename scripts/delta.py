#!/usr/bin/env python3
"""Mechanical diff between the previous run and today's listing.

    scripts/delta.py cache/runs/2026-09-03 [--previous cache/runs/2026-09-02]

Without --previous, the most recent other run directory that contains a
listing.json is used. Prints JSON the agent can paste into report.json's
"delta" after annotating:

  disappeared   PR numbers open last run, not open now. The API (or merge
                box) says whether each was MERGED or CLOSED; git can only
                confirm merges: a disappeared PR whose head is an ancestor of
                origin/main was merged.
  opened        open now, not open last run
  draft_flips   draft flag changed
  entered_top15 / left_top15   from the previous report.json, if present
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "cache" / "repo.git"


def load(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


def merged_into_main(sha):
    if not sha or not REPO.exists():
        return None
    r = subprocess.run(["git", "--git-dir", str(REPO), "merge-base", "--is-ancestor", sha,
                        "refs/remotes/origin/main"], capture_output=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--previous")
    args = ap.parse_args()
    cur = Path(args.run_dir)
    if args.previous:
        prev = Path(args.previous)
    else:
        runs = sorted(d for d in (ROOT / "cache" / "runs").iterdir()
                      if d.is_dir() and d != cur and (d / "listing.json").exists())
        if not runs:
            print(json.dumps({"previous_run": None, "note": "no previous listing"}, indent=1))
            return
        prev = runs[-1]
    a = {p["number"]: p for p in load(prev / "listing.json")["prs"]}
    b = {p["number"]: p for p in load(cur / "listing.json")["prs"]}
    prev_report = load(prev / "report.json") or {}
    cur_report = load(cur / "report.json") or {}
    prev_top = [i["number"] for i in prev_report.get("top15", [])]
    cur_top = [i["number"] for i in cur_report.get("top15", [])]
    disappeared = []
    for n in sorted(set(a) - set(b)):
        m = merged_into_main(a[n].get("head_sha"))
        disappeared.append({"number": n, "title": a[n].get("title"),
                            "git_says": "merged (head is ancestor of main)" if m else
                                        ("not in main: closed, or merged via squash/rebase; confirm via API" if m is False else "unknown")})
    out = {
        "previous_run": prev.name,
        "disappeared": disappeared,
        "opened": [{"number": n, "title": b[n].get("title"), "author": b[n].get("author"), "draft": b[n].get("draft")}
                   for n in sorted(set(b) - set(a))],
        "draft_flips": [{"number": n, "now_draft": b[n].get("draft")} for n in sorted(set(a) & set(b))
                        if bool(a[n].get("draft")) != bool(b[n].get("draft"))],
        "entered_top15": [n for n in cur_top if n not in prev_top],
        "left_top15": [n for n in prev_top if n not in cur_top],
        "counts": {"previous_open": len(a), "current_open": len(b)},
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
