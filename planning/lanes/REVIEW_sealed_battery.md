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

(appended in the scoring commit)
