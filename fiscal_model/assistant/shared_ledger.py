"""
A daily spend and turn counter shared by every copy of the server.

The sqlite ledger in :mod:`.rate_limit` is one file per process. That is one
ledger for the Streamlit app, but on a serverless host every warm instance has
its own ``/tmp``, so the $5/day cap became $5/day *per instance*. This module
keeps the two numbers the caps need, today's spend and each session's turns
today, in a Redis store reached over HTTPS (Upstash's REST API, which Vercel's
Upstash integration provisions). The sqlite ledger still keeps the per-turn
telemetry rows.

Configured by either pair of environment variables, whichever is set:

- ``UPSTASH_REDIS_REST_URL`` and ``UPSTASH_REDIS_REST_TOKEN``
- ``KV_REST_API_URL`` and ``KV_REST_API_TOKEN`` (the names Vercel sets)

Unset, :meth:`SharedLedger.from_env` returns ``None`` and the limiter uses
sqlite alone, as before.
"""

from __future__ import annotations

import os
from typing import Any

#: Counters outlive their day by two, so a request that straddles midnight
#: still finds yesterday's key, and the store cleans itself.
_TTL_SECONDS = 3 * 24 * 3600
_TIMEOUT_SECONDS = 3.0


class SharedLedgerError(RuntimeError):
    """The shared store could not be read or written."""


class SharedLedger:
    """Today's spend and per-session turn counts in a Redis store over REST."""

    def __init__(self, url: str, token: str, *, prefix: str = "ask", timeout: float = _TIMEOUT_SECONDS):
        self.url = url.rstrip("/")
        self._token = token
        self.prefix = prefix
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> SharedLedger | None:
        for url_name, token_name in (
            ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"),
            ("KV_REST_API_URL", "KV_REST_API_TOKEN"),
        ):
            url = os.environ.get(url_name, "").strip()
            token = os.environ.get(token_name, "").strip()
            if url.startswith("https://") and token:
                return cls(url, token)
        return None

    def __repr__(self) -> str:  # never print the token
        return f"SharedLedger({self.url!r})"

    # ------------------------------------------------------------------

    def _pipeline(self, commands: list[list[Any]]) -> list[Any]:
        import requests

        try:
            response = requests.post(
                f"{self.url}/pipeline",
                json=commands,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SharedLedgerError(f"shared ledger unreachable: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise SharedLedgerError(f"shared ledger returned HTTP {response.status_code}")
        try:
            replies = response.json()
        except ValueError as exc:
            raise SharedLedgerError("shared ledger returned a non-JSON reply") from exc
        if not isinstance(replies, list) or len(replies) != len(commands):
            raise SharedLedgerError("shared ledger returned an unexpected reply")
        results = []
        for reply in replies:
            if not isinstance(reply, dict) or "error" in reply:
                raise SharedLedgerError("shared ledger refused a command")
            results.append(reply.get("result"))
        return results

    def _spend_key(self, day: str) -> str:
        return f"{self.prefix}:spend:{day}"

    def _turns_key(self, day: str, session_id: str) -> str:
        return f"{self.prefix}:turns:{day}:{session_id}"

    # ------------------------------------------------------------------

    def spend_usd(self, day: str) -> float:
        (value,) = self._pipeline([["GET", self._spend_key(day)]])
        return float(value or 0.0)

    def add_spend(self, day: str, cost_usd: float) -> None:
        key = self._spend_key(day)
        self._pipeline([["INCRBYFLOAT", key, f"{cost_usd:.6f}"], ["EXPIRE", key, _TTL_SECONDS]])

    def session_turns(self, day: str, session_id: str) -> int:
        (value,) = self._pipeline([["GET", self._turns_key(day, session_id)]])
        return int(float(value or 0))

    def add_turn(self, day: str, session_id: str) -> None:
        key = self._turns_key(day, session_id)
        self._pipeline([["INCR", key], ["EXPIRE", key, _TTL_SECONDS]])


__all__ = ["SharedLedger", "SharedLedgerError"]
