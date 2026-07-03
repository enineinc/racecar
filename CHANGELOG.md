# Changelog

All notable changes to racecar are recorded here, in the style of
[Keep a Changelog](https://keepachangelog.com). racecar is pre-1.0, so a minor
bump may carry breaking changes for adopters; those are marked **Breaking**.

## 0.15.1 - 2026-07-02

### Fixed
- **The racecar-overrides gate no longer rejects racecar's own bindings.** 0.15.0 flagged any
  `[tool.racecar]` table as a fork, which would fail every adopter that declares the `surface`,
  `roles`, or `subsystem-docs` binding racecar's own checkers read (surface generation, the
  orchestration detector, the subsystem-docs check). The gate now allows those three canon
  bindings and flags only non-canon keys: `[tool.racecar.overrides]` and anything else.
- **The prose-punctuation gate exempts machine-readable content.** The em-dash / en-dash / `--`
  ban now applies to human prose only. Markdown is scanned minus its fenced code blocks and inline
  code spans, matching the "code is machine-readable, exempt" rule already applied to Python
  docstrings; VOICE.md states the exemption. The `--` detector also now catches a sentence dash at
  a line wrap that the previous pattern missed, and the version-bump checker's own docstring no
  longer trips that rule.

## 0.15.0 - 2026-07-02

### Added
- **Version-bump gate (`scripts/check_version_bump.py`, commit-msg stage).** A commit whose
  conventional type maps to a semver bump (feat, fix, perf, or a breaking change) fails when the
  version home is unchanged between the index and HEAD. It resolves the version home per
  COMMITS.md ([project].version, else a root VERSION file) and asserts only that a bump happened,
  not that the magnitude is correct (that stays racecar-commit's). Non-bumpable types pass. Wired
  into `templates/classic/pre-commit-config.yaml` and delivered to adopters via `sync_scripts`.
- **Prose-punctuation gate (`scripts/check_prose_punctuation.py`, pre-commit + commit-msg).**
  Enforces VOICE.md "No em-dashes in prose", extended to the en-dash and the `--` sentence dash.
  It scans commit messages unconditionally, staged Markdown whole-file, and Python docstrings only
  (code is not prose). A machine-generated file opts out inclusively by carrying the marker
  `racecar:prose-exempt`, not through a central ignore-list. Delivered to adopters via
  `sync_scripts`.
- **racecar-overrides gate (`scripts/check_racecar_overrides.py`, consumer-side).** Asserts a repo
  has not forked racecar: no `[tool.racecar]` table in pyproject.toml and a `racecar.mk`
  byte-identical to canon (fix racecar, do not override it). It reuses `check_config_drift`'s
  template-diff helper (one home) and is racecar-run-only, wired into `racecar.mk`'s `arch` target
  (guarded on RACECAR_ROOT) and the upgrade procedure. It no-ops on racecar's own repo.

### Changed
- **`racecar.mk`'s `install-dev` installs the commit-msg hook type** (`pre-commit install
  --hook-type pre-commit --hook-type commit-msg`), so the new commit-msg-stage gates actually fire.

## 0.13.4 - 2026-06-29

### Fixed
- **The canonical pylint config excludes django migrations.** 0.13.3 began shipping the authserver
  `0001_initial.py`, and auto-generated django migrations always trip `invalid-name` (the `0001_`
  filename) and `missing-class-docstring`, so `make lint` failed in every regenerated repo. The
  `library-pyproject.toml` `ignore-paths` now skips `.*/migrations/.*`. This lives in the rcfile,
  not a command-line `--ignore-paths`, because the command-line form *replaces* a repo's own
  exclusions (audit/, notebooks/) while the rcfile entry *merges* with them. The generated-output
  lint test now lints migrations too, so a future regression fails racecar's own suite. Existing
  repos add the one `ignore-paths` entry when they regenerate (their pyproject is repo-owned).

## 0.13.3 - 2026-06-29

### Added
- **`server/connect_mcp.sh` is generated into every project.** One parameterized script registers
  the MCP surface with Claude Code, local by default (`http://mcp.localhost:<port>/mcp`), `--url`
  to point at the deployed server. On first tool use Claude Code drives the OAuth itself (discover
  the AS, DCR self-register, browser WebAuthn login, opaque token, call tools). The MCP-client
  hookup is a per-app need, so racecar generates it rather than each repo reinventing it.

### Fixed
- **`secure-server` ships the authserver migration** (gfem-pilot finding). The generated app
  carried the models but no migration, so a bare `manage.py migrate` silently skipped the
  `WebAuthnCredential` / `BackupCode` / `TemporaryAccessPass` / `AuditLog` tables. The
  deterministic `0001_initial.py` is now in the template, so `migrate` just works.
- **`secure-server` populates the AS scope catalog from the generated surfaces** (gfem-pilot
  finding). `OAUTH2_PROVIDER["SCOPES"]` carried only `introspection`, so the AS could not issue a
  token bearing any per-command scope and every resource call failed `insufficient_scope`. A new
  `discover_scopes` reads each `apps/<app>/commands.py` and writes the full catalog into `SCOPES`.

## 0.13.2 - 2026-06-29

### Security
- **The generated Authorization Server is hardened at the transport / session / secret layer.** A
  security review found the core model already fail-closed (opaque-token introspection with
  sha256-keyed, exp-clamped caching; default-deny scopes; every surface message gated; WebAuthn
  replay / attestation / AAGUID enforcement; recovery sessions firewalled from token issuance; CSRF
  correct). The gaps were below the application layer and are now closed:
  - the `auth.*` settings set `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`,
    `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, and HSTS in production (the session cookie carries
    the authenticated state behind a TLS-terminating proxy Django otherwise cannot see as secure);
  - the issuer host joins `ALLOWED_HOSTS` automatically, since `request.get_host()` drives the issued
    OAuth metadata under `USE_X_FORWARDED_HOST`;
  - `DJANGO_SECRET_KEY` is guarded in production like the issuer (a placeholder key signs forgeable AS
    sessions);
  - the recovery throttle refuses a per-process `LocMemCache` in production (multi-worker would fail the
    lockout open), backup codes widen to 64 bits, and the WebAuthn login failure is opaque (no
    credential-existence oracle).
  AUTH.md documents the introspection revocation-latency window; the open-DCR redirect-URI guarantee is
  noted as django-oauth-toolkit's exact-match, not racecar's.

### Added
- **The generated server is linted at the consumer bar.** `make install-dev` installs a `django`
  dependency group (the pylint-django plugin plus the django / DOT / webauthn runtime), and a new test
  renders the full server and runs pylint at the canonical `library-pyproject.toml` bar. racecar never
  linted its own generated output before, so a generator change that would fail a consumer's lint now
  fails racecar's own `make test` first.
- **`check_packaging` flags retired make variables in `.pre-commit-config.yaml`** (`RETIRED_MAKE_VARS`,
  `DJAPP -> SERVER`). A repo-owned scaffold file survives a racecar upgrade, so a stale hook body
  (`make -s print-DJAPP` after the djapp/server rename) silently broke the import-linter hook; that
  staleness is now a Blocker with a test.

### Changed
- **Authorization Server views are grouped under `apps/authserver/views/`** (`metadata.py`,
  `recovery.py`, `webauthn.py`), Django-canonical and matching the surfaces side, replacing the flat
  `*_views.py` at the app root.
- **`too-few-public-methods` (R0903) joins the canonical pylint disable set**, matching what racecar
  itself and adopters already do (pydantic models, config / exception classes, django middleware).
- **`make install-dev` is the canonical target for the `django` group** (the `library-pyproject.toml`
  comment that pointed at a non-existent `make install-django` is corrected).
- **`render_tree` skips `.DS_Store` / `__pycache__`**, so a stray OS file can no longer crash generation.

## 0.13.1 - 2026-06-28

### Fixed
- **The surface generator now emits code that passes racecar's own lint.** Caught by the gfem
  pilot (the first repo regenerated on 0.13.0): three generator defects that racecar's own
  `make check` never saw, because it does not lint generated output.
  - `templates/classic/racecar.mk` still invoked the renamed-away `check_face_orchestration.py`;
    it now calls `check_surface_orchestration.py` (the 0.13.0 face/surface rename missed the Make
    template, so `make arch` broke in any regenerated repo).
  - `scaffold_surfaces.py`'s generated REST view had nine `return` statements, over pylint's
    default `max-returns` of 6. Request validation is extracted into an `_extract` helper that
    raises a small `_RequestError`, leaving the view with three returns.
  - the generated `issue_tap` management `Command` class had no docstring.

## 0.13.0 - 2026-06-28

### Changed
- **"surface" is now canon; "face" is retired.** A racecar HTTP interface over `api` is a
  **surface** (the noun already used in `external_surface` and the surface taxonomy); the code
  that translates a transport into an `api` call is an **adapter**. The rename runs through the
  canon: `FACES.md` → `SURFACES.md` ("the surfaces axis"), `scaffold_web_face*.py` →
  `scaffold_surfaces*.py`, `check_face_orchestration.py` → `check_surface_orchestration.py`,
  `faceguard` → `surfaceguard`. **Breaking** for adopters of the deploy surface: the binding key
  `[tool.racecar.web_face]` → `[tool.racecar.surface]` and the write-rail env var
  `RACECAR_WEB_FACE_ALLOW_WRITES` → `RACECAR_ALLOW_WRITES`; regenerate the server after upgrading.
- **The shape model is `PYTHON_LIBRARY` × `DJANGO_PROJECT`.** A project is the product of the
  library (`src/<pkg>`, the pyproject **always** at the repo root) and the Django deployable
  (`server/`, marked by `server/manage.py`), yielding three shapes: `src` (library only),
  `src+server` (library × Django), and `server` (standalone Django, no library). Detection is
  duplicated in lockstep — `check_packaging_rules/_shape.py::detect_shape` (Python) and
  `templates/classic/racecar.mk` (Make), held by `test_sync_scripts.py`. **Breaking:** the
  deployable directory `djapp/` → `server/` throughout (settings, urls, run.sh, vhosts, the binding,
  the docs); regenerate after upgrading.
- **Renamed the role manifest to name what it holds.** The advisory detector's optional manifest moved
  from `[tool.racecar.surfaces]` to `[tool.racecar.roles]`: it declares each vertical's module **roles**
  (lib / api / surface) for role identification, so it is named for its content, not for the check that
  reads it. This also de-collides it from `create-server`'s per-command generation binding
  `[tool.racecar.surface]` (the old `surfaces`/`surface` pair differed by a single `s`, a latent footgun).
  `check_surface_orchestration` reads the new key. **Breaking** only for a project that declared the
  manifest (advisory, rarely used).

### Removed
- **The `pypkg/` shape and `racecar-reshape-to-pypkg` are gone.** 0.12.0's `src → pypkg/src`
  migration is dropped: `migrate_shape.py` is deleted and the skill removed. The library is the
  canon root `src/<pkg>` in every shape, with its pyproject at the repo root — no wrapper directory,
  no shape migration. **Breaking** for anyone who reshaped to `pypkg/`: move `pypkg/<pkg>/src/<pkg>`
  back to `src/<pkg>` and the library pyproject back to the repo root. (Workspace
  `{packages,pypkg}/<pkg>/src/<pkg>` polymorphism is a recognized future, not this release.)

### Added
- **The server-cascade skills** (replacing the reshape → deploy pipeline). The lifecycle cascade is
  `racecar-create-package` → `racecar-create-server` → `racecar-secure-server` →
  `racecar-deploy-server` (each idempotent, each ensuring its precondition by invoking the one below);
  `racecar-create-server` delegates the Django shell scaffold to the generic, reusable
  `racecar-start-django-project`.
  - **`racecar-create-package`**: scaffolds the `src/<pkg>` library, django-free and `-m`-runnable; the
    greenfield root of the cascade.
  - **`racecar-start-django-project`**: a **generic, location-free, racecar-agnostic** Django scaffold
    (a standalone reusable skill) that lays down a vanilla Django project anywhere: a single
    `project/settings.py`, an empty `project/urls.py`, asgi/wsgi, `manage.py`, an empty `apps/`. Bootable
    (`manage.py check` passes); knows nothing about `src/`, `api`, or surfaces. `racecar-create-server`
    delegates the `server/` scaffold to it. `render_shell(out)` / `scaffold_surfaces.py --shell-only --out server`.
  - **`racecar-create-server`**: the racecar-specific composition — reads `src/<pkg>/api` and writes
    the REST (`api.*`) + MCP (`mcp.*`) surfaces over it. `render_project` **replaces** the vanilla
    `settings.py`/`urls.py` modules with the per-surface `settings/`/`urls/` packages and adds
    `surfaceguard`, `project/auth.py`, `run.sh`, the vhosts, and the per-vertical adapters
    (`render_project` = `_write_surface_shell` + `_write_surfaces`; surface output unchanged from
    0.12.0). It writes only `server/`, never `src/`, and invokes `racecar-start-django-project` when
    no shell exists.
  - **`racecar-secure-server`**: the Authorization Server (below).
  - **`racecar-deploy-server`**: a TODO stub — host/sysadmin deployment (TLS, processes, secrets), no
    code generation yet.
- **Auth canon (the doctrine and its gate, ahead of the implementation).** `arch-coherence/AUTH.md`:
  a generated surface is **closed by default** — one OAuth 2.1 opaque-bearer path on both surfaces, a
  separate WebAuthn hardware-key Authorization Server, per-tool scopes, no JWT.
  `arch-coherence/scripts/check_surface_auth.py` fails a surface that ships anonymous or any command
  with no scope; it bites before the rail exists, making "closed by default" mechanical. The
  resource-surface rail lands with `racecar-create-server` (below).
- **`racecar-secure-server` — the Authorization Server skill (Units A-D).** The third step of the
  cascade (`create-package → create-server → secure-server → deploy-server`): it generates the OAuth
  2.1 Authorization Server that issues the opaque bearer token
  the surfaces validate. `auth.*` is a third ASGI process
  generated *into* the server, the only stateful component and DB owner; the surfaces stay db-light and
  reach it only by introspection over HTTP (so they never import it).
  - **Unit A (OAuth core):** `scaffold_authserver.py` configures django-oauth-toolkit closed by
    default — PKCE required, and the cardinal override `DEFAULT_SCOPES = []` (DOT defaults to the
    wide-open `["__all__"]`) — plus RFC 8414 server metadata advertising S256. Opaque tokens, never
    JWT; revocation (RFC 7009) and introspection (RFC 7662) come from DOT.
  - **Unit B (WebAuthn hardware-key login):** FIDO2 login (py_webauthn) gates `/o/authorize` — a token
    is issued only after a hardware-key assertion, and there is no password path. Enforced
    hardware-key-only: cross-platform attachment, user-verification required, direct attestation, and
    an AAGUID whitelist that fails closed when unset (synced/platform passkeys rejected). Usernameless
    discoverable-credential login; the `WebAuthnCredential` store is the AS's only model.
  - **Unit C (recovery):** multi-key, one-time backup codes, and an admin Temporary Access Pass
    (issued by the `issue_tap` management command — no web admin login, so no password backdoor).
    Recovery is doctrine-preserving: a redeemed code or pass grants a **recovery-only session** that
    can enroll a new hardware key but never reach `/o/authorize`, enforced by the `TokenIssuanceGuard`
    middleware (a recovery secret is never a token-issuing bypass of the hardware-key requirement).
    Secrets are stored hashed; CSRF protection is on.
  - **Unit D (client registration):** Dynamic Client Registration (RFC 7591) via `oauth_dcr` at
    `/o/register/`, advertised in the RFC 8414 metadata, so an MCP client (Claude) self-registers its
    redirect URIs and runs auth-code + PKCE-S256. CIMD (client-id-as-URL) is the spec-moving,
    Claude-dependent preferred path and is validated at the pilot, not faked in the generator.
  - The WebAuthn ceremony and the Claude OAuth flow are verified against a real authenticator and a
    real MCP client at the gfem pilot (Stage 7).
- **The resource-surface auth rail (`racecar-create-server`).** Both surfaces become OAuth 2.1 resource
  servers, closed by default, the identity analog of the write rail. The generator now threads a
  per-command `scope` through the binding (`--scaffold-binding` emits a default-deny stub) and emits
  `project/auth.py`: it extracts the bearer token and validates it by introspection (RFC 7662) against
  the AS, cached briefly, using the surface's own `introspection`-scoped client credential. With
  introspection unconfigured it **fails closed** (refuses every call). The REST adapter returns 401
  (no/invalid token) or 403 (insufficient scope); the MCP adapter gates every message, returns 401 +
  `WWW-Authenticate`, and serves `/.well-known/oauth-protected-resource` (RFC 9728) so a client
  discovers the AS. The OpenAPI document gains `securitySchemes` + per-operation `security`. The
  Stage 3 gate that failed the anonymous surface now passes a regenerated scoped one.
- **Scopes + audit.** Per-command scopes are now **auto-derived** `pkg:vertical:read|write` from the
  verb (read for GET, write otherwise) when the binding omits one, with an explicit binding scope
  overriding — ergonomic, still default-deny at the token. The write rail folds into scope (a write
  verb's scope is a `:write` scope), `RACECAR_ALLOW_WRITES` retained as a global kill switch. Audit is
  split to keep the surfaces db-light: an `AuditLog` model **in the AS** records auth events (login
  success/failure, enrollment, recovery use) via a `record_event` helper, while the surfaces emit
  structured **log lines** for every per-call allow/deny decision. (Splitting the docs generators
  into `scaffold_surfaces_docs.py` kept the templates module under the size limit.)

## 0.12.0 - 2026-06-26

### Added
- **Two stacked skills that turn a CLI-compliant project into a deployable REST + MCP
  web service: `racecar-reshape-to-pypkg` and `racecar-create-server`.** `racecar-reshape-to-pypkg` (the shapes
  axis) migrates a project's packaging shape from `src/` to `pypkg/src/` with a
  dry-run-by-default, idempotent path-rewrite that repairs the references the move
  breaks (relative doc links, `__file__.parents[N]` anchors, the library pyproject);
  `racecar-upgrade` reuses it. `racecar-create-server` (the surfaces axis, which stacks on
  reshape) inserts an `api` cut vertex and then generates a Django 6 ASGI surface over
  it from one Interface Manifest (the CLI audit tree plus a `[tool.racecar.surface]`
  binding plus api signature introspection). The generated app is vertical-first: one
  Django app per vertical co-locates both surfaces over a single `commands.py` binding,
  and a single `apps/mcp.py` is the MCP endpoint. It runs as two ASGI processes, one
  per surface (REST on `api.*`, MCP on `mcp.*`), host-split at boot by per-surface settings,
  behind Apache. REST routes follow `/api/v1/<package>/<vertical-path>/<command>`;
  write verbs are off by default (`RACECAR_ALLOW_WRITES`). The same manifest
  also renders `docs/api/{manifest.json, openapi.json (OpenAPI 3.1.0), ENDPOINTS.md}`
  and a sitemap, so the spec cannot drift from the routes, and the OpenAPI document is
  built from the manifest rather than introspected from views (no DRF).
- **Doctrine and wiring for the above.** `GENERATION.md` (the generation pipeline, the
  manifest IR, the MCP wire conformance, the write rail), a `SURFACES.md` amendment
  (HTTP-delivered MCP is a route family in the surface, not a standalone `mcp.py`),
  and an `llm-summary` rule (the surface's endpoints source the brief's external
  surface from `docs/api/openapi.json` + `ENDPOINTS.md`). `install` and
  `sync_claude_md` register both skills.
- **racecar now gates its own changelog against `VERSION`.** A new `make check` step
  (`scripts/check_changelog.py`) fails when `CHANGELOG.md`'s newest entry does not
  match `VERSION`, so the per-version record cannot silently fall behind the code (the
  gap that left 0.10.6, 0.11.0, and 0.12.0 undocumented until now).

### Changed
- **`PACKAGING.md`'s Django dev-group reconciled to the real dependencies.** The web
  surface validates its generated OpenAPI with `openapi-spec-validator`, not
  `drf-spectacular`; there is no DRF in the generated app.

### Fixed
- **`check_dj_model_ref_as_string` no longer mishandles a repo named after its
  package.** It now excludes the repo root from the package index, so a repo directory
  sharing the package name cannot shadow the real package under a source root, and it
  guards non-UTF-8 reads. Previously such a repo could make the check scan `.venv` and
  crash on a non-UTF-8 dependency file.

## 0.11.0 - 2026-06-24

### Added
- **The packaging audit now flags a repo whose agent-instruction file never names
  racecar.** A `CLAUDE.md` / `AGENTS.md` that does not mention racecar is not portably
  opted in: a clone without the author's global `~/.claude` block sees nothing tying it
  to racecar. `check_optin` reports this as an advisory Finding. It stays silent when no
  agent file exists (racecar neither scaffolds nor demands a per-repo `CLAUDE.md`) and
  does a presence check only, never a path check.

## 0.10.6 - 2026-06-24

### Fixed
- **The build no longer hard-codes the author's path to the racecar checkout.**
  `racecar.mk` defaulted `RACECAR_ROOT` to a personal `$(HOME)/dev/...` path that was
  wrong on every adopter's machine but the author's. It now derives the location from
  the installed skill symlink (`readlink ~/.claude/skills/racecar`), stays
  `?=`-overridable, and makes `make sync` fail with a clear message when the checkout
  cannot be located.

## 0.10.5 - 2026-06-24

### Fixed
- **The build now aims the package-level checks at the actual package, not the folder
  above it.** racecar finds where your code lives (for the `pypkg` layout that is
  `pypkg/src/`) and then needs the package *inside* it (`pypkg/src/<yourpkg>/`) to run
  the CLI and coverage checks — the CLI audit imports the package, so it requires the
  directory with the `__init__.py`, not the namespace folder above it. The build was
  stopping at that outer folder (`PKG` defaulted to the source root for every layout).
  The `pypkg` layout was always wrong this way; a flat `src/` layout only happened to
  work because the source root and the package were the same directory. `racecar.mk` now
  descends to the package directory automatically for every layout (`src/<pkg>`,
  `pypkg/src/<pkg>`, nested Django apps), leaves the whole-tree (`.`) and flat cases
  alone, and still lets you override `PKG` by hand. The docs table already promised this;
  the build now matches it.

## 0.10.4 - 2026-06-23

### Fixed
- **The packaging check stopped silently passing a broken Makefile setup.** racecar's
  build is split in two: a shared `racecar.mk` (identical in every repo) and a thin
  `Makefile` that pulls it in with `include racecar.mk`. The check that verifies this only
  looked at whether `racecar.mk` existed on disk, not whether the `Makefile` actually
  included it. So when an upgrade copied `racecar.mk` in next to an old all-in-one
  `Makefile` that never included it, the shared build did nothing, the old Makefile kept
  running everything, and the check passed anyway. That broken state is now a hard failure
  (`racecar-mk-not-included`), separate from the gentler "this repo hasn't adopted the
  split yet" notice (`no-racecar-mk`). This is what let `racecar-upgrade` leave a custom
  Makefile in place instead of replacing it.

### Changed
- **`racecar-upgrade` now separates racecar's shared files from your project's own
  choices.** When the tool finds a difference between your repo and racecar, it used to
  lean toward keeping your version unless there was a strong reason to change it. That is
  right for things your project genuinely decided (its architecture, its naming, its extra
  build targets), but wrong for the files racecar ships identically to every repo (the
  shared `racecar.mk`, the check scripts, the tool config, the pre-commit hooks). For
  those, "different" just means "out of date," so the tool now always brings them current.
  Blurring the two is what let an old custom Makefile survive an upgrade. One specific
  consequence: an old repo keeps its whole build in a single Makefile, while the current
  design splits it into a shared half and a project half. The docs had implied `make sync`
  does that split for you. It does not; you do it by hand, and the docs now say so
  (`upgrade/README.md`, `upgrade/SKILL.md`, `PACKAGING.md`).

## 0.10.3 - 2026-06-23

### Fixed
- **The surfaces detector stopped raising a false alarm on a top-level entry point that
  only routes to sub-commands.** `check_surface_orchestration` looks for "verticals" — a
  feature exposed through a thin entry point sitting over a library. A top-level
  `__main__.py` that does nothing but dispatch to named sub-commands, living next to
  shared folders like `auth/` or `config/`, was mistaken for a vertical and then flagged
  for having no library beneath it. But that is a dispatcher plus shared code, not a
  vertical, so there was nothing wrong to report. The detector now stays quiet when the
  only entry point is a dispatcher that never reaches into a sibling it would be wiring
  together; an entry point that does reach a sibling is still flagged, because then it
  really is wiring one. Advisory only, never blocks a build. Found while upgrading an
  adopter project.

## 0.10.2 - 2026-06-23

### Changed
- **The llm-summary brief no longer carries `target.sha`.** The frontmatter snapshot
  SHA was circular (a brief is written before its own commit exists, so it could only
  ever name the parent) and low-value to the brief's reader, who asks the file what the
  system is, not which commit. `check_brief` no longer requires or validates it;
  `target.date` and `generator.version` remain as provenance. An existing brief that
  still carries a sha validates fine, the field is ignored.

## 0.10.1 - 2026-06-23

### Fixed
- **The Django string-relation gate no longer requires Django to boot.**
  `check_dj_model_ref_as_string` booted `manage.py shell` eagerly to resolve
  `INSTALLED_APPS`, so an architecture gate (a static import-graph concern) hard-failed
  whenever an inactive Django scaffold could not fully boot, for example a server that
  lists dev-only apps it does not install. The boot is now lazy: the static AST walk
  runs first, Django is booted only to classify violations that exist, and a boot that
  does not complete degrades to an UNCLASSIFIED report (exit 1 on the finding) instead
  of a configuration error (exit 2). A clean tree never boots. This restores
  discrete-first: the deterministic pass does all it can before any runtime step.
  Surfaced by a real adopter whose server could not boot in dev.

## 0.10.0 - 2026-06-23

The shape-and-Makefile release: the project shape is now inferred from the
filesystem, the Makefile is split into an owned thin file plus canonical
`racecar.mk`, and a speculative shared-context module was removed. Several
changes are breaking for existing adopters; `racecar-upgrade` reconciles them
without clobbering the owned `Makefile`.

### Added
- **Self-detecting `racecar.mk`.** A single canonical file, identical in every
  repo, computes the project shape (`src` / `pypkg` / `pypkg+server` / `server`)
  from the layout at make-time and selects the matching source variables, falling
  back to stock for any unrecognized layout (PACKAGING.md §7).
- **The Makefile fold.** Projects keep an owned thin `Makefile` that
  `include`s `racecar.mk`; project customization lives in the owned Makefile,
  canon lives in `racecar.mk`. There is no override registry.
- **Manifest-driven remote sync.** `sync_remote.py` (the no-clone `curl | python`
  path) now fetches a generated, drift-tested `scripts/racecar-manifest.txt`, so
  it delivers exactly what local `make sync` delivers, including checker
  implementation packages and the Django-only checks.
- **`make lint` over racecar's own scripts.** The framework now passes its own
  pylint bar at 10/10; the tooling is no longer self-exempt.
- **`pylint-django` as a canonical Django dev tool.** Required in the django group
  for any repo with a `manage.py`; `racecar.mk`'s lint loads it on the server only
  (`--load-plugins=pylint_django`), so a Django app stops false-positiving on every
  ORM idiom against the plain library config.
- **A `print-%` target in `racecar.mk`** (`make -s print-LIB_PYPROJECT`), so the
  pre-commit hooks read shape-derived config through Make.

### Changed
- **Breaking: shape is governed by what is on disk, not declared.** There is no
  `[tool.racecar].shape` entry; the Make build and `check_packaging.detect_shape`
  infer it identically, pinned by a coherence test.
- **Breaking: the Makefile contract.** Per-shape Makefile overrides are gone;
  upgrade replaces a project's build wiring with the owned-Makefile + `racecar.mk`
  split. `racecar-upgrade` performs this without touching your customization.
- `check_packaging` is reorganized into a thin entry plus a one-audit-per-module
  `check_packaging_rules/` package, composed by a plain `run_all`.
- Documentation checks are reference-driven (reachability from README / CLAUDE /
  SKILL seeds), not a fixed taxonomy. Dense lens content moved to named topic docs
  (`AXIOMS.md`, `WORKFLOW.md`, `PROTOCOL.md`, `SPEC.md`) with human-readable
  resolver READMEs.

### Fixed
- **Django is recognized by `manage.py`, never a bare `server/` directory.** A
  `server/` holding only a pyproject is no longer mis-detected as Django. Fixed in
  `detect_shape`, `racecar.mk`, and `init`.
- **The makefile-fold corruption.** `init --shape server` shipped a scaffold the
  build mis-detected as `src`, so `make sync` rewrote `racecar.mk` to the wrong
  shape; the self-detecting `racecar.mk` makes this impossible.
- **Remote/local sync drift.** `sync_remote` and `sync_scripts` carried divergent
  hardcoded script lists, and the remote path could not deliver packages; both now
  read one manifest.
- **The Makefile fold broke the config-deriving pre-commit hooks.** isort, black,
  import-linter, and validate-pyproject grepped the owned `Makefile` for
  `LIB_PYPROJECT` / `SERVER`, which the fold moved into `racecar.mk` (computed from
  the layout); they failed with "Could not read any configuration." They now read
  the resolved values via `make -s print-X`.
- **The Django string-relation gate was a false green on `pypkg+server`.**
  `check_dj_model_ref_as_string` looked for its pyproject, its `manage.py`, and the
  packages it walks all at the repo root, where on `pypkg+server` none of them are, so
  it skipped silently and passed over real broken models. It now takes the contract
  (library pyproject) and `manage.py` from `detect_shape` and globs each
  `root_package` from the tree, finding each wherever it lives. A good/bad
  `pypkg+server` fixture pair guards it. Surfaced by a real adopter upgrade.

### Removed
- **Breaking: `check_claude_shape`** (the last fixed-taxonomy documentation gate).
- **`repo_context.py`**, a shared role-map module that had no consumers; its
  source-root helpers returned to the surfaces detector, their origin.
- Stale synced scripts are now removed from an adopter on sync (so a repo that
  received `repo_context.py` has it cleaned up by the next `racecar-upgrade`).
