#!/usr/bin/env python3
"""Render the readiness board from a run directory.

    scripts/render.py cache/runs/YYYY-MM-DD [-o artifacts/index.html]

Inputs (all in the run directory; schema in cache/SCHEMA.md):
  report.json        the agent's verdicts: ranking, buckets, patterns, delta, method
  listing.json       titles / authors / draft flags (from GitHub)
  measurements.json  diff figures vs today's main (from measure.py)
  prstate/N.json     merge-box state per PR (optional; used for chips)

Output: a self-contained light-mode HTML page built from artifacts/template.html
with tabbed panes: Top 15 / One fix away / Fast lane / Close candidates /
Stacks / Changes since last run / Method. It is also copied to
artifacts/history/YYYY-MM-DD.html unless --no-history.

The renderer is deliberately dumb: it prints what report.json says and
decorates with measured numbers. All judgment lives in report.json.
"""
import argparse
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH = "https://github.com/reflex-dev/reflex"


def esc(s):
    return html.escape(str(s if s is not None else ""))


def link(n):
    return f'<a href="{GH}/pull/{n}">#{n}</a>'


def linkify(text):
    """Turn bare #1234 references in free text into PR/issue links."""
    import re
    return re.sub(r"(?<![\w/])#(\d{3,6})\b", lambda m: f'<a href="{GH}/pull/{m.group(1)}">#{m.group(1)}</a>', esc(text))


class Board:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.report = json.loads((self.run_dir / "report.json").read_text())
        self.listing = self._load("listing.json", {"prs": []})
        self.meas = self._load("measurements.json", {"prs": {}, "stacks": []})
        self.prs = {p["number"]: p for p in self.listing.get("prs", [])}
        self.state = {}
        for f in (self.run_dir / "prstate").glob("*.json") if (self.run_dir / "prstate").is_dir() else []:
            try:
                d = json.loads(f.read_text())
                self.state[int(d["number"])] = d
            except Exception:
                pass

    def _load(self, name, default):
        p = self.run_dir / name
        return json.loads(p.read_text()) if p.exists() else default

    # ----- card pieces -------------------------------------------------
    def title(self, n):
        p = self.prs.get(n, {})
        return esc(p.get("title") or "(title not in listing)")

    def meta(self, n):
        p = self.prs.get(n, {})
        m = self.meas.get("prs", {}).get(str(n), {})
        bits = []
        if p.get("author"):
            role = p.get("author_association", "")
            role = {"MEMBER": "member", "COLLABORATOR": "collaborator", "CONTRIBUTOR": "contributor",
                    "FIRST_TIME_CONTRIBUTOR": "first-time contributor", "FIRST_TIMER": "first-timer",
                    "NONE": "", "OWNER": "owner"}.get(role, role.lower())
            bits.append(f"by <b>{esc(p['author'])}</b>" + (f" ({role})" if role else ""))
        if p.get("is_fork"):
            bits.append("fork")
        if "files" in m:
            bits.append(f"{m['files']} files, +{m['insertions']}/−{m['deletions']}")
            bits.append(f"{m['commits_ahead']} ahead / {m['behind_main']} behind main")
            pr = m.get("parent_relative")
            if pr and "files" in pr:
                bits.append(f"vs parent {link(pr['parent'])}: {pr['files']} files, +{pr['insertions']}/−{pr['deletions']}")
            elif pr:
                bits.append(f"stacked on {link(pr['parent'])} (figures above are vs main)")
        if p.get("labels"):
            bits.append("labels: " + ", ".join(esc(l) for l in p["labels"]))
        return " · ".join(bits)

    def chips(self, n, extra=()):
        m = self.meas.get("prs", {}).get(str(n), {})
        s = self.state.get(n, {})
        chips = []
        f = m.get("flags", {})
        b = m.get("buckets", {})
        if f.get("has_unit_tests"): chips.append(("good", f"unit tests ×{b.get('unit_tests')}"))
        if b.get("playwright"): chips.append(("good", f"playwright ×{b['playwright']}"))
        if f.get("has_real_docs"): chips.append(("good", "docs"))
        if f.get("has_fragment"):
            chips.append(("", f"fragments {sum(1 for _ in m.get('bucket_paths', {}).get('fragments', []))}/{f.get('fragments_expected')}"))
        elif f.get("fragments_expected"):
            chips.append(("warn", "no news fragment"))
        if f.get("components_without_pyi_hash"): chips.append(("warn", "components/*.py without pyi_hashes"))
        if s:
            if s.get("mergeable") == "CONFLICTING": chips.append(("bad", "conflicts"))
            ck = s.get("checks") or {}
            if ck.get("failing"): chips.append(("bad", f"{len(ck['failing'])} failing checks"))
            if ck.get("rollup") == "SUCCESS" and not ck.get("failing"): chips.append(("good", "checks green"))
            if s.get("ci_never_ran"): chips.append(("warn", "workflows awaiting approval"))
            th = (s.get("threads") or {}).get("unresolved") or []
            if th: chips.append(("bad", f"{len(th)} unresolved threads"))
            if s.get("review_decision") == "APPROVED": chips.append(("good", "approved"))
            if s.get("review_decision") == "CHANGES_REQUESTED": chips.append(("bad", "changes requested"))
            if s.get("auto_merge"): chips.append(("", "auto-merge on"))
        for c in extra:
            chips.append(("", c) if isinstance(c, str) else tuple(c))
        return '<div class="chips">' + "".join(f'<span class="chip {k}">{esc(t)}</span>' for k, t in chips) + "</div>" if chips else ""

    def card(self, item, rank=None):
        n = item["number"]
        h = '<div class="card">'
        h += "<h3>"
        if rank: h += f'<span class="rank">{rank}.</span>'
        h += f"{link(n)} {self.title(n)}"
        if "score" in item: h += f'<span class="score">score {esc(item["score"])}</span>'
        h += "</h3>"
        h += f'<div class="meta">{self.meta(n)}</div>'
        h += self.chips(n, item.get("chips", ()))
        if item.get("summary"): h += f"<p>{linkify(item['summary'])}</p>"
        if item.get("evidence"):
            h += "<ul>" + "".join(f"<li>{linkify(e)}</li>" for e in item["evidence"]) + "</ul>"
        if item.get("blocker"):
            who = f" <span class=\"chip\">{esc(item['whose_move'])}'s move</span>" if item.get("whose_move") else ""
            h += f'<div class="blocker"><b>In the way:</b> {linkify(item["blocker"])}{who}</div>'
        if item.get("override_reason"):
            h += f'<div class="meta">Ranking override: {linkify(item["override_reason"])}</div>'
        h += "</div>"
        return h

    # ----- panes -------------------------------------------------------
    def pane_top(self):
        items = self.report.get("top15", [])
        if not items: return '<p class="empty">No ranked PRs in this run.</p>'
        return "".join(self.card(it, i + 1) for i, it in enumerate(items))

    def pane_onefix(self):
        g = self.report.get("one_fix_away", {})
        out = ""
        for who, label in (("maintainer", "Your move"), ("author", "Author's move")):
            items = g.get(who, [])
            out += f'<h2 class="group">{label} · {len(items)}</h2>'
            out += "".join(self.card(dict(it, whose_move=None)) for it in items) or '<p class="empty">none</p>'
        return out

    def pane_simple(self, key, empty):
        items = self.report.get(key, [])
        return "".join(self.card(it) for it in items) or f'<p class="empty">{empty}</p>'

    def pane_close(self):
        items = self.report.get("closure", [])
        out = "".join(self.card(dict(it, chips=(["keep issue #%s" % it["keep_issue"]] if it.get("keep_issue") else []) + list(it.get("chips", ())))) for it in items)
        return out or '<p class="empty">No closure candidates.</p>'

    def pane_stacks(self):
        out = ""
        chains = self.report.get("stacks") or [{"chain": c} for c in self.meas.get("stacks", [])]
        out += f'<h2 class="group">Stacks · {len(chains)}</h2>'
        if chains:
            out += "<table><tr><th>Chain (root → tip)</th><th>Note</th></tr>"
            for c in chains:
                out += f"<tr><td>{' → '.join(link(n) for n in c['chain'])}</td><td>{linkify(c.get('note', ''))}</td></tr>"
            out += "</table>"
        else:
            out += '<p class="empty">No stacked PRs detected (head-SHA containment over all non-draft PRs).</p>'
        clusters = self.report.get("conflict_clusters", [])
        out += f'<h2 class="group">Conflict clusters · {len(clusters)}</h2>'
        if clusters:
            out += "<table><tr><th>PRs</th><th>Files fought over</th><th>Note</th></tr>"
            for c in clusters:
                out += f"<tr><td>{', '.join(link(n) for n in c['prs'])}</td><td>{'<br>'.join(esc(f) for f in c.get('files', []))}</td><td>{linkify(c.get('note', ''))}</td></tr>"
            out += "</table>"
        else:
            out += '<p class="empty">None recorded.</p>'
        struct = self.report.get("structural", [])
        if struct:
            out += f'<h2 class="group">Other structural problems · {len(struct)}</h2>'
            out += "".join(self.card(it) for it in struct)
        return out

    def pane_delta(self):
        d = self.report.get("delta", {})
        prev = d.get("previous_run") or "(no previous run)"
        out = f'<p class="meta">Compared with run <b>{esc(prev)}</b>.</p>'
        rows = [("merged", "Merged"), ("closed", "Closed without merge"), ("opened", "Newly opened"),
                ("entered_top15", "Entered top 15"), ("left_top15", "Left top 15"),
                ("newly_blocked", "Newly blocked"), ("newly_unblocked", "Newly unblocked"),
                ("draft_flips", "Draft ↔ ready flips")]
        out += "<table><tr><th>Change</th><th>PRs</th></tr>"
        for k, label in rows:
            items = d.get(k, [])
            cells = ", ".join((link(i) if isinstance(i, int) else f"{link(i['number'])} <span class=\"meta\">{linkify(i.get('note', ''))}</span>") for i in items) or '<span class="empty">none</span>'
            out += f"<tr><td>{label} ({len(items)})</td><td>{cells}</td></tr>"
        out += "</table>"
        pats = self.report.get("patterns", [])
        if pats:
            out += f'<h2 class="group">Cross-cutting patterns · {len(pats)}</h2>'
            for p in pats:
                out += f'<div class="card"><h3>{esc(p["title"])}</h3><p>{linkify(p["detail"])}</p></div>'
        return out

    def pane_method(self):
        m = self.report.get("method", {})
        run = self.report.get("run", {})
        out = "<table>"
        for k, v in [("Run started", run.get("started_at")), ("Runner", run.get("runner")),
                     ("GitHub identity", run.get("github_login")),
                     ("Review/CI layer", run.get("review_ci_layer")),
                     ("main at", (self.meas.get("main") or "")[:12] + " " + (self.meas.get("main_date") or "")),
                     ("Listing fetched", self.listing.get("fetched_at")),
                     ("PRs measured", self.meas.get("measured")),
                     ("Model / session", run.get("session"))]:
            if v: out += f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"
        out += "</table>"
        for key, label in (("notes", "Method notes"), ("audit_corrections", "Corrections after fact-check"), ("caveats", "Caveats")):
            items = m.get(key, [])
            if items:
                out += f'<h2 class="group">{label} · {len(items)}</h2><ul>' + "".join(f"<li>{linkify(i)}</li>" for i in items) + "</ul>"
        return out

    # ----- page --------------------------------------------------------
    def render(self):
        r = self.report
        run = r.get("run", {})
        st = r.get("stats", {})
        date = run.get("date") or self.run_dir.name
        n_drafts = sum(1 for p in self.prs.values() if p.get("draft"))
        tiles = [
            (st.get("open", self.listing.get("open_count", len(self.prs))), "open PRs"),
            (st.get("nondraft", len(self.prs) - n_drafts), "non-draft"),
            (st.get("drafts", n_drafts), "drafts (excluded)"),
            (st.get("counting_approvals", "—"), "counting approvals"),
            (st.get("fast_lane", len(r.get("fast_lane", []))), "fast lane"),
            (st.get("one_fix_away", sum(len(v) for v in r.get("one_fix_away", {}).values())), "one fix away"),
            (st.get("fork_ci_unrun", "—"), "fork PRs, CI never ran"),
            (st.get("never_human_reviewed", "—"), "never human-reviewed"),
        ]
        body = f'<header><h1>Reflex PR readiness</h1><div class="sub">reflex-dev/reflex · open non-draft PRs ranked by how close they are to merging today · updated {esc(date)}'
        if run.get("started_at"): body += f' ({esc(run["started_at"])})'
        body += "</div></header>"
        body += '<div class="tiles">' + "".join(f'<div class="tile"><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>' for n, l in tiles) + "</div>"
        if r.get("attention"):
            body += '<div class="attention"><h2>Needs attention today</h2><ul>' + "".join(f"<li>{linkify(a)}</li>" for a in r["attention"]) + "</ul></div>"
        panes = [
            ("top", "Top 15", len(r.get("top15", [])), self.pane_top()),
            ("onefix", "One fix away", sum(len(v) for v in r.get("one_fix_away", {}).values()), self.pane_onefix()),
            ("fast", "Fast lane", len(r.get("fast_lane", [])), self.pane_simple("fast_lane", "Nothing verified mergeable at a glance.")),
            ("close", "Close candidates", len(r.get("closure", [])), self.pane_close()),
            ("stacks", "Stacks", len(r.get("stacks") or self.meas.get("stacks", [])), self.pane_stacks()),
            ("delta", "Since last run", None, self.pane_delta()),
            ("method", "Method & caveats", None, self.pane_method()),
        ]
        body += '<nav class="tabs">' + "".join(
            f'<button data-pane="{pid}">{esc(label)}' + (f'<span class="c">{c}</span>' if c is not None else "") + "</button>"
            for pid, label, c, _ in panes) + "</nav>"
        for pid, _, _, content in panes:
            body += f'<section class="pane" id="{pid}">{content}</section>'
        body += f'<footer>Generated by the <a href="https://github.com/masenf/rx-review-queue">rx-review-queue</a> skill. Only the GitHub merge box is authoritative; search qualifiers and bot summaries are not. Source data: <code>{esc(self.run_dir.resolve().relative_to(ROOT) if self.run_dir.resolve().is_relative_to(ROOT) else self.run_dir)}/</code>.</footer>'
        tpl = (ROOT / "artifacts" / "template.html").read_text()
        return tpl.replace("{{DATE}}", esc(date)).replace("{{BODY}}", body)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("-o", "--output", default=str(ROOT / "artifacts" / "index.html"))
    ap.add_argument("--no-history", action="store_true")
    args = ap.parse_args()
    b = Board(args.run_dir)
    out = Path(args.output)
    out.write_text(b.render())
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    if not args.no_history:
        hist = ROOT / "artifacts" / "history" / f"{Path(args.run_dir).name}.html"
        hist.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, hist)
        print(f"copied to {hist}")


if __name__ == "__main__":
    main()
