# racecar-secure-server: the procedure

Accessed via [`SKILL.md`](SKILL.md). Doctrine home: [`../arch-coherence/AUTH.md`](../arch-coherence/AUTH.md)
(the auth rail) and [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md) (the
resource-surface rail this AS feeds).

Mechanism: `render_authserver(...)` in `../arch-coherence/scripts/scaffold_authserver.py`, invoked as
`scaffold_authserver.py --server <server> --issuer <https://auth.host>`. It writes the `auth.*` process
into an existing `src+server` (idempotent), beside the `api.*` and `mcp.*` surfaces.

## What this skill is for

Generate the **Authorization Server** that closes a project's REST + MCP surfaces. A surface exposes
`api` to an untrusted outside; AUTH.md says it must be **closed by default**. The closer is an OAuth
2.1 Authorization Server: it authenticates a human at a **FIDO2 hardware key** and issues the
**opaque bearer token** the surfaces validate. The surfaces are generated closed by `racecar-create-server`
(the validators); this skill generates the **issuer**.

It owns the issuer only. It does **not** write the resource-side bearer/scope checks in the REST and
MCP adapters: that is `racecar-create-server` (GENERATION.md, the resource-surface rail).

## Dependency cascade

`secure-server` closes the surfaces; each skill ensures its precondition by invoking the one below,
each idempotent:

- `racecar-secure-server`: needs a surface to close. If none exists, it **invokes `racecar-create-server`**.
- `racecar-create-server`: needs a `server/` shell. If absent, it **invokes `racecar-start-django-project`**; it reads the library at `src/<pkg>`.
- `racecar-start-django-project`: scaffolds the `server/` Django shell; needs nothing below it.
- `racecar-create-package`: scaffolds the `src/<pkg>` library; the greenfield root of the cascade.

## Where the AS lives

The AS is a **third ASGI process generated into the target server** (`auth.*` beside `api.*`/`mcp.*`),
not a separate project. One server, one deploy, one host-split (the existing `surfaceguard` extends to
the `auth.*` host). It owns the `authserver` app and is the **only stateful component and the only DB
owner**. The resource surfaces stay db-light: no token table, no import of `authserver`; they validate
a token **only by introspection over HTTP** to `auth.*`. That HTTP-only coupling keeps the import DAG
acyclic: the Stage 5 import-linter contract is "surfaces never import the AS".

```
server/
  project/
    settings/auth.py            # the auth.* settings: oauth2_provider + authserver app; OAUTH2_PROVIDER config
    urls/authurls.py            # /o/ (DOT), /.well-known/oauth-authorization-server, WebAuthn login, DCR
  apps/
    authserver/                 # the stateful app (DB owner)
      models.py                 # WebAuthnCredential, BackupCode, TemporaryAccessPass, AuditLog
      webauthn_views.py         # the two WebAuthn ceremonies gating /o/authorize
      metadata_views.py         # RFC 8414 server metadata (+ CIMD)
  run.sh                        # gains a third uvicorn: auth on :8003 (settings.auth)
  apache/auth.vhost.conf        # the auth.* reverse-proxy snippet
```

## What the generator emits, by unit

The skill is built in units; each is independently reviewable. The doctrine (AUTH.md) and the
mechanical gate (`check_surface_auth.py`) already exist; this skill is the implementation.

### Unit A: OAuth core (configuration over django-oauth-toolkit 3.2.0)

DOT ships the endpoints; the generator **configures** them, it does not re-implement them:

- `/o/authorize`, `/o/token`, `/o/revoke_token` (RFC 7009), `/o/introspect` (RFC 7662), mounted from
  `oauth2_provider.urls`. Tokens are **opaque** (a server-side `TextField` indexed by SHA-256
  checksum), never JWT.
- `OAUTH2_PROVIDER` config: `PKCE_REQUIRED=True`; `ACCESS_TOKEN_EXPIRE_SECONDS` short (default 3600);
  `ROTATE_REFRESH_TOKEN=True` with `REFRESH_TOKEN_REUSE_PROTECTION=True`; and the cardinal override
  **`DEFAULT_SCOPES=[]`**. DOT defaults `DEFAULT_SCOPES` to `["__all__"]` (every token gets every
  scope, wide-open, the opposite of the doctrine), so the generator forces it empty: **default-deny**
  is a config fact. The per-command scopes (Stage 6) populate `SCOPES`.
- RFC 8414 server metadata at `/.well-known/oauth-authorization-server`, advertising the endpoints,
  `code_challenge_methods_supported=["S256"]` (mirrors the eninesites precedent).

### Unit B: WebAuthn hardware-key login (built new)

No WebAuthn exists in the house; this is new code over `py_webauthn`. Two ceremonies gate access to
`/o/authorize`, so a token is only ever issued after a hardware-key assertion:

- Registration (enroll a key) and authentication (login), with
  `authenticator_attachment="cross-platform"` (no platform/synced passkeys),
  `user_verification="required"`, `attestation="direct"`, and a FIDO-MDS authenticator whitelist
  (e.g. YubiKey AAGUIDs). The `WebAuthnCredential` model stores enrolled keys per user.

### Unit C: recovery (mandatory)

Hardware-key-only has no cloud fallback, so recovery is not optional: multiple enrolled keys per user,
one-time `BackupCode`s, and an admin-issued `TemporaryAccessPass`.

### Unit D: client registration for MCP

`django-oauth-toolkit-dcr` (RFC 7591) at `/o/register/`, advertised in the RFC 8414 metadata, so a
Claude MCP client self-registers its redirect URIs and runs auth-code + PKCE-S256 against this AS. CIMD
(client-id-as-URL) is the spec-moving, Claude-dependent preferred path; it is validated at the pilot
(Stage 7) rather than emitted speculatively, since it depends on the live client behavior.

## Procedure

1. **Precondition.** A surface exists (run `racecar-create-server` first; `secure-server` invokes it if absent).
2. **Generate the AS:** `scaffold_authserver.py --server server --issuer https://auth.<host>` writes
   `settings/auth.py`, `urls/authurls.py`, `apps/authserver/`, the third uvicorn in `run.sh`, and the
   `auth.vhost.conf`. Idempotent.
3. **Migrate (gated).** The AS adds DB models, so it carries migrations, the one stateful commitment.
   This is owner-authorized per change; the generator emits the migration, the owner applies it.
4. **Enroll a hardware key**, configure the resource surfaces' introspection endpoint to point at
   `auth.*`, and regenerate the surfaces (`racecar-create-server`) so their bearer/scope checks come online.
5. **Verify closed.** `check_surface_auth.py` passes (auth gate present, every command scoped); a call
   with no token is refused; an out-of-scope token is refused.

## Edges and limits

- **The AS is stateful: by design, contained.** It is the only departure from db-light, isolated to
  the `authserver` app. The surfaces stay db-light.
- **No JWT, ever.** Opaque tokens only (AUTH.md). Revocation and short TTL are the point.
- **Hardware-key-only.** No password fallback, no platform-cloud passkeys. Recovery (Unit C) is
  mandatory, not optional, because there is no other way back in.
- **Owner-authorized.** It issues credentials and adds DB state; the migration is a gated commitment.

## Implementation

`scaffold_authserver.py` writes the `auth.*` process into an existing server and is exercised by
racecar's own test suite (scaffold into a temp server, `manage.py check` clean). The skill is wired into
`install` + `scripts/sync_claude_md.py`. The resource-side validators it pairs with are generated by
`racecar-create-server`; the mechanical gate that both must satisfy is
[`../arch-coherence/scripts/check_surface_auth.py`](../arch-coherence/scripts/check_surface_auth.py).

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).
