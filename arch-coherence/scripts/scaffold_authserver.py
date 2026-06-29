#!/usr/bin/env python3
"""scaffold_authserver.py — generate the Authorization Server (auth.* process) into a server.

Writes the OAuth 2.1 Authorization Server that closes a project's REST + MCP surfaces
(AUTH.md). The AS is a third ASGI process beside api.* and mcp.*, generated *into* an
existing src+server, and is the only stateful component (the only DB owner). The
resource surfaces stay database-light: they validate a presented token only by
introspection over HTTP to auth.*, and import nothing from the authserver app.

Units (each independently reviewable):
  A  OAuth core    — configuration over django-oauth-toolkit (opaque tokens, never JWT;
                     PKCE required; DEFAULT_SCOPES empty = closed by default) + RFC 8414.
  B  WebAuthn      — FIDO2 hardware-key login (py_webauthn) gating /o/authorize; the
                     WebAuthnCredential store; cross-platform + UV-required + direct
                     attestation + an AAGUID whitelist (synced/platform passkeys rejected).
  C  recovery      — multi-key + backup codes + admin TAP. Recovery grants a recovery-only
                     session (enroll a new key, never a token); TokenIssuanceGuard enforces.
  D  registration  — DCR (RFC 7591) via oauth_dcr: an MCP client self-registers, then runs
                     auth-code + PKCE-S256. (CIMD is validated at the pilot — see README.)

Purely additive: it writes new files only and edits nothing the shell or deploy own —
settings/auth.py adds oauth2_provider + the authserver app to its *own* INSTALLED_APPS via
the `from .settings import *` composition idiom. Idempotent: re-running re-emits every file.

Run it with the *target project's* interpreter (the one with django-oauth-toolkit and
py_webauthn installed) when applying to a real project; the emitted text itself is pure
Python and Django-free, so racecar's own tests exercise it without those installed. The
WebAuthn ceremony is verified against a real hardware authenticator at Stage 7.
"""

import argparse
import re
from pathlib import Path

from scaffold_tree import render_tree

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
AUTH_PORT = 8003
_SCOPE_RE = re.compile(r"""["']scope["']\s*:\s*["']([^"']+)["']""")


def discover_scopes(server: Path) -> dict[str, str]:
    """The per-command scopes the surfaces enforce, read from the generated commands.py.

    create-server has already written `"scope": "pkg:vertical:action"` into each vertical's
    apps/<app>/commands.py; the AS must offer every one in SCOPES or it cannot issue a token the
    resource surfaces accept. Returns {scope: human description}, ordered and de-duplicated."""
    scopes: dict[str, str] = {}
    for commands_py in sorted(server.glob("apps/*/commands.py")):
        for scope in _SCOPE_RE.findall(commands_py.read_text(encoding="utf-8")):
            parts = scope.split(":")
            scopes[scope] = f"{parts[-1]} {parts[-2]}" if len(parts) >= 2 else scope
    return scopes

DEFAULT_ISSUER = "https://auth.example.com"


def settings_auth_py(issuer: str, scopes: dict[str, str] | None = None) -> str:
    """project/settings/auth.py — DOT configured closed by default + WebAuthn config.

    `scopes` is the per-command scope catalog (discover_scopes); the AS must offer every one in
    SCOPES or it cannot issue a token the resource surfaces accept."""
    scopes = scopes or {}
    _entries = ['"introspection": "Introspect token validity (resource servers)",']
    _entries += [f'"{_s}": "{_d}",' for _s, _d in scopes.items()]
    scopes_block = "\n        ".join(_entries)
    return f'''"""Authorization Server settings (auth.* process). The only stateful surface:
it owns the OAuth 2.1 token store and the WebAuthn credentials (plus the recovery
material and audit log). Closed by default — DEFAULT_SCOPES is empty, so a token
carries no scope unless the authorization explicitly grants one, and the only path to an
authenticated session is a hardware-key assertion (there is no password login).

Launched by the auth.* vhost (DJANGO_SETTINGS_MODULE=project.settings.auth)."""
import os
import pathlib
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

# Django settings composition idiom: pull the shared base in, override below.
# pylint: disable=wildcard-import,unused-wildcard-import
from .settings import *  # noqa: F401,F403

SURFACE = "auth"
ROOT_URLCONF = "project.urls.authurls"

# The AS is the stateful piece: oauth2_provider (the OAuth 2.1 server) + the authserver
# app (WebAuthn credentials, recovery, audit) go in THIS settings module only, never the
# surface-clean base. auth/sessions back the human login ceremony.
INSTALLED_APPS = INSTALLED_APPS + [  # noqa: F405
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "oauth2_provider",
    "oauth_dcr",
    "apps.authserver",
]

MIDDLEWARE = [  # noqa: F405
    MIDDLEWARE[0],  # SecurityMiddleware  # noqa: F405
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Token issuance is hardware-key only: a recovery session (backup code / TAP) may
    # enroll a new key but must never reach /o/authorize. Fail-closed.
    "apps.authserver.middleware.TokenIssuanceGuard",
    *MIDDLEWARE[1:],  # noqa: F405
]

# login() needs a backend to attach a session; there is no password *login view*, so no
# password path is exposed. The only login is the WebAuthn ceremony (LOGIN_URL below).
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "/login/"

# The public issuer URL (RFC 8414 metadata and the WebAuthn RP id derive from it).
AUTH_SERVER_ISSUER = os.environ.get("AUTH_SERVER_ISSUER", "{issuer}")
# Fail loud in prod rather than mis-scope ceremonies/metadata to a placeholder host.
if not DEBUG and "example.com" in AUTH_SERVER_ISSUER:  # noqa: F405
    raise ImproperlyConfigured(
        "AUTH_SERVER_ISSUER is unset/placeholder; set it (and WEBAUTHN_RP_ID/ORIGIN)"
    )
_issuer = urlparse(AUTH_SERVER_ISSUER)

# The AS answers at the issuer host; add it to the base allowlist. ALLOWED_HOSTS must stay an
# explicit allowlist (never "*"): request.get_host() drives the issued OAuth metadata and the
# WWW-Authenticate / protected-resource URLs, so an attacker-controlled Host would poison them.
if _issuer.hostname and _issuer.hostname not in ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS = ALLOWED_HOSTS + [_issuer.hostname]  # noqa: F405

# Transport hardening for the security-critical process. The session cookie carries the entire
# authenticated / recovery-session state; behind the TLS-terminating vhost Django must be told
# the proxied request is https (SECURE_PROXY_SSL_HEADER) before it will set Secure cookies.
# Gated on prod so local http dev still works.
if not DEBUG:  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Recovery throttling (the brute-force defense on backup codes / TAPs) is cache-backed. In a
# multi-worker prod deploy the default per-process LocMemCache gives each worker its own counter,
# silently multiplying the lockout budget into a fail-open. Require a cache shared across workers.
CACHES = {{
    "default": {{
        "BACKEND": os.environ.get(
            "DJANGO_CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": os.environ.get("DJANGO_CACHE_LOCATION", "auth-throttle"),
    }}
}}
if not DEBUG and "locmem" in CACHES["default"]["BACKEND"].lower():  # noqa: F405
    raise ImproperlyConfigured(
        "the recovery throttle needs a cache shared across workers in production; set "
        "DJANGO_CACHE_BACKEND (e.g. django.core.cache.backends.redis.RedisCache) and "
        "DJANGO_CACHE_LOCATION"
    )

# WebAuthn relying party. RP id is the registrable host; origin is scheme + host.
WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID", _issuer.hostname or "localhost")
WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Authorization Server")
WEBAUTHN_ORIGIN = os.environ.get(
    "WEBAUTHN_ORIGIN", f"{{_issuer.scheme}}://{{_issuer.netloc}}"
)
# Hardware-key whitelist: only authenticators whose AAGUID is listed may enroll (e.g.
# YubiKeys, from FIDO MDS). Empty = enrollment is CLOSED (fail-safe): a deployment must
# set this explicitly before the first key is enrolled (Stage 7 supplies the AAGUIDs).
WEBAUTHN_ALLOWED_AAGUIDS = [
    a.strip() for a in os.environ.get("WEBAUTHN_ALLOWED_AAGUIDS", "").split(",") if a.strip()
]
# Attestation roots (PEM bytes) for the "packed" format (modern FIDO2 YubiKeys). When set,
# py_webauthn verifies the attestation chains to them, so verification.aaguid is trustworthy
# and the whitelist above is a real hardware guarantee; UNSET, the AAGUID is self-reported
# (advisory). fido-u2f / other formats stay self-reported even when set; set this in prod.
WEBAUTHN_PACKED_ROOT_CERTS = [
    pathlib.Path(p.strip()).read_bytes()
    for p in os.environ.get("WEBAUTHN_PACKED_ROOT_CERTS", "").split(",") if p.strip()
]

# OAuth 2.1 Authorization Server (django-oauth-toolkit). Tokens are OPAQUE: random
# server-side strings indexed by SHA-256 checksum, carrying no claims on the wire and
# revocable. Never JWT (AUTH.md). PKCE is mandatory.
OAUTH2_PROVIDER = {{
    "PKCE_REQUIRED": True,
    "ACCESS_TOKEN_EXPIRE_SECONDS": int(
        os.environ.get("OAUTH2_ACCESS_TOKEN_EXPIRE_SECONDS", "3600")
    ),
    "ROTATE_REFRESH_TOKEN": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,
    "REFRESH_TOKEN_GRACE_PERIOD_SECONDS": 120,
    # Closed by default. DOT defaults DEFAULT_SCOPES to ["__all__"] — every token gets
    # every scope, wide-open, the opposite of the doctrine. Force it EMPTY: a token
    # carries no scope unless the authorization explicitly grants one. The per-command
    # scopes (racecar-create-server, from the binding) populate SCOPES; "introspection" lets a
    # resource server call /o/introspect.
    "DEFAULT_SCOPES": [],
    "SCOPES": {{
        {scopes_block}
    }},
}}
'''















# The runtime dependencies the AS adds on top of the server shell (django, uvicorn). They
# are not written into the shell's pyproject (create-server owns and regenerates that);
# the operator adds them before the migration. The list includes django-oauth-toolkit-dcr
# for RFC 7591 Dynamic Client Registration.
AUTH_RUNTIME_DEPS = [
    "django-oauth-toolkit>=3.2",
    "webauthn>=2.0",
    "django-oauth-toolkit-dcr",
]


def render_authserver(server: Path, issuer: str = DEFAULT_ISSUER) -> None:
    """Write the auth.* Authorization Server process into an existing server (idempotent).

    Additive: copies the AS static mirror tree (templates/authserver -> apps/authserver, the
    auth urlconf, the ceremony pages, the vhost, run-auth.sh) and overlays the interpolated
    settings/auth.py (which embeds the issuer). Edits nothing the shell or create-server own."""
    render_tree(
        _TEMPLATES / "authserver",
        server,
        {"__PORT__": str(AUTH_PORT), "{next_json}": '"/o/authorize/"'},
    )
    (server / "project" / "settings" / "auth.py").write_text(
        settings_auth_py(issuer, discover_scopes(server))
    )


def main() -> None:
    """CLI entry: write the auth.* Authorization Server into an existing server."""
    ap = argparse.ArgumentParser(
        description="Generate the OAuth 2.1 Authorization Server (auth.*) into a server."
    )
    ap.add_argument("--server", type=Path, required=True, help="existing server root")
    ap.add_argument(
        "--issuer",
        default=DEFAULT_ISSUER,
        help=f"public AS issuer URL (default {DEFAULT_ISSUER})",
    )
    args = ap.parse_args()
    if not (args.server / "project" / "settings" / "settings.py").exists():
        ap.error(f"no server shell at {args.server} (run racecar-create-server first)")
    render_authserver(args.server, args.issuer)
    deps = " ".join(AUTH_RUNTIME_DEPS)
    print(f"authserver (auth.*, issuer {args.issuer}) -> {args.server}")
    print(f"  add runtime deps before migrating: {deps}")


if __name__ == "__main__":
    main()
