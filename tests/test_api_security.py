"""
Contract tests for API hardening: key auth, rate limiting, and request logging.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model import api_security


class _DummyScoringResult:
    def __init__(self) -> None:
        self.years = np.arange(2026, 2036)
        self.static_revenue_effect = np.full(10, 5.0)
        self.behavioral_offset = np.full(10, -1.0)
        self.final_deficit_effect = np.full(10, -4.0)
        self.baseline = SimpleNamespace(baseline_vintage_date="Feb 2026")
        self.dynamic_effects = None


class _DummyScorer:
    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def score_policy(self, policy, dynamic=False):
        del policy, dynamic
        return _DummyScoringResult()


@pytest.fixture(autouse=True)
def _reset_security(monkeypatch):
    """Each test starts with a fresh limiter and the env default (auth off)."""
    # Strip any prod env that might leak in so we control the state.
    monkeypatch.delenv("FISCAL_API_KEYS", raising=False)
    monkeypatch.delenv("FISCAL_API_RATE_LIMIT_PER_MINUTE", raising=False)
    monkeypatch.delenv("FISCAL_API_RATE_LIMIT_BURST", raising=False)
    api_security.configure(keys=None)
    api_security.reset_limiter()
    yield
    api_security.configure(keys=None)
    api_security.reset_limiter()


def _client() -> TestClient:
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Auth off (default) — contract compatibility
# ---------------------------------------------------------------------------


class TestAuthDisabledByDefault:
    def test_auth_disabled_when_no_env(self):
        assert api_security.is_auth_enabled() is False

    def test_open_endpoint_ignores_key(self):
        response = _client().get("/")
        assert response.status_code == 200
        assert response.json()["auth_required"] is False

    def test_score_endpoint_accepts_no_key_when_auth_disabled(self, monkeypatch):
        monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
        response = _client().post(
            "/score",
            json={
                "name": "No Auth Test",
                "rate_change": 0.026,
                "income_threshold": 400_000,
                "elasticity": 0.25,
                "duration_years": 10,
                "dynamic": False,
            },
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Auth on — rejects missing/invalid keys, accepts valid
# ---------------------------------------------------------------------------


class TestAuthEnabled:
    def _enable_auth(self):
        api_security.configure(keys={"classroom": "secret-abc", "research": "secret-def"})

    def test_auth_enabled_flag(self):
        self._enable_auth()
        assert api_security.is_auth_enabled() is True

    def test_open_paths_skip_auth(self, monkeypatch):
        self._enable_auth()
        monkeypatch.setattr(api_module, "check_health", lambda: {"overall": "ok"})
        client = _client()
        # Root and health remain open.
        assert client.get("/").status_code == 200
        assert client.get("/health").status_code == 200

    def test_missing_key_returns_401(self):
        self._enable_auth()
        response = _client().post(
            "/score",
            json={
                "name": "Needs Auth",
                "rate_change": 0.026,
                "income_threshold": 400_000,
                "elasticity": 0.25,
                "duration_years": 10,
                "dynamic": False,
            },
        )
        assert response.status_code == 401
        assert "X-API-Key" in response.json()["detail"]

    def test_invalid_key_returns_401(self):
        self._enable_auth()
        response = _client().post(
            "/score",
            headers={"X-API-Key": "not-a-real-key"},
            json={
                "name": "Bad Key",
                "rate_change": 0.026,
                "income_threshold": 400_000,
                "elasticity": 0.25,
                "duration_years": 10,
                "dynamic": False,
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key."

    def test_valid_key_is_accepted(self, monkeypatch):
        self._enable_auth()
        monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
        response = _client().post(
            "/score",
            headers={"X-API-Key": "secret-abc"},
            json={
                "name": "Good Key",
                "rate_change": 0.026,
                "income_threshold": 400_000,
                "elasticity": 0.25,
                "duration_years": 10,
                "dynamic": False,
            },
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Key parsing — accepts both label:secret and bare secret forms
# ---------------------------------------------------------------------------


class TestKeyParsing:
    def test_label_and_secret_form(self, monkeypatch):
        monkeypatch.setenv("FISCAL_API_KEYS", "research:r-123,classroom:c-456")
        api_security.configure()
        assert api_security.is_auth_enabled() is True

    def test_blank_env_disables_auth(self, monkeypatch):
        monkeypatch.setenv("FISCAL_API_KEYS", "   ")
        api_security.configure()
        assert api_security.is_auth_enabled() is False

    def test_whitespace_only_entries_ignored(self, monkeypatch):
        monkeypatch.setenv("FISCAL_API_KEYS", "one,,,  ,two")
        api_security.configure()
        assert api_security.is_auth_enabled() is True


# ---------------------------------------------------------------------------
# Rate limiting — sliding window
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_allows_up_to_capacity(self):
        limiter = api_security.SlidingWindowLimiter(per_minute=3, burst=0)
        allowed = [limiter.allow("alice", now=float(i) * 0.1) for i in range(5)]
        assert allowed == [True, True, True, False, False]

    def test_recovers_after_window(self):
        limiter = api_security.SlidingWindowLimiter(per_minute=2, burst=0)
        assert limiter.allow("bob", now=0.0)
        assert limiter.allow("bob", now=0.5)
        assert limiter.allow("bob", now=1.0) is False
        # 61s later, the original two timestamps are out of the window.
        assert limiter.allow("bob", now=61.0)

    def test_buckets_are_per_caller(self):
        limiter = api_security.SlidingWindowLimiter(per_minute=1, burst=0)
        assert limiter.allow("alice", now=0.0)
        assert limiter.allow("bob", now=0.0)
        # Alice is out; Bob still has headroom.
        assert limiter.allow("alice", now=0.1) is False

    def test_integration_returns_429(self, monkeypatch):
        """Exhaust the limiter and confirm the middleware returns 429."""
        monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
        api_security.configure(keys={"k": "s"}, per_minute=2, burst=0)

        client = _client()
        headers = {"X-API-Key": "s"}
        payload = {
            "name": "t",
            "rate_change": 0.01,
            "income_threshold": 0,
            "elasticity": 0.25,
            "duration_years": 10,
            "dynamic": False,
        }
        r1 = client.post("/score", headers=headers, json=payload)
        r2 = client.post("/score", headers=headers, json=payload)
        r3 = client.post("/score", headers=headers, json=payload)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        assert r3.headers["retry-after"] == "60"


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------


class TestRequestLogging:
    def test_each_request_emits_structured_log(self, monkeypatch, caplog):
        monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
        api_security.configure(keys={"classroom": "secret-abc"})

        with caplog.at_level(logging.INFO, logger="fiscal_model.api_security"):
            _client().post(
                "/score",
                headers={"X-API-Key": "secret-abc"},
                json={
                    "name": "Logged",
                    "rate_change": 0.01,
                    "income_threshold": 0,
                    "elasticity": 0.25,
                    "duration_years": 10,
                    "dynamic": False,
                },
            )

        records = [
            json.loads(record.message)
            for record in caplog.records
            if record.name == "fiscal_model.api_security"
        ]
        assert any(
            rec["event"] == "api_request"
            and rec["path"] == "/score"
            and rec["method"] == "POST"
            and rec["key_label"] == "classroom"
            and rec["status"] == 200
            and isinstance(rec["duration_ms"], (int, float))
            for rec in records
        )


# ---------------------------------------------------------------------------
# A secret never reaches the log (planning/ROUTE_TO_9.md, defect 2)
# ---------------------------------------------------------------------------
#
# ``_parse_keys`` used the secret itself as the label for an entry with no
# colon and for one with an empty label, and the middleware logs the label in
# two fields of every request line — so the supported configuration wrote the
# key to the log in the clear. Labels are now positional for any entry without
# a safe one.

_DUMMY_SECRETS = ("dummy-secret-7f3a9c", "second-dummy-2b8e", "same-9d1e")


def _configure_from_env(monkeypatch, raw: str) -> None:
    monkeypatch.setenv("FISCAL_API_KEYS", raw)
    api_security.configure()


def _labels() -> dict[str, str]:
    return {secret: info.label for secret, info in api_security._state.keys.items()}


class TestSecretsNeverReachTheLog:
    def test_an_unlabelled_key_gets_a_positional_label(self, monkeypatch):
        _configure_from_env(monkeypatch, "dummy-secret-7f3a9c")
        assert _labels() == {"dummy-secret-7f3a9c": "unlabelled-key-1"}

    def test_an_empty_label_is_treated_as_unlabelled(self, monkeypatch):
        _configure_from_env(monkeypatch, ":second-dummy-2b8e")
        assert _labels() == {"second-dummy-2b8e": "unlabelled-key-1"}

    def test_a_label_identical_to_its_secret_is_not_used(self, monkeypatch):
        """Same leak, written out by hand rather than created by the parser."""
        _configure_from_env(monkeypatch, "same-9d1e:same-9d1e")
        assert _labels() == {"same-9d1e": "unlabelled-key-1"}

    def test_positions_count_keys_not_commas_and_explicit_labels_survive(self, monkeypatch):
        _configure_from_env(
            monkeypatch, "dummy-secret-7f3a9c,, research:r-123 ,:second-dummy-2b8e"
        )
        assert _labels() == {
            "dummy-secret-7f3a9c": "unlabelled-key-1",
            "r-123": "research",
            "second-dummy-2b8e": "unlabelled-key-3",
        }

    def test_the_startup_warning_names_the_position_never_the_secret(
        self, monkeypatch, caplog
    ):
        with caplog.at_level(logging.WARNING, logger="fiscal_model.api_security"):
            _configure_from_env(monkeypatch, "dummy-secret-7f3a9c,:second-dummy-2b8e")
        assert "unlabelled-key-1" in caplog.text
        assert "unlabelled-key-2" in caplog.text
        for secret in _DUMMY_SECRETS:
            assert secret not in caplog.text

    def test_no_request_log_line_contains_a_secret(self, monkeypatch, caplog):
        monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
        _configure_from_env(
            monkeypatch, "dummy-secret-7f3a9c,:second-dummy-2b8e,same-9d1e:same-9d1e"
        )
        client = _client()
        with caplog.at_level(logging.INFO, logger="fiscal_model.api_security"):
            for secret in _DUMMY_SECRETS:
                response = client.post(
                    "/score",
                    headers={"X-API-Key": secret},
                    json={"name": "Logged", "rate_change": 0.01, "dynamic": False},
                )
                assert response.status_code == 200

        records = [
            json.loads(record.message)
            for record in caplog.records
            if record.name == "fiscal_model.api_security"
            and record.message.startswith("{")
        ]
        assert [rec["key_label"] for rec in records] == [
            "unlabelled-key-1",
            "unlabelled-key-2",
            "unlabelled-key-3",
        ]
        # Every field, not just the two known to have carried it.
        for secret in _DUMMY_SECRETS:
            assert secret not in caplog.text

    def test_unlabelled_keys_keep_separate_rate_limit_buckets(self, monkeypatch):
        """Distinct labels, so one unlabelled caller cannot exhaust another."""
        monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
        monkeypatch.setenv("FISCAL_API_KEYS", "dummy-secret-7f3a9c,second-dummy-2b8e")
        api_security.configure(per_minute=1, burst=0)
        client = _client()
        payload = {"name": "t", "rate_change": 0.01, "dynamic": False}

        first = {"X-API-Key": "dummy-secret-7f3a9c"}
        second = {"X-API-Key": "second-dummy-2b8e"}
        assert client.post("/score", headers=first, json=payload).status_code == 200
        assert client.post("/score", headers=first, json=payload).status_code == 429
        assert client.post("/score", headers=second, json=payload).status_code == 200

    def test_a_rejected_key_is_not_logged_either(self, monkeypatch, caplog):
        _configure_from_env(monkeypatch, "research:r-123")
        with caplog.at_level(logging.INFO, logger="fiscal_model.api_security"):
            response = _client().post(
                "/score",
                headers={"X-API-Key": "wrong-guess-4e6d"},
                json={"name": "t", "rate_change": 0.01, "dynamic": False},
            )
        assert response.status_code == 401
        assert "wrong-guess-4e6d" not in caplog.text
