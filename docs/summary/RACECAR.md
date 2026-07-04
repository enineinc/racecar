---
generator:
  name: racecar-llm-summary
  version: "0.15.1"
target:
  repo: racecar
  date: 2026-07-02
bundle:
  - RACECAR.md

entities:
  - name: Lens
    case: none
    purpose: A deterministic review discipline applied to a repo (architecture, engineering hygiene, documentation).
    notes: Three lenses — arch-coherence, eng-review, doc-coherence. Each pairs a SKILL.md router with mechanical check scripts; llm-summary is a generator, not a lens.
  - name: Skill
    case: on_disk_managed
    purpose: A SKILL.md + README.md pointer pair the Claude Code harness invokes as /racecar-<name>.
    notes: 16 skill directories, each with a SKILL.md (router) and README.md (procedure). `./install` symlinks them into ~/.claude/skills/.
  - name: ProjectShape
    case: none
    purpose: The packaging shape a repo presents, governed by what is on disk.
    notes: The product of two independent presences (has_library, has_django) -- PYTHON_LIBRARY (src/<pkg>, pyproject at repo root) x DJANGO_PROJECT (server/manage.py). The 2x2 cells derive the labels src (lib only), src+server (lib x Django), server (Django only), and unknown (neither -- a no-shape finding, never silently "src"). The booleans are the primitive; the enum is a derived label. Detected in lockstep by check_packaging_rules/_shape.py and templates/classic/racecar.mk.
  - name: Surface
    case: none
    purpose: A thin adapter exposing the library's api over one transport.
    notes: cli (__main__), rest (api.*), mcp (mcp.*). A surface translates transport input, calls api, renders the result; it holds no orchestration policy.
  - name: MirrorTree
    case: content_tree
    purpose: A static template tree whose directory layout mirrors the generated server output 1:1.
    path_pattern: arch-coherence/templates/<tree>/<mirrored-output-path>
    count: 3 trees (django-project, server, authserver)
    validator: render_tree (scaffold_tree.py) + make check
  - name: InterfaceManifest
    case: on_disk_managed
    purpose: The derived JSON IR binding each exposed command to its api callable and arg schema.
    notes: Built from the CLI audit tree + the [tool.racecar.surface] binding + api signature introspection; written to server/docs/api/manifest.json. Never hand-maintained.
  - name: MechanicalCheck
    case: none
    purpose: A deterministic check script that fails a violation by naming file:line; the trust primitive (never an LLM as a gate).
    notes: >-
      e.g. check_packaging, check_surface_auth, check_surface_orchestration (advisory, surface-rooted), check_upward_imports,
      check_docs, check_subsystem_docs, check_file_placement, check_todo_format, check_changelog, check_brief, and the 0.15.0
      commit-time gate check_version_bump (a bumpable commit type must move the version home), plus check_config_drift and the
      racecar-run-only check_racecar_overrides (a repo has not forked canon). Run via make check and pre-commit; the version-bump
      gate runs at pre-commit's commit-msg stage. Vendored into adopter repos.
  - name: AuthorizationServer
    case: none
    purpose: The OAuth 2.1 + WebAuthn FIDO2 Authorization Server that secure-server generates.
    notes: A third ASGI process (auth.*), the only stateful component and DB owner; issues opaque bearer tokens the surfaces validate by introspection. Never JWT.
  - name: Cascade
    case: none
    purpose: The idempotent scaffolding skills that stand up a library and its surfaces.
    notes: Lifecycle cascade create-package -> create-server -> secure-server -> deploy-server (each ensures its precondition by invoking the one below; deploy-server is a TODO stub). create-server delegates the Django shell scaffold to the generic, reusable start-django-project (a standalone skill, not a cascade rung).
  - name: Baseline
    case: on_disk_managed
    purpose: The always-on standards force-loaded into every agent session.
    notes: shared/*.md (PERSONA, DRIFT, OPERATIONAL, OWNERSHIP, COMMITS, VOICE, GLOSSARY, VOCABULARY, TODO_FORMAT) plus the CLAUDE.md router; loaded by the session_load_standards hook.
  - name: Hook
    case: none
    purpose: A Claude Code SessionStart / PreCompact hook that force-loads the baseline and checks sync.
    notes: Seven hook scripts under hooks/, wired into a project's settings by sync_claude_md.py.

relationships:
  - from: Skill
    to: Lens
    cardinality: "M:N"
    notes: The review skills (arch-coherence, eng-review, doc-coherence) each front a lens; most skills are generators or utilities, not lenses.
  - from: Lens
    to: MechanicalCheck
    cardinality: "1:N"
    notes: A lens is enforced by one or more deterministic check scripts; the prose review is the reviewer-facing version of the same rules.
  - from: InterfaceManifest
    to: Surface
    cardinality: "1:N"
    owner_side: InterfaceManifest
    notes: The REST and MCP surfaces are a deterministic projection of one manifest; sibling surfaces are derived, never hand-written.
  - from: MirrorTree
    to: Surface
    cardinality: "1:N"
    notes: render_tree copies a mirror tree into the output; the generators overlay the manifest-interpolated files on top.
  - from: AuthorizationServer
    to: Surface
    cardinality: "1:N"
    notes: The AS issues the opaque token; each surface is a resource server that validates it by cached introspection, closed by default.
  - from: ProjectShape
    to: Surface
    cardinality: "1:N"
    notes: A surface exists only in the src+server / server shapes (a Django deployable); the src shape is library-only.

external_surface:
  cli_verbs:
    - verb: /racecar-arch-coherence
      module: arch-coherence/SKILL.md
      args: none
      behavior: Review the import DAG for acyclicity, direction, layer integrity, depth-plus-one; the lib->api->surfaces shape.
    - verb: /racecar-eng-review
      module: eng-review/SKILL.md
      args: none
      behavior: Code-quality review (Python/Django hygiene) wrapping gstack plan-eng-review when installed.
    - verb: /racecar-doc-coherence
      module: doc-coherence/SKILL.md
      args: none
      behavior: Documentation update + review (links, citations, vocabulary, prose-vs-code drift).
    - verb: /racecar-llm-summary
      module: llm-summary/SKILL.md
      args: none
      behavior: Generate this shareable brief (docs/summary/<REPO>.md).
    - verb: /racecar-create-package
      module: create-package/SKILL.md
      args: none
      behavior: Scaffold the src/<pkg> library (the greenfield root of the cascade).
    - verb: /racecar-start-django-project
      module: start-django-project/SKILL.md
      args: none
      behavior: Scaffold a vanilla, location-free Django shell at server/ (no surfaces, no auth).
    - verb: /racecar-create-server
      module: create-server/SKILL.md
      args: none
      behavior: Generate REST + MCP surfaces over src/<pkg>/api into server/, behind Apache.
    - verb: /racecar-secure-server
      module: secure-server/SKILL.md
      args: none
      behavior: Generate the OAuth 2.1 + WebAuthn FIDO2 Authorization Server (auth.*).
    - verb: /racecar-deploy-server
      module: deploy-server/SKILL.md
      args: none
      behavior: TODO stub — host/sysadmin deployment (TLS, processes, secrets); no code generation yet.
    - verb: /racecar-normalize
      module: normalize/SKILL.md
      args: none
      behavior: Audit a project against racecar canon.
    - verb: /racecar-upgrade
      module: upgrade/SKILL.md
      args: none
      behavior: Upgrade a repo to current racecar without clobbering local changes.
    - verb: /racecar-commit
      module: commit/SKILL.md
      args: none
      behavior: Author a conventional commit message + semver version bump.
    - verb: /racecar-commit-preflight
      module: commit-preflight/SKILL.md
      args: none
      behavior: Dry-run the pre-commit hooks before committing.
    - verb: /racecar-commit-decompose
      module: commit-decompose/SKILL.md
      args: none
      behavior: Split a working tree into a clean ordered commit series.
    - verb: /racecar-doctor
      module: doctor/SKILL.md
      args: none
      behavior: Verify racecar is installed and force-loaded here, with evidence (the load token).
    - verb: /racecar-expert-mode
      module: expert/SKILL.md
      args: "install | uninstall"
      behavior: Toggle the terse expert output overlay (scripts/expert_mode.py).
  library_exports:
    - name: make check
      module: Makefile
      signature: make check
      behavior: The local gate — check-docs + check-subsystem-docs + check-changelog + lint (pylint 10/10) + test (pytest) + check-brief.
    - name: make init
      module: scripts/init_project.py
      signature: make init ARGS=...
      behavior: Scaffold a new conforming project from templates/classic/.
    - name: make sync-scripts
      module: scripts/sync_scripts.py
      signature: make sync-scripts DEST=<path> [TEMPLATES=--templates]
      behavior: Sync the vendored check scripts into an adopter repo.
    - name: sync_remote
      module: scripts/sync_remote.py
      signature: curl ... sync_remote.py | python3 - --dest . --ref <tag>
      behavior: One-liner remote adoption — pull the check scripts + scaffolding from a racecar ref.
---

# Racecar — Knowledge Package

racecar is a deterministic code-review and scaffolding framework for Python/Django, delivered as Claude Code skills plus vendored check scripts. This brief is a portable snapshot for interviewing the system without source access. Cross-references use `§N.M`.

## §1. Map

### §1.1 Purpose

racecar turns engineering discipline into mechanical, reproducible checks so AI-assisted work stays trustworthy. Its thesis: deterministic checks decide; the model is the last, deferred stage and never a gate ("the detector must have lower entropy than the thing it watches," `shared/DRIFT.md`). It fights drift structurally — one home per rule, then automatic per-change checks, then periodic sweep.

The audience is the author (Vishal Apte) and the repos that adopt racecar: a portfolio of unrelated-domain projects governed by one canon. The user-facing primitives are **skills** (slash commands the Claude Code harness invokes), **lenses** (review disciplines), **mechanical checks** (scripts that fail a violation by file:line), and the **scaffolding cascade** (five skills that stand up a library and its REST/MCP surfaces). racecar is itself a racecar-governed repo: `make check` gates its own scripts to pylint 10/10.

### §1.2 Modules

| Module | Purpose |
| --- | --- |
| `arch-coherence/` | The architecture lens: import-DAG axioms, the lib→api→surfaces shape, packaging shapes, surface generation, auth doctrine, and the scaffold/check scripts. |
| `eng-review/` | The engineering-hygiene lens (Python/Django), wrapping gstack `plan-eng-review` when installed. |
| `doc-coherence/` | The documentation lens: link/citation/vocabulary checks + prose-vs-code review. |
| `llm-summary/` | The brief generator (this file) + `check_brief.py`. |
| `create-package/`, `create-server/`, `secure-server/`, `deploy-server/` | The scaffolding cascade (§2.7 flow 1). |
| `start-django-project/` | The generic, racecar-agnostic Django scaffold `create-server` delegates to. |
| `commit/`, `commit-preflight/`, `commit-decompose/` | Commit authoring, pre-commit dry-run, working-tree decomposition. |
| `normalize/`, `upgrade/`, `doctor/`, `expert/` | Adoption audit, non-clobbering upgrade, install verification, expert output overlay. |
| `shared/` | The always-on baseline (persona, drift, operational, ownership, commits, voice, glossary, vocabulary, TODO format). |
| `scripts/` | Cross-cutting scripts: init, sync, doctor, changelog/config-drift checks, claude.md wiring. |
| `templates/` | `classic/` (the project scaffold copied into adopters); `arch-coherence/templates/` holds the generation mirror trees. |
| `hooks/` | SessionStart / PreCompact hooks that force-load the baseline and check sync. |

### §1.3 Vendors

No paid SaaS, no cloud platform, no sibling local packages. The dev toolset is community/PSF/PyPA OSS only (pylint, black, isort, import-linter, pytest, mypy, pip-audit, pre-commit, validate-pyproject) — a deliberate governance rule (no VC-backed tooling, which excludes ruff) in `arch-coherence/PACKAGING.md`. The *generated* server pulls django + uvicorn at runtime, and the generated Authorization Server adds django-oauth-toolkit, py_webauthn, and django-oauth-toolkit-dcr; those are dependencies of racecar's output, not of racecar itself. gstack (the author's separate skill bundle) is an optional peer that eng-review wraps when present.

## §2. Implementation

### §2.1 Runtime

racecar is not a service. It has three runtime faces:

| Face | Entry point | State |
| --- | --- | --- |
| Skills (markdown) | `/racecar-<name>` invoked by the Claude Code harness; each `SKILL.md` routes to a `README.md`/lens doc | none — instructions loaded into an agent session |
| Mechanical checks (CLI) | `make check` (and pre-commit); individual `*.py` scripts run with the target project's interpreter | none — exit 0 clean, exit 1 prints file:line findings |
| Generators (CLI) | `scaffold_surfaces.py`, `scaffold_authserver.py`, `init_project.py`, `sync_scripts.py` | writes files into a target repo (`server/`, `src/`); idempotent |

The baseline is force-loaded every SessionStart by `hooks/session_load_standards.py` (wired by `./install` / `sync_claude_md.py`), so an agent opens any governed repo with the canon already in context. There is no server, no database, no scheduled job in racecar itself.

### §2.2 Entities

racecar's entities are mostly **conceptual primitives** (frontmatter `case: none`): a Lens, a Surface, a ProjectShape, a MechanicalCheck, the Cascade, the AuthorizationServer. The on-disk ones are the Skill pair (`SKILL.md` + `README.md`), the Baseline (`shared/*.md`), and the InterfaceManifest (`server/docs/api/manifest.json`). The one content tree is the **MirrorTree**: three template directories under `arch-coherence/templates/` whose layout matches the generated output 1:1. See frontmatter `entities` for the full set; there are no ORM models — racecar persists nothing of its own.

### §2.3 Relationships

```
Skill ─fronts─> Lens ─enforced by─> MechanicalCheck
InterfaceManifest ─projects─> Surface <─validates token─ AuthorizationServer
MirrorTree ─render_tree─> Surface
ProjectShape ─determines─> Surface (src has none; src+server / server do)

Cascade (each invokes the one below; each idempotent):
  create-package ─> start-django-project ─> create-server ─> secure-server ─> deploy-server
Library shape:  lib ─> api ─> { cli, rest, mcp }   (imports run the reverse; the graph is a DAG)
```

### §2.4 External surface

The surface is the **slash commands** (frontmatter `cli_verbs`, 16 skills) plus the **make targets / scaffold CLIs** (frontmatter `library_exports`). racecar exposes no HTTP routes, no MCP tools, and no library imports of its own — it is invoked as agent skills and as command-line checks/generators. The load-bearing entry is `make check` (the gate) and the cascade commands. The generators (`scaffold_surfaces.py --audit … --binding … --out server`; `scaffold_authserver.py --server … --issuer …`) are normally invoked *by* the create-server / secure-server skills, not directly. Adopter onboarding is `make sync-scripts DEST=<repo>` or the `sync_remote.py` curl one-liner.

### §2.5 Internal contracts

- **CLI audit JSON** — produced by `check_cli_commands.py --json <pkg>`, consumed by `scaffold_surfaces.py`. The enriched command tree is both the exposure allow-list and the arg schema (`oneOf` mutex groups are JSON-Schema).
- **Interface Manifest** — produced by `scaffold_surfaces.py::build_manifest` (audit + binding + api introspection), consumed by the surface templates; written to `server/docs/api/manifest.json`. The single source for OpenAPI + ENDPOINTS.
- **Surface binding** — `[tool.racecar.surface]` in `pyproject.toml` (JSON form also accepted): per-command api callable, method, and scope. `--scaffold-binding` emits a default-deny stub.
- **import-linter `layers` contract** — the one gated architectural contract (`[tool.importlinter]`); `check_surface_orchestration.py` is the advisory detector (exit 0 by default, `--strict` to fail) for surfaces reaching past `api`. Since 0.14.0 it is **surface-rooted**: it anchors only on the surfaces it can name or is told to map (`__main__.py` = cli, `mcp.py`/`mcp/` = mcp), with no structural guessing, so an ingestion-shaped package or a `sources/<protocol>` adapter is deliberately not a vertical and is not flagged (`arch-coherence/SURFACES.md §7`, `CLI.md`).
- **Commit-time gate** (0.15.0, adopter-facing via `templates/classic/pre-commit-config.yaml`) — `check_version_bump.py` (commit-msg stage) fails a feat/fix/perf/breaking commit when the version home is unchanged between index and HEAD, asserting a bump happened, not its magnitude (`shared/COMMITS.md`). `install-dev` installs both `pre-commit` and `commit-msg` hook types so the commit-msg gate fires. (A prose-punctuation dash gate shipped alongside it in 0.15.0 and was retired in 0.18.2: its false-positive rate exceeded its value; the em-dash rule is now a `shared/VOICE.md` voice convention, not a checker.)
- **Shape markers** — `pyproject.toml` (root) + `src/` + `server/manage.py` on disk; `detect_shape` (Python) and `racecar.mk` (Make) read them in lockstep, held by `test_sync_scripts.py`.
- **Resource-server auth rail** — `project/auth.py` validates a bearer token by RFC 7662 introspection against the AS; `check_surface_auth.py` fails a surface that ships anonymous or a command with no scope.

### §2.6 Configuration

- `VERSION` (repo root) — the single version home (0.15.0), used because racecar's `pyproject.toml` has no `[project].version`; gated against the CHANGELOG by `check_changelog.py` and, in adopters, against the commit type by `check_version_bump.py`.
- **No override registry by design.** `check_racecar_overrides.py` asserts a consuming repo declares no non-canon `[tool.racecar]` key and keeps a `racecar.mk` byte-identical to canon (customization lives in the owned `Makefile`, not a fork). The legitimate `[tool.racecar.*]` tables are the input bindings racecar's own checkers read — `surface` (scaffold_surfaces), `roles` (check_surface_orchestration), `subsystem-docs` (check_subsystem_docs); `[tool.racecar.overrides]` and any other key are flagged.
- `pyproject.toml` `[tool.racecar.surface]` — the surface binding; `[tool.racecar.subsystem-docs]` — `loc_threshold` / `exclude` for the subsystem-docs check; `[tool.importlinter]` — the layers contract; `[tool.pylint.MASTER].ignore-paths` — the one ignore key check_docs honors.
- Generated-server env (the output's config, not racecar's): `RACECAR_ALLOW_WRITES` (write rail, off by default), `AUTH_INTROSPECTION_URL` / `_CLIENT_ID` / `_CLIENT_SECRET` / `_CACHE_SECONDS` (resource-server introspection; unset → fail closed), `AUTH_ISSUER`.
- Generated-AS env: `AUTH_SERVER_ISSUER` (fails loud in prod if a placeholder), `WEBAUTHN_RP_ID` / `_ORIGIN` / `_ALLOWED_AAGUIDS` (fail-closed when empty) / `WEBAUTHN_PACKED_ROOT_CERTS` (attestation roots; unset → AAGUID advisory), `OAUTH2_ACCESS_TOKEN_EXPIRE_SECONDS`.

### §2.7 Flows

1. **Scaffolding cascade.** `create-package` scaffolds `src/<pkg>` → `create-server` invokes the generic `start-django-project` to lay down the vanilla `server/` shell (`render_tree(templates/django-project)`), then reads `src/<pkg>/api`, builds the manifest, copies `templates/server/` and overlays the per-vertical adapters → `secure-server` copies `templates/authserver/` and overlays `settings/auth.py` → `deploy-server` (TODO) ships it. Each step is idempotent; `create-server`/`secure-server` write only `server/` and **refuse if `src/<pkg>/api` is absent** (they never write `src/`).
2. **`make check` (the gate).** Runs check-docs, check-subsystem-docs, check-changelog, lint (pylint 10/10 at 100 cols), test (pytest), check-brief — in sequence; any failure names file:line. Mirrored per-change by pre-commit. Idempotent and read-only.
3. **Generated auth (runtime of the output).** Claude/MCP client → OAuth 2.1 auth-code + PKCE-S256 at the AS → WebAuthn hardware-key assertion gates `/o/authorize` → opaque token → REST/MCP surface validates by cached introspection + per-tool scope, closed by default. Fail-closed when introspection is unconfigured or unreachable (503).
4. **Adoption.** `make sync-scripts DEST=<repo>` (or `sync_remote.py` curl) copies the vendored check scripts; the adopter wires `make check` + pre-commit; `racecar-normalize` audits conformance; `racecar-upgrade` pulls newer racecar without clobbering local edits.

### §2.8 Seams

- **Skills** — add a behavior by adding a `<name>/SKILL.md` + `README.md` and wiring it in `install` + `sync_claude_md.py` (recent: `start-django-project/`, `deploy-server/`).
- **Mechanical checks** — add a `check_*.py` under `arch-coherence/scripts/` (auto-included by the `make lint`/`make check` globs); recent: `check_surface_auth.py`.
- **Packaging rules** — `check_packaging_rules/` is a rule package; add a `_rule.py` module + register it in `__init__.py`.
- **Mirror trees** — add a static generated file by dropping it into `arch-coherence/templates/{django-project,server,authserver}/` at its target path; `render_tree` (`scaffold_tree.py`) copies it. Manifest-interpolated files stay builder functions in `scaffold_surfaces_templates.py`.

### §2.9 Design decisions

- **Mechanical over heuristic; LLM-last.** Every gate is a deterministic script; the model never decides pass/fail. (`shared/DRIFT.md`, `shared/OWNERSHIP.md`.)
- **One home per rule.** Each rule lives in exactly one canonical doc; other docs link, never restate. Drift is fought by eliminating the surface first.
- **"surface" is canon; "face" retired.** `lib → api → surfaces {cli, rest, mcp}`; binding key `[tool.racecar.surface]`. (0.13.0, commit `d032a59`; superseded the `faces`/`FACES.md` vocabulary.)
- **Shape is the PYTHON_LIBRARY × DJANGO_PROJECT presence product.** `has_library × has_django` is the primitive; the enum (src / src+server / server / unknown) is the derived label, and `(neither)` is a no-shape finding, not a silent `src`. Governed by on-disk markers, no config flag; the `pypkg/` wrapper was removed in 0.13.0 (the library is canon root `src/<pkg>`). `server`-only (Django, no library) is in scope: a control-plane-only app or a raw scaffold. (commits `323fa77`, `d032a59`.)
- **The library is the architectural center; the ORM is confined to the control plane.** Agent-grade software is data-plane-dominant: the more useful the package, the smaller the ORM-governed fraction. So the library (`src/<pkg>`, Django-free) holds the high-volume data path, and the ORM is confined to the `server/` control plane (auth/config/audit, the AS's state), touching the data plane never. The `src/` vs `server/` split is that confinement made physical, which is what *forces* the layout rather than choosing it. Full argument in `MANIFESTO.md`; the forcing constraints in `arch-coherence/PACKAGING.md`.
- **The generation skills write zero bytes to `src/`.** `create-server` / `secure-server` / `deploy-server` read `src/<pkg>/api` and write only `server/`; the `api` seam is the author's arch-coherent code, verified and refused if absent, never synthesized by a skill (`arch-coherence/GENERATION.md`).
- **Mirror-tree generation.** Static bodies are real files under `arch-coherence/templates/` mirroring the output; `render_tree` copies + substitutes, generators overlay the interpolated files. (0.13.0; replaced inline string constants and the loader modules.)
- **Auth: OAuth 2.1 opaque bearer, never JWT; WebAuthn FIDO2 hardware keys; closed by default.** `DEFAULT_SCOPES=[]` overrides DOT's wide-open default; the resource rail fails closed when unconfigured. (`arch-coherence/AUTH.md`; 0.13.0.)
- **Filesystem-governed Makefile.** A thin owned `Makefile` includes a canonical `racecar.mk` that re-derives shape variables. (commit `fe654bf`.)

### §2.10 Operational

- **Install:** `./install` (in the racecar checkout) symlinks the skills into `~/.claude/skills/` and wires the SessionStart/PreCompact hooks; idempotent, refuses to clobber present-but-wrong files. `make doctor` (or `/racecar-doctor`) verifies the install with evidence (a load token reproduced from context).
- **Self-gate:** `make check` enforces pylint 10/10, 324 tests, and the doc + changelog + brief checks. `make arch` is not a racecar target — the arch *checks* are vendored into adopters, not run against racecar's own tooling. (As of 0.15.1 the lint stage is red: `check_surface_orchestration.py` rates 9.99/10 — `W0621` redefined `main`, `R0911` too-many-returns — a regression from the 0.14.0 rewrite; every other stage is green.)
- **Adopter gate:** `make check` + pre-commit in the consuming repo, using the synced scripts. Enforcement is local (pre-commit, make), never CI-as-gate; the owner authorizes, the tooling confirms.
- **No deploy, no schedule, no healthcheck** — racecar ships files, not a running service.

### §2.11 Weirdness

- **The `.py` files under `arch-coherence/templates/server/python/` are template assets, not modules.** They are syntactically valid Django code copied verbatim into a generated server; they reference `project.*` / django and would not import standalone. They are excluded from racecar's own lint/test (the globs scope to `scripts/`).
- **`detect_shape` is duplicated in Python and Make on purpose.** Make cannot import Python, so the shape logic lives in both `check_packaging_rules/_shape.py` and `templates/classic/racecar.mk`, kept identical by `test_sync_scripts.py`. The duplication is guarded, not eliminated.
- **The generated surfaces are database-light; the Authorization Server is the only stateful piece.** Surfaces validate tokens by HTTP introspection and never import the AS — so the import DAG stays clean and the surfaces hold no auth state.
- **The AAGUID hardware-key whitelist is advisory unless `WEBAUTHN_PACKED_ROOT_CERTS` is set.** Without attestation roots, py_webauthn trusts the self-reported AAGUID; the whitelist becomes a real hardware guarantee only when roots are configured (a logged warning fires otherwise).
- **`racecar-create-server` re-runs the whole tree.** Generation is copy + overlay, not patch; it replaces the vanilla single-module `settings.py`/`urls.py` with per-surface packages, and re-rendering a changed manifest does not prune a removed vertical's stale `apps/<v>/`.

## §3. Live access

racecar is a tooling/standards repo distributed as source (Claude Code skills + vendored scripts), not a deployed service. There is no hosted instance, no API to call, no credentials. Consumption is local: clone/symlink the checkout, run `./install`, invoke the skills, run `make check`.

### §3.1 Environments

N/A — no deployed instance. Local only: the racecar checkout + `~/.claude/skills/` symlinks.

### §3.2 Auth

N/A — no deployed instance. (The OAuth 2.1 + WebAuthn auth racecar *generates* is the output's surface, documented in `arch-coherence/AUTH.md` and §2.7 flow 3, not racecar's own.)

### §3.3 Operations

N/A — no deployed instance. The callable surface is the slash commands and make targets in §2.4 / frontmatter.

### §3.4 Rate limits

N/A — no deployed instance.

### §3.5 Errors

N/A — no deployed instance. Check scripts signal by exit code (0 clean, 1 with file:line findings).

### §3.6 SDKs

N/A — no deployed instance, no public API to wrap.

## Confidence

**Least confident**

- §2.4 (External surface): the `/racecar-expert-mode` verb name is inferred from the `expert/` skill dir + `scripts/expert_mode.py`; the exact slash-command string the harness registers was not directly sourced. Verify against `install` and `scripts/sync_claude_md.py`.
- §2.1 / §2.10 (Hooks): "seven hook scripts" is counted from `ls hooks/` (claude_racecar_hook.sh, compound-command-allow.sh, precompact_history.py, session_check_sync.py, session_compact_history.py, session_discover_cli.py, session_load_standards.py); which subset is actually wired by `sync_claude_md.py` into a consuming project's settings was not fully traced. Verify with `grep -n hook scripts/sync_claude_md.py`.
- §2.6 (Configuration): the generated-AS env var names (`WEBAUTHN_PACKED_ROOT_CERTS`, `AUTH_SERVER_ISSUER`) are sourced from `arch-coherence/templates/authserver/` and `scaffold_authserver.py`; the full set a real deployment must set before first enrollment was not exhaustively enumerated. Verify against `scaffold_authserver.py` `settings_auth_py`.
- §1.3 (Vendors): "no VC-backed tooling (excludes ruff)" is the stated governance rule in `PACKAGING.md`; that the dev toolset in `templates/classic/library-pyproject.toml` fully complies was spot-checked, not audited line by line. Verify against that file's `[dependency-groups]`.

**Not in this brief**

- Roadmap intent beyond the named TODO stubs (deploy-server, review-package/review-server, workspace polymorphism), the order of the planned 8-repo fleet migration, and any strategic priorities — unknown, ask user.
- Adoption metrics, who else uses racecar, and the bus factor — unknown, ask user.
