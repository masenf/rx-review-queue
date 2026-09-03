#!/usr/bin/env python3
"""Measure every non-draft PR against today's main using cache/repo.git.

    scripts/measure.py cache/runs/YYYY-MM-DD/listing.json \
        -o cache/runs/YYYY-MM-DD/measurements.json

Reads the PR numbers (non-draft only unless --include-drafts) from a
listing.json (see cache/SCHEMA.md), expects `scripts/prscan.sh fetch-main`
and `fetch-from` to have populated refs/remotes/origin/main and refs/pr/N,
and writes per-PR figures computed from merge-base(main, pr)..pr:

  files, insertions, deletions, commits_ahead, behind_main, buckets,
  head/merge_base SHAs, flags (components-without-pyi-hash, fragments),
  plus a stack analysis (head-SHA containment) and, for chain members that
  share a merge-base with their parent, a parent-relative diff.

Every number is recomputed on each run. Nothing is copied forward.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "cache" / "repo.git"
MAIN = "refs/remotes/origin/main"

BUCKET_RULES = [
    # (bucket, predicate). First match wins, so order matters.
    ("unit_tests", lambda p: p.startswith("tests/units/")),
    ("playwright", lambda p: p.startswith("tests/integration/tests_playwright/")),
    ("selenium", lambda p: p.startswith("tests/integration/")),
    ("benchmarks", lambda p: p.startswith(("tests/benchmarks/", "benchmarks/"))),
    ("tests_other", lambda p: p.startswith("tests/")),
    ("ci", lambda p: p.startswith(".github/")),
    ("pyi", lambda p: p.endswith(".pyi") or p.endswith("pyi_hashes.json")),
    ("scripts", lambda p: p.startswith("scripts/")),
    # Changelog fragments live in news/ and packages/*/news/. They are
    # markdown but are NOT documentation.
    ("fragments", lambda p: bool(re.match(r"^(news/|packages/[^/]+/news/)", p))),
    # Real docs are under docs/ and end in .md/.mdx.
    ("docs", lambda p: p.startswith("docs/") and p.endswith((".md", ".mdx"))),
    ("frontend", lambda p: p.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".json"))
        and ("/.templates/" in p or p.startswith("reflex/.templates/") or "/web/" in p)),
    ("frontend", lambda p: p.endswith((".js", ".jsx", ".ts", ".tsx", ".css"))),
    ("python", lambda p: p.endswith(".py")),
    ("config", lambda p: p.split("/")[-1] in {
        "pyproject.toml", "uv.lock", "poetry.lock", "package.json", "bun.lock",
        ".pre-commit-config.yaml", "Makefile", "mkdocs.yml"}),
    # Compiled towncrier output (release / backport PRs), not docs and not a fragment.
    ("changelog", lambda p: p.split("/")[-1] == "CHANGELOG.md"),
    ("markdown_other", lambda p: p.endswith((".md", ".mdx", ".rst"))),
]


def git(*args, check=True):
    r = subprocess.run(["git", "--git-dir", str(REPO), *args],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def rev(ref):
    return git("rev-parse", "--verify", "-q", ref, check=False).strip() or None


def bucket(path):
    for name, pred in BUCKET_RULES:
        if pred(path):
            return name
    return "other"


def numstat(base, head):
    files, ins, dels = [], 0, 0
    for line in git("diff", "--numstat", "-M", base, head).splitlines():
        a, d, p = line.split("\t", 2)
        if "=>" in p:  # rename: "old => new" or "dir/{old => new}"
            p = re.sub(r"\{[^}]* => ([^}]*)\}", r"\1", p)
            p = p.split(" => ")[-1]
        files.append(p)
        ins += int(a) if a != "-" else 0
        dels += int(d) if d != "-" else 0
    return files, ins, dels


def measure(number):
    head = rev(f"refs/pr/{number}")
    if not head:
        return {"number": number, "error": "ref refs/pr/%d not fetched" % number}
    mb = git("merge-base", MAIN, head).strip()
    files, ins, dels = numstat(mb, head)
    ahead = git("rev-list", "--count", f"{mb}..{head}").strip()
    behind = git("rev-list", "--count", f"{mb}..{MAIN}").strip()
    commits = git("rev-list", f"{mb}..{head}").split()
    buckets = defaultdict(list)
    for p in files:
        buckets[bucket(p)].append(p)
    touches_components = [p for p in files
                          if re.search(r"(^|/)components/.*\.py$", p) and not p.endswith(".pyi")]
    pyi_hash_updated = any(p.endswith("pyi_hashes.json") for p in files)
    frag = buckets.get("fragments", [])
    frag_numbers = sorted({int(m.group(1)) for p in frag
                           for m in [re.search(r"/(\d+)\.[a-z]+\.md$", p)] if m})
    pkgs_touched = sorted({m.group(1) for p in files
                           for m in [re.match(r"^packages/([^/]+)/", p)] if m})
    touches_core = any(p.startswith("reflex/") for p in files)
    return {
        "number": number,
        "head": head,
        "merge_base": mb,
        "files": len(files),
        "insertions": ins,
        "deletions": dels,
        "commits_ahead": int(ahead),
        "behind_main": int(behind),
        "buckets": {k: len(v) for k, v in sorted(buckets.items())},
        "bucket_paths": {k: v for k, v in sorted(buckets.items())},
        "flags": {
            "touches_components_py": bool(touches_components),
            "pyi_hashes_updated": pyi_hash_updated,
            "components_without_pyi_hash": bool(touches_components) and not pyi_hash_updated,
            "has_unit_tests": "unit_tests" in buckets,
            "has_real_docs": "docs" in buckets,
            "has_fragment": bool(frag),
            # Per-package fragments are REQUIRED: a PR touching reflex/ and N
            # packages needs 1+N fragments. Report the expectation, not a
            # "collision".
            "fragments_expected": (1 if touches_core else 0) + len(pkgs_touched),
            "fragment_numbers": frag_numbers,
            "fragment_named_after_pr": number in frag_numbers,
            "packages_touched": pkgs_touched,
        },
        "_commits": commits,
    }


def stacks(results):
    """Head-SHA containment: PR A is an ancestor of PR B iff head(A) is in
    B's commit set vs main. Linear in total commits, no pairwise merge-base."""
    by_num = {r["number"]: r for r in results if "head" in r}
    owner = defaultdict(set)  # sha -> PRs whose commit set contains it
    for n, r in by_num.items():
        for sha in r["_commits"]:
            owner[sha].add(n)
    chains = []
    for n, r in by_num.items():
        parents = sorted(m for m in owner.get(r["head"], ()) if m != n)
        r["contained_in"] = parents  # PRs that include this PR's head
    for n, r in by_num.items():
        children = sorted(m for m, s in by_num.items() if n in s["contained_in"])
        r["contains"] = children
        # Parent-relative diff: pick the largest ancestor PR among those this
        # PR contains (deepest parent) and only quote when merge-bases match.
        r["parent_relative"] = None
        if children:
            parent = max(children, key=lambda m: by_num[m]["commits_ahead"])
            pr = by_num[parent]
            if pr["merge_base"] == r["merge_base"]:
                files, ins, dels = numstat(pr["head"], r["head"])
                r["parent_relative"] = {
                    "parent": parent, "files": len(files),
                    "insertions": ins, "deletions": dels,
                    "commits": len(r["_commits"]) - len(pr["_commits"]),
                }
            else:
                r["parent_relative"] = {
                    "parent": parent, "note":
                    "merge-bases differ; quote vs-main figures and label them"}
    # Assemble chains root->tip
    seen = set()
    for n, r in sorted(by_num.items(), key=lambda kv: kv[1]["commits_ahead"]):
        if r["contains"] or r["contained_in"]:
            members = {n, *r["contains"], *r["contained_in"]}
            key = frozenset(members)
            if key in seen:
                continue
            seen.add(key)
            chains.append(sorted(members, key=lambda m: by_num[m]["commits_ahead"]))
    return chains


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("listing")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--numbers", help="comma-separated override of PR numbers")
    args = ap.parse_args()

    if not rev(MAIN):
        sys.exit("origin/main not present: run scripts/prscan.sh fetch-main")
    listing = json.loads(Path(args.listing).read_text())
    if args.numbers:
        numbers = [int(x) for x in args.numbers.split(",") if x]
    else:
        numbers = [p["number"] for p in listing["prs"]
                   if args.include_drafts or not p.get("draft")]
    results = [measure(n) for n in numbers]
    chains = stacks(results)
    for r in results:
        r.pop("_commits", None)
    out = {
        "main": rev(MAIN),
        "main_date": git("log", "-1", "--format=%cI", MAIN).strip(),
        "listing_fetched_at": listing.get("fetched_at"),
        "measured": len([r for r in results if "head" in r]),
        "missing_refs": [r["number"] for r in results if "error" in r],
        "stacks": chains,
        "prs": {str(r["number"]): r for r in results},
    }
    Path(args.output).write_text(json.dumps(out, indent=1) + "\n")
    print(f"measured {out['measured']} PRs vs main {out['main'][:10]}; "
          f"{len(chains)} stack(s); missing refs: {out['missing_refs']}")


if __name__ == "__main__":
    main()
