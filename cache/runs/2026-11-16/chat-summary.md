## Needs attention today

- Make the cheap merge decisions first on #7714; each already has a current-head counting approval.
- Spend the first review block on #7898, #7766, #7911, #7886: the highest-value clean, full-green, thread-free candidates after merge-ready work.
- Cheap unblock: approve fork workflows for #7901, #7887, #7829, #7884 before committing review time.
- Focused re-review: #7594 is clean, full-green, thread-free, and has author activity after the maintainer's prior change request; re-review or dismiss that stale decision.
- Duplicate cleanup: compare #7744 with the better-tested #7759, and #7888 with the clean/green #7886; close the superseded implementation in each pair.
- The queue is moving quickly: 107 PRs merged and 19 closed without merge since November 2, while 56 currently-open PRs arrived.

## Since last run

- Merged: #6936, #7057, #7060, #7233, #7276, #7409, #7575, #7590, #7616, #7638, #7642, #7647, #7648, #7651, #7652, #7656, #7668, #7670, #7673, #7679, #7693, #7694, #7696, #7697, #7698, #7700, #7706, #7707, #7710, #7712, #7713, #7715, #7716, #7717, #7721, #7722, #7723, #7724, #7731, #7733, #7734, #7735, #7738, #7739, #7740, #7741, #7742, #7743, #7745, #7746, #7747, #7748, #7750, #7751, #7752, #7753, #7754, #7755, #7756, #7757, #7758, #7770, #7779, #7782, #7783, #7784, #7789, #7793, #7794, #7795, #7796, #7797, #7798, #7799, #7800, #7802, #7803, #7804, #7806, #7807, #7808, #7809, #7810, #7811, #7812, #7813, #7814, #7815, #7816, #7817, #7818, #7820, #7821, #7828, #7855, #7859, #7861, #7862, #7863, #7864, #7865, #7866, #7870, #7878, #7879, #7895, #7912.
- Closed without merge: #6378, #7058, #7442, #7451, #7595, #7625, #7631, #7659, #7687, #7690, #7692, #7701, #7726, #7728, #7762, #7765, #7792, #7801, #7889.
- Currently open and new since November 2: #7727, #7744, #7759, #7760, #7761, #7764, #7766, #7769, #7776, #7777, #7778, #7780, #7781, #7786, #7788, #7790, #7823, #7824, #7829, #7853, #7867, #7868, #7871, #7872, #7874, #7875, #7876, #7877, #7880, #7881, #7882, #7883, #7884, #7885, #7886, #7887, #7888, #7890, #7891, #7892, #7893, #7897, #7898, #7899, #7900, #7901, #7902, #7903, #7904, #7905, #7906, #7907, #7908, #7909, #7910, #7911.
- Entered the top 15: #7714, #7898, #7766, #7911, #7886, #7899, #7881, #7671, #7874, #7885, #7905, #7890, #7901, #7824.
- Left the top 15: #7712, #7693, #7716, #7670, #7668, #7717, #7409, #7594, #7715, #7276, #7647, #7652, #7590, #7651.
- Newly unblocked: #7033, #7671, #7714, #7718. Newly blocked: none.

## Duplicate candidates

- #7744 and #7759 both close #7736; #7759 has broader saved regression coverage, so confirm it as the winner and close #7744.
- #7888 and #7886 both close #7832 and overlap four core files; #7886 is clean, green, and thread-free, so confirm it as the winner and close #7888.

## Caveats

- Final snapshot: 134 open PRs (106 non-drafts, 28 drafts); 20 meet the strict waiting-on-maintainer test.
- #7741 is the only merged PR in the delta that did not target main; all 106 main-target merge commits were verified on current main.
- Duplicate recommendations require maintainer confirmation before closure.

[Open the review board](https://masenf.github.io/rx-review-queue/)
