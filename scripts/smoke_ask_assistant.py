"""
Live smoke test for the Ask assistant.

Spends a few cents of Anthropic API credit. Run from the repo root:

    python scripts/smoke_ask_assistant.py

Runs three short questions through the real ``FiscalAssistant``:

1. A tool-routed question (forces ``get_cbo_baseline``).
2. A hypothetical-scoring question (forces ``score_hypothetical_policy``).
3. A knowledge-grounded question (forces ``search_knowledge``).

Prints the streamed text, the tool-call trail, citation markers,
stripped-marker count (a defect signal), and the per-turn cost. Exits
with code 0 on success, 1 on any unexpected failure.
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

# Ensure the repo root is on sys.path when invoked as a script.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build_assistant(model: str | None = None) -> Any:
    from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
    from fiscal_model.assistant import FiscalAssistant
    from fiscal_model.data.fred_data import FREDData
    from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
    from fiscal_model.scoring import FiscalPolicyScorer

    knowledge_dir = ROOT / "fiscal_model" / "assistant" / "knowledge"
    scorer = FiscalPolicyScorer()
    kwargs: dict[str, Any] = dict(
        scorer=scorer,
        baseline=scorer.baseline,
        cbo_score_map=CBO_SCORE_MAP,
        presets=PRESET_POLICIES,
        fred_data=FREDData(),
        knowledge_dir=knowledge_dir,
        policy_types=PolicyType,
        tax_policy_cls=TaxPolicy,
        spending_policy_cls=SpendingPolicy,
        # Web search slows things down and adds cost; off for the smoke test.
        enable_web_search=False,
    )
    if model:
        kwargs["model"] = model
    return FiscalAssistant(**kwargs)


SCENARIOS: list[dict[str, Any]] = [
    {
        "label": "1. CBO baseline (forces get_cbo_baseline)",
        "question": (
            "Using the get_cbo_baseline tool, tell me the cumulative 10-year "
            "deficit and the debt-to-GDP ratio at the end of the window in "
            "this app's loaded baseline. Keep the answer under 100 words."
        ),
        "must_include_tool": "get_cbo_baseline",
    },
    {
        "label": "2. Hypothetical scoring (forces score_hypothetical_policy)",
        "question": (
            "Use score_hypothetical_policy to score a corporate tax rate "
            "increase from 21% to 25% (rate_change=0.04). Report the 10-year "
            "deficit impact in dollars, with a citation. Under 80 words."
        ),
        "must_include_tool": "score_hypothetical_policy",
    },
    {
        "label": "3. Knowledge corpus (forces search_knowledge)",
        "question": (
            "Use search_knowledge to find what the 2025 SSA Trustees Report "
            "projects for the OASI trust fund depletion date and the "
            "post-depletion benefit-payment ratio. Cite the source URL. "
            "Under 80 words."
        ),
        "must_include_tool": "search_knowledge",
    },
]


def _print_separator(char: str = "-", width: int = 78) -> None:
    print(char * width)


def _run_scenario(assistant: Any, scenario: dict[str, Any]) -> dict[str, Any]:
    print()
    _print_separator("=")
    print(scenario["label"])
    _print_separator("=")
    print("Q:", scenario["question"])
    _print_separator()
    print("A: ", end="", flush=True)

    start = time.time()
    accumulated: list[str] = []
    try:
        for chunk in assistant.stream_response(
            user_message=scenario["question"],
            history=[],
            scoring_context=None,
        ):
            accumulated.append(chunk)
            sys.stdout.write(chunk)
            sys.stdout.flush()
    except Exception as exc:  # noqa: BLE001
        print(f"\n\n!!! Stream raised: {type(exc).__name__}: {exc}")
        return {
            "label": scenario["label"],
            "ok": False,
            "elapsed_s": time.time() - start,
            "error": f"{type(exc).__name__}: {exc}",
            "tool_calls": [],
            "stripped_markers": [],
        }

    elapsed = time.time() - start
    print()
    _print_separator()
    tools_used = [p["tool"] for p in assistant.last_provenance]
    print(f"Tool calls: {tools_used or '(none)'}")
    print(f"Stripped citation markers: {assistant.last_stripped_markers}")
    if assistant.last_usage:
        usage = assistant.last_usage
        print(
            f"Tokens: in={usage.input_tokens:,} out={usage.output_tokens:,} "
            f"cache_w={usage.cache_creation_tokens:,} "
            f"cache_r={usage.cache_read_tokens:,} | "
            f"cost ≈ ${usage.cost_usd:.5f} | "
            f"elapsed {elapsed:.1f}s"
        )

    return {
        "label": scenario["label"],
        "ok": scenario["must_include_tool"] in tools_used,
        "elapsed_s": elapsed,
        "tool_calls": tools_used,
        "stripped_markers": assistant.last_stripped_markers,
        "answer": "".join(accumulated),
        "expected_tool": scenario["must_include_tool"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=None,
        help="Override the model id (defaults to claude-sonnet-4-6).",
    )
    parser.add_argument(
        "--only",
        type=int,
        metavar="N",
        help="Run only scenario N (1-indexed) to save cost.",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in the environment.")
        return 1

    assistant = _build_assistant(model=args.model)
    print(f"Model: {assistant._model}")  # noqa: SLF001 — debug script
    print(f"Knowledge dir: {ROOT / 'fiscal_model' / 'assistant' / 'knowledge'}")
    print(f"Web search: {'on' if assistant._enable_web_search else 'off'}")  # noqa: SLF001

    scenarios = SCENARIOS
    if args.only is not None:
        scenarios = [SCENARIOS[args.only - 1]]

    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        results.append(_run_scenario(assistant, scenario))

    # Summary
    print()
    _print_separator("=")
    print("SUMMARY")
    _print_separator("=")
    any_failure = False
    for r in results:
        status = "PASS" if r["ok"] else "FAIL"
        msg = (
            f"  {status} {r['label']}  "
            f"({r['elapsed_s']:.1f}s, tools: {r.get('tool_calls') or 'none'})"
        )
        print(msg)
        if not r["ok"]:
            any_failure = True
            if "error" in r:
                print(f"      Error: {r['error']}")
            else:
                print(
                    f"      Expected tool {r['expected_tool']!r} but got "
                    f"{r['tool_calls'] or '(none)'}"
                )
            if r.get("answer"):
                print(textwrap.indent(r["answer"][:400] + "…", "      | "))

    total_cost = assistant.cost.total_cost_usd
    print(f"\nTotal cost across {len(results)} call(s): ${total_cost:.4f}")
    print(f"Session summary: {assistant.cost.summary()}")

    return 1 if any_failure else 0


if __name__ == "__main__":
    sys.exit(main())
