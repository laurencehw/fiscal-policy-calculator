"""
Tool implementations for the Ask assistant.

Each tool has:
1. An Anthropic tool_use schema in :data:`TOOL_SCHEMAS`.
2. A Python implementation as a method on :class:`AssistantTools`.

The dispatcher :meth:`AssistantTools.dispatch` routes a tool name to its
implementation and returns a JSON-serializable result dict. Errors are
caught and returned as ``{"error": "..."}`` so the agentic loop never
crashes on a single bad tool call.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlparse

from .sources import SOURCES, allowlisted_domain, web_search_allowed_domains

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Anthropic tool schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_app_scoring_context",
        "description": (
            "Return the user's currently scored policy and its results from "
            "this Fiscal Policy Calculator session, if any. Use this any time "
            "the user asks about 'this policy', 'the current run', 'why does "
            "it widen the deficit', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_cbo_baseline",
        "description": (
            "Return the 10-year CBO baseline projection currently loaded in "
            "this app: years, revenues, outlays, deficits, debt, and the "
            "vintage label (e.g. 'cbo_feb_2026'). Use this for questions "
            "about baseline deficit/debt path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_validation_scorecard",
        "description": (
            "Return the table of this app's preset policies vs. their official "
            "CBO/JCT scores, with error percentages. Use this when asked how "
            "accurate the model is, or for the official CBO score of a "
            "specific preset."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional substring filter on policy name (case-insensitive).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_presets",
        "description": (
            "List the names of all preset policies available in this app, "
            "with a one-line description of each. Use this when the user "
            "asks 'what can I score' or 'show me available policies'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_preset",
        "description": (
            "Return the full configuration of a single preset policy by name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Exact preset name (must match list_presets output).",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "score_hypothetical_policy",
        "description": (
            "Run the app's real scoring engine on a hypothetical tax or "
            "spending policy. Returns the 10-year deficit impact, year-by-"
            "year effects, and (optionally) dynamic feedback. Use this for "
            "requests like 'score a 25% corporate rate' or 'what if the top "
            "marginal rate were 45%'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Short human-readable name for the policy.",
                },
                "policy_type": {
                    "type": "string",
                    "enum": [
                        "income_tax",
                        "corporate_tax",
                        "payroll_tax",
                        "capital_gains_tax",
                        "estate_tax",
                        "discretionary_nondefense",
                        "discretionary_defense",
                        "mandatory_spending",
                    ],
                    "description": "Policy category.",
                },
                "rate_change": {
                    "type": "number",
                    "description": (
                        "Change in tax rate as a decimal fraction. "
                        "+2.6 percentage points = 0.026. "
                        "Use a negative value for rate cuts. "
                        "For corporate, 21%→28% is +0.07."
                    ),
                },
                "affected_income_threshold": {
                    "type": "number",
                    "description": (
                        "Income threshold in dollars (for income/cap-gains "
                        "policies). 0 means the change applies to all "
                        "filers. Default 0."
                    ),
                },
                "spending_change_billions": {
                    "type": "number",
                    "description": (
                        "For spending policies: annual spending change in "
                        "billions of dollars (positive = more spending)."
                    ),
                },
                "duration_years": {
                    "type": "integer",
                    "description": "Years the policy is in force (default 10).",
                },
                "dynamic": {
                    "type": "boolean",
                    "description": (
                        "If true, include dynamic-scoring feedback (GDP, "
                        "employment, revenue feedback). Default false."
                    ),
                },
            },
            "required": ["name", "policy_type"],
        },
    },
    {
        "name": "search_knowledge",
        "description": (
            "Keyword-search the curated knowledge corpus (Markdown snapshots "
            "of CBO, JCT, PWBM, TPC, SSA, etc. reports maintained by the "
            "app authors). Returns up to k passages with the file's source "
            "URL — cite that URL in your answer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms; use natural-language keywords.",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of passages to return (1-10, default 4).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_fred",
        "description": (
            "Fetch the recent observations of a FRED time series by ID "
            "(GDPC1, UNRATE, FEDFUNDS, GS10, CPIAUCSL, PAYEMS, etc.). "
            "Returns the most recent N points and summary statistics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "string",
                    "description": "FRED series ID, e.g. 'GDPC1', 'UNRATE'.",
                },
                "n_recent": {
                    "type": "integer",
                    "description": "Number of most-recent observations to return (1-60, default 12).",
                },
            },
            "required": ["series_id"],
        },
    },
    {
        "name": "fetch_url",
        "description": (
            "Fetch the textual content of a single URL. Only allowlisted "
            "authoritative domains are accepted: " + ", ".join(web_search_allowed_domains()) +
            ". PDFs are parsed via pdfplumber. Returns extracted text (truncated)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full HTTPS URL. Must be an allowlisted domain.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Truncate returned text to this many characters (default 6000).",
                },
            },
            "required": ["url"],
        },
    },
]


def web_search_tool_definition() -> dict[str, Any]:
    """Anthropic native web_search tool, restricted to allowlisted domains.

    Returned separately because it uses a server-side tool type rather than
    a custom function schema. Wired into the assistant via
    :meth:`FiscalAssistant._tool_kwargs`.
    """
    return {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5,
        "allowed_domains": web_search_allowed_domains(),
    }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _safe_jsonable(obj: Any, *, max_depth: int = 6) -> Any:
    """Convert ``obj`` to a JSON-serializable structure (best effort)."""
    if max_depth <= 0:
        return repr(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_jsonable(v, max_depth=max_depth - 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_safe_jsonable(v, max_depth=max_depth - 1) for v in obj]
    # numpy / pandas
    try:
        import numpy as np

        if isinstance(obj, np.ndarray):
            return [_safe_jsonable(v, max_depth=max_depth - 1) for v in obj.tolist()]
        if isinstance(obj, np.generic):
            return obj.item()
    except ImportError:
        pass
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    if hasattr(obj, "value"):  # Enum-ish
        try:
            return obj.value
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return _safe_jsonable(vars(obj), max_depth=max_depth - 1)
        except Exception:
            pass
    return repr(obj)


class AssistantTools:
    """Bundle of injected app dependencies + per-turn session state.

    Each public method corresponds to a tool name in :data:`TOOL_SCHEMAS`.
    """

    def __init__(
        self,
        *,
        scorer: Any,
        baseline: Any,
        cbo_score_map: dict[str, dict[str, Any]],
        presets: dict[str, dict[str, Any]],
        fred_data: Any = None,
        knowledge_searcher: Any = None,
        policy_types: Any = None,
        tax_policy_cls: Any = None,
        spending_policy_cls: Any = None,
    ) -> None:
        self._scorer = scorer
        self._baseline = baseline
        self._cbo_score_map = cbo_score_map
        self._presets = presets
        self._fred_data = fred_data
        self._knowledge_searcher = knowledge_searcher
        self._policy_types = policy_types
        self._tax_policy_cls = tax_policy_cls
        self._spending_policy_cls = spending_policy_cls
        # Per-turn scoring context, set by the assistant before dispatch.
        self._scoring_context: dict[str, Any] | None = None
        # Provenance trail of every successful tool call this turn.
        self.provenance: list[dict[str, Any]] = []

    # ---- per-turn hooks --------------------------------------------------

    def set_scoring_context(self, ctx: dict[str, Any] | None) -> None:
        self._scoring_context = ctx

    def reset_provenance(self) -> None:
        self.provenance = []

    # ---- dispatcher ------------------------------------------------------

    def dispatch(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Run a tool by name. Always returns a dict (never raises)."""
        impl = getattr(self, f"tool_{tool_name}", None)
        if impl is None:
            return {"error": f"unknown tool {tool_name!r}"}
        try:
            result = impl(**(args or {}))
        except TypeError as exc:
            return {"error": f"bad arguments to {tool_name}: {exc}"}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tool %s failed", tool_name)
            return {"error": f"{type(exc).__name__}: {exc}"}
        # Record provenance for citation post-processing.
        self.provenance.append(
            {"tool": tool_name, "args": args, "result_summary": _summarize(result)}
        )
        return _safe_jsonable(result)

    # ---- app-internal tools ---------------------------------------------

    def tool_get_app_scoring_context(self) -> dict[str, Any]:
        if not self._scoring_context:
            return {
                "status": "no_active_policy",
                "message": (
                    "User has not scored a policy in this session. Use "
                    "score_hypothetical_policy or list_presets if relevant."
                ),
            }
        return {"status": "active", "scoring": self._scoring_context}

    def tool_get_cbo_baseline(self) -> dict[str, Any]:
        proj = self._baseline
        if proj is None:
            return {"error": "baseline not available"}
        # ``BaselineProjection`` exposes per-category arrays plus computed
        # totals as properties. Pull what we need; fall back gracefully if
        # the object is some other baseline-like shape.
        try:
            years = list(getattr(proj, "years"))
            revenues = list(getattr(proj, "total_revenues"))
            outlays = list(getattr(proj, "total_outlays"))
            deficits = list(getattr(proj, "deficit"))
            debt = list(getattr(proj, "debt_held_by_public", []))
            nominal_gdp = list(getattr(proj, "nominal_gdp", []))
        except Exception as exc:  # noqa: BLE001
            return {"error": f"could not read baseline: {exc}"}

        ten_year_deficit = float(sum(deficits)) if deficits else None
        end_debt = float(debt[-1]) if debt else None
        end_gdp = float(nominal_gdp[-1]) if nominal_gdp else None
        debt_to_gdp_end = (
            round(end_debt / end_gdp * 100, 1) if end_debt and end_gdp else None
        )
        return {
            "vintage": "CBO baseline as loaded by this app (see app settings)",
            "years": years,
            "revenues_billions": revenues,
            "outlays_billions": outlays,
            "deficits_billions": deficits,
            "debt_held_by_public_billions": debt,
            "nominal_gdp_billions": nominal_gdp,
            "ten_year_cumulative_deficit_billions": ten_year_deficit,
            "end_of_window_debt_to_gdp_pct": debt_to_gdp_end,
            "source": (
                "Internal BaselineProjection. Underlying figures come from "
                "the CBO Budget and Economic Outlook (see app's baseline "
                "vintage). For the precise CBO publication URL, the assistant "
                "should search_knowledge for 'CBO baseline' or fetch the "
                "current outlook page directly."
            ),
        }

    def tool_get_validation_scorecard(self, filter: str = "") -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        f = (filter or "").lower().strip()
        for name, info in self._cbo_score_map.items():
            if f and f not in name.lower():
                continue
            rows.append(
                {
                    "preset_name": name,
                    "official_score_billions": info.get("official_score"),
                    "source": info.get("source"),
                    "source_date": info.get("source_date"),
                    "source_url": info.get("source_url"),
                    "notes": info.get("notes"),
                }
            )
        return {"n_rows": len(rows), "rows": rows[:50]}

    def tool_list_presets(self) -> dict[str, Any]:
        names = list(self._presets.keys())
        return {
            "n_presets": len(names),
            "names": names,
        }

    def tool_get_preset(self, name: str) -> dict[str, Any]:
        spec = self._presets.get(name)
        if spec is None:
            return {"error": f"preset {name!r} not found"}
        score = self._cbo_score_map.get(name, {})
        return {"name": name, "config": spec, "official_score": score}

    def tool_score_hypothetical_policy(
        self,
        *,
        name: str,
        policy_type: str,
        rate_change: float = 0.0,
        affected_income_threshold: float = 0.0,
        spending_change_billions: float = 0.0,
        duration_years: int = 10,
        dynamic: bool = False,
    ) -> dict[str, Any]:
        if self._scorer is None or self._policy_types is None:
            return {"error": "scoring engine not available"}

        try:
            pt = self._policy_types(policy_type)
        except ValueError:
            return {"error": f"unknown policy_type {policy_type!r}"}

        is_spending = policy_type in {
            "discretionary_nondefense",
            "discretionary_defense",
            "mandatory_spending",
        }

        try:
            if is_spending:
                policy = self._spending_policy_cls(
                    name=name,
                    description=f"Assistant hypothetical: {name}",
                    policy_type=pt,
                    spending_change_billions=spending_change_billions,
                    duration_years=duration_years,
                )
            else:
                policy = self._tax_policy_cls(
                    name=name,
                    description=f"Assistant hypothetical: {name}",
                    policy_type=pt,
                    rate_change=rate_change,
                    affected_income_threshold=affected_income_threshold,
                    duration_years=duration_years,
                )
        except Exception as exc:  # noqa: BLE001
            return {"error": f"could not construct policy: {exc}"}

        try:
            result = self._scorer.score_policy(policy, dynamic=dynamic)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"scoring failed: {exc}"}

        return {
            "name": name,
            "policy_type": policy_type,
            "ten_year_deficit_impact_billions": float(getattr(result, "total_10_year_cost", 0.0)),
            "static_deficit_total_billions": float(getattr(result, "total_static_cost", 0.0)),
            "revenue_feedback_10yr_billions": float(getattr(result, "revenue_feedback_10yr", 0.0)),
            "is_dynamic": bool(getattr(result, "is_dynamic", False)),
            "years": getattr(result, "years", None),
            "final_deficit_by_year": getattr(result, "final_deficit_effect", None),
            "source": (
                "Run of FiscalPolicyScorer (this app). Engine calibrated to "
                "CBO/JCT benchmarks within ~5% mean absolute error across 25 "
                "validated policies."
            ),
        }

    # ---- knowledge -------------------------------------------------------

    def tool_search_knowledge(self, *, query: str, k: int = 4) -> dict[str, Any]:
        if self._knowledge_searcher is None:
            return {"hits": [], "note": "knowledge corpus not initialized"}
        k = max(1, min(int(k), 10))
        try:
            hits = self._knowledge_searcher.search(query, k=k)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"knowledge search failed: {exc}"}
        return {"query": query, "n_hits": len(hits), "hits": hits}

    # ---- live external ---------------------------------------------------

    def tool_query_fred(self, *, series_id: str, n_recent: int = 12) -> dict[str, Any]:
        n_recent = max(1, min(int(n_recent), 60))
        if self._fred_data is None:
            return {"error": "FRED client not configured"}
        try:
            # Prefer raw fetch via the underlying fredapi client if available.
            fred_client = getattr(self._fred_data, "_fred", None)
            if fred_client is None or not getattr(self._fred_data, "is_available", lambda: False)():
                return {
                    "error": (
                        "Live FRED unavailable in this environment "
                        "(missing FRED_API_KEY or network)."
                    )
                }
            series = fred_client.get_series(series_id)
            tail = series.tail(n_recent)
            obs = [
                {"date": str(idx.date() if hasattr(idx, "date") else idx), "value": float(v)}
                for idx, v in tail.items()
                if v == v  # filter NaN
            ]
            return {
                "series_id": series_id,
                "n_observations": len(obs),
                "observations": obs,
                "latest": obs[-1] if obs else None,
                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"FRED query failed: {exc}"}

    def tool_fetch_url(self, *, url: str, max_chars: int = 6000) -> dict[str, Any]:
        domain = allowlisted_domain(url)
        if domain is None:
            return {
                "error": (
                    f"URL not on allowlist. Permitted domains: "
                    f"{sorted(SOURCES[k]['domain'] for k in SOURCES)}"
                ),
            }
        max_chars = max(500, min(int(max_chars), 30_000))

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        # Honest User-Agent identifying the tool and contact URL. Some
        # government sites (CBO, SSA) hard-block any non-browser UA; for
        # those, the model should prefer `web_search` (Anthropic server-
        # side) or the curated `knowledge/*.md` snapshots.
        headers = {
            "User-Agent": (
                "FiscalPolicyCalculatorBot/1.0 "
                "(+https://fiscal-policy-calculator.streamlit.app; "
                "research/citation use)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/pdf",
        }
        try:
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return {
                "error": (
                    f"fetch failed: {exc}. "
                    "If this domain blocks bot fetches (CBO/SSA commonly do), "
                    "try web_search instead or rely on search_knowledge."
                )
            }

        content_type = resp.headers.get("Content-Type", "").lower()
        is_pdf = url.lower().endswith(".pdf") or "application/pdf" in content_type

        text: str
        if is_pdf:
            text = _extract_pdf_text(resp.content) or ""
            kind = "pdf"
        else:
            text = _extract_html_text(resp.text)
            kind = "html"

        if not text:
            return {"error": "no text extracted", "kind": kind, "url": url}

        return {
            "url": url,
            "domain": domain,
            "kind": kind,
            "n_chars": len(text),
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
        }


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_html_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse runs of blank lines.
        lines = [ln for ln in (line.strip() for line in text.splitlines()) if ln]
        return "\n".join(lines)
    except ImportError:
        # Fallback: crude tag stripping.
        import re

        cleaned = re.sub(r"<[^>]+>", " ", html)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()


def _extract_pdf_text(pdf_bytes: bytes) -> str | None:
    try:
        import io

        import pdfplumber

        out: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # Cap at first 20 pages to keep latency bounded; tables get
            # text-extracted alongside running prose.
            for page in pdf.pages[:20]:
                try:
                    page_text = page.extract_text() or ""
                except Exception:  # noqa: BLE001
                    page_text = ""
                out.append(page_text)
        return "\n\n".join(s for s in out if s.strip())
    except ImportError:
        logger.warning("pdfplumber not installed; cannot parse PDF")
        return None
    except Exception:  # noqa: BLE001
        logger.exception("PDF extraction failed")
        return None


def _summarize(result: Any) -> str:
    """Compact one-line summary of a tool result for the provenance trail."""
    try:
        s = json.dumps(_safe_jsonable(result), default=str)
    except Exception:  # noqa: BLE001
        s = repr(result)
    return s[:240] + ("…" if len(s) > 240 else "")


__all__ = [
    "TOOL_SCHEMAS",
    "AssistantTools",
    "web_search_tool_definition",
]
