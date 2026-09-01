# Redesign — owner decisions (2026-08-31)

Resolves the open questions in `REDESIGN_PLAN.md` §10. These are settled; do not re-ask.

| # | Question | Decision |
|---|----------|----------|
| 1 | Full Data Status panel location | **Popover on the pill.** The compact `CBO Feb 2026 · SOI 2023` pill in the shared chrome opens an `st.popover` containing the full Data Status panel (moved from the sidebar). Reachable on every page. |
| 2 | Model settings placement | **Inline + settings popover. No sidebar anywhere.** Dynamic-scoring toggle sits next to Score/Calculate on Tailor and Explore. Dark mode lives in a small ⚙ popover in the shared chrome. |
| 3 | Package Studio (#65) vs Phase 3b | **Merge: refactor Package Studio into the "Start from your values" panel inside Build.** Enforce the plan's architecture rule — LLM only translates free text → values vector; a deterministic selector (`values/select.py`) picks policies from tags + vector; archetypes work with no LLM; symmetry harness + determinism tests. One surface, one scoreboard, one export path. Studio's separate tab goes away (redirect if it had a URL). |
| 4 | Execution style | **Parallel Opus agents where the Phase 0 file-ownership map shows disjoint files;** orchestrator integrates and runs the test suite between waves. |
| 5 | Page naming | **Build** (with "Start from your values" as its opening panel), per wireframes. |
| 6 | Top-nav styling | Accept stock `st.navigation(position="top")` look; at most one isolated CSS block. Pin Streamlit to the tested minor version. |
| 7 | Deployment entry point | `app.py` stays the Streamlit Cloud entry point (it becomes the router). |

Still owner-review-before-launch (not blocking): the five archetype names/vectors (§5b.3) for steelman quality.
