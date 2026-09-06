# Cold start: where the first-hit wait actually goes

*Measured 2026-09-05/06 on `perf/cold-start-measurement`, branched from `main`
@ `a251b32`. Every number here comes from `python scripts/measure_cold_start.py`
on this tree; nothing is estimated. Reproduce with:*

```bash
python scripts/measure_cold_start.py all --repeats 3 --json cold_start.json
python scripts/measure_cold_start.py imports --repeats 3 --no-pycache
python scripts/measure_cold_start.py paint --repeats 5
```

This closes the measurement `planning/redesign/FOLLOWUPS.md` and
`planning/MODELING_IMPROVEMENT.md` §6.2 item 29 both left open. PR #82 shipped
option (a) — paint the chrome before the heavy work — and the open question was
whether the remaining wait is **import / first-run compute** (in which case
there is more of (a) to do) or **container scheduling** (in which case only
(b) a warm container or (c) an explanation in the copy around the link helps).

**The answer is neither of the two things the question offered.** Import time
was real but small and is now largely gone. Container scheduling is real and
unmeasurable from here. The largest single term in the local first hit was
something nobody had looked for: **the page footer computes the entire
validation scorecard to print one sentence**, and on the landing page that is
93% of the first script run.

This is 🔵 exploratory tier (UX), so everything below is held to a UX bar, not
an accuracy bar. Nothing here changes a scored number.

---

## 1. The decomposition

Local cold first hit, landing page (`/`), median of 3 cold subprocesses. The
"share of 20s" column apportions against the ~20s figure FOLLOWUPS quotes for
the live first hit — see §5 for why that mapping is loose at both ends.

| Term | Before | After | Share of ~20s |
|---|---|---|---|
| **Network transport** (DNS + TCP + TLS + edge TTFB) | 0.55s | 0.55s | ~3% |
| **Container scheduling / wake** | not measurable locally | unchanged | unknown, see §4 |
| **Python + Streamlit import** (`import streamlit`, unavoidable) | 0.64s | 0.64s | ~3% |
| **App module-level import before first paint** | 1.59s | **0.02s** | 8% → 0.1% |
| **App module import after first paint** (deps + page modules) | ~1.7s | ~1.7s | ~9% |
| **Dependency / data build** (`build_app_dependencies`) | 0.33–2.3s | unchanged | ~2–11% |
| **Footer validation scorecard** | 5.79s idle / 8.68s loaded | **0.000s** (§5) | **29–43%** → 0 |
| **Everything else in the render** | ~0.7s | ~0.7s | ~4% |

Two rows are load-bearing and neither was in the original hypothesis.

### 1.1 The footer computes the scorecard

`components/chrome.render_page_footer` → `fiscal_model/ui/tabs_controller.render_footer`
→ `_footer_validation_clause()` → `fiscal_model/ui/helpers.validated_policy_count()`
→ `fiscal_model/validation/scorecard.cached_default_scorecard()` →
`compute_scorecard()` → `validate_all()`.

That runs **every specialized validator over all 81 scorecard rows** in order to
render one clause: *"75 policies benchmarked against published scores · "*.

Measured standalone, medians of 3 fresh processes on an idle machine:

```
import fiscal_model.validation.scorecard    1.640s
cached_default_scorecard()   first, cold    5.787s
cached_default_scorecard()   second         0.000s   (lru_cache, maxsize=1)
published_entries=75 total=81
```

In-run, via `measure_cold_start.py firstrun` (machine shared with five
concurrent modelling lanes, so absolutes are inflated; the **shares** are the
robust part):

| Scenario | AppTest first run | of which scorecard | of which deps build |
|---|---|---|---|
| landing `/` | 9.375s | **8.676s (93%)** | 0.325s |
| scored `/explore?preset=tcja-full-extension&run=1` | 20.240s | **11.142s (55%)** | 2.258s |

Under cProfile the call tree is unambiguous — the cost is the capital-gains
machinery, `fiscal_model/data/capital_gains.py`'s `get_brackets_above_threshold`
/ `realization_hazard` / `pareto_tail_index` and `policies_core.py`'s
`lock_in_wedge` / `stock_ratio`, running pandas `iterrows` roughly 93,000 times
across the 81 rows.

Three things about this are worth stating carefully:

- **It is memoized process-wide**, not per session (`@lru_cache(maxsize=1)` on a
  module-level function). So exactly **one visitor per container** pays it — the
  first one — and every visitor after that gets the clause for free. That is
  precisely the cold-start case, and precisely the visitor FOLLOWUPS is about.
- **The docstrings disagree with the measurement, in both directions.**
  `scorecard.py` says "takes ~50ms"; `ui/helpers.py` says "~2.5s on a cold
  process". It is 5.8s idle. Both comments predate the Wave 2 L1 capital-gains
  rebuild, which is where the cost came from. Neither was wrong when written.
- **`ui/helpers.py` already states the right principle** — *"That is fine at the
  foot of a page that has already painted, and not fine on the critical path of
  the very first script run"* — and `app._render_head_metadata` already honours
  it via `allow_compute=False`. The footer does not, and on Streamlit the footer
  **is** on the critical path: the script run must complete before the page is
  interactive.

### 1.2 Bytecode compilation is a real cold-container tax

A fresh Community Cloud container clones the repo and pip-installs
requirements. It does **not** pre-compile the app's own 402 modules, so the
first `import` in a container's life compiles them all. Measured by copying the
tree to a scratch directory with every `__pycache__` stripped
(`imports --no-pycache`), medians of 3:

| | warm `__pycache__` | stripped | modules |
|---|---|---|---|
| `import app` **before** | 2.296s | **4.317s** | 1,901 |
| `import app` **after** | 0.672s | **0.702s** | 586 |

Measuring in the working tree would have hidden 2.0s of this, because every run
leaves `.pyc` files behind for the next one.

---

## 2. What changed, and what it bought

One commit, `app.py` only. **No page renders differently.**

`app.py` named a `fiscal_model` submodule at module scope — `from
fiscal_model.ui.runtime_logging import …`. Streamlit executes the file top to
bottom before `main()` reaches a line, so that import was paid before the first
pixel. Almost none of it was the thing being imported: `runtime_logging` is
three stdlib-only functions. It was the **packages on the way there**, which
Python must execute to reach a submodule:

```
fiscal_model.ui.runtime_logging      1.110s cumulative
  fiscal_model/__init__                0.984s   (re-exports every policy module)
    fiscal_model.uncertainty             0.563s   -> scipy.stats
    fiscal_model.reporting               0.374s   -> matplotlib.pyplot
  fiscal_model/ui/__init__               0.125s
  runtime_logging itself                 0.001s
```

Three moves:

1. The logging helpers move behind `_runtime_logging()`, called after the boot
   placeholder is on screen. The `app_boot` log line therefore lands slightly
   later than it used to — the only behavioural change, and it is in the log,
   not the page.
2. `pandas` leaves module scope. `main(pd_module=…)` keeps its seam (every test
   passes it explicitly); `None` means "import it in the deps builder", which is
   after first paint and before the build that needs it.
3. `_render_head_metadata` stops asking for the benchmark count on the run where
   the answer is **provably 0**. `allow_compute=False` reads an `lru_cache`
   inside `fiscal_model.validation.scorecard`; a cache in a module that has not
   been imported is empty by construction, so the question cost a 1.1s import of
   `fiscal_model` to be told nothing. It is skipped until something else loads
   the module — which the footer does moments later — so from the second run on,
   the branch is taken and the `<meta>` blurb is byte-identical.

Measured before and after, back to back on the same tree under the same load:

| | before | after |
|---|---|---|
| **time to first paint** (process start → `st.set_page_config`) | **1.593s** | **0.022s** |
| `import app`, warm `__pycache__` | 2.296s | 0.672s |
| `import app`, stripped `__pycache__` | 4.317s | 0.702s |
| modules loaded at import | 1,901 | 586 |

The **full** first run is unchanged, by design. `fiscal_model` is pulled in a
moment later by the dependency build regardless. This is ordering, not
avoidance: what moved is how long the page is blank before PR #82's boot
caption can appear.

### 2.1 What was *not* done, and why

The bar set before measuring was: *act on imports only if they are ≥3s of the
local first hit.* On the pre-change tree they were **1.59s** before paint with a
warm `__pycache__` — under the bar — and **4.32s** with it stripped, over it.
The change was made on the stripped reading, because that is the one a real
container pays, and it is confined to ordering. Recording the bar and both
readings because the decision turned on which of the two you look at, and a
later reader should be able to disagree with the choice rather than have to
reconstruct it.

Beyond that, **nothing further was implemented, deliberately**:

- **Plotly is not a problem.** `import plotly` is 0.030s — it defers its own
  submodules. The 0.140s under `streamlit.elements.plotly_chart` is inside
  Streamlit and not reachable from app code.
- **matplotlib and scipy are not reachable from this lane.** Their 0.94s comes
  from `fiscal_model/__init__` re-exporting `reporting` and `uncertainty`.
  Making that lazy means editing the scoring package's `__init__`, which is out
  of scope while five modelling lanes are working in `fiscal_model/`. It is also
  a smaller prize than it looks: the deps build needs those modules within the
  same script run anyway, so the win would again be ordering, and the ordering
  win has already been taken at the `app.py` boundary.
- **The page modules are already cheap.** `app_pages.build/tailor/explore/
  tracker/methodology/classroom/about` each import in ≤0.007s once `chrome` has
  loaded. There is no bill-tracker/OLG/assistant-client import to defer on the
  landing path; those are already function-level.
- **The scorecard was not deferred**, and that is the one substantive thing left
  undone. See §3.

---

## 3. The open finding: defer the footer's scorecard

> **Closed 2026-09-06 by `perf/footer-scorecard`, and on neither of the two
> candidates below — see §5.** The count is now a generated artifact, the
> landing page's first script run went **8.404s → 0.668s**, and the clause
> still prints the same number. The rest of this section is left as written,
> because §5.2 is an argument against one of its own candidates.

**This is the largest remaining item and it is not this lane's to fix.** The
call site is `fiscal_model/ui/tabs_controller.render_footer`, and this lane's
charter limits `fiscal_model/ui/**` to import ordering and lazy imports. Handing
it over with the numbers rather than editing it.

The shape of the fix, for whoever picks it up:

- `validated_policy_count(allow_compute=False)` already exists and already has
  the right contract — `_footer_validation_clause` is documented to return `""`
  at a zero count so *"the footer simply loses the clause rather than showing an
  empty one"*. Using it in the footer would take 5.8–8.7s off the first hit at
  the cost of the clause being absent on the **first** script run only.
- Pair it with a background pre-warm so the clause is present from the second
  run on. The app already spawns a daemon thread for the Ask prompt-cache
  pre-warm, so the pattern exists. Note that Community Cloud containers are
  small; a pre-warm thread overlaps poorly with the boot work on one vCPU, so
  the honest expectation is that it moves the cost off the *first* run rather
  than eliminating it.
- **The alternative is to make the scorecard fast**, which is a green-tier
  question and a better one. 5.8s for 81 rows is ~72ms/row, and the profile puts
  nearly all of it in ~93,000 pandas `iterrows` calls under the Wave 2 L1
  capital-gains path. That is a scoring-module performance question and belongs
  to a modelling lane, not a UX one. It is also the version of the fix that
  needs no UX compromise at all.

Whichever is chosen, **update the two stale docstrings** — `scorecard.py`'s
"~50ms" and `ui/helpers.py`'s "~2.5s" — since both now understate by 2–100×.

---

## 4. The Cloud half: what these numbers cannot see

**Streamlit Community Cloud apps sleep after 12 hours without traffic, and they
do not wake by themselves.** A visitor arriving at a sleeping app gets
Streamlit's own page with a **"Yes, get this app back up!"** button and must
click it; anyone with view access can, not just the owner.
([docs.streamlit.io — Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app),
corroborated on [discuss.streamlit.io](https://discuss.streamlit.io/t/my-apps-are-sleeping-and-it-doesnt-wake-up/49909).)

This is decisive for the FOLLOWUPS decision and it is worth being blunt about:
**for a slept app, no amount of import or render optimisation touches the first
visitor's experience at all.** They are looking at Streamlit's interstitial, not
at the app, until they click a button. Only (b) a warm container — paid tier, or
an external pinger inside the 12-hour window — or (c) copy around the link that
sets the expectation, changes that.

The local measurements also cannot see:

- **Container scheduling and image pull.** Between the click and the app's first
  script run, Community Cloud has to schedule and start a container. Nothing
  here observes it.
- **Cloud CPU.** Every local number is from a developer machine that was
  simultaneously running five modelling lanes. Absolutes swung ~2× with load
  during this session (a landing first run measured 8.5s idle and ~19s loaded);
  a Community Cloud container is small and shared. Read the **shares**, not the
  seconds.
- **The app's own first byte over HTTP.** `https://fiscal-policy-calculator.streamlit.app/`
  does not serve the shell: it answers `303` to
  `share.streamlit.io/-/auth/app?redirect_uri=…`, an auth bounce a scripted
  client cannot complete (it terminates at a `404` for a non-browser). So the
  live lane can only bound transport — **0.55s median for the whole terminating
  chain, warm** — and cannot reach the app's own TTFB. What it does establish is
  that DNS, TCP, TLS and edge latency together are ~3% of 20s and can be ruled
  out as a cause.

### 4.1 Runbook for the cold Cloud measurement

A sleep cannot be forced; it has to be waited out.

1. Leave the app untouched for **>12 hours** (no visits, and disable any
   uptime pinger). A single visit resets the clock.
2. From a browser with devtools open on the Network tab, load
   `https://fiscal-policy-calculator.streamlit.app`. Record: whether the
   sleeping page appears; the wall-clock from the **click on "Yes, get this app
   back up!"** to the first painted element; and to full interactivity.
3. Immediately after, run `python scripts/measure_cold_start.py live --repeats 3`
   to capture the now-warm transport for comparison, and note the first-hop TTFB.
4. Reload once warm and record the same two wall-clocks. **Warm minus cold is
   the scheduling + wake cost** — the term this memo can only name.
5. Append the numbers to §1's table.

The measurement is cheap but has a 12-hour lead time, which is why it is a
runbook rather than a result.

---

## 5. Outturn (2026-09-06): §3 closed, on a third option

*Branch `perf/footer-scorecard`, from `main` @ `099332a`. Every number below is
`python scripts/measure_cold_start.py firstrun --repeats 3` on this tree,
before and after, back to back under the same load. The baseline differs from
§1's — that was measured on a different day against a different `main` — so
read the pairs, not the cross-section.*

### 5.1 The number

| first script run, median of 3 cold processes | before | after |
|---|---|---|
| **landing `/`** — `AppTest first run` | **8.404s** | **0.668s** |
| of which the validation scorecard | 7.652s (91%) | **0.000s** |
| whole probe process, landing | 11.168s | 3.447s |
| **scored `/explore?preset=tcja-full-extension&run=1`** | 10.377s | 10.604s |
| of which the validation scorecard | 6.629s | 6.352s |
| whole probe process, scored | 13.075s | 13.375s |

The landing page's first script run is **92% shorter**. The scored page's is
**unchanged**, and that is a finding rather than a failure — see §5.4.

### 5.2 Which of §3's candidates, and why neither

§3 offered two: defer the clause behind `allow_compute=False` (fast, but the
first visitor loses the clause), or make the scorecard fast (no UX compromise,
but it is a green-tier scoring-performance project). A third option costs less
than either and gives up nothing:

**Pin the count as a generated artifact.** `scripts/build_validation_headline.py`
computes the scorecard once, at author time, and writes
`fiscal_model/data_files/validation/headline_counts.json`;
`fiscal_model/ui/validation_headline.py` reads it with stdlib `json`; and
`tests/test_validation_headline.py` recomputes the scorecard and fails if the
two ever disagree. That is the generate-then-pin pattern the repository already
uses for the outlay profiles (`scripts/fit_outlay_rates.py` +
`tests/test_spending_outlays.py`) and the policy tags
(`scripts/derive_policy_tags.py` + `tests/test_policy_catalog.py`).

The reason to prefer it here is that the footer's clause is a **validation
claim**, and each of the alternatives concedes something on that front:

- *Deferring* means the first visitor — the only one who was ever paying the
  8s, and the one the whole memo is about — is also the only one who is not
  told what the model has been benchmarked against. The clause is dropped
  precisely for the reader with the least context.
- *A cheap derivation from the registries*, §3's implied option (b), **cannot
  be made exact**, and this is worth recording because it looks like it should
  be. `published_entries` is `len(entries) − model_estimate − unclassified`,
  and `entries` is not a registry property: every runner appends a row only if
  its validator *returns* one, `validate_all_capital_gains` swallows exceptions
  per scenario and `core.validate_all` drops a falsy result. A registry count
  would therefore over-report by exactly the number of benchmarks currently
  failing to score — the state in which an accurate count matters most. The
  only way to know how many rows the scorecard has is to build the scorecard.
- *Making the scorecard fast* remains the better fix and is untouched here. It
  is ~93,000 pandas `iterrows` under the Wave 2 L1 capital-gains path, it is a
  green-tier question, and it would also fix §5.4, which this lane cannot.

### 5.3 How the count stays exact

Three sources, in `fiscal_model/ui/helpers.validated_policy_count`, first one
that answers wins:

1. **A scorecard already computed in this process** (`sys.modules` probe, no
   import, `lru_cache` currsize check). Exact by definition and free, so it
   wins — which is also why a stale artifact self-corrects within a session
   rather than outvoting a scorecard the process actually built.
2. **The pinned artifact.** This is the path the first script run takes.
3. **Computing the scorecard**, only if the artifact cannot be read *and* the
   caller allows it. Deleting the file costs the old 5.8s; it never costs the
   truth.

Zero — and the dropped clause — is now reached only when all three fail.

Exactness rests on `test_the_pinned_count_is_the_scorecard_count`, which builds
the live scorecard and compares, and on
`test_the_whole_payload_is_reproducible_from_the_scorecard`, which regenerates
every count in the file so a hand edit to any of them fails in CI with the
regeneration command in the message. `python scripts/build_validation_headline.py
--check` is the same assertion as a one-line CI step. The file carries no
timestamp, deliberately: it is a pure function of the tree, so regenerating an
unchanged tree must produce a byte-identical file, and a "generated at" field
would churn every diff while being the one field no test could check. The
current value is **75 published of 81 rows**, which is what `main` prints today.

The cold-start invariant is pinned structurally rather than by a timing
assertion, which would flake:
`test_the_footer_clause_never_computes_the_scorecard_on_a_cold_process` runs a
fresh interpreter, produces both clauses, and asserts the scorecard's
`lru_cache` is still **empty** — and that the clause came out non-empty anyway,
which is the half that makes it a fix rather than a deletion.
`test_a_cold_process_prints_the_same_clause_a_warm_one_does` pins the two
against each other byte-for-byte.

Note the assertion is about the *compute*, not the import. `fiscal_model.ui`'s
own `__init__` reaches `dependencies` → `assistant.benchmarks` →
`validation.cbo_scores`, and `fiscal_model/validation/__init__` re-exports
`cached_default_scorecard`, so §1.1's 1.6s module import is paid by anything
that touches `fiscal_model.ui` at all and is not reachable from this lane. The
5.8s behind it is what moved.

### 5.4 What did not move: the scored route pays for a different caller

`/explore?…&run=1` still computes the scorecard, and it is no longer the
footer. Instrumented with a stack capture, the scored run has exactly **one**
call over half a second — **6.555s** — and it arrives at
`preset_validation.get_validation_badge` → `_scorecard_index`, from
`policy_input_tax.render_tax_policy_inputs`. The per-preset accuracy badge
needs each row's model figure, official figure, rating and source URL, not a
count, so an artifact of counts cannot serve it, and pinning model outputs
would be a much larger claim than pinning how many rows exist. That is a real
carry-over and it belongs with whoever makes the scorecard fast.

Because the footer is no longer the first caller, the two routes now differ in
an informative way: the landing page proves the clause costs nothing, and the
scored page shows the remaining cost is entirely the evidence badge.

### 5.5 The two docstrings

Both corrected, as §3 asked:

- `fiscal_model/validation/scorecard.py`'s `cached_default_scorecard` said the
  scorecard "takes ~50ms". It is **~5.8s** on an idle cold process. The
  docstring now says so, says when it stopped being true (the Wave 2 L1
  capital-gains rebuild), and says to treat it as seconds when choosing where
  to call it from.
- `fiscal_model/ui/helpers.py`'s `validated_policy_count` said "~2.5s on a cold
  process". Rewritten around the three sources above, with 5.8s / 7.65s-of-8.40s
  in place of the 2.5s.

### 5.6 Files

- `fiscal_model/ui/validation_headline.py` — the artifact's reader and payload
  shape (new).
- `fiscal_model/data_files/validation/headline_counts.json` — the artifact
  (generated).
- `scripts/build_validation_headline.py` — the generator, `--check` mode
  included (new).
- `fiscal_model/ui/helpers.py` — the three-source lookup and the corrected
  docstring.
- `fiscal_model/ui/tabs_controller.py` — docstring only; both clause functions
  call `validated_policy_count` and neither changed.
- `fiscal_model/validation/scorecard.py` — docstring only. No validation logic
  was touched by this lane.
- `tests/test_validation_headline.py` — 18 tests (new).
- `tests/test_polish.py`, `tests/test_ui_helpers_review_fixes.py` — the two
  existing tests whose contract moved: `allow_compute=False` now answers from
  the artifact instead of returning 0, and a broken scorecard alone no longer
  drops the clause, because the artifact behind it is not an invented number.

---

## 6. Honest caveats on the ~20s

The ~20s in FOLLOWUPS is a single observed figure from an external reviewer, not
a distribution, and the mapping in §1's last column is loose at both ends:

- It is not known whether that observation was of a **slept** app (in which case
  most of it is the interstitial and the wake, and the app-side terms barely
  matter) or of a **cold-but-scheduled** container (in which case the app-side
  terms are most of it). §4.1 is how to find out.
- The local totals were measured on a loaded developer machine. It is a
  coincidence, and should not be read as corroboration, that a loaded landing
  first run measured 18–20s.
- The shares in §1 assume the app-side terms scale together under a slower CPU,
  which is roughly right for pure-Python work and wrong for anything I/O-bound.
  The FRED seed inside `build_app_dependencies` is the one I/O term, and it is
  small (the deps build ranged 0.33–2.3s across runs, most of the variance being
  the network).

## 7. Files

- `scripts/measure_cold_start.py` — all four lanes; this memo's numbers are its
  output.
- `app.py` — the ordering change in §2.
- `tests/test_cold_start_ordering.py` — pins the invariant that `app.py` reaches
  nothing under `fiscal_model` at module scope, so the ordering cannot silently
  regress the next time someone adds a convenient top-level import.
- The §5 outturn's files are listed in §5.6 — the artifact, its generator, its
  reader, and `tests/test_validation_headline.py`, which is what keeps a pinned
  validation claim honest.
