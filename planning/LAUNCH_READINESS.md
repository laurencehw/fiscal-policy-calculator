# Launch Readiness Plan — Fiscal Policy Calculator

> QA review conducted April 6, 2026 on fiscal-policy-calculator.streamlit.app

---

## Critical (Must Fix Before Launch)

### 1. OLG Analysis Corrupts Session State — Crashes 3 of 5 Tabs
**Repro:** Go to Generational tab → click "Run OLG Analysis" → after results load, switch to State, Bill Tracker, or Methodology tabs. All three crash with a raw Python `KeyError` traceback visible to the user.
**Root cause:** The OLG analysis likely writes to `st.session_state` with a key that collides with or corrupts the tab rendering logic in `app_controller.py`. The error traces through `_render_generational`.
**Impact:** Any user who tries the Generational tab before other tabs sees a broken app. This is the #1 launch blocker.
**Fix:** Isolate OLG session state keys with a namespace prefix, or catch the KeyError gracefully and re-initialize state.

### 2. OLG Transition Charts Show Nonsensical Values
**Repro:** Generational tab → Run OLG Analysis → scroll to transition path charts.
**Observed:** GDP change drops to -100% around year 2030, interest rate changes show values in the millions of percentage points. These are mathematically impossible outputs.
**Impact:** Instant credibility killer for your target audience of economists and policy staff. If someone screenshots this, it undermines trust in the entire tool.
**Fix:** Clamp chart output ranges to economically plausible bounds (e.g., GDP change ±30%, interest rate ±10pp). Also investigate the OLG solver convergence — the model may be diverging for certain parameter combinations.

### 3. Bill Tracker Dates Show "1970-01-01"
**Repro:** Bill Tracker tab → observe "Introduced" dates on bill cards.
**Observed:** Many bills show "Introduced 1970-01-01" — the Unix epoch default, meaning the date parser returned 0/null.
**Impact:** Makes the bill tracker look broken/unfinished. Users will question data accuracy.
**Fix:** Debug the date parsing in `bill_tracker/database.py` or the congress.gov fetch pipeline. Likely a missing field or format mismatch. Show "Date unknown" as fallback instead of epoch.

---

## High Priority (Next 48 Hours)

### 4. No SEO Metadata
**Observed:** Page has no meta description, no Open Graph tags, no Twitter Card tags. Sharing the URL on Slack, Twitter, or LinkedIn will show a blank preview with just "Streamlit".
**Fix:** Add `st.set_page_config()` with proper title/icon, then inject OG/Twitter meta tags via `st.markdown()` with `unsafe_allow_html=True`. Consider a `.streamlit/config.toml` for theming.

### 5. "Data: Not available" in Sidebar
**Observed:** The sidebar shows "Data: Not available" status indicator, which looks like the app is broken even when everything works fine.
**Fix:** Either populate this with actual data vintage info ("IRS SOI 2022, CBO Feb 2026") or remove it entirely. Showing "not available" is worse than showing nothing.

### 6. Sensitivity Range Shows Identical Bounds
**Observed:** When dynamic scoring is off, the sensitivity range displays "X to X" (e.g., "$4,581.9B to $4,581.9B") which looks like a bug.
**Fix:** Hide the sensitivity range entirely when dynamic scoring is disabled, or show "Enable dynamic scoring for sensitivity analysis."

### 7. Proposal Dropdown Truncates CBO Scores
**Observed:** The preset dropdown shows policy names with CBO scores, but long names get truncated by the Streamlit selectbox width.
**Fix:** Use `format_func` to show shorter display names in the dropdown, with CBO score shown separately below the selector.

### 8. Bill Sponsors Showing as "Unknown"
**Observed:** Several bill cards show "Sponsor: Unknown" despite having valid bill IDs.
**Fix:** Check the congress.gov API response parsing for sponsor fields. May need to fetch from a different endpoint or field name.

### 9. Welcome Card Copy Polish
**Observed:** The welcome card is well-structured but could be tighter. "Select a policy proposal from the sidebar" is the key instruction but it competes with a lot of surrounding text.
**Fix:** Trim to essentials: one sentence explaining what the tool does, one sentence telling them to pick a policy. Move the methodology link and details below the fold.

---

## Nice to Have (This Week)

### 10. Add Quick-Start Presets on Landing
Show 3-4 clickable "scenario cards" on the welcome screen (e.g., "What does extending the TCJA cost?", "Impact of Biden's corporate tax plan", "Score a custom proposal") that auto-populate the sidebar and run the calculation. Reduces time-to-value from ~30 seconds to one click.

### 11. Loading States for Tab Switching
Tab switches have no loading indicator — there's a brief blank state that could be confusing. Add a spinner or skeleton.

### 12. Mobile Tab Scrolling
Verify the mobile CSS fix actually landed in production. The horizontal scroll on tab labels should work, but Streamlit Cloud caching may serve the old version for a while.

### 13. Classroom Mode Discoverability
The separate `classroom_app.py` is invisible from the main app. Add a link or callout for educators: "Teaching a policy class? Try Classroom Mode →"

### 14. Bill Tracker: Add Search/Filter
With 283 bills, scrolling is tedious. Add a text search box and category filter (tax, spending, appropriations).

### 15. Methodology Tab: Add Worked Examples
The methodology documentation is thorough but abstract. Add 1-2 worked examples showing how a specific policy flows through the scoring pipeline (e.g., "How we score a 2pp income tax rate increase on $400K+").

### 16. Export Improvements
CSV export works but could be more useful. Add PDF export for the full results page, and a "Share this analysis" link that encodes the policy parameters in a URL query string.

---

## Post-Launch Backlog

### 17. Favicon and Branding
Currently uses default Streamlit favicon. Add a custom favicon and consistent branding.

### 18. Performance Optimization
First load is ~5-8 seconds on Streamlit Cloud. Profile the import chain — lazy-load heavy modules (OLG, microsim) that aren't needed on first render.

### 19. Error Boundaries
Any unhandled exception shows a raw Python traceback. Wrap tab rendering in try/except with user-friendly error messages and a "Report this bug" link.

### 20. Analytics
Add basic usage analytics (which policies are most scored, which tabs are most visited, drop-off points). Streamlit Cloud provides some of this but custom events would be more useful.

### 21. A/B Test Welcome Card vs. Guided Tour
For first-time visitors, test whether a short interactive walkthrough ("Click here to select a policy → now click Calculate") outperforms the current text-based welcome card.

### 22. Multi-Model Comparison Platform
Per the roadmap — run the same policy through CBO-style, TPC-style, and FRB/US models side by side. This is still a major post-launch feature. Start with the feasibility gate in [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md) before committing UI work to it.

### 23. CPS Microsimulation Feasibility Sprint
Do not promise citation-grade microsimulation in launch messaging yet. First run the CPS checklist in [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md) to validate tax-unit construction, weighting, reproducibility, and whether the current stack improves weak benchmark cases.

---

## Recommended Launch Strategy

**Soft launch (Day 1-2):** Fix the 3 critical issues. Deploy with all 5 tabs but add a "Beta" badge on Generational and Bill Tracker. The Calculator tab is production-quality — lead with it.

**Hard launch (Day 3-5):** Fix high-priority items (#4-9). Remove beta badges once OLG is stable. Share on economics Twitter, send to colleagues, post on relevant subreddits (r/economics, r/dataisbeautiful).

**Week 1 post-launch:** Implement nice-to-haves based on user feedback. Quick-start presets (#10) will likely have the highest impact on engagement.
