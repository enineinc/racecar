---
generator:
  name: racecar-llm-summary
  version: "0.22.0"
target:
  repo: racecar
  date: 2026-07-18
bundle:
  - RACECAR.md

entities:
  - name: Lens
    case: none
    purpose: A deterministic review discipline applied to a repo (architecture, engineering hygiene, documentation, hardware sizing).
    notes: Three review lenses — arch-coherence, eng-review, doc-coherence — each pairs a SKILL.md router with mechanical check scripts. sysadmin-hardware is a fourth lens that recommends rather than gates (an EC2 proposal, not pass/fail). llm-summary and docs-orchestrator are generators/orchestrators, not lenses.
  - name: Skill
    case: on_disk_managed
    purpose: A SKILL.md + README.md pointer pair the Claude Code harness invokes as /racecar-<name>.
    notes: 18 skill directories plus a top-level `racecar` router skill (root SKILL.md), each with a SKILL.md (router) and README.md (procedure). `./install` symlinks them into ~/.claude/skills/.
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
      check_docs, check_doc_graph (the pnode doc-graph DAG), check_subsystem_docs, check_file_placement, check_todo_format, check_changelog, check_brief,
      the 0.22.0 doc-spine checkers check_required_docs (the repo-root README/CLAUDE/brief tier) and check_content_blind (structural leak guard, no-op until opt-in),
      and the 0.15.0 commit-time gate check_version_bump (a bumpable commit type must move the version home), plus check_config_drift and the
      racecar-run-only check_racecar_overrides (a repo has not forked canon). Run via make check and pre-commit; the version-bump
      gate runs at pre-commit's commit-msg stage. Vendored into adopter repos via the sync manifest.
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
    notes: shared/*.md (PRINCIPLES, PERSONA, DRIFT, OPERATIONAL, OWNERSHIP, COMMITS, VOICE, GLOSSARY, VOCABULARY, TODO_FORMAT) plus the CLAUDE.md router; loaded by the session_load_standards hook.
  - name: Axiom
    case: none
    purpose: One of the twelve first principles every racecar rule, lens, and check derives from, split into known principles (P-01..P-05) and racecar principles (R-01..R-07).
    notes: Homed in shared/PRINCIPLES.md, each stated in five parts (axiom + rests-on + why + enforced-by + origin) so it is testable and credited. Known principles are the borrowed canon (P-01 acyclic dependencies, P-02 one home, P-03 reconcile-to-source, P-04 resolve-drift-at-the-largest-frame, P-05 idempotent-by-default); racecar principles are the stances racecar takes (R-01 a-detector-must-have-lower-entropy-than-what-it-watches, R-02 enforced-not-professed/the-enforced-contract-is-truth, R-03 determinism/model-last, R-04 scope honesty, R-05 ownership-not-delegable, R-06 help-not-law, R-07 agent-grade-software-is-data-plane-dominant). The file is itself DAG-ordered (P-01 applied to the axioms). MANIFESTO.md argues the why and credits the prior art each descends from.
  - name: Reconciliation
    case: none
    purpose: A scaffold that ties an engine's output to reference data as a fixed set of generic manifolds over a private catalog, replacing one golden test per model.
    notes: Homed in eng-review/RECONCILIATION.md. Three manifolds — tie (engine vs an authoritative oracle within tolerance), identity (an accounting/algebraic law inside the engine's own output), integrity (a reference surface's structural soundness). A tie's oracle is either a handcrafted synthetic checksum (crafted per transform for edges/corners, tracked, always-on) or a real reference surface (confidential, in the private gitignored catalog). The tracked tree names no model; the catalog instance and reference data stay outside version control (the security partition). This is P-02 (one home) applied to test artifacts, so hand-written test code stays O(1) in models while instances become catalog rows bounded by configs x transforms.
  - name: DocsPipeline
    case: none
    purpose: The re-runnable documentation pipeline racecar-docs composes from the existing generators and checkers, owning only the orchestration.
    notes: >-
      Four ordered stages (generate-missing -> regenerate the machine spine no-clobber-but-repair -> content-blindness gate -> coherence/link gate). A thin
      composer that re-implements nothing — the brief comes from llm-summary, the CLI/REST/MCP surface docs from arch-coherence's scaffold_surfaces_docs.py, the
      link/graph/subsystem/placement gates from doc-coherence. The machine spine lives inside sentinel-delimited regions (<!-- racecar:generated:<spine> start/end -->)
      that regeneration rewrites while preserving all hand narrative byte-for-byte. Homed in docs-orchestrator/ORCHESTRATION.md; driven by scripts/docs_orchestrate.py
      (stages 1-report, 3, 4), with the generative stages the agent's to author. New in 0.22.0.
  - name: ContentBlindness
    case: none
    purpose: A leak-prevention discipline for a repo published from a fresh history — its machine-checkable policy plus the structural guard that enforces it.
    notes: >-
      Declared in README.md frontmatter (content_blind, content_blind_exempt, content_blind_placeholders, optional content_blind_structural). The reusable guard
      docs-orchestrator/scripts/check_content_blind.py enforces the one tier that needs no private data — formulae and worked examples in prose must be written in
      variables, not numbers — and is a no-op until a repo opts in. Generalized from seshat's test_content_blind.py; one home in docs-orchestrator/CONTENT_BLINDNESS.md.
      The repo-specific blocklist tier stays in the consuming repo. New in 0.22.0.
  - name: Telemetry
    case: on_disk_managed
    purpose: An optional stdlib-only CLI resource probe plus its append-only JSONL log — the empirical half of the hardware-sizing lens.
    notes: >-
      sysadmin-hardware/lib/_telemetry.py, copied into a governed repo as <pkg>/_telemetry.py (the same offered-template shape as arch-coherence/lib/_cli.py) and
      attached at the one main() dispatch seam per __main__.py with a one-line wrap (run(main)), covering every subcommand. Off by default (RACECAR_TELEMETRY=1 to
      enable); never changes command behavior or output; failures are swallowed. One JSON record per invocation (command, argv, wall, CPU time, cores_used=cpu_total/wall,
      peak RSS, exit_status, workers, cpu_count) appended to ./.telemetry/usage.jsonl. Reduced to a per-command p50/p95/max profile by
      sysadmin-hardware/scripts/telemetry_profile.py. Schema in sysadmin-hardware/TELEMETRY.md. New in 0.21.0.
  - name: HardwareProposal
    case: none
    purpose: An evidence-defended EC2 instance proposal for a governed repo — a recommendation, not a pass/fail verdict.
    notes: >-
      The sysadmin-hardware lens (HARDWARE.md) reasons from two inputs — the Telemetry profile (what commands cost) and a four-surface structural review (concurrency
      model, compute engine, memory pattern, data footprint/growth, GPU, bound class) — to a primary pick, a priced alternatives ladder (step-down/primary/alt/step-up),
      a burstable-vs-sustained call, EBS sizing, and the single de-risking measurement that would justify stepping down a tier. Every claim ties to a profile number or a
      named code line; it refuses to assert and does not use the review lenses' Blocker/Ship vocabulary. Worked gfem reference in HARDWARE.md. New in 0.21.0.
  - name: Hook
    case: none
    purpose: A Claude Code SessionStart / PreCompact hook that force-loads the baseline and checks sync.
    notes: Seven hook scripts under hooks/, wired into a project's settings by sync_claude_md.py.

relationships:
  - from: Skill
    to: Lens
    cardinality: "M:N"
    notes: The review skills (arch-coherence, eng-review, doc-coherence, sysadmin-hardware) each front a lens; most skills are generators or utilities, not lenses.
  - from: Lens
    to: MechanicalCheck
    cardinality: "1:N"
    notes: A lens is enforced by one or more deterministic check scripts; the prose review is the reviewer-facing version of the same rules. (The sysadmin-hardware lens recommends rather than gates — its telemetry_profile.py reads, it does not fail.)
  - from: DocsPipeline
    to: MechanicalCheck
    cardinality: "1:N"
    notes: The orchestrator is a composer — it calls the checkers each lens already owns (check_docs, check_doc_graph, check_subsystem_docs, check_file_placement, check_required_docs, check_content_blind, check_brief) and re-implements none of them.
  - from: DocsPipeline
    to: ContentBlindness
    cardinality: "1:1"
    notes: The content-blindness gate is stage 3 of the pipeline; it runs immediately after the machine-spine regeneration so a generator that emitted a real figure fails before it can ship.
  - from: HardwareProposal
    to: Telemetry
    cardinality: "1:1"
    owner_side: HardwareProposal
    notes: The sizing proposal's empirical input is the telemetry profile; without a representative log the lens stops rather than guesses.
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
    - verb: /racecar-docs
      module: docs-orchestrator/SKILL.md
      args: none
      behavior: Run the whole documentation pipeline (generate missing docs, regenerate the machine spine no-clobber-but-repair, content-blindness gate, coherence gate); re-implements nothing. New in 0.22.0.
    - verb: /racecar-llm-summary
      module: llm-summary/SKILL.md
      args: none
      behavior: Generate this shareable brief (docs/summary/<REPO>.md).
    - verb: /racecar-sysadmin-hardware
      module: sysadmin-hardware/SKILL.md
      args: none
      behavior: Propose an EC2 instance type from evidence — the telemetry profile plus a four-surface structural review. Recommends, does not gate. New in 0.21.0.
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
      behavior: Author conventional commit(s) + semver bump; decomposes the working tree into a dependency-ordered series by default (0.20.0), emitting a runbook the owner runs via scripts/rc-commit.sh.
    - verb: /racecar-commit-preflight
      module: commit-preflight/SKILL.md
      args: none
      behavior: Dry-run the pre-commit hooks before committing.
    - verb: /racecar-commit-decompose
      module: commit-decompose/SKILL.md
      args: none
      behavior: Alias of /racecar-commit (0.20.0) — decomposition is now that skill's default; the alias resolves for old muscle memory and adds no behavior.
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
      behavior: The local gate — check-docs + check-doc-graph + check-subsystem-docs + check-changelog + check-required-docs + check-content-blind + lint (pylint 10/10) + test (pytest) + check-brief.
    - name: make docs
      module: docs-orchestrator/scripts/docs_orchestrate.py
      signature: make docs
      behavior: Run the documentation orchestration pipeline (0.22.0) — the deterministic report + gate stages; the generative stages are agent-driven.
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
    - name: rc-commit.sh
      module: scripts/rc-commit.sh
      signature: scripts/rc-commit.sh <message-file> [path ...]
      behavior: The owner's commit tool (0.20.0) — stage the named paths, then `git commit -eF` opens the editor seeded from a drafted message so nothing lands unreviewed; the runbook racecar-commit emits calls it.
  scripts:
    - name: docs_orchestrate.py
      path: docs-orchestrator/scripts/docs_orchestrate.py
      purpose: Run the documentation pipeline's deterministic gates (required-docs report, content-blindness, coherence/link) and return one exit code; resolves each checker whether under a lens dir or synced flat into an adopter's scripts/.
      invocation: make docs
    - name: check_required_docs.py
      path: docs-orchestrator/scripts/check_required_docs.py
      purpose: Enforce the repo-root doc spine — README with pnode frontmatter, CLAUDE with an H2, the docs/summary/<REPO>.md brief (opt-out via [tool.racecar.required-docs] brief=false).
      invocation: make check (check-required-docs)
    - name: check_content_blind.py
      path: docs-orchestrator/scripts/check_content_blind.py
      purpose: Structural content-blindness guard parameterized by README frontmatter — a no-op until a repo opts in; fails the pipeline on a numeric figure in prose that should be a variable.
      invocation: make check (check-content-blind)
    - name: telemetry_profile.py
      path: sysadmin-hardware/scripts/telemetry_profile.py
      purpose: Reduce a telemetry JSONL log to a per-command p50/p95/max profile sorted by peak RSS — the hardware lens's empirical input.
      invocation: manual
    - name: init_project.py
      path: scripts/init_project.py
      purpose: Scaffold a new conforming project from templates/classic/.
      invocation: make init
    - name: sync_scripts.py
      path: scripts/sync_scripts.py
      purpose: Sync the vendored check scripts (racecar-manifest.txt) into an adopter repo; deletes retired scripts on the next sync.
      invocation: make sync-scripts
    - name: sync_remote.py
      path: scripts/sync_remote.py
      purpose: One-liner remote adoption — pull the check scripts + scaffolding from a racecar ref over curl.
      invocation: curl ... | python3 -
    - name: sync_claude_md.py
      path: scripts/sync_claude_md.py
      purpose: Wire the SessionStart/PreCompact hooks and the racecar pointer block into a project's Claude settings.
      invocation: install
    - name: doctor.py
      path: scripts/doctor.py
      purpose: Verify racecar is installed, wired, and force-loaded, layer by layer, with a load-token challenge.
      invocation: make doctor
    - name: check_version_bump.py
      path: scripts/check_version_bump.py
      purpose: Commit-msg gate — a feat/fix/perf/breaking commit must move the version home between index and HEAD.
      invocation: pre-commit (commit-msg)
    - name: check_changelog.py
      path: scripts/check_changelog.py
      purpose: Gate the VERSION home against a matching CHANGELOG entry.
      invocation: make check (check-changelog)
    - name: check_config_drift.py
      path: scripts/check_config_drift.py
      purpose: Report advisory drift of an adopter's config (e.g. the gitleaks / djhtml hooks whose binaries are non-pip and kept out of the required set).
      invocation: manual / advisory
---

# Racecar — Knowledge Package

racecar is a deterministic code-review and scaffolding framework for Python/Django, delivered as Claude Code skills plus vendored check scripts. This brief is a portable snapshot for interviewing the system without source access. Cross-references use `§N.M`.

## §1. Map

### §1.1 Purpose

racecar turns engineering discipline into mechanical, reproducible checks so AI-assisted work stays trustworthy. Its thesis: deterministic checks decide; the model is the last, deferred stage and never a gate ("the detector must have lower entropy than the thing it watches," `shared/DRIFT.md`). It fights drift structurally — one home per rule, then automatic per-change checks, then periodic sweep.

The audience is the author (Vishal Apte) and the repos that adopt racecar: a portfolio of unrelated-domain projects governed by one canon. The user-facing primitives are **skills** (slash commands the Claude Code harness invokes), **lenses** (review disciplines), **mechanical checks** (scripts that fail a violation by file:line), and the **scaffolding cascade** (skills that stand up a library and its REST/MCP surfaces). racecar is itself a racecar-governed repo: `make check` gates its own scripts to pylint 10/10.

### §1.2 Modules

| Module | Purpose |
| --- | --- |
| `arch-coherence/` | The architecture lens: import-DAG axioms, the lib→api→surfaces shape, packaging shapes, surface generation, auth doctrine, and the scaffold/check scripts. |
| `eng-review/` | The engineering-hygiene lens (Python/Django), wrapping gstack `plan-eng-review` when installed; carries the `RECONCILIATION.md` companion (manifolds-over-a-private-catalog testing) loaded on demand for reconciliation tests/fixtures. |
| `doc-coherence/` | The documentation lens: link/citation/vocabulary/graph checks + prose-vs-code review. |
| `docs-orchestrator/` | The docs orchestrator (`/racecar-docs`, 0.22.0): composes the generators + checkers into one re-runnable pipeline; owns only the required-docs manifest and the content-blindness contract. |
| `sysadmin-hardware/` | The hardware-sizing lens (`/racecar-sysadmin-hardware`, 0.21.0): the `_telemetry` CLI probe + `telemetry_profile.py` reader + the evidence-based EC2 proposal method (`HARDWARE.md`). |
| `llm-summary/` | The brief generator (this file) + `check_brief.py`. |
| `create-package/`, `create-server/`, `secure-server/`, `deploy-server/` | The scaffolding cascade (§2.7 flow 1). |
| `start-django-project/` | The generic, racecar-agnostic Django scaffold `create-server` delegates to. |
| `commit/`, `commit-preflight/`, `commit-decompose/` | Commit authoring, pre-commit dry-run, working-tree decomposition. |
| `normalize/`, `upgrade/`, `doctor/`, `expert/` | Adoption audit, non-clobbering upgrade, install verification, expert output overlay. |
| `shared/` | The always-on baseline: the twelve first principles (`PRINCIPLES.md`, known P-01..P-05 and racecar R-01..R-07) plus persona, drift, operational, ownership, commits, voice, glossary, vocabulary, TODO format. |
| `scripts/` | Cross-cutting scripts: init, sync, doctor, changelog/config-drift/version-bump checks, claude.md wiring, the `rc-commit.sh` owner helper. |
| `templates/` | `classic/` (the project scaffold copied into adopters); `arch-coherence/templates/` holds the generation mirror trees. |
| `hooks/` | SessionStart / PreCompact hooks that force-load the baseline and check sync. |

### §1.3 Vendors

No paid SaaS, no cloud platform, no sibling local packages. The canonical dev toolset (thirteen tools, `arch-coherence/PACKAGING.md` §6) is community/PSF/PyPA OSS only: black, isort, pylint, mypy, pytest, pytest-cov, pytest-xdist, pip-audit, pre-commit (the nine mainstream de-facto-canon tools), plus import-linter, validate-pyproject, djhtml, and the gitleaks secret-scan binary. `pytest-xdist` ships in the dev group but parallelism is never canon-default (0.18.0): the owning repo opts in via `PYTEST_ARGS := -n auto`. This is a deliberate governance rule — no VC-backed tooling, which excludes ruff. The *generated* server pulls django + uvicorn at runtime, and the generated Authorization Server adds django-oauth-toolkit, py_webauthn, and django-oauth-toolkit-dcr; those are dependencies of racecar's output, not of racecar itself. The `_telemetry` probe is stdlib-only (0.21.0), so the hardware lens adds no dependency to a governed repo. gstack (the author's separate skill bundle) is an optional peer that eng-review wraps when present.

## §2. Implementation

### §2.1 Runtime

racecar is not a service. It has three runtime faces:

| Face | Entry point | State |
| --- | --- | --- |
| Skills (markdown) | `/racecar-<name>` invoked by the Claude Code harness; each `SKILL.md` routes to a `README.md`/lens doc | none — instructions loaded into an agent session |
| Mechanical checks + orchestration (CLI) | `make check` / `make docs` (and pre-commit); individual `*.py` scripts run with the target project's interpreter | none — exit 0 clean, exit 1 prints file:line findings |
| Generators (CLI) | `scaffold_surfaces.py`, `scaffold_authserver.py`, `init_project.py`, `sync_scripts.py` | writes files into a target repo (`server/`, `src/`); idempotent |

The baseline is force-loaded every SessionStart by `hooks/session_load_standards.py` (wired by `./install` / `sync_claude_md.py`), so an agent opens any governed repo with the canon already in context. There is no server, no database, no scheduled job in racecar itself. The one runtime artifact racecar *offers* (never runs) is the `_telemetry` probe (§2.2, entity `Telemetry`): stdlib-only, copied into a governed repo, off by default, appending JSONL to `./.telemetry/usage.jsonl` only when `RACECAR_TELEMETRY=1`.

### §2.2 Entities

racecar's entities are mostly **conceptual primitives** (frontmatter `case: none`): a Lens, a Surface, a ProjectShape, a MechanicalCheck, the Cascade, the AuthorizationServer, an **Axiom** (one of the twelve first principles, split known P-01..P-05 and racecar R-01..R-07, `shared/PRINCIPLES.md`), **Reconciliation** (the manifolds-over-a-private-catalog testing scaffold, `eng-review/RECONCILIATION.md`), the **DocsPipeline** (the thin docs orchestrator, 0.22.0), **ContentBlindness** (the leak-prevention contract, 0.22.0), and the **HardwareProposal** (the evidence-based EC2 sizing, 0.21.0). The on-disk ones are the Skill pair (`SKILL.md` + `README.md`), the Baseline (`shared/*.md`), the InterfaceManifest (`server/docs/api/manifest.json`), and **Telemetry** (the `_telemetry` probe + its `./.telemetry/usage.jsonl` log, 0.21.0). The one content tree is the **MirrorTree**: three template directories under `arch-coherence/templates/` whose layout matches the generated output 1:1. See frontmatter `entities` for the full set; there are no ORM models — racecar persists nothing of its own (the telemetry log lives in the *governed* repo, not in racecar).

### §2.3 Relationships

```
Skill ─fronts─> Lens ─enforced by─> MechanicalCheck
DocsPipeline ─composes─> MechanicalCheck (check_docs, check_doc_graph, check_subsystem_docs,
                          check_file_placement, check_required_docs, check_content_blind, check_brief)
DocsPipeline ─stage 3 gate─> ContentBlindness
HardwareProposal ─reads─> Telemetry (profile) + the four surfaces (structural review)
InterfaceManifest ─projects─> Surface <─validates token─ AuthorizationServer
MirrorTree ─render_tree─> Surface
ProjectShape ─determines─> Surface (src has none; src+server / server do)

Cascade (each invokes the one below; each idempotent):
  create-package ─> start-django-project ─> create-server ─> secure-server ─> deploy-server
Library shape:  lib ─> api ─> { cli, rest, mcp }   (imports run the reverse; the graph is a DAG)
```

### §2.4 External surface

The surface is the **slash commands** (frontmatter `cli_verbs`, 18 skills) plus the **make targets / scaffold CLIs** (frontmatter `library_exports`) and the **operational scripts under `scripts/`** and the lens `scripts/` dirs (frontmatter `scripts`). racecar exposes no HTTP routes, no MCP tools, and no library imports of its own — it is invoked as agent skills and as command-line checks/generators. The load-bearing entries are `make check` (the gate), `make docs` (the documentation pipeline, 0.22.0), and the cascade commands. The generators (`scaffold_surfaces.py --audit … --binding … --out server`; `scaffold_authserver.py --server … --issuer …`) are normally invoked *by* the create-server / secure-server skills, not directly. Adopter onboarding is `make sync-scripts DEST=<repo>` or the `sync_remote.py` curl one-liner; the sync manifest (`scripts/racecar-manifest.txt`) is the vendored-script set, which now includes the three docs-orchestrator scripts.

### §2.5 Internal contracts

- **CLI audit JSON** — produced by `check_cli_commands.py --json <pkg>`, consumed by `scaffold_surfaces.py`. The enriched command tree is both the exposure allow-list and the arg schema (`oneOf` mutex groups are JSON-Schema).
- **Interface Manifest** — produced by `scaffold_surfaces.py::build_manifest` (audit + binding + api introspection), consumed by the surface templates and `scaffold_surfaces_docs.py`; written to `server/docs/api/manifest.json`. The single source for OpenAPI + ENDPOINTS.
- **Surface binding** — `[tool.racecar.surface]` in `pyproject.toml` (JSON form also accepted): per-command api callable, method, and scope. `--scaffold-binding` emits a default-deny stub.
- **import-linter `layers` contract** — the one gated architectural contract (`[tool.importlinter]`); `check_surface_orchestration.py` is the advisory detector (exit 0 by default, `--strict` to fail) for surfaces reaching past `api`. Since 0.14.0 it is **surface-rooted**: it anchors only on the surfaces it can name or is told to map (`__main__.py` = cli, `mcp.py`/`mcp/` = mcp), with no structural guessing (`arch-coherence/SURFACES.md §7`, `CLI.md`).
- **Commit-time gate** (0.15.0, adopter-facing via `templates/classic/pre-commit-config.yaml`) — `check_version_bump.py` (commit-msg stage) fails a feat/fix/perf/breaking commit when the version home is unchanged between index and HEAD, asserting a bump happened, not its magnitude (`shared/COMMITS.md`). `install-dev` installs both `pre-commit` and `commit-msg` hook types so the commit-msg gate fires.
- **Required-docs manifest** (0.22.0, `docs-orchestrator/ORCHESTRATION.md`) — split by owner so no rule is stated twice: `check_required_docs.py` owns the repo-root tier (README+pnode, CLAUDE+H2, the brief), while `doc-coherence`'s `check_subsystem_docs.py` owns the subsystem tier (README+CLAUDE per import-linter layer); the two sets do not overlap. The orchestrator runs both and restates neither.
- **Content-blindness policy** (0.22.0, `docs-orchestrator/CONTENT_BLINDNESS.md`) — the README frontmatter keys (`content_blind`, `content_blind_exempt`, `content_blind_placeholders`, optional `content_blind_structural`) parameterize `check_content_blind.py` entirely; the guard is a no-op until a repo opts in.
- **Generated-doc sentinel regions** (0.22.0) — the machine spine inside a mixed doc lives between `<!-- racecar:generated:<spine> start -->` / `end` sentinels; the orchestrator's no-clobber-but-repair rewrites only the text between them and preserves every character outside byte-for-byte (the brief is the exception, whose sub-generator owns its own preserve-body lifecycle).
- **Telemetry record** (0.21.0, `sysadmin-hardware/TELEMETRY.md`) — one JSON object per CLI invocation, produced by `<pkg>/_telemetry.py`'s `run(main)` wrap, consumed by `telemetry_profile.py`. Keys: `ts_start`/`ts_end`, `command`, `module`, `subcommand`, `argv`, `wall_s`, `cpu_user_s`/`cpu_sys_s`/`cpu_total_s`, `cores_used` (`cpu_total/wall`), `peak_rss_mb`, `io_read_blocks`/`io_write_blocks`, `workers`, `cpu_count`, `exit_status`, `pid`, `platform`. Append-only JSONL at `./.telemetry/usage.jsonl`.
- **Shape markers** — `pyproject.toml` (root) + `src/` + `server/manage.py` on disk; `detect_shape` (Python) and `racecar.mk` (Make) read them in lockstep, held by `test_sync_scripts.py`.
- **gitleaks secret scan** (0.16.0, adopter-facing via `templates/classic/pre-commit-config.yaml`) — a `gitleaks` hook runs first in the pre-commit set, reading the index directly (`--staged`) and redacting hits (`--redact`); kept out of `check_packaging`'s required-hooks set like `djhtml` because it depends on a non-pip binary (its absence is advisory config drift, not a blocker).
- **Resource-server auth rail** — `project/auth.py` validates a bearer token by RFC 7662 introspection against the AS; `check_surface_auth.py` fails a surface that ships anonymous or a command with no scope.

### §2.6 Configuration

- `VERSION` (repo root) — the single version home (0.15.0), used because racecar's `pyproject.toml` has no `[project].version`; gated against the CHANGELOG by `check_changelog.py` and, in adopters, against the commit type by `check_version_bump.py`.
- **No override registry by design.** `check_racecar_overrides.py` asserts a consuming repo declares no non-canon `[tool.racecar]` key and keeps a `racecar.mk` byte-identical to canon. The legitimate `[tool.racecar.*]` tables are the input bindings racecar's own checkers read — `surface` (scaffold_surfaces), `roles` (check_surface_orchestration), `subsystem-docs` (check_subsystem_docs), and `required-docs` (check_required_docs, `brief = false` to opt a repo out of the brief requirement, 0.22.0); `[tool.racecar.overrides]` and any other key are flagged.
- `pyproject.toml` `[tool.racecar.surface]` — the surface binding; `[tool.racecar.subsystem-docs]` — `loc_threshold` / `exclude` for the subsystem-docs check; `[tool.racecar.required-docs]` — `brief` toggle (0.22.0); `[tool.importlinter]` — the layers contract; `[tool.pylint.MASTER].ignore-paths` — the one ignore key check_docs / check_doc_graph honor.
- `RACECAR_TELEMETRY` (0.21.0) — off by default; `=1` in the governed repo's environment switches the `_telemetry` probe on (dotenv-at-entrypoints convention). Storage is `./.telemetry/usage.jsonl`; the probe never changes behavior and swallows its own failures.
- README frontmatter `content_blind` / `content_blind_exempt` / `content_blind_placeholders` / `content_blind_structural` (0.22.0) — a governed repo's opt-in content-blindness policy; unset means the gate is a no-op.
- Generated-server env (the output's config, not racecar's): `RACECAR_ALLOW_WRITES` (write rail, off by default), `AUTH_INTROSPECTION_URL` / `_CLIENT_ID` / `_CLIENT_SECRET` / `_CACHE_SECONDS` (resource-server introspection; unset → fail closed), `AUTH_ISSUER`.
- Generated-AS env: `AUTH_SERVER_ISSUER` (fails loud in prod if a placeholder), `WEBAUTHN_RP_ID` / `_ORIGIN` / `_ALLOWED_AAGUIDS` (fail-closed when empty) / `WEBAUTHN_PACKED_ROOT_CERTS` (attestation roots; unset → AAGUID advisory), `OAUTH2_ACCESS_TOKEN_EXPIRE_SECONDS`.

### §2.7 Flows

1. **Scaffolding cascade.** `create-package` scaffolds `src/<pkg>` → `create-server` invokes the generic `start-django-project` to lay down the vanilla `server/` shell (`render_tree(templates/django-project)`), then reads `src/<pkg>/api`, builds the manifest, copies `templates/server/` and overlays the per-vertical adapters → `secure-server` copies `templates/authserver/` and overlays `settings/auth.py` → `deploy-server` (TODO) ships it. Each step is idempotent; `create-server`/`secure-server` write only `server/` and **refuse if `src/<pkg>/api` is absent** (they never write `src/`).
2. **`make check` (the gate).** Runs check-docs, check-doc-graph, check-subsystem-docs, check-changelog, check-required-docs, check-content-blind, lint (pylint 10/10 at 100 cols), test (pytest), check-brief — in sequence; any failure names file:line. Mirrored per-change by pre-commit. Idempotent and read-only.
3. **Docs orchestration** (0.22.0, `make docs`). Four ordered stages: (1) generate the missing required docs (stub the skeleton, drive `/racecar-llm-summary` for a missing brief); (2) regenerate the machine spine — the brief frontmatter and the CLI/REST/MCP surface docs — no-clobber-but-repair inside the sentinel regions; (3) the content-blindness gate (`check_content_blind.py`, a no-op until opt-in); (4) the coherence/link gate (`check_docs`, `check_doc_graph`, `check_subsystem_docs`, `check_file_placement`). `docs_orchestrate.py` runs the deterministic stages (1-report, 3, 4) and returns one exit code; re-running with no source change is a no-op (P-05).
4. **Hardware sizing** (0.21.0, `/racecar-sysadmin-hardware`). Switch on `_telemetry` (`RACECAR_TELEMETRY=1`) over a representative period → `telemetry_profile.py` reduces the log to per-command p50/p95/max sorted by peak RSS → review the four surfaces for six structural signals (concurrency floor, compute engine/GIL, memory pattern, data footprint/growth, GPU, bound class) → walk the reasoning chain (latency gate → binding constraint → cores reconcile → architecture family → EBS → de-risking measurement) → emit an EC2 proposal with a priced alternatives ladder. A proposal without measured peak-command data is refused, not guessed.
5. **Generated auth (runtime of the output).** Claude/MCP client → OAuth 2.1 auth-code + PKCE-S256 at the AS → WebAuthn hardware-key assertion gates `/o/authorize` → opaque token → REST/MCP surface validates by cached introspection + per-tool scope, closed by default. Fail-closed when introspection is unconfigured or unreachable (503).
6. **Adoption.** `make sync-scripts DEST=<repo>` (or `sync_remote.py` curl) copies the vendored check scripts; the adopter wires `make check` + pre-commit; `racecar-normalize` audits conformance; `racecar-upgrade` pulls newer racecar without clobbering local edits.

### §2.8 Seams

- **Skills** — add a behavior by adding a `<name>/SKILL.md` + `README.md` and wiring it in `install` + `sync_claude_md.py` + the `CLAUDE.md` resolver + root `SKILL.md` (recent: `docs-orchestrator/`, `sysadmin-hardware/`).
- **Mechanical checks** — add a `check_*.py` under a lens `scripts/` dir (auto-included by the `make lint`/`make check` globs); recent: `check_required_docs.py`, `check_content_blind.py` (docs-orchestrator).
- **Docs pipeline** — the orchestrator resolves each checker whether it lives under a lens dir or is synced flat into an adopter's `scripts/`; a new gate is added by registering its resolver in `docs_orchestrate.py`, not by re-implementing the check.
- **Telemetry** — the probe attaches at the one `main()` dispatch seam per `__main__.py` with `run(main)`; a governed repo adds coverage of a new subcommand for free (the wrap is uniform).
- **Packaging rules** — `check_packaging_rules/` is a rule package; add a `_rule.py` module + register it in `__init__.py`.
- **Mirror trees** — add a static generated file by dropping it into `arch-coherence/templates/{django-project,server,authserver}/` at its target path; `render_tree` (`scaffold_tree.py`) copies it. Manifest-interpolated files stay builder functions in `scaffold_surfaces_templates.py`.

### §2.9 Design decisions

- **The twelve principles are the derivation root, split known vs racecar.** `shared/PRINCIPLES.md` names the first principles every rule, lens, and check descends from: five **known principles** (P-01..P-05, the borrowed canon) and seven **racecar principles** (R-01..R-07, the stances racecar takes). Each is stated in five parts (axiom, rests-on, why, enforced-by, origin), and the file is itself DAG-ordered. `MANIFESTO.md` argues the why and states plainly that racecar originates none of them (DRY, the Acyclic Dependencies Principle, Parnas, Lakos, Dijkstra, Deming, Lehman, Cunningham): the wager is enforcing borrowed wisdom together without drift, unproven at fleet scale, not originality.
- **The docs orchestrator is a thin composer that re-implements nothing** (0.22.0, commit `c3d85b2`). `/racecar-docs` sequences the existing generators and checkers — the brief from `llm-summary`, the surface docs from `arch-coherence`'s `scaffold_surfaces_docs.py`, the link/graph/subsystem/placement gates from `doc-coherence` — and owns only three things nothing else does: the required-docs manifest, the content-blindness contract, and the no-clobber-but-repair generation contract. Leaving a drifted machine spine in place is a failure, not a courtesy: the spine is re-derived every run while hand narrative is preserved byte-for-byte (`docs-orchestrator/ORCHESTRATION.md`).
- **Content-blindness is one machine-checkable contract** (0.22.0). Generalized from seshat's `test_content_blind.py`: a repo published from a fresh history declares its policy in README frontmatter and points to the one-home rule rather than restating it; the reusable guard enforces only the structural tier that needs no private data (formulae written in variables, not numbers) and is a no-op until opt-in. The gate runs immediately after spine regeneration, so a generator that emitted a real figure fails the pipeline (`docs-orchestrator/CONTENT_BLINDNESS.md`).
- **Hardware sizing is defended from evidence, not asserted** (0.21.0, commit `0eeee17`). The `sysadmin-hardware` lens ties every claim to a telemetry number or a named code line and emits a recommendation, not a Blocker/Ship verdict. The empirical half is `_telemetry`: stdlib-only, off by default (`RACECAR_TELEMETRY=1`), attached at one `main()` seam, swallowing its own failures — the same offered-template, opt-in shape as `arch-coherence/lib/_cli.py`. A sizing without measured peak-command data is refused (`sysadmin-hardware/HARDWARE.md`, `TELEMETRY.md`).
- **Reconciliation as a scaffold, not golden-per-model.** `eng-review/RECONCILIATION.md` encodes engine-to-reference testing as three generic manifolds (tie / identity / integrity) over a private, gitignored catalog. The security partition (tracked code names no model; reference data stays out of version control) and the bounded-test-surface corollary of P-02 (test code O(1) in models; instances = configs x transforms as catalog rows) both fall out of it.
- **Identity and token model recorded as an ADR.** `arch-coherence/adr/adr-identity-and-token-model.md` fixes the opaque-bearer + introspection identity decision as a durable architectural record. (commit `86739b1`.)
- **The documentation is itself a checked DAG.** `doc-coherence/DOC_GRAPH.md` + `check_doc_graph.py` require every non-CLAUDE, non-SKILL doc to declare its parent once in `pnode` frontmatter; children and peers are derived, never stored, and the graph is held acyclic (P-01 and P-02 turned on the docs themselves). The reviewer-facing arch lens was renamed `AXIOMS.md` → `CHECKS.md` in the same pass.
- **Mechanical over heuristic; LLM-last.** Every gate is a deterministic script; the model never decides pass/fail. (`shared/DRIFT.md`, `shared/OWNERSHIP.md`, R-01/R-03.)
- **One home per rule.** Each rule lives in exactly one canonical doc; other docs link, never restate. Drift is fought by eliminating the surface first. (P-02.) The 0.22.0 required-docs split — repo-root tier in `check_required_docs.py`, subsystem tier in `check_subsystem_docs.py`, non-overlapping — is P-02 applied to the doc manifest.
- **gitleaks secret scan and opt-in parallel tests.** A `gitleaks` pre-commit hook fails a leaked credential before any other hook (0.16.0); `pytest-xdist` ships in the dev group but racecar never sets `-n` in canon, leaving parallelism as the owning repo's opt-in (0.18.0). `check-full` runs its targets serially for attributable output on GNU Make 3.81 (0.18.1). The CLI audit infers its root from a `src/` layout instead of a required dotted name (0.17.0).
- **"surface" is canon; "face" retired.** `lib → api → surfaces {cli, rest, mcp}`; binding key `[tool.racecar.surface]`. (0.13.0, commit `d032a59`.)
- **Shape is the PYTHON_LIBRARY × DJANGO_PROJECT presence product.** `has_library × has_django` is the primitive; the enum (src / src+server / server / unknown) is the derived label, and `(neither)` is a no-shape finding, not a silent `src`. Governed by on-disk markers, no config flag. (commits `323fa77`, `d032a59`.)
- **The library is the architectural center; the ORM is confined to the control plane.** Agent-grade software is data-plane-dominant (R-07): the library (`src/<pkg>`, Django-free) holds the high-volume data path, and the ORM is confined to the `server/` control plane (auth/config/audit). The `src/` vs `server/` split is that confinement made physical, which is what *forces* the layout rather than choosing it. Full argument in `MANIFESTO.md`; forcing constraints in `arch-coherence/PACKAGING.md`.
- **The generation skills write zero bytes to `src/`.** `create-server` / `secure-server` / `deploy-server` read `src/<pkg>/api` and write only `server/`; the `api` seam is the author's arch-coherent code, verified and refused if absent, never synthesized by a skill (`arch-coherence/GENERATION.md`).
- **Auth: OAuth 2.1 opaque bearer, never JWT; WebAuthn FIDO2 hardware keys; closed by default.** `DEFAULT_SCOPES=[]` overrides DOT's wide-open default; the resource rail fails closed when unconfigured. (`arch-coherence/AUTH.md`; 0.13.0.)
- **Commit decomposes by default; the owner still commits.** `racecar-commit` inventories the whole tree and commits it as one when it tells one story or as a dependency-ordered series when it tells several; `commit-decompose` folds into it as an alias (0.20.0, commit `ba565b5`). The emitted runbook runs through `scripts/rc-commit.sh`, which forces `git commit -e` so nothing lands unreviewed — the agent drafts, the owner authorizes (R-05; `shared/OWNERSHIP.md`). racecar never runs `git commit` itself.

### §2.10 Operational

- **Install:** `./install` (in the racecar checkout) symlinks the 18 skills into `~/.claude/skills/` and wires the SessionStart/PreCompact hooks; idempotent, refuses to clobber present-but-wrong files. The 0.20.1 fix corrected a stale symlink map that had planted two dangling links under retired skill names — re-run `./install` after upgrading. `make doctor` (or `/racecar-doctor`) verifies the install with evidence (a load token reproduced from context).
- **Self-gate:** `make check` enforces pylint 10.00/10, 357 tests (pytest), and the doc + doc-graph + subsystem + changelog + required-docs + content-blind + brief checks, in sequence. `make docs` runs the documentation orchestration pipeline (0.22.0). `make check-full` runs the same targets serially (0.18.1) for attributable output on stock macOS GNU Make 3.81. `make arch` is not a racecar target — the arch *checks* are vendored into adopters, not run against racecar's own tooling.
- **Adopter gate:** `make check` + pre-commit in the consuming repo, using the synced scripts (`scripts/racecar-manifest.txt`, now including the three docs-orchestrator scripts). Enforcement is local (pre-commit, make), never CI-as-gate; the owner authorizes, the tooling confirms.
- **No deploy, no schedule, no healthcheck** — racecar ships files, not a running service. The `_telemetry` probe is offered for a governed repo to run; racecar itself runs nothing.

### §2.11 Weirdness

- **The `.py` files under `arch-coherence/templates/server/python/` are template assets, not modules.** They are syntactically valid Django code copied verbatim into a generated server; they reference `project.*` / django and would not import standalone. They are excluded from racecar's own lint/test (the globs scope to the lens `scripts/` dirs).
- **`detect_shape` is duplicated in Python and Make on purpose.** Make cannot import Python, so the shape logic lives in both `check_packaging_rules/_shape.py` and `templates/classic/racecar.mk`, kept identical by `test_sync_scripts.py`. The duplication is guarded, not eliminated.
- **The `_telemetry` probe is off by default and swallows every failure.** A resource probe that changes behavior or crashes the command it measures would be worse than no probe; it appends a JSONL line only when `RACECAR_TELEMETRY=1` and never lets its own error reach the wrapped `main()`. Absent data is a reason the hardware lens *stops*, not a reason it degrades gracefully into a guess.
- **The content-blindness gate is a no-op until a repo opts in — and that is the design.** `check_content_blind.py` ships to every adopter but does nothing until the README frontmatter declares a `content_blind` policy; the guard is fully parameterized by that frontmatter, so the same synced script is inert in a public repo and load-bearing in a fresh-history one.
- **The generated surfaces are database-light; the Authorization Server is the only stateful piece.** Surfaces validate tokens by HTTP introspection and never import the AS — so the import DAG stays clean and the surfaces hold no auth state.
- **The AAGUID hardware-key whitelist is advisory unless `WEBAUTHN_PACKED_ROOT_CERTS` is set.** Without attestation roots, py_webauthn trusts the self-reported AAGUID; the whitelist becomes a real hardware guarantee only when roots are configured (a logged warning fires otherwise).
- **`racecar-create-server` re-runs the whole tree.** Generation is copy + overlay, not patch; re-rendering a changed manifest does not prune a removed vertical's stale `apps/<v>/`.

## §3. Live access

racecar is a tooling/standards repo distributed as source (Claude Code skills + vendored scripts), not a deployed service. There is no hosted instance, no API to call, no credentials. Consumption is local: clone/symlink the checkout, run `./install`, invoke the skills, run `make check` / `make docs`.

### §3.1 Environments

N/A — no deployed instance. Local only: the racecar checkout + `~/.claude/skills/` symlinks. The `_telemetry` probe writes to `./.telemetry/usage.jsonl` in whatever governed repo enables it — a local file, not a service.

### §3.2 Auth

N/A — no deployed instance. (The OAuth 2.1 + WebAuthn auth racecar *generates* is the output's surface, documented in `arch-coherence/AUTH.md` and §2.7 flow 5, not racecar's own.)

### §3.3 Operations

N/A — no deployed instance. The callable surface is the slash commands, make targets, and `scripts/` scripts in §2.4 / frontmatter.

### §3.4 Rate limits

N/A — no deployed instance.

### §3.5 Errors

N/A — no deployed instance. Check scripts and the orchestrator signal by exit code (0 clean, 1 with file:line findings).

### §3.6 SDKs

N/A — no deployed instance, no public API to wrap.

## Confidence

**Least confident**

- §2.4 / §2.10 ("357 tests"): the count is `pytest --co` at the current HEAD (357 collected, up from 318 in the 0.20.1 brief); the number a fresh checkout collects can drift with any test addition. Verify with `.venv/bin/python -m pytest --co -q | tail -1`.
- §2.5 / §2.9 (sentinel regions): the `<!-- racecar:generated:<spine> start/end -->` marker syntax is quoted from `docs-orchestrator/ORCHESTRATION.md`'s prose; the literal string `docs_orchestrate.py` writes (and whether it wraps sentinels at all today, given the CHANGELOG describes the contract more than a shipped wrapper) was not confirmed against the implementation. Verify against `docs-orchestrator/scripts/docs_orchestrate.py`.
- §2.7 (Docs orchestration flow): the stage-2 spine regeneration is described from `ORCHESTRATION.md`; how much of stages 1–2 `docs_orchestrate.py` automates versus leaves to the agent (the doc says it runs the "report half" of stage 1 plus gates 3–4) was read from prose, not traced through the script. Verify against `docs-orchestrator/scripts/docs_orchestrate.py`.
- §2.1 / §2.10 (Hooks): "seven hook scripts" is counted from `ls hooks/`; which subset `sync_claude_md.py` actually wires into a consuming project's settings was not fully traced. Verify with `grep -n hook scripts/sync_claude_md.py`.

**Not in this brief**

- Roadmap intent beyond the named TODO stubs (deploy-server, review-package/review-server, workspace polymorphism), the order of the planned fleet migration, and any strategic priorities — unknown, ask user.
- Adoption metrics, who else uses racecar, and the bus factor — unknown, ask user.
