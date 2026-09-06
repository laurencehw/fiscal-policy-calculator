#!/usr/bin/env python3
"""
Measure where the first-hit wait goes: imports, first script run, or the network.

``planning/redesign/FOLLOWUPS.md`` records ~20s of blank skeleton on the first
visit to the Streamlit Community Cloud deployment, and PR #82 shipped only the
half of the fix that a script can reach (paint the chrome before the heavy
work). Deciding what to do next needs a decomposition, not a guess: if the
remaining wait is **import + first-run compute** there is more app-side work to
do; if it is **container scheduling**, only a warm container or a note in the
copy around the link helps.

Four lanes, each runnable on its own:

``imports``
    ``python -X importtime`` over ``app``, the page modules and the third-party
    heavyweights, in a fresh subprocess per repeat. Reports the parsed total
    (the sum of every *self* time, which is what the process actually paid) and
    the top cumulative importers. Medians over ``--repeats``.

    ``--no-pycache`` copies the tree to a scratch directory stripped of every
    ``__pycache__`` and measures there. **That is the number a cold container
    pays**: Streamlit Community Cloud clones the repository and installs
    requirements, it does not pre-compile the app's own 400-odd modules, so the
    first import in a container's life compiles them. The gap between the two
    is a one-off bytecode-compilation tax, and it is large.

``paint``
    Time to **first paint** — process start to ``st.set_page_config``, which is
    the first thing ``app.main`` does and is immediately followed by the boot
    placeholder PR #82 added. This is the number option (a) moves: how long the
    visitor looks at nothing. Measured in a cold subprocess, so it carries the
    module-level import cost of ``app.py`` and nothing else.

``firstrun``
    A phase-instrumented first render through the **real router** with
    ``streamlit.testing.v1.AppTest``, in a cold subprocess so nothing is
    pre-imported. Splits the wait into (i) import, (ii) page-config + chrome,
    (iii) the dependency/data build, (iv) the render residual. Also runs the
    scored first hit, ``/explore?preset=tcja-full-extension&run=1``.

``live``
    A plain ``GET /`` against the deployment, split into DNS, TCP, TLS, TTFB
    and body, following the redirect chain — ``<app>.streamlit.app/`` answers
    ``303`` to an auth bounce rather than serving the shell, so a single hop
    times the edge and not the app. This measures a **warm** container unless
    the app has actually slept; Community Cloud sleeps an app after 12 hours
    without traffic and does not wake it automatically. See
    ``planning/memos/COLD_START.md`` for the runbook that gets a cold one.

Usage::

    python scripts/measure_cold_start.py all
    python scripts/measure_cold_start.py imports --repeats 3 [--no-pycache]
    python scripts/measure_cold_start.py paint --repeats 5
    python scripts/measure_cold_start.py firstrun --repeats 3
    python scripts/measure_cold_start.py live --repeats 3 --url https://…
    python scripts/measure_cold_start.py all --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: The deployment FOLLOWUPS.md is talking about.
DEFAULT_LIVE_URL = "https://fiscal-policy-calculator.streamlit.app"

#: Module graphs worth timing separately. ``app`` is the entry point Streamlit
#: Cloud runs; the page modules are what ``build_navigation`` imports; the rest
#: are the third-party costs those two sit on top of.
IMPORT_TARGETS: tuple[str, ...] = (
    "app",
    "fiscal_model",
    "streamlit",
    "plotly",
    "pandas",
    "app_pages.ask",
    "app_pages.build",
    "app_pages.tailor",
    "app_pages.explore",
    "app_pages.tracker",
    "app_pages.methodology",
    "components.chrome",
    "fiscal_model.ui.dependencies",
)

_IMPORTTIME_LINE = re.compile(
    r"^import time:\s*(?P<self>[\d,]+)\s*\|\s*(?P<cumulative>[\d,]+)\s*\|\s*(?P<name>.*)$"
)


# ── lane 1: import time ──────────────────────────────────────────────────


def _parse_importtime(stderr: str) -> dict[str, Any]:
    """Turn ``-X importtime`` stderr into totals and a cumulative ranking.

    ``self`` times partition the work exactly (each module's own bytecode
    execution, exclusive of its children), so their sum is the process's real
    import bill. ``cumulative`` double-counts across a parent/child chain and
    is only useful for *attribution* — which is what the ranking is for.
    """
    rows: list[tuple[str, int, int]] = []
    for line in stderr.splitlines():
        match = _IMPORTTIME_LINE.match(line.strip())
        if not match:
            continue
        name = match["name"].strip()
        rows.append(
            (
                name,
                int(match["self"].replace(",", "")),
                int(match["cumulative"].replace(",", "")),
            )
        )
    total_us = sum(self_us for _, self_us, _ in rows)
    # Only top-level modules (no dot) are meaningful cumulative roots: a
    # submodule's cumulative is already inside its package's.
    ranked = sorted(rows, key=lambda row: row[2], reverse=True)
    return {
        "total_seconds": total_us / 1e6,
        "module_count": len(rows),
        "top_cumulative": [
            {"module": name, "self_seconds": s / 1e6, "cumulative_seconds": c / 1e6}
            for name, s, c in ranked[:25]
        ],
    }


def _pycache_free_tree() -> Path:
    """A copy of the repository with every ``__pycache__`` removed.

    Streamlit Community Cloud clones the repo into a fresh container; the app's
    own modules arrive as source with no compiled bytecode, so the first import
    compiles all ~400 of them. Measuring in the working tree hides that,
    because every run here has been leaving ``.pyc`` files behind since the
    first one.
    """
    import shutil
    import tempfile

    dst = Path(tempfile.gettempdir()) / "fpc_cold_start_nopycache"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(
        PROJECT_ROOT,
        dst,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"
        ),
    )
    return dst


def measure_imports(
    targets: tuple[str, ...], repeats: int, *, no_pycache: bool = False
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for target in targets:
        runs: list[dict[str, Any]] = []
        for _ in range(repeats):
            # A fresh strip per repeat: the previous run wrote the bytecode it
            # was measuring the absence of.
            cwd = _pycache_free_tree() if no_pycache else PROJECT_ROOT
            proc = subprocess.run(
                [sys.executable, "-X", "importtime", "-c", f"import {target}"],
                cwd=cwd,
                capture_output=True,
                text=True,
                errors="replace",
            )
            if proc.returncode != 0:
                runs.append({"error": proc.stderr[-2000:]})
                continue
            runs.append(_parse_importtime(proc.stderr))
        ok = [r for r in runs if "total_seconds" in r]
        if not ok:
            out[target] = {"error": runs[0].get("error", "unknown")}
            continue
        totals = [r["total_seconds"] for r in ok]
        out[target] = {
            "totals_seconds": totals,
            "median_seconds": statistics.median(totals),
            "min_seconds": min(totals),
            "max_seconds": max(totals),
            "module_count": ok[-1]["module_count"],
            # Ranking from the *last* (warmest) run: the first run's ranking is
            # dominated by whichever module happened to touch the disk first.
            "top_cumulative": ok[-1]["top_cumulative"],
        }
    return out


# ── lane 2: time to first paint ──────────────────────────────────────────

#: ``app.main`` calls ``_render_head_metadata`` (which is ``set_page_config``)
#: first, and claims the boot placeholder immediately after. So the moment
#: ``set_page_config`` fires is the moment the visitor stops looking at
#: nothing, and everything before it is the module-level import cost of
#: ``app.py``. Streamlit itself has to be imported before the stamp can be
#: installed; that cost is identical on both sides of any change to the app,
#: so the clock starts *after* it.
_PAINT_PROBE = r"""
import json, os, sys, time
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)
os.environ.pop("ANTHROPIC_API_KEY", None)

t_process = time.perf_counter()
import streamlit as st
from streamlit.testing.v1 import AppTest
t_streamlit = time.perf_counter() - t_process
t_ready = time.perf_counter()

# NOTE: the health snapshot is seeded *from inside the stamp*, not before it.
# ``fiscal_model.ui.cache`` cannot be imported up here without dragging in the
# whole ``fiscal_model`` package — which is precisely the cost being measured,
# and pre-warming it reports a first paint of 20ms that no visitor ever sees.
# By the time ``set_page_config`` fires, ``app.py``'s own imports have already
# paid for that package, so seeding here is free and lands before the health
# probe in ``render_chrome``.
stamp = {}
_real = st.set_page_config
def _stamped(*a, **k):
    if "at" not in stamp:
        stamp["at"] = time.perf_counter()
        from fiscal_model.ui import cache as ui_cache
        ui_cache._health_snapshot["value"] = {"status": "healthy", "checks": {}}
        ui_cache._health_snapshot["at"] = time.monotonic()
    return _real(*a, **k)
st.set_page_config = _stamped

at = AppTest.from_file("app.py", default_timeout=300)
at.run()
t_end = time.perf_counter()

print("@@RESULT@@" + json.dumps({
    "streamlit_import_seconds": t_streamlit,
    "first_paint_seconds": stamp.get("at", t_end) - t_ready,
    "full_run_seconds": t_end - t_ready,
    "exception": [e.message for e in at.exception] if at.exception else [],
}))
"""


def measure_paint(repeats: int) -> dict[str, Any]:
    """Time to ``set_page_config`` in a cold process, median of ``repeats``.

    Note the health snapshot is seeded *before* the clock starts: the data
    pill's health probe is a network call that has nothing to do with boot
    cost and would otherwise dominate the variance.
    """
    runs: list[dict[str, Any]] = []
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONWARNINGS"] = "ignore"
    for _ in range(repeats):
        source = f"PROJECT_ROOT = {str(PROJECT_ROOT)!r}\n" + _PAINT_PROBE
        proc = subprocess.run(
            [sys.executable, "-c", source],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            errors="replace",
            env=env,
        )
        found = False
        for line in proc.stdout.splitlines():
            if line.startswith("@@RESULT@@"):
                runs.append(json.loads(line[len("@@RESULT@@") :]))
                found = True
        if not found:
            runs.append({"error": (proc.stderr or proc.stdout)[-3000:]})
    ok = [r for r in runs if "first_paint_seconds" in r]
    if not ok:
        return {"error": runs[0].get("error", "unknown")}
    return {
        "runs": len(ok),
        "first_paint_median_seconds": statistics.median([r["first_paint_seconds"] for r in ok]),
        "first_paint_seconds": [r["first_paint_seconds"] for r in ok],
        "full_run_median_seconds": statistics.median([r["full_run_seconds"] for r in ok]),
        "streamlit_import_median_seconds": statistics.median(
            [r["streamlit_import_seconds"] for r in ok]
        ),
        "exceptions": ok[0]["exception"],
    }


# ── lane 3: first script run ─────────────────────────────────────────────

#: Run inside a *cold* subprocess (nothing pre-imported) so the import phase is
#: paid here rather than by the harness. Written as source rather than a helper
#: module so that no part of it can be accidentally warmed by this script's own
#: imports.
_FIRSTRUN_PROBE = r"""
import json, os, sys, time
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)
os.environ.pop("ANTHROPIC_API_KEY", None)

phases = []
def phase(label, fn):
    t = time.perf_counter()
    value = fn()
    phases.append((label, time.perf_counter() - t))
    return value

t_process = time.perf_counter()

def _import(name):
    def go():
        import importlib
        return importlib.import_module(name)
    return go

phase("import streamlit", _import("streamlit"))
phase("import AppTest", lambda: __import__("streamlit.testing.v1", fromlist=["AppTest"]))
phase("import app (router module graph)", _import("app"))
phase("import components.chrome", _import("components.chrome"))
for _page in ("ask", "build", "tailor", "explore", "tracker", "methodology", "classroom", "about"):
    phase("import app_pages." + _page, _import("app_pages." + _page))
deps_mod = phase("import fiscal_model.ui.dependencies", _import("fiscal_model.ui.dependencies"))

import pandas as pd
phase("build_app_dependencies (data loads, standalone)",
      lambda: deps_mod.build_app_dependencies(pd_module=pd))

# Keep the health probe off the network: it is a data-status decoration, not
# part of the boot path, and on CI it would time out rather than measure.
from fiscal_model.ui import cache as ui_cache
ui_cache._health_snapshot["value"] = {"status": "healthy", "checks": {}}
ui_cache._health_snapshot["at"] = time.monotonic()

# Instrument the phases that happen *inside* the script run. app.py imports
# these at call time, so patching the module objects here reaches the copy
# AppTest's freshly executed script will import from sys.modules.
inner = {"deps_build": 0.0, "scorecard": 0.0, "page_config": 0.0}

_real_build = deps_mod.build_app_dependencies
def _timed_build(*a, **k):
    t = time.perf_counter()
    try:
        return _real_build(*a, **k)
    finally:
        inner["deps_build"] += time.perf_counter() - t
deps_mod.build_app_dependencies = _timed_build

# The page footer asks for the benchmark count on every page, which computes
# the whole validation scorecard. It is memoized process-wide, so exactly one
# visitor per container pays it — the first one, on the critical path of the
# first script run. Timed here because it turned out to be the largest single
# term in the local cold hit, larger than every import put together.
import fiscal_model.validation as validation_pkg
import fiscal_model.validation.scorecard as scorecard_mod
scorecard_mod.reset_scorecard_cache()
_real_scorecard = scorecard_mod.cached_default_scorecard
def _timed_scorecard(*a, **k):
    t = time.perf_counter()
    try:
        return _real_scorecard(*a, **k)
    finally:
        inner["scorecard"] += time.perf_counter() - t
# BOTH bindings, and the second one is not optional. ui/helpers.py imports it
# from the submodule but ui/preset_validation.py imports it from the *package*,
# which re-exported it into a separate name at import time. Patching only the
# submodule reported 0.000s on a scored first hit — where the evidence card
# reaches the package binding first, computes the scorecard, and leaves the
# footer a warm cache to read through the instrumented one.
scorecard_mod.cached_default_scorecard = _timed_scorecard
validation_pkg.cached_default_scorecard = _timed_scorecard

import streamlit as st
_real_page_config = st.set_page_config
def _timed_page_config(*a, **k):
    t = time.perf_counter()
    try:
        return _real_page_config(*a, **k)
    finally:
        inner["page_config"] += time.perf_counter() - t
st.set_page_config = _timed_page_config

from streamlit.testing.v1 import AppTest

QUERY = json.loads(QUERY_JSON)
PAGE = PAGE_NAME

def _run():
    at = AppTest.from_file("app.py", default_timeout=300)
    if QUERY:
        at.query_params.update(QUERY)
    if PAGE:
        at.switch_page(PAGE)
    at.run()
    return at

at = phase("AppTest first run (router + page render)", _run)

total = time.perf_counter() - t_process
result = {
    "phases": [{"label": k, "seconds": v} for k, v in phases],
    "inner": inner,
    "total_seconds": total,
    "exception": [e.message for e in at.exception] if at.exception else [],
    "markdown_elements": len(at.markdown),
}
print("@@RESULT@@" + json.dumps(result))
"""


def _firstrun_once(page: str | None, query: dict[str, str]) -> dict[str, Any]:
    source = (
        f"PROJECT_ROOT = {str(PROJECT_ROOT)!r}\n"
        f"QUERY_JSON = {json.dumps(json.dumps(query))}\n"
        f"PAGE_NAME = {page!r}\n" + _FIRSTRUN_PROBE
    )
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONWARNINGS"] = "ignore"
    proc = subprocess.run(
        [sys.executable, "-c", source],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("@@RESULT@@"):
            return json.loads(line[len("@@RESULT@@") :])
    return {"error": (proc.stderr or proc.stdout)[-4000:]}


def measure_firstrun(repeats: int) -> dict[str, Any]:
    scenarios = {
        "landing (/)": (None, {}),
        "scored (/explore?preset=tcja-full-extension&run=1)": (
            "app_pages/explore.py",
            {"preset": "tcja-full-extension", "run": "1"},
        ),
    }
    out: dict[str, Any] = {}
    for label, (page, query) in scenarios.items():
        runs = [_firstrun_once(page, query) for _ in range(repeats)]
        ok = [r for r in runs if "total_seconds" in r]
        if not ok:
            out[label] = {"error": runs[0].get("error", "unknown")}
            continue
        labels = [p["label"] for p in ok[0]["phases"]]
        medians = {
            name: statistics.median(
                [next(p["seconds"] for p in r["phases"] if p["label"] == name) for r in ok]
            )
            for name in labels
        }
        inner_keys = ok[0]["inner"].keys()
        out[label] = {
            "runs": len(ok),
            "total_median_seconds": statistics.median([r["total_seconds"] for r in ok]),
            "totals_seconds": [r["total_seconds"] for r in ok],
            "phase_median_seconds": medians,
            "inner_median_seconds": {
                k: statistics.median([r["inner"][k] for r in ok]) for k in inner_keys
            },
            "exceptions": ok[0]["exception"],
            "markdown_elements": ok[0]["markdown_elements"],
        }
    return out


# ── lane 4: the live deployment ──────────────────────────────────────────


def _timed_get(url: str, cookies: dict[str, str] | None = None) -> dict[str, Any]:
    """DNS / TCP / TLS / TTFB / body for one hop. Redirects are reported, not followed."""
    import http.client
    import socket
    import ssl
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query

    t0 = time.perf_counter()
    addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    t_dns = time.perf_counter() - t0

    family, socktype, proto, _canon, sockaddr = addrinfo[0]
    sock = socket.socket(family, socktype, proto)
    sock.settimeout(60)
    t1 = time.perf_counter()
    sock.connect(sockaddr)
    t_tcp = time.perf_counter() - t1

    t_tls = 0.0
    if parts.scheme == "https":
        ctx = ssl.create_default_context()
        t2 = time.perf_counter()
        sock = ctx.wrap_socket(sock, server_hostname=host)
        t_tls = time.perf_counter() - t2

    conn = http.client.HTTPConnection(host, port, timeout=60)
    conn.sock = sock
    headers = {"User-Agent": "fpc-cold-start-measure/1.0"}
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    t3 = time.perf_counter()
    conn.request("GET", path, headers=headers)
    response = conn.getresponse()
    status = response.status
    # Case-insensitive: the edge answers HTTP/2-style lowercase header names,
    # and a dict lookup on "Location" silently returns None for every redirect.
    response_location = response.getheader("Location")
    # First byte of the body — getresponse() has already read the headers.
    first = response.read(1)
    t_ttfb = time.perf_counter() - t3
    rest = response.read()
    t_body = time.perf_counter() - t3 - t_ttfb
    conn.close()

    body = first + rest
    text = body.decode("utf-8", "replace")
    return {
        "status": status,
        "bytes": len(body),
        "dns_seconds": t_dns,
        "tcp_seconds": t_tcp,
        "tls_seconds": t_tls,
        "ttfb_seconds": t_ttfb,
        "body_seconds": t_body,
        "total_seconds": t_dns + t_tcp + t_tls + t_ttfb + t_body,
        # Streamlit Cloud serves its own interstitial when a container is
        # asleep or being scheduled; the shell HTML is otherwise static.
        # Streamlit Cloud serves the sleeping page when a container has been
        # idle 12 hours. Its tell is the wake button's own label.
        "looks_asleep": "get this app back up" in text.lower(),
        "location": response_location,
        "set_cookie": [v for k, v in response.getheaders() if k.lower() == "set-cookie"],
        "title": (re.search(r"<title>(.*?)</title>", text, re.S) or [None, ""])[1].strip()[:120],
    }


def _timed_get_following(url: str, *, max_hops: int = 8) -> dict[str, Any]:
    """Walk the redirect chain like a browser would, summing the hops.

    ``https://<app>.streamlit.app/`` does **not** answer with the app shell: it
    answers ``303`` to ``share.streamlit.io/-/auth/app?redirect_uri=…``, an auth
    bounce every anonymous visitor takes. Timing only the first hop measures the
    edge redirect and calls it the app.

    The bounce sets a cookie and only terminates for a client that sends it
    back, so cookies are carried across hops. Without them the chain loops
    ``/`` → auth → ``/-/login`` → ``/`` forever and the hop cap turns an
    infinite redirect into a plausible-looking total — which is a measurement
    artifact, not a slow app. ``looped`` says so explicitly rather than leaving
    the reader to notice a repeated URL.
    """
    hops: list[dict[str, Any]] = []
    cookies: dict[str, str] = {}
    seen: set[str] = set()
    current = url
    looped = False
    for _ in range(max_hops):
        hop = _timed_get(current, cookies)
        hops.append({**hop, "url": current})
        for raw in hop.get("set_cookie", []):
            name, _, rest = raw.partition("=")
            cookies[name.strip()] = rest.split(";", 1)[0]
        location = hop.get("location")
        if hop["status"] not in (301, 302, 303, 307, 308) or not location:
            break
        current = location if "://" in location else current.rsplit("/", 1)[0] + location
        if current in seen:
            looped = True
            break
        seen.add(current)
    total = sum(h["total_seconds"] for h in hops)
    return {
        "hops": hops,
        "hop_count": len(hops),
        "chain_total_seconds": total,
        "final_status": hops[-1]["status"],
        "final_url": hops[-1]["url"],
        "looped": looped or len(hops) >= max_hops,
        "looks_asleep": any(h["looks_asleep"] for h in hops),
    }


def measure_live(url: str, repeats: int) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for _ in range(repeats):
        try:
            runs.append(_timed_get_following(url))
        except Exception as exc:  # network is allowed to be unavailable
            runs.append({"error": f"{type(exc).__name__}: {exc}"})
    ok = [r for r in runs if "chain_total_seconds" in r]
    summary: dict[str, Any] = {"url": url, "runs": runs}
    if ok:
        first = [r["hops"][0] for r in ok]
        for key in ("dns", "tcp", "tls", "ttfb", "body"):
            summary[f"{key}_median_seconds"] = statistics.median(
                [h[f"{key}_seconds"] for h in first]
            )
        summary["first_hop_median_seconds"] = statistics.median([h["total_seconds"] for h in first])
        summary["chain_median_seconds"] = statistics.median([r["chain_total_seconds"] for r in ok])
        summary["hop_count"] = ok[0]["hop_count"]
        summary["chain"] = [
            {"url": h["url"], "status": h["status"], "seconds": round(h["total_seconds"], 3)}
            for h in ok[0]["hops"]
        ]
        summary["looks_asleep"] = any(r["looks_asleep"] for r in ok)
        summary["looped"] = any(r["looped"] for r in ok)
        summary["final_status"] = ok[0]["final_status"]
    return summary


# ── reporting ────────────────────────────────────────────────────────────


def _print_imports(data: dict[str, Any]) -> None:
    print("\n=== 1. Import time (median of repeats, fresh subprocess each) ===\n")
    print(f"{'target':<34}{'median':>9}{'min':>9}{'max':>9}{'modules':>9}")
    for target, row in data.items():
        if "error" in row:
            print(f"{target:<34}  ERROR {row['error'][:60]}")
            continue
        print(
            f"{target:<34}{row['median_seconds']:>8.3f}s{row['min_seconds']:>8.3f}s"
            f"{row['max_seconds']:>8.3f}s{row['module_count']:>9}"
        )
    app_row = data.get("app")
    if app_row and "top_cumulative" in app_row:
        print("\n  top 25 cumulative importers under `import app`:\n")
        print(f"  {'#':<4}{'module':<52}{'cumulative':>12}{'self':>10}")
        for i, row in enumerate(app_row["top_cumulative"], 1):
            print(
                f"  {i:<4}{row['module'][:50]:<52}"
                f"{row['cumulative_seconds']:>11.3f}s{row['self_seconds']:>9.3f}s"
            )


def _print_paint(data: dict[str, Any]) -> None:
    print("\n=== 2. Time to first paint (process start -> st.set_page_config) ===\n")
    if "error" in data:
        print(textwrap.indent(data["error"][:1500], "    "))
        return
    print(
        f"  first paint          {data['first_paint_median_seconds']:>8.3f}s"
        f"   (median of {data['runs']}; app.py's module-level imports)"
    )
    print(f"  full first run       {data['full_run_median_seconds']:>8.3f}s")
    print(
        f"  [streamlit import]   {data['streamlit_import_median_seconds']:>8.3f}s"
        "   (paid before the clock starts; unaffected by app code)"
    )
    print(f"  raw: {[round(v, 3) for v in data['first_paint_seconds']]}")


def _print_firstrun(data: dict[str, Any]) -> None:
    print("\n=== 3. First script run, cold process, real router via AppTest ===\n")
    for label, row in data.items():
        if "error" in row:
            print(f"{label}: ERROR\n{textwrap.indent(row['error'][:1500], '    ')}")
            continue
        print(f"-- {label}  (median of {row['runs']} cold processes)")
        for name, seconds in row["phase_median_seconds"].items():
            print(f"     {name:<52}{seconds:>8.3f}s")
        print(f"     {'-' * 52}{'':>8}")
        for name, seconds in row["inner_median_seconds"].items():
            print(f"     [inside the run] {name:<35}{seconds:>8.3f}s")
        print(f"     {'TOTAL':<52}{row['total_median_seconds']:>8.3f}s")
        if row["exceptions"]:
            print(f"     exceptions: {row['exceptions']}")
        print()


def _print_live(data: dict[str, Any]) -> None:
    print("\n=== 4. Live deployment, plain GET / ===\n")
    print(f"  url: {data['url']}")
    if "chain_median_seconds" not in data:
        for run in data["runs"]:
            print(f"  ERROR {run.get('error')}")
        return
    print("  first hop, split:")
    for key in ("dns", "tcp", "tls", "ttfb", "body"):
        print(f"    {key:<6}{data[f'{key}_median_seconds']:>8.3f}s")
    print(f"    {'total':<6}{data['first_hop_median_seconds']:>8.3f}s")
    print(
        f"\n  redirect chain ({data['hop_count']} hop(s)); median total over all "
        f"repeats {data['chain_median_seconds']:.3f}s. Per-hop timings below are "
        "from the first repeat, not medians:"
    )
    for hop in data["chain"]:
        print(f"    {hop['status']}  {hop['seconds']:>6.3f}s  {hop['url'][:88]}")
    print(f"\n  final status: {data['final_status']}")
    print(f"  sleeping page detected: {data['looks_asleep']}")
    if data["looped"]:
        print(
            "  WARNING: the chain did not terminate — the total above is an\n"
            "  artifact of the hop cap, not a page load time. Do not quote it."
        )
    print(
        "\n  NOTE: this measures whatever state the container is in *now*. A\n"
        "  container that has served traffic recently is warm, and a warm TTFB\n"
        "  says nothing about the cold one. Community Cloud apps sleep after\n"
        "  12 hours without traffic and do NOT wake on their own — the visitor\n"
        "  gets a page with a 'Yes, get this app back up!' button and has to\n"
        "  click it. See planning/memos/COLD_START.md for the cold runbook."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "lane",
        nargs="?",
        default="all",
        choices=("all", "imports", "paint", "firstrun", "live"),
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--url", default=DEFAULT_LIVE_URL)
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument(
        "--targets",
        default=None,
        help="comma-separated import targets, overriding the default list",
    )
    parser.add_argument(
        "--no-pycache",
        action="store_true",
        help="measure imports in a pycache-stripped copy — what a fresh container pays",
    )
    args = parser.parse_args(argv)

    targets = tuple(t.strip() for t in args.targets.split(",")) if args.targets else IMPORT_TARGETS
    results: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "repeats": args.repeats,
    }

    if args.lane in ("all", "imports"):
        results["no_pycache"] = args.no_pycache
        results["imports"] = measure_imports(targets, args.repeats, no_pycache=args.no_pycache)
        _print_imports(results["imports"])
    if args.lane in ("all", "paint"):
        results["paint"] = measure_paint(args.repeats)
        _print_paint(results["paint"])
    if args.lane in ("all", "firstrun"):
        results["firstrun"] = measure_firstrun(args.repeats)
        _print_firstrun(results["firstrun"])
    if args.lane in ("all", "live"):
        results["live"] = measure_live(args.url, args.repeats)
        _print_live(results["live"])

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
