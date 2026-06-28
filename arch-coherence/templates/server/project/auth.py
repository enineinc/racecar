"""Resource-server auth rail: validate the OAuth 2.1 bearer token a surface receives.

Closed by default (AUTH.md). Each surface is an OAuth 2.1 resource server: it extracts the
bearer token, validates it by introspection (RFC 7662) against the Authorization Server,
caches the result briefly, and checks the command's required scope. With introspection
unconfigured it FAILS CLOSED -- every call is refused, never allowed.

The surface authenticates its own introspection calls with a client credential carrying the
"introspection" scope (AUTH_INTROSPECTION_CLIENT_ID/SECRET), registered at the AS."""
import base64
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

_CACHE = {}  # sha256(token) -> (monotonic_expiry, introspection_response)
_CACHE_MAX = 4096  # bound: sweep expired entries once the cache grows past this
# Surface-side audit (database-light): the per-call access trail is the log, not a table.
_log = logging.getLogger("racecar.surface.auth")


class AuthServerError(Exception):
    """No introspection verdict: AS unreachable or unconfigured. Reported as 503 (not a
    401 blaming the caller's token); still fail-closed -- the call is refused."""


def _introspect(token):
    """Introspect a token at the AS (RFC 7662); cache the verdict briefly.

    Returns the response (maybe {"active": false}); raises AuthServerError if the AS is
    unconfigured or unreachable (never conflated with a rejected token). Keyed by
    sha256(token), TTL clamped to the token's own exp; swept when it grows past _CACHE_MAX."""
    now = time.monotonic()
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]
    url = getattr(settings, "AUTH_INTROSPECTION_URL", "")
    client_id = getattr(settings, "AUTH_INTROSPECTION_CLIENT_ID", "")
    client_secret = getattr(settings, "AUTH_INTROSPECTION_CLIENT_SECRET", "")
    if not (url and client_id and client_secret):
        raise AuthServerError("introspection not configured")
    body = urllib.parse.urlencode({"token": token}).encode()
    req = urllib.request.Request(url, data=body)
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req.add_header("Authorization", f"Basic {basic}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            info = json.loads(resp.read())
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        _log.warning("introspection failed (AS unreachable): %s", exc)
        raise AuthServerError("authorization server unreachable") from exc
    ttl = float(getattr(settings, "AUTH_INTROSPECTION_CACHE_SECONDS", 30))
    exp = info.get("exp")
    if exp:  # never serve a cached verdict past the token's own expiry
        ttl = max(0.0, min(ttl, exp - time.time()))
    _CACHE[key] = (now + ttl, info)
    if len(_CACHE) > _CACHE_MAX:  # bounded memory: drop expired entries
        for stale in [c for c, (e, _i) in _CACHE.items() if e <= now]:
            _CACHE.pop(stale, None)
    return info


def _bearer(request):
    """The bearer token from the Authorization header, or an empty string."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    return header[7:].strip() if header.startswith("Bearer ") else ""


def check(request, scope):
    """None if the request carries a valid token with `scope`; else (status, message).

    Fail-closed: no/invalid token -> 401; valid token missing scope -> 403; AS
    unreachable or unconfigured -> 503 (a server fault, not the caller's bad token)."""
    token = _bearer(request)
    if not token:
        _log.warning("deny %s scope=%s reason=no-token", request.path, scope)
        return (401, "missing bearer token")
    try:
        info = _introspect(token)
    except AuthServerError as exc:
        # Log the specific cause; tell the client only that auth is unavailable (do not
        # disclose "not configured" vs "unreachable" to an unauthenticated caller).
        _log.error("deny %s scope=%s reason=auth-server: %s", request.path, scope, exc)
        return (503, "authorization temporarily unavailable")
    if not info.get("active"):
        _log.warning("deny %s scope=%s reason=inactive", request.path, scope)
        return (401, "invalid or inactive token")
    sub = info.get("username") or info.get("client_id")
    if scope and scope not in (info.get("scope") or "").split():
        _log.warning("deny %s scope=%s sub=%s reason=scope", request.path, scope, sub)
        return (403, f"insufficient_scope: {scope} required")
    _log.info("allow %s scope=%s sub=%s", request.path, scope, sub)
    return None
