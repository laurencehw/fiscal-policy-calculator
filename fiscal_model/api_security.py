"""
API security: key authentication, rate limiting, and structured logging.

Design goals
------------
1. **Default off.** If ``FISCAL_API_KEYS`` is unset, every endpoint is
   open — the app is still pleasant to run locally and every existing test
   that calls the API without a key keeps passing. Operators opt into
   hardening explicitly by setting the env var before launch.

2. **No new hard dependencies.** Rate limiting is implemented as a small
   sliding-window counter in process memory. That is good enough for a
   single-worker Uvicorn deployment behind a reverse proxy that does its
   own rate limiting at the edge; for multi-worker or multi-instance
   deployments, front with Nginx/Cloudflare/a dedicated limiter.

3. **Machine-readable logs.** Each request emits one structured JSON log
   line with path, method, status, latency, API key id (if any), and
   policy name when available. Plays well with standard aggregators.

Wiring
------
Endpoints that mutate or score attach ``Depends(require_api_key)``; health
and discovery endpoints stay open. The FastAPI app installs a single
``@app.middleware`` that enforces rate limits and writes the request log.

Env vars
--------
- ``FISCAL_API_KEYS``: comma-separated list of ``label:secret`` pairs, e.g.
  ``classroom:abc123,research:def456``. If a value has no colon, the key
  itself is used as the label. Blank or unset disables auth.
- ``FISCAL_API_RATE_LIMIT_PER_MINUTE``: requests per minute per-key (or
  per-IP if auth is disabled). Default 60.
- ``FISCAL_API_RATE_LIMIT_BURST``: additional bucket size. Default 20.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger("fiscal_model.api_security")

API_KEY_HEADER = "X-API-Key"
_api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)

_ANON_KEY_LABEL = "anonymous"
_DISABLED_KEY_LABEL = "auth_disabled"


# ---------------------------------------------------------------------------
# Key registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _KeyInfo:
    label: str
    secret: str


def _parse_keys(raw: str | None) -> dict[str, _KeyInfo]:
    """Parse ``FISCAL_API_KEYS`` into a ``{secret: KeyInfo}`` map."""
    if not raw or not raw.strip():
        return {}
    keys: dict[str, _KeyInfo] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            label, _, secret = token.partition(":")
            label = label.strip() or secret.strip()
            secret = secret.strip()
        else:
            label = token
            secret = token
        if not secret:
            continue
        keys[secret] = _KeyInfo(label=label, secret=secret)
    return keys


def _load_keys_from_env() -> dict[str, _KeyInfo]:
    return _parse_keys(os.environ.get("FISCAL_API_KEYS"))


def _rate_limits_from_env() -> tuple[int, int]:
    def _int_env(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            logger.warning("Invalid %s=%r; using default %d", name, raw, default)
            return default
        return max(1, value)

    per_minute = _int_env("FISCAL_API_RATE_LIMIT_PER_MINUTE", 60)
    burst = _int_env("FISCAL_API_RATE_LIMIT_BURST", 20)
    return per_minute, burst


# ---------------------------------------------------------------------------
# Sliding-window rate limiter
# ---------------------------------------------------------------------------


class SlidingWindowLimiter:
    """
    Per-caller sliding-window rate limiter.

    Each caller (identified by an opaque string — key label or IP) gets a
    deque of the timestamps of their recent requests inside the last 60s.
    When a new request arrives, timestamps older than 60s are dropped; if
    the remaining count is below ``per_minute + burst``, it is allowed and
    recorded.
    """

    def __init__(self, per_minute: int, burst: int) -> None:
        self.per_minute = per_minute
        self.burst = burst
        self.capacity = per_minute + burst
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, caller: str, *, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._buckets.setdefault(caller, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.capacity:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        """Clear all buckets. Useful in tests."""
        with self._lock:
            self._buckets.clear()


# ---------------------------------------------------------------------------
# Module-level mutable state (rebuilt by ``configure`` for tests)
# ---------------------------------------------------------------------------


class _SecurityState:
    """Mutable container so tests can reconfigure without re-importing."""

    def __init__(self) -> None:
        self.keys: dict[str, _KeyInfo] = _load_keys_from_env()
        per_minute, burst = _rate_limits_from_env()
        self.limiter = SlidingWindowLimiter(per_minute=per_minute, burst=burst)

    @property
    def auth_enabled(self) -> bool:
        return bool(self.keys)


_state = _SecurityState()


def configure(
    *,
    keys: dict[str, str] | None = None,
    per_minute: int | None = None,
    burst: int | None = None,
) -> None:
    """Reconfigure the security state in-process. Primarily used in tests."""
    if keys is None:
        _state.keys = _load_keys_from_env()
    else:
        _state.keys = {
            secret: _KeyInfo(label=label, secret=secret)
            for label, secret in keys.items()
        }
    env_per_minute, env_burst = _rate_limits_from_env()
    _state.limiter = SlidingWindowLimiter(
        per_minute=per_minute if per_minute is not None else env_per_minute,
        burst=burst if burst is not None else env_burst,
    )


def reset_limiter() -> None:
    _state.limiter.reset()


def is_auth_enabled() -> bool:
    return _state.auth_enabled


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def _resolve_key_or_raise(api_key: str | None) -> str:
    if not _state.auth_enabled:
        return _DISABLED_KEY_LABEL
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {API_KEY_HEADER} header.",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )
    info = _state.keys.get(api_key)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )
    return info.label


async def require_api_key(
    api_key: str | None = Security(_api_key_scheme),
) -> str:
    """
    FastAPI dependency: validate the ``X-API-Key`` header.

    Returns the key label (for logging) when auth is enabled and the key
    matches; returns ``"auth_disabled"`` when no keys are configured.
    Raises 401 on missing or invalid key when auth is enabled. Endpoints
    attach this via ``Depends(require_api_key)``.
    """
    return _resolve_key_or_raise(api_key)


# ---------------------------------------------------------------------------
# Middleware for rate limiting + structured request logging
# ---------------------------------------------------------------------------


OPEN_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def _caller_identity(request: Request, resolved_key_label: str | None) -> str:
    if resolved_key_label and resolved_key_label not in {
        _ANON_KEY_LABEL,
        _DISABLED_KEY_LABEL,
    }:
        return f"key:{resolved_key_label}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


async def security_middleware(request: Request, call_next: Callable):
    """
    Enforce rate limits and emit a structured request log.

    Auth itself is enforced via the per-endpoint ``Depends`` dependency so
    that OpenAPI docs show the security scheme correctly. The middleware
    handles the cross-cutting concerns: rate limiting and logging.
    """
    started = time.perf_counter()
    path = request.url.path
    method = request.method

    # Resolve the caller's key label early so rate-limit buckets are
    # per-key rather than per-IP whenever auth is enabled and the key is
    # present in the header. Invalid keys fall through to IP-based limits
    # here; the dependency will reject them with 401.
    header_key = request.headers.get(API_KEY_HEADER)
    key_info = _state.keys.get(header_key) if header_key else None
    key_label = key_info.label if key_info else None
    caller = _caller_identity(request, key_label)

    if path not in OPEN_PATHS:
        if not _state.limiter.allow(caller):
            _log_request(
                path=path,
                method=method,
                status_code=429,
                caller=caller,
                key_label=key_label,
                duration_ms=0.0,
                reason="rate_limited",
            )
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded ({_state.limiter.per_minute}/min "
                        f"with burst {_state.limiter.burst}). Retry after 60s."
                    )
                },
                headers={"Retry-After": "60"},
            )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000.0
        _log_request(
            path=path,
            method=method,
            status_code=500,
            caller=caller,
            key_label=key_label,
            duration_ms=duration_ms,
            reason="unhandled_exception",
        )
        raise

    duration_ms = (time.perf_counter() - started) * 1000.0
    _log_request(
        path=path,
        method=method,
        status_code=response.status_code,
        caller=caller,
        key_label=key_label,
        duration_ms=duration_ms,
    )
    return response


def _log_request(
    *,
    path: str,
    method: str,
    status_code: int,
    caller: str,
    key_label: str | None,
    duration_ms: float,
    reason: str | None = None,
) -> None:
    record = {
        "event": "api_request",
        "path": path,
        "method": method,
        "status": status_code,
        "duration_ms": round(duration_ms, 2),
        "caller": caller,
        "key_label": key_label,
    }
    if reason:
        record["reason"] = reason
    logger.info(json.dumps(record, separators=(",", ":")))


__all__ = [
    "API_KEY_HEADER",
    "OPEN_PATHS",
    "SlidingWindowLimiter",
    "configure",
    "is_auth_enabled",
    "require_api_key",
    "reset_limiter",
    "security_middleware",
]
