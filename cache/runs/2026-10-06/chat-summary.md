# Review board, 2026-10-06

- Review #7438, #7409, and #7416 first. They are compact, clean, green, and waiting for a first maintainer review.
- Give #7273 the next slot, then make the deliberate API-compatibility call on breaking PR #7408. Both are clean and full-green.
- Resolve the single outdated thread on each of #7411, #7441, and #7407; all three are otherwise strong review candidates.
- Approve workflow runs for #7345, #7437, and #7443. Their remaining blocker is maintainer action rather than author code.
- Rerun or adjudicate likely off-path failures on #7404, #7434, and #7442 before sending them back to authors.
- Send #7412 and #7446 back to their authors: each fails tests introduced by its own change. Leave new #7449 with its author as well; its Python 3.10 warning breaks import-lightness and six CLI probes on both platforms.

The refreshed board has 6 PRs in **Waiting on maintainer** and 35 in **No maintainer review**. Since 10/05, #7398, #7414, and #7423 merged, #7400 closed without merge, and 17 PRs opened. The label audit added 72 missing labels across all open PRs: 31 `bug`, 6 `perf`, 28 `documentation`, and 7 `breaking`.
