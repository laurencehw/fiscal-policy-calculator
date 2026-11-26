# Lane REVIEW-2: a sealed battery, with tax cuts (entry)

Entered 2026-11-26. Owner decision (2026-11-26, project thread): "i agree with
your recommendations -- please move forward". This is proposal 2 of
`planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md`.

The rules are in the docstring of `fiscal_model/validation/sealed.py`. In
short:
- The rows are locked at entry and scored in a later commit.
- They are never pooled with the 44-row tier, and never gated or tuned to.
- A row read for a fix leaves the battery.
- Tax cuts enter alongside rises.

## Rows entered (scoring off in this commit)

| Case | Published (10 yr, $B) | Source | Shape |
|---|--:|---|---|
| `tf3_opt1_top_rate_35` | +625.3 | Tax Foundation *Options 3.0*, Option 1 | ordinary rate -2pt, top bracket |
| `tf3_opt4_top_rate_50` | -1,603.8 | Option 4 | ordinary rate +13pt, top bracket |
| `tf3_opt7_cg_top_rate_15` | +170.7 | Option 7 | capital gains -5pt above $613,700 |
| `tf3_opt8_cg_top_rate_30` | -362.5 | Option 8 | capital gains +10pt above $613,700 |

All four were read from Tax Foundation's option pages on 2026-11-26. The figures
are conventional primary deficit changes over calendar 2027-2036, on the
post-P.L. 119-21 baseline.

**Why these four.** They are the only rate options in the guide's individual
chapter that the generic path can express with no new code: one rate change
above one threshold. Each comes as a cut and a rise. The H.R. 1 rows (JCX-35-25)
that the follow-up memo suggested are bundles relative to an expiring law, so no
single generic shape expresses them. They are also already scored in the
reconstruction tier, so they are not sealed.

**What the battery does not claim.** The four were published before the lock,
so they are sealed (never run) rather than prospective. A score published
after the lock for a bill the generic path can express enters the same way.

## Outturn

Scored 2026-11-26 in the commit after the entry commit (68a6bfb), with
`python scripts/sealed_battery.py`. Rule 3 applies from here on: these are
recorded, not fixed.

| Case | Published | Model | Error |
|---|--:|--:|--:|
| `tf3_opt1_top_rate_35` (cut) | +625.3 | +230.1 | 63.2% |
| `tf3_opt4_top_rate_50` (rise) | -1,603.8 | -1,495.8 | 6.7% |
| `tf3_opt7_cg_top_rate_15` (cut) | +170.7 | model error | n/a |
| `tf3_opt8_cg_top_rate_30` (rise) | -362.5 | -59.0 | 83.7% |

The pooled mean over four rows is 63.4% and is not a figure anyone should
quote. The three findings below are what the battery is for.

1. **The ordinary-rate path is linear in the point change; Tax Foundation's is
   not.** The model gives $115B a point both ways: +13 points is -$1,495.8B
   and -2 points is +$230.1B. Tax Foundation gives $123B a point for the rise
   and $313B a point for the cut. The rise lands within 7%; the cut misses by
   63%. The model has never been tested on a cut, and the first cut it meets
   is the row it misses.
2. **The capital-gains module cannot score a cut in the top rate.** It moves
   the effective rate in each SOI income bracket above the threshold by the
   statutory change. In at least one bracket the effective rate is below five
   points, so a -5 point change takes it below zero and the module raises.
   This is the same limit Tailor's new capital-gains lever reports. Scoring a
   statutory top-rate change needs the top-bracket share of each bracket's
   gains, which the module does not carry.
3. **The capital-gains rise is a sixth of Tax Foundation's.** +10 points above
   $613,700 gives -$59.0B against -$362.5B. The realization response, the
   frozen Dowd-McClelland-Muthitacharoen pair, takes back most of the static
   gain at a rate change this large. The 44-row tier tests only +2 points.

None of the three is fixed here. A fix to any of them is its own lane, and the
row it was found on leaves the battery when that lane opens (rule 3).

