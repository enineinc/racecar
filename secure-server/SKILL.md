---
name: racecar-secure-server
description: Generate the Authorization Server that closes a project's REST + MCP surfaces — the auth rail (AUTH.md). Adds a third ASGI process (auth.*) into an existing src+server: an OAuth 2.1 Authorization Server (django-oauth-toolkit — opaque bearer tokens, never JWT; PKCE-required; short-lived, scoped, revocable; introspection RFC 7662 and revocation RFC 7009 out of the box) whose human login is FIDO2 hardware-key WebAuthn (py_webauthn, cross-platform authenticator + user-verification required + attestation-whitelisted), plus RFC 8414 server metadata, dynamic client registration (RFC 7591) for MCP clients, multi-key + backup-code + admin-TAP recovery, and an audit log. The AS is the only stateful component and the only DB owner; the resource surfaces stay db-light and validate by introspection over HTTP, never importing it. Closed by default: DEFAULT_SCOPES is empty, so a token carries no scope unless explicitly granted. Stacks on racecar-create-server (a surface to close must exist); invokes it when no surface is present. Owner-authorized (issues credentials, adds DB state), idempotent, regenerable. Use when asked to "add auth", "secure the API/MCP", "stand up the authorization server", "require login", or "close the surfaces".
---

# racecar-secure-server — the Authorization Server (closes the surfaces)

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: a racecar surface exposes `api` to an untrusted outside, so it must be **closed by default**
([`../arch-coherence/AUTH.md`](../arch-coherence/AUTH.md)). This skill generates the piece that closes
it — an OAuth 2.1 **Authorization Server**, the identity provider that authenticates a human at a
**FIDO2 hardware key** and issues the **opaque bearer token** the REST and MCP surfaces then validate.
One auth path, both surfaces (AUTH-03); built into the generator, package-agnostic (AUTH-02); canon,
not a deployer's afterthought (AUTH-01).

**The cascade.** `create-package → create-server → secure-server → deploy-server` (create-server delegates the Django shell to the generic `start-django-project`),
each idempotent. `secure-server` closes the surfaces `create-server` generated: it ensures its own
precondition by invoking `racecar-create-server` when no surface exists (which scaffolds the `server/`
shell via `racecar-start-django-project` and reads the `src/<pkg>` library).

**Where the AS lives (the load-bearing shape).** The AS is a **third ASGI process generated into the
target server** — `auth.*` beside `api.*` and `mcp.*` — not a separate project. One server, one deploy.
It owns the `authserver` app, and it is the **only stateful component and the only DB owner**. The two
resource surfaces stay **database-light**: they hold no token table, import nothing from `authserver`,
and validate a presented token only by **introspection over HTTP** to `auth.*` (cached briefly). That
HTTP-only coupling is what keeps the import DAG acyclic (Stage 5's import-linter gate: surfaces never
import the AS) and what lets the surfaces remain db-light while the AS carries all the state.

**What it generates (grounded in django-oauth-toolkit 3.2.0).**
- **OAuth core, mostly configuration.** DOT ships `/o/authorize`, `/o/token`, `/o/revoke_token`
  (RFC 7009), `/o/introspect` (RFC 7662). Tokens are **opaque** server-side strings (a `TextField`
  indexed by SHA-256 checksum), never JWT — exactly the doctrine. The generator does not re-implement
  these; it **configures** them: `PKCE_REQUIRED=True`, short `ACCESS_TOKEN_EXPIRE_SECONDS`,
  `ROTATE_REFRESH_TOKEN` with reuse protection, and — the cardinal override — **`DEFAULT_SCOPES=[]`**.
  DOT defaults `DEFAULT_SCOPES` to `["__all__"]` (every token gets every scope: wide-open, the
  opposite of our doctrine), so the generator forces it empty: a token carries **no** scope unless the
  authorization explicitly grants it. Default-deny is a config fact, not a hope.
- **Server metadata (RFC 8414).** `/.well-known/oauth-authorization-server` advertising the endpoints,
  `code_challenge_methods_supported = ["S256"]`, so an MCP client can complete the flow.
- **WebAuthn hardware-key login (built new — none exists in the house).** `py_webauthn` ceremonies
  gate `/o/authorize`: `authenticator_attachment="cross-platform"` + `user_verification="required"` +
  `attestation="direct"` with a FIDO-MDS authenticator whitelist, so only a registered hardware key
  (e.g. YubiKey) can authenticate. A `WebAuthnCredential` model holds the enrolled keys.
- **Recovery (mandatory).** Hardware-key-only has no cloud fallback, so: multiple enrolled keys,
  one-time backup codes, and an admin-issued Temporary Access Pass.
- **Client registration for MCP.** `django-oauth-toolkit-dcr` (RFC 7591) plus CIMD, with the correct
  Claude redirect URIs, so a Claude client can register and run auth-code + PKCE-S256.
- **Audit.** An `AuditLog` model recording identity, tool, allow/deny, ip, timestamp (Stage 6).

Doctrine home: [`../arch-coherence/AUTH.md`](../arch-coherence/AUTH.md) (the auth rail) and
[`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md) (the resource-surface rail that
consumes the AS). The resource-side enforcement — bearer extraction, cached introspection, per-tool
scope checks in the REST and MCP adapters — is generated by `racecar-create-server`, not here; this skill
generates the issuer, deploy generates the validators.
