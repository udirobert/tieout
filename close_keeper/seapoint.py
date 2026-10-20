"""Seapoint connection for close-keeper — a remote MCP server, not a token REST API.

Seapoint exposes its data through a **remote MCP server over streamable HTTP with
OAuth** at `https://mcp.seapoint.dev/mcp`. In Claude Code you register and sign in
once:

    claude mcp add --transport http seapoint-staging https://mcp.seapoint.dev/mcp
    # then: /mcp  -> select seapoint-staging -> authenticate

That connection is owned by Claude Code; its OAuth tokens live in Claude's own
credential store. There is **nothing to paste into `.env`** for it, and there is
no static Seapoint API token to obtain.

This module lets the *standalone* close-keeper agent reach the same server. It is
deliberately adaptable:

- **Discovers tools at runtime** — it lists whatever the connected workspace
  exposes (e.g. `query_transactions`, `query_accounts`, `query_invoices`,
  `query_treasury_returns`, …) instead of assuming fixed REST endpoints, so it
  tracks Seapoint's surface as it changes and works for any workspace's
  permissions.
- **Points anywhere** — `SEAPOINT_MCP_URL` selects staging vs prod vs a local
  mock; the default is the production server.
- **Any auth the server offers** — see below.
- **Degrades cleanly** — if Seapoint is disabled, unconfigured, or unreachable,
  the agent still runs on the local close package; live tools are simply absent.

Auth resolution (first match wins):

  1. `SEAPOINT_MCP_TOKEN`                             -> static bearer header
     (use if your workspace issues a personal/service access token)
  2. `SEAPOINT_MCP_CLIENT_ID` + `SEAPOINT_MCP_CLIENT_SECRET`
     (+ optional `SEAPOINT_MCP_SCOPES`)              -> OAuth client_credentials (M2M)
  3. `SEAPOINT_MCP_OAUTH=1`                           -> interactive OAuth (dynamic
     registration + PKCE, browser sign-in once, cached + refreshed thereafter).
     Works only where the server ENABLES DCR. The hackathon sandbox disables DCR
     and issues no client_id, so only Claude's pre-registered connector can reach
     it — see seapoint_oauth.py and close_keeper/README.md.
  4. none                                            -> anonymous; the server may
     still serve public tools, otherwise calls fail cleanly
"""

from __future__ import annotations

import os

DEFAULT_URL = "https://mcp.seapoint.dev/mcp"

# env knobs (documented in .env.example)
URL_ENV = "SEAPOINT_MCP_URL"
ENABLED_ENV = "SEAPOINT_MCP_ENABLED"
TOKEN_ENV = "SEAPOINT_MCP_TOKEN"
CLIENT_ID_ENV = "SEAPOINT_MCP_CLIENT_ID"
CLIENT_SECRET_ENV = "SEAPOINT_MCP_CLIENT_SECRET"
SCOPES_ENV = "SEAPOINT_MCP_SCOPES"
OAUTH_ENV = "SEAPOINT_MCP_OAUTH"

_FALSEY = {"0", "false", "no", "off"}
_TRUTHY = {"1", "true", "yes", "on"}


def seapoint_url() -> str:
    """The MCP server URL — prod by default, overridable for staging/local."""
    return os.environ.get(URL_ENV, DEFAULT_URL).strip() or DEFAULT_URL


def seapoint_enabled() -> bool:
    """True unless explicitly turned off. A URL is all that's strictly required."""
    if os.environ.get(ENABLED_ENV, "").strip().lower() in _FALSEY:
        return False
    return bool(seapoint_url())


def _auth_mode() -> str:
    if os.environ.get(TOKEN_ENV, "").strip():
        return "bearer"
    if os.environ.get(CLIENT_ID_ENV, "").strip() and os.environ.get(CLIENT_SECRET_ENV, "").strip():
        return "client_credentials"
    if os.environ.get(OAUTH_ENV, "").strip().lower() in _TRUTHY:
        return "oauth"
    return "anonymous"


def _scopes() -> list[str] | None:
    raw = os.environ.get(SCOPES_ENV, "").strip()
    return raw.split() if raw else None


def build_seapoint_client(prefix: str = "seapoint"):
    """Return a configured Strands `MCPClient` for Seapoint, or None if disabled.

    The client is a context manager: the caller must keep it open (via `with` or
    an `ExitStack`) for as long as the agent may call its tools. Raises only if
    `strands` is missing; connection failures surface when the caller enters the
    context, where they should be caught and treated as "no live data".

    Args:
        prefix: namespace applied to the server's tool names (default "seapoint",
            so `query_transactions` is exposed as `seapoint_query_transactions`).
    """
    if not seapoint_enabled():
        return None

    from strands.tools.mcp import MCPClient

    kwargs: dict = {
        "url": seapoint_url(),
        "prefix": prefix,
        # one failing Seapoint tool must not sink the whole agent
        "continue_on_error": True,
        "application_name": "close-keeper",
    }

    mode = _auth_mode()
    if mode == "bearer":
        token = os.environ[TOKEN_ENV].strip()
        kwargs["headers"] = {"Authorization": f"Bearer {token}"}
    elif mode == "client_credentials":
        creds: dict = {
            "client_id": os.environ[CLIENT_ID_ENV].strip(),
            "client_secret": os.environ[CLIENT_SECRET_ENV].strip(),
        }
        scopes = _scopes()
        if scopes:
            creds["scopes"] = scopes
        kwargs["auth"] = creds
    elif mode == "oauth":
        try:
            from close_keeper.seapoint_oauth import build_oauth_provider
        except ImportError:  # loaded as a loose module with close_keeper/ on sys.path
            from seapoint_oauth import build_oauth_provider

        kwargs["auth_provider"] = build_oauth_provider(seapoint_url(), scopes=_scopes())
    # else: anonymous — let the server decide

    return MCPClient(**kwargs)


def seapoint_status_line() -> str:
    """One human-readable line about how Seapoint will connect — never a secret."""
    if not seapoint_enabled():
        return f"Seapoint: disabled ({ENABLED_ENV}=0) — local close package only"
    mode = {
        "bearer": "static bearer token",
        "client_credentials": "OAuth client_credentials",
        "oauth": "interactive OAuth (browser sign-in, cached)",
        "anonymous": "anonymous / server-managed auth",
    }[_auth_mode()]
    return f"Seapoint: {seapoint_url()} ({mode})"
