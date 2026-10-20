"""Interactive OAuth for the standalone close-keeper agent against Seapoint.

Seapoint's MCP server speaks OAuth 2.1 with authorization-code + PKCE. This module
lets close-keeper's *own* process complete that flow via dynamic client registration.

IMPORTANT — the hackathon sandbox: its Auth0 tenant has **dynamic client registration
disabled** and issues no client_id, so this standalone flow cannot self-register there
(`POST /oidc/register` → 400 "dynamic client registration is disabled"). Only a client
Seapoint pre-registered — the Claude connector — can sign in to the sandbox; use Claude
as the harness for it (see close_keeper/README.md). This module works against Seapoint
deployments that ENABLE DCR, or use `SEAPOINT_MCP_TOKEN` for a bearer-token deployment.

What it provides:

- **Dynamic registration** — no pre-issued client id/secret; the client registers
  itself with the server on first run (matching "leave OAuth fields empty").
- **Persistent token cache** — tokens + the registered client are stored in a
  0600 JSON file, so you sign in once and later runs reuse/refresh silently.
- **Loopback callback** — a tiny single-request HTTP server on localhost catches
  the authorization redirect; the browser is opened automatically.

The provider is an `httpx2.Auth` (`OAuthClientProvider`), which Strands' streamable
HTTP transport drives natively via its `auth_provider` parameter — see
`close_keeper/seapoint.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp.client.auth import OAuthClientProvider
from mcp.client.auth.oauth2 import TokenStorage
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

DEFAULT_CACHE = Path.home() / ".close-keeper" / "seapoint-token.json"
DEFAULT_PORT = 8737  # loopback callback port (override with SEAPOINT_MCP_OAUTH_PORT)


class FileTokenStorage(TokenStorage):
    """OAuth token + client-registration storage backed by a single 0600 JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._read().get("tokens")
        return OAuthToken.model_validate(raw) if raw else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = self._read()
        data["tokens"] = tokens.model_dump(mode="json")
        self._write(data)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._read().get("client_info")
        return OAuthClientInformationFull.model_validate(raw) if raw else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        data = self._read()
        data["client_info"] = client_info.model_dump(mode="json")
        self._write(data)


async def _open_browser(auth_url: str) -> None:
    """Redirect handler: open the user's browser at the authorization URL."""
    import webbrowser

    print(
        "[close-keeper] Authorize Seapoint in your browser "
        f"(opening automatically; if it doesn't, visit):\n  {auth_url}",
        file=sys.stderr,
    )
    try:
        webbrowser.open(auth_url)
    except Exception:  # noqa: BLE001 — headless box: the printed URL is the fallback
        pass


def _make_callback_handler(port: int):
    """Callback handler factory: serve exactly one loopback request, return the code."""

    async def callback_handler() -> AuthorizationCodeResult:
        captured: dict[str, str | None] = {}

        def _serve_once() -> None:
            from http.server import BaseHTTPRequestHandler, HTTPServer
            from urllib.parse import parse_qs, urlparse

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:  # noqa: N802 — http.server API
                    params = parse_qs(urlparse(self.path).query)
                    captured["code"] = (params.get("code") or [None])[0]
                    captured["state"] = (params.get("state") or [None])[0]
                    captured["error"] = (params.get("error") or [None])[0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    body = (
                        "<html><body style='font:16px system-ui;padding:3rem'>"
                        "<h2>close-keeper is connected to Seapoint.</h2>"
                        "<p>You can close this tab and return to the terminal.</p>"
                        "</body></html>"
                    )
                    self.wfile.write(body.encode())

                def log_message(self, *args) -> None:  # silence request logging
                    pass

            server = HTTPServer(("localhost", port), Handler)
            try:
                server.handle_request()  # blocks until exactly one request
            finally:
                server.server_close()

        await asyncio.to_thread(_serve_once)

        if captured.get("error"):
            raise RuntimeError(f"Seapoint authorization failed: {captured['error']}")
        code = captured.get("code")
        if not code:
            raise RuntimeError("Seapoint authorization returned no code on the callback")
        return AuthorizationCodeResult(code=code, state=captured.get("state"))

    return callback_handler


def _relax_issuer_trailing_slash() -> None:
    """Accept an auth-server issuer that differs only by a trailing slash.

    Seapoint's authorization server advertises its issuer WITH a trailing slash
    (`https://auth.seapoint.dev/`) while the MCP SDK derives it WITHOUT, and
    `validate_metadata_issuer` does an exact string compare (RFC 8414 §3.3 /
    RFC 3986 §6.2.1) — so an otherwise-valid server is rejected. RFC 3986 §6.2.3
    treats the two as equivalent. We relax ONLY that one difference; every other
    issuer mismatch still raises. Idempotent; patches the name in oauth2's module
    namespace, which is where the flow resolves it at call time.
    """
    from mcp.client.auth import oauth2 as _oauth2

    original = _oauth2.validate_metadata_issuer
    if getattr(original, "_seapoint_relaxed", False):
        return

    def relaxed(oauth_metadata, expected_issuer):  # noqa: ANN001, ANN202
        issuer = str(getattr(oauth_metadata, "issuer", "") or "")
        if issuer.rstrip("/") == (expected_issuer or "").rstrip("/"):
            return  # same issuer up to a trailing slash — accept
        return original(oauth_metadata, expected_issuer)

    relaxed._seapoint_relaxed = True  # type: ignore[attr-defined]
    _oauth2.validate_metadata_issuer = relaxed


def build_oauth_provider(
    server_url: str,
    *,
    cache_path: Path | None = None,
    port: int | None = None,
    scopes: list[str] | None = None,
) -> OAuthClientProvider:
    """Build an interactive OAuth provider for the Seapoint MCP server.

    First use opens a browser to sign in and caches the result; later runs reuse
    and silently refresh the stored token.

    Args:
        server_url: the MCP server URL (e.g. https://mcp.seapoint.dev/mcp).
        cache_path: token/registration cache file (default ~/.close-keeper/...).
        port: loopback callback port the redirect_uri binds to.
        scopes: advisory scopes; the server's advertised scopes win if it lists any.
    """
    _relax_issuer_trailing_slash()  # tolerate Seapoint's trailing-slash issuer
    port = port or int(os.environ.get("SEAPOINT_MCP_OAUTH_PORT", DEFAULT_PORT))
    cache_path = cache_path or _cache_path_from_env()
    redirect_uri = f"http://localhost:{port}/callback"
    metadata = OAuthClientMetadata(
        client_name="close-keeper",
        redirect_uris=[redirect_uri],  # pydantic coerces str -> AnyUrl
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",  # public client; PKCE, no secret
        scope=" ".join(scopes) if scopes else None,
    )
    return OAuthClientProvider(
        server_url=server_url,
        client_metadata=metadata,
        storage=FileTokenStorage(cache_path),
        redirect_handler=_open_browser,
        callback_handler=_make_callback_handler(port),
    )


def _cache_path_from_env() -> Path:
    raw = os.environ.get("SEAPOINT_MCP_OAUTH_CACHE", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_CACHE
