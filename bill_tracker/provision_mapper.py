"""
Provision mapper: bill summary → calculator Policy objects.

Architecture (LLM-first):
  1. Send CRS summary to Claude Haiku API (primary extractor)
  2. Parse JSON response into candidate Policy objects
  3. Validate with regex patterns as sanity-check layer
  4. Fall back to manual overrides when available

API cost: ~$0.001–$0.002/bill with claude-haiku-4-5-20251001.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Prompt template
# ------------------------------------------------------------------

LLM_EXTRACTION_PROMPT = """\
You are a fiscal policy parameter extractor. Given the CRS summary of a Congressional bill,
extract all fiscal provisions and return a JSON array of policy objects.

Each policy object MUST have these fields:
  - "policy_type": one of:
      income_tax, capital_gains, corporate, credits, spending, transfer,
      payroll, estate, trade, tcja_extension, other
  - "parameters": dict of numeric/boolean parameters matching the calculator's Policy classes:
      income_tax:      rate_change, affected_income_threshold, taxable_income_elasticity
      capital_gains:   rate_change, affected_income_threshold
      corporate:       rate_change, corporate_elasticity
      credits:         credit_type, credit_amount_billions, expansion_years
      spending:        spending_change_billions, multiplier
      transfer:        transfer_change_billions
      payroll:         rate_change, cap_change
      estate:          exemption_change, rate_change
      tcja_extension:  extend_all, keep_salt_cap, extension_years
      other:           description
  - "confidence": "high" | "medium" | "low"
      high = explicit numeric values found; medium = inferred from context;
      low = provision is vague or unmappable
  - "provision_text": the exact summary sentence(s) this was extracted from

Rules:
- Use rate_change as a decimal fraction (e.g. 2.6 percentage points = 0.026)
- Dollar amounts in billions unless noted otherwise
- If no fiscal provisions found, return []
- Return ONLY valid JSON (no markdown, no explanation)

Bill summary:
{summary}
"""

# ------------------------------------------------------------------
# Regex patterns used as a VALIDATION layer only (not primary extractor)
# ------------------------------------------------------------------

PROVISION_PATTERNS = {
    "percentage_change": re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:percentage\s*points?|pp|percent(?:age)?)?\s*(?:increase|decrease|cut|raise|lower)",
        re.IGNORECASE,
    ),
    "dollar_billions": re.compile(
        r"\$\s*(\d+(?:\.\d+)?)\s*(billion|trillion|million)", re.IGNORECASE
    ),
    "rate_number": re.compile(
        r"(?:rate|rates?|percent)\s+(?:of|to|from|at)?\s*(\d+(?:\.\d+)?)\s*(?:percent|%)",
        re.IGNORECASE,
    ),
    "threshold_400k": re.compile(
        r"\$400[,\s]*000|\$400K|\$400\s*thousand", re.IGNORECASE
    ),
    "income_above": re.compile(
        r"(?:income|earnings|wages)?\s+(?:above|over|exceeding|in\s+excess\s+of)\s+"
        r"\$?([\d,]+(?:\.\d+)?)\s*(billion|million|thousand|K)?",
        re.IGNORECASE,
    ),
}


@dataclass
class MappingResult:
    """Result of mapping a bill summary to calculator Policy objects."""

    bill_id: str
    policies: list[dict]            # Extracted policy parameter dicts (not yet instantiated)
    confidence: str                 # "high" | "medium" | "low" (overall)
    confidence_reason: str
    unmapped_provisions: list[str] = field(default_factory=list)
    mapping_notes: str = ""
    extraction_method: str = "llm"  # "llm" | "manual" | "regex_validated"
    validation_warnings: list[str] = field(default_factory=list)
    raw_llm_response: str = ""


class ProvisionMapper:
    """
    Maps bill summaries to calculator Policy parameter dicts via LLM + regex validation.

    The Anthropic client is injected to allow mocking in tests.
    """

    MANUAL_OVERRIDES_PATH = Path(__file__).parent  # manual_mappings.json lives here

    def __init__(self, anthropic_client=None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic_client
        self._model = model

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY")
                )
            except ImportError as err:
                raise RuntimeError(
                    "anthropic package is required for ProvisionMapper. "
                    "Install it: pip install anthropic"
                ) from err
        return self._client

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def map_bill(self, bill_id: str, summary: str | None) -> MappingResult:
        """
        Primary path: LLM extraction → regex validation → MappingResult.

        If a manual override exists for bill_id, returns that instead.
        """
        # Check for manual override first
        override = self._load_override(bill_id)
        if override:
            return MappingResult(
                bill_id=bill_id,
                policies=override["policies"],
                confidence="high",
                confidence_reason="Manual override by " + override.get("mapped_by", "unknown"),
                mapping_notes=override.get("override_reason", ""),
                extraction_method="manual",
            )

        if not summary or not summary.strip():
            return MappingResult(
                bill_id=bill_id,
                policies=[],
                confidence="low",
                confidence_reason="No summary available for extraction",
                extraction_method="llm",
            )

        # LLM extraction
        raw_response, policies = self._extract_with_llm(summary)

        # Regex validation
        warnings = self._validate_with_regex(policies, summary)

        # Compute overall confidence
        if not policies:
            confidence = "low"
            reason = "No fiscal provisions identified"
        elif any(p.get("confidence") == "low" for p in policies):
            confidence = "low"
            reason = "One or more provisions have low confidence"
        elif all(p.get("confidence") == "high" for p in policies):
            confidence = "high"
            reason = f"{len(policies)} provision(s) extracted with high confidence"
        else:
            confidence = "medium"
            reason = f"{len(policies)} provision(s) extracted with mixed confidence"

        if warnings:
            if confidence == "high":
                confidence = "medium"
            reason += f"; {len(warnings)} validation warning(s)"

        unmapped = [
            p["provision_text"]
            for p in policies
            if p.get("policy_type") == "other"
        ]

        return MappingResult(
            bill_id=bill_id,
            policies=[p for p in policies if p.get("policy_type") != "other"],
            confidence=confidence,
            confidence_reason=reason,
            unmapped_provisions=unmapped,
            mapping_notes="; ".join(warnings) if warnings else "",
            extraction_method="llm" if not warnings else "regex_validated",
            validation_warnings=warnings,
            raw_llm_response=raw_response,
        )

    def map_manual(self, bill_id: str, policies: list[dict]) -> MappingResult:
        """Manual override for bills where LLM extraction fails or is wrong."""
        return MappingResult(
            bill_id=bill_id,
            policies=policies,
            confidence="high",
            confidence_reason="Manual override",
            extraction_method="manual",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_with_llm(self, summary: str) -> tuple[str, list[dict]]:
        """Call Claude Haiku to extract fiscal provisions. Returns (raw, policies)."""
        prompt = LLM_EXTRACTION_PROMPT.format(summary=summary[:4000])  # cap at 4K chars

        try:
            message = self.client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            policies = self._parse_llm_json(raw)
            return raw, policies
        except Exception as e:
            logger.warning("LLM extraction failed for bill summary: %s", e)
            return "", []

    def _parse_llm_json(self, raw: str) -> list[dict]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
        cleaned = cleaned.strip("`").strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return [p for p in parsed if isinstance(p, dict)]
            if isinstance(parsed, dict) and "policies" in parsed:
                return parsed["policies"]
        except json.JSONDecodeError as e:
            logger.debug("LLM JSON parse error: %s | raw: %s", e, raw[:200])

        # Try to find a JSON array anywhere in the response
        array_match = re.search(r"\[.*?\]", cleaned, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

        return []

    def _validate_with_regex(self, policies: list[dict], summary: str) -> list[str]:
        """
        Regex validation layer: sanity-check LLM-extracted numeric values.

        Returns a list of warning strings.
        """
        warnings: list[str] = []

        for policy in policies:
            params = policy.get("parameters", {})
            policy_type = policy.get("policy_type", "")

            # Check rate_change plausibility
            rate_change = params.get("rate_change")
            if rate_change is not None:
                if abs(rate_change) > 0.5:
                    warnings.append(
                        f"{policy_type}: implausible rate_change={rate_change:.3f} (>50pp)"
                    )
                # Verify the numeric value appears in the summary text
                rate_pct = abs(rate_change) * 100
                rate_str = f"{rate_pct:.1f}"
                if rate_pct > 0.5 and rate_str not in summary and str(int(rate_pct)) not in summary:
                    warnings.append(
                        f"{policy_type}: rate_change {rate_pct:.1f}% not found in summary text"
                    )

            # Check for implausible spending amounts
            spending = params.get("spending_change_billions") or params.get("credit_amount_billions")
            if spending is not None and abs(spending) > 10_000:
                warnings.append(
                    f"{policy_type}: implausible amount ${spending:.0f}B (>$10T)"
                )

        return warnings

    def _load_override(self, bill_id: str) -> dict | None:
        """
        Load manual override for a bill_id.

        Checks two locations in order:
        1. bill_tracker/manual_mappings.json (combined file, keyed by bill_id)
        2. <MANUAL_OVERRIDES_PATH>/<bill_id>.json (individual file per bill)
        """
        # Combined file (primary)
        combined = self.MANUAL_OVERRIDES_PATH / "manual_mappings.json"
        if combined.exists():
            try:
                data = json.loads(combined.read_text())
                entry = data.get(bill_id)
                if entry:
                    return entry
            except Exception:
                pass

        # Individual file (secondary)
        override_file = self.MANUAL_OVERRIDES_PATH / f"{bill_id}.json"
        if override_file.exists():
            try:
                return json.loads(override_file.read_text())
            except Exception as e:
                logger.warning("Failed to load override for %s: %s", bill_id, e)

        return None
