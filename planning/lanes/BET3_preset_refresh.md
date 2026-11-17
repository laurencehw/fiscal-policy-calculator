# Bet 3, first PR: archive the pre-2025-law presets, restore the PTC label, add a permanent $40K SALT cap (pre-registration)

Pre-registered 2026-11-17, before any code in this lane is written. The outturn
is appended below the line at the end, in the same commit series, and the
predictions above it are not edited after the first code commit.

## Scope (owner's choice on the decision card, option A)

The 16 November site review's bigger bet 3 asks for a preset set fit for 2026
debates: retire what the 2025 law overtook and add the live questions (tip,
overtime and senior deductions after 2028, the SALT cap reverting in 2030, the
lapsed enhanced premium credits, current tariffs, 2034 Social Security
options). Laurence chose a first PR that uses only machinery already in the
repository and needs no figure that cannot be checked from here (JCT, CBO, Tax
Foundation, CRFB and Yale are all refused by this environment's proxy):

1. **Archive the eight pre-2025-law presets.** The presets flagged
   `pre_2025_law=True` in `fiscal_model/policy_status.py` (TCJA full, TCJA
   rates only, TCJA without the SALT cap, estate, CTC, AMT, IRA clean-energy
   repeal, EV credit repeal) move into their own last group on Explore and
   Build, named "Archived: scored against pre-2025 law", with one note saying
   why. Nothing is deleted: every page, share link, frozen link and CSV keeps
   working, and bet 1's current-law answers stay on each page. Build already
   leaves them out of starting packages (PR #248).
2. **"Extend ACA Enhanced PTCs" becomes "Restore ACA Enhanced PTCs".** The
   enhanced credits lapsed at the end of 2025, so on the FY2026-2035 window the
   proposal is a restoration. Slug unchanged, old label kept in
   `LEGACY_LABEL_ALIASES`, the published figure ($335B) unchanged. Whether any
   law since my training data restored them is not something I can check from
   here, so the status note says they lapsed after 2025 and is flagged for
   Laurence to confirm.
3. **A new preset, "Keep the $40K SALT Cap After 2029"** (`salt-cap-40k-permanent`).
   Under P.L. 119-21 sec. 70120 the cap is $40,000 in 2025, $40,400 in 2026,
   101% of the prior year through 2029, phased down by 30% of MAGI above the
   threshold but never below $10,000, and $10,000 flat from 2030. The reform
   keeps the 2029 limitation and threshold and carries them forward at the same
   101% a year, phasedown included. It is priced by the existing
   `SaltCapBaseline` machinery (PR #161) as a difference of two cap paths on
   the same SOI distribution: no new data, no new constant, nothing fitted.

Not in this PR: tips, overtime and the senior deduction (no income base for
any of them; JCT nets the senior deduction inside another row), current tariff
policy, and 2034 Social Security options. Each is a lane of its own.

## Mechanism for the SALT preset

`TaxExpenditurePolicy` with `expenditure_type=SALT`, `action="expand"` (the
action cap repeal already uses, so it takes the same sourced offset direction
and the same unsourced 0.05 magnitude with no new rule), plus a new field naming
the cap path the reform moves *to*. `None` keeps today's meaning, no cap at
all, so `salt-cap-repeal` and every other SALT row are untouched. The new path
is a fourth `SaltCapBaseline` member, `RAISED_CAP_PERMANENT`, which equals
`CURRENT_LAW` through 2029.

## Predictions

Computed before any code from the existing path functions
(`salt_expenditure_billions`, `SaltCapYear.cap_at`, the SOI capped-deduction
distribution) with the expenditure record's 3%/yr base growth, i.e. the
mechanism's own arithmetic, not a target:

| FY | Current law ($B) | Raised cap kept ($B) | Static cost ($B) |
|---|--:|--:|--:|
| 2026-2029 | 39.9-42.2 | identical | **0.0** each year |
| 2030 | 25.8 | 43.0 | 17.2 |
| 2035 | 26.6 | 47.4 | 20.8 |
| FY2026-2035 | | | **+113.6 static** |

* The preset's ten-year conventional score lands in **[+$105B, +$125B]**
  (static +$113.6B moved by the 5% magnifying offset cap repeal uses, and by
  whatever the engine's own growth convention does to a path that is zero for
  four years). Sign: adds to the deficit.
* FY2026-FY2029 contribute **exactly $0**.
* It is **below** `salt-cap-repeal` (+$740.3B) and below the 2030-2035 slice of
  that repeal, since a $47K cap is still a cap.
* **No published score is attached.** The preset has no `CBO_SCORE_MAP` row,
  so it carries no badge, is not in Build (Build lists published figures) and
  appears in Explore with "No published score". Any figure I find for it by web
  search would be flagged for Laurence, not registered.
* **Nothing else moves**: every other preset's static and dynamic score,
  `cold_holdout.py --json`, `run_validation_dashboard.py`, `run_loo.py
  --donor-matrix` and `current_evidence.json` are byte-identical. The archive
  and the rename are presentation only.

## Falsification

* Any non-zero year in FY2026-2029, or a ten-year figure outside the band,
  means the path or the engine's aging is not doing what this document says.
* Any change to `salt-cap-repeal` or to either SALT benchmark row means the new
  field leaked into the default.
