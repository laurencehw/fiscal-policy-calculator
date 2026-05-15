"""
Authoritative source registry for the Ask assistant.

Used in three places:

1. ``system_prompt.py`` — enumerates sources the model is allowed to cite.
2. ``tools.py`` — the ``fetch_url`` allowlist (strict domain match) and the
   ``web_search`` ``allowed_domains`` parameter.
3. ``citations.py`` — to recognize a returned URL as belonging to a known source.

The user maintains this file by hand. Add a new authoritative source by
appending a key here; no other file changes are required.
"""

from __future__ import annotations

from urllib.parse import urlparse


SOURCES: dict[str, dict[str, object]] = {
    "cbo": {
        "name": "Congressional Budget Office",
        "domain": "cbo.gov",
        "homepage": "https://www.cbo.gov/",
        "data_pages": [
            "https://www.cbo.gov/topics/budget",
            "https://www.cbo.gov/topics/economy",
            "https://www.cbo.gov/data/budget-economic-data",
        ],
        "when_to_cite": (
            "10-year baseline projections, deficit/debt paths, official scores "
            "of legislation, economic outlook, long-term outlook."
        ),
    },
    "jct": {
        "name": "Joint Committee on Taxation",
        "domain": "jct.gov",
        "homepage": "https://www.jct.gov/",
        "data_pages": [
            "https://www.jct.gov/publications/",
        ],
        "when_to_cite": (
            "Revenue estimates of tax legislation, tax expenditure estimates, "
            "distributional analyses of tax changes."
        ),
    },
    "pwbm": {
        "name": "Penn Wharton Budget Model",
        "domain": "budgetmodel.wharton.upenn.edu",
        "homepage": "https://budgetmodel.wharton.upenn.edu/",
        "data_pages": [
            "https://budgetmodel.wharton.upenn.edu/issues/",
        ],
        "when_to_cite": (
            "Dynamic scoring with OLG general-equilibrium effects, Social Security "
            "solvency analyses, long-run growth effects of tax policy."
        ),
    },
    "yale_budget_lab": {
        "name": "Yale Budget Lab",
        "domain": "budgetlab.yale.edu",
        "homepage": "https://budgetlab.yale.edu/",
        "data_pages": [
            "https://budgetlab.yale.edu/research",
        ],
        "when_to_cite": (
            "Tariff impacts, tax policy distributional effects, behavioral "
            "responses with macro feedback."
        ),
    },
    "tpc": {
        "name": "Tax Policy Center",
        "domain": "taxpolicycenter.org",
        "homepage": "https://www.taxpolicycenter.org/",
        "data_pages": [
            "https://www.taxpolicycenter.org/model-estimates",
            "https://www.taxpolicycenter.org/statistics",
        ],
        "when_to_cite": (
            "Distributional tables by income quintile/decile, microsimulation-"
            "based estimates of tax law changes, state-by-state effects."
        ),
    },
    "pgpf": {
        "name": "Peter G. Peterson Foundation",
        "domain": "pgpf.org",
        "homepage": "https://www.pgpf.org/",
        "data_pages": [
            "https://www.pgpf.org/the-fiscal-and-economic-challenge",
        ],
        "when_to_cite": (
            "Debt sustainability, fiscal outlook explainers, comparison of "
            "fiscal policy proposals."
        ),
    },
    "bea": {
        "name": "Bureau of Economic Analysis",
        "domain": "bea.gov",
        "homepage": "https://www.bea.gov/",
        "data_pages": [
            "https://www.bea.gov/data/gdp/gross-domestic-product",
            "https://www.bea.gov/data/income-saving",
        ],
        "when_to_cite": (
            "GDP, personal income, national accounts, sector contributions. "
            "Prefer FRED proxies (e.g., GDPC1, GDP) for time-series queries."
        ),
    },
    "bls": {
        "name": "Bureau of Labor Statistics",
        "domain": "bls.gov",
        "homepage": "https://www.bls.gov/",
        "data_pages": [
            "https://www.bls.gov/cpi/",
            "https://www.bls.gov/ces/",
            "https://www.bls.gov/cps/",
        ],
        "when_to_cite": (
            "CPI inflation, employment situation, wages, unemployment. "
            "Prefer FRED proxies (CPIAUCSL, UNRATE, PAYEMS) for series queries."
        ),
    },
    "ssa": {
        "name": "Social Security Administration / Trustees Report",
        "domain": "ssa.gov",
        "homepage": "https://www.ssa.gov/",
        "data_pages": [
            "https://www.ssa.gov/oact/TRSUM/",
            "https://www.ssa.gov/oact/TR/",
        ],
        "when_to_cite": (
            "Social Security trust fund solvency, trustees projections, "
            "OASDI cost rates, disability program data."
        ),
    },
    "fred": {
        "name": "Federal Reserve Economic Data (FRED)",
        "domain": "stlouisfed.org",
        "homepage": "https://fred.stlouisfed.org/",
        "data_pages": [
            "https://fred.stlouisfed.org/categories",
        ],
        "when_to_cite": (
            "Live macro time series (GDP, UNRATE, FEDFUNDS, GS10, CPIAUCSL, "
            "PAYEMS, etc.). Cite via the FRED series ID."
        ),
    },
}


# Pre-computed allowlist for fast lookups by fetch_url.
_ALLOWED_DOMAINS: frozenset[str] = frozenset(
    str(spec["domain"]) for spec in SOURCES.values()
)


def allowlisted_domain(url: str) -> str | None:
    """Return the matching allowlisted domain for ``url``, or ``None``.

    A URL matches if its hostname equals an allowlisted domain or is a
    subdomain thereof (e.g., ``www.cbo.gov`` and ``apps.bea.gov`` match).
    """
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return None
    if not host:
        return None
    for domain in _ALLOWED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def web_search_allowed_domains() -> list[str]:
    """Return the list of bare domains for the Anthropic web_search filter."""
    return sorted(_ALLOWED_DOMAINS)


__all__ = [
    "SOURCES",
    "allowlisted_domain",
    "web_search_allowed_domains",
]
