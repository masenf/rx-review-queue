# Review board, 2026-09-30

- Clear #7325 first: it has a current-head approval, clean merge, full green CI, and one P3 bot thread left to adjudicate.
- Review #7219 next: focused issue-backed fix, three files, targeted test, clean merge, full green CI, and no unresolved threads. Prefer it over broader #7350.
- Give #6553 its first maintainer look: clean, full-green, tested, issue-backed, and blocked only by one current P2 bot finding.
- #7357 and #7288 also meet the strict waiting-on-maintainer rule. Reserve a dedicated block for #7288 because it spans 93 files and +16,973 lines.
- Leave #7352 and #7366 with their authors for now: #7352 has a CodeQL secret-logging finding; #7366 has Ruff failures and two open findings.

The new board has 3 PRs in **Waiting on maintainer** and all 35 non-draft PRs with no other human maintainer interaction in **No maintainer review**, ordered by review value. Since 9/29, #6676, #7237, #7279, #7286, #7330, and #7348 merged; #6413, #6597, #6743, #6744, and #6912 closed without merge.
