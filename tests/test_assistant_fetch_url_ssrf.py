"""``fetch_url`` must connect only to the host the allowlist validated.

Defect (2026-10 hunt): ``allowlisted_domain`` judged the host with
``urlparse`` while ``requests`` connected to the host *its own* parser found,
so ``http://127.0.0.1:PORT\\@cbo.gov/`` passed the allowlist and fetched
loopback. These tests run a real local HTTP server as the "internal service"
and assert it is never reached.
"""

from __future__ import annotations

import http.server
import socket
import threading
from typing import Any

import pytest

from fiscal_model.assistant import tools as tools_mod
from fiscal_model.assistant.sources import allowlisted_domain
from fiscal_model.assistant.tools import AssistantTools


class _Handler(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self) -> None:
        type(self).hits.append(self.path)
        body = b"<html><body>INTERNAL-SECRET-METADATA</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture()
def internal_server(monkeypatch: pytest.MonkeyPatch):
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    _Handler.hits = []
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv.server_port, _Handler.hits
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.fixture()
def tools() -> AssistantTools:
    return AssistantTools(scorer=None, baseline=None, cbo_score_map={}, presets={})


@pytest.fixture()
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every allowlisted name resolve to a public address."""

    def fake(host: str, *a: Any, **k: Any):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake)


class _Resp:
    def __init__(
        self,
        status: int = 200,
        body: bytes = b"<html><body>Hello CBO</body></html>",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status
        self._body = body
        self.headers = {"Content-Type": "text/html; charset=utf-8", **(headers or {})}
        self.encoding = "utf-8"
        self.closed = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 1024):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------


class TestAllowlistParserDifferential:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000\\@cbo.gov/",
            "http://evil.com\\@cbo.gov/",
            "http://169.254.169.254\\.cbo.gov/",
            "http://127.0.0.1:8000\t@cbo.gov/",
            "http://user:pw@cbo.gov/",
            "http://evil.com@www.cbo.gov/",
            "http://cbo.gov@evil.com/",
            "http://cbo.gov /x",
            "http://cbo.gov/x\nHost: evil.com",
            "ftp://cbo.gov/x",
            "file:///etc/passwd#.cbo.gov",
            "javascript://cbo.gov/%0aalert(1)",
            "http://cbo.gov:8080/",
            "http://evilcbo.gov/",
            "http://cbo.gov.evil.com/",
            "http://notcbo.gov/",
            "http://evil.com/?x=.cbo.gov",
            "http://evil.com/#@cbo.gov",
            "//cbo.gov/x",
            "cbo.gov/x",
            "http://cbo.gov:99999999/",
            "http://cбo.gov/",
        ],
    )
    def test_rejected(self, url: str) -> None:
        assert allowlisted_domain(url) is None

    @pytest.mark.parametrize(
        "url,domain",
        [
            ("https://www.cbo.gov/publication/12345", "cbo.gov"),
            ("http://cbo.gov/", "cbo.gov"),
            ("https://CBO.GOV/x", "cbo.gov"),
            ("https://apps.bea.gov/iTable/", "bea.gov"),
            ("https://www.cbo.gov:443/x?y=1#z", "cbo.gov"),
            ("https://fred.stlouisfed.org/series/GDP", "stlouisfed.org"),
        ],
    )
    def test_accepted(self, url: str, domain: str) -> None:
        assert allowlisted_domain(url) == domain


class TestFetchUrlSsrf:
    def test_backslash_userinfo_bypass_never_reaches_loopback(
        self, tools: AssistantTools, internal_server
    ) -> None:
        port, hits = internal_server
        result = tools.dispatch(
            "fetch_url", {"url": f"http://127.0.0.1:{port}\\@cbo.gov/"}
        )
        assert "error" in result
        assert "INTERNAL-SECRET" not in str(result)
        assert hits == []

    def test_tab_userinfo_bypass_never_reaches_loopback(
        self, tools: AssistantTools, internal_server
    ) -> None:
        port, hits = internal_server
        result = tools.dispatch(
            "fetch_url", {"url": f"http://127.0.0.1:{port}\t@cbo.gov/"}
        )
        assert "error" in result and hits == []

    def test_redirect_from_allowlisted_host_to_loopback_is_refused(
        self,
        tools: AssistantTools,
        internal_server,
        public_dns,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        port, hits = internal_server
        calls: list[str] = []

        def fake_get(url: str, **kw: Any) -> _Resp:
            calls.append(url)
            assert kw["allow_redirects"] is False
            if "cbo.gov" in url:
                return _Resp(302, headers={"Location": f"http://127.0.0.1:{port}/"})
            raise AssertionError("must not be reached")

        monkeypatch.setattr("requests.get", fake_get)
        result = tools.dispatch("fetch_url", {"url": "https://www.cbo.gov/x"})
        assert "error" in result and "refused" in result["error"]
        assert calls == ["https://www.cbo.gov/x"]
        assert hits == []

    def test_redirect_chain_is_capped(
        self, tools: AssistantTools, public_dns, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        n = {"calls": 0}

        def fake_get(url: str, **kw: Any) -> _Resp:
            n["calls"] += 1
            return _Resp(301, headers={"Location": f"https://www.cbo.gov/{n['calls']}"})

        monkeypatch.setattr("requests.get", fake_get)
        result = tools.dispatch("fetch_url", {"url": "https://www.cbo.gov/start"})
        assert "redirects" in result["error"]
        assert n["calls"] == tools_mod.MAX_FETCH_REDIRECTS + 1

    def test_allowlisted_host_resolving_to_private_ip_is_refused(
        self, tools: AssistantTools, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
        )

        def boom(*a: Any, **k: Any) -> None:
            raise AssertionError("must not connect")

        monkeypatch.setattr("requests.get", boom)
        result = tools.dispatch("fetch_url", {"url": "https://localhost.cbo.gov/x"})
        assert "non-public" in result["error"]

    def test_oversized_body_is_refused(
        self, tools: AssistantTools, public_dns, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        big = b"a" * (tools_mod.MAX_FETCH_BYTES + 1)
        monkeypatch.setattr("requests.get", lambda url, **kw: _Resp(200, body=big))
        result = tools.dispatch("fetch_url", {"url": "https://www.cbo.gov/big"})
        assert "larger than" in result["error"]

    def test_legit_fetch_still_works(
        self, tools: AssistantTools, public_dns, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_get(url: str, **kw: Any) -> _Resp:
            seen["url"] = url
            seen["stream"] = kw.get("stream")
            return _Resp()

        monkeypatch.setattr("requests.get", fake_get)
        result = tools.dispatch("fetch_url", {"url": "https://www.cbo.gov/publication/1"})
        assert result["text"] == "Hello CBO"
        assert result["domain"] == "cbo.gov"
        assert result["kind"] == "html"
        assert seen == {"url": "https://www.cbo.gov/publication/1", "stream": True}

    def test_legit_same_site_redirect_is_followed(
        self, tools: AssistantTools, public_dns, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_get(url: str, **kw: Any) -> _Resp:
            if url == "https://cbo.gov/a":
                return _Resp(301, headers={"Location": "/b"})
            assert url == "https://cbo.gov/b"
            return _Resp()

        monkeypatch.setattr("requests.get", fake_get)
        result = tools.dispatch("fetch_url", {"url": "https://cbo.gov/a"})
        assert result["text"] == "Hello CBO"
