# racecar — agent baseline (machine)

This file is racecar's machine-facing baseline. It is FORCE-LOADED into every session by the `session_load_standards` hook, together with every `*.md` under `shared/`. The human-facing storefront is [README.md](README.md); README is written for people and is **not** loaded into agent context. This file is, and it can be dense.

racecar is a deterministic code-review framework for Python and Django: written standards plus low-entropy checks the agent runs (stdlib Python scripts, never LLM judgment). When doing AI-assisted work in a project that has applied racecar, obey the standards and run the checks.

## What "loaded" means

- **Baseline (always on).** This file plus `shared/*.md` are injected every SessionStart — operational discipline, persona, drift doctrine, voice, glossary, ownership, commit rules, TODO format. Treat them as present; do not re-Read them.
- **Lenses (on demand).** The files under `arch-coherence/`, `eng-review/`, `doc-coherence/`, `llm-summary/` load only when a task selects them. Read the file the resolver below names when the task matches its topic; do not load lenses speculatively.
- The correct answer to "is racecar loaded?" is "yes — baseline is present; lenses load when a task selects them," evidenced by reproducing the `Load token:` planted in the session preamble.

## Resolver (topic → load)

This is the routing table. Load the file that applies to the task at hand. Do not load all files.

Topic: Agent persona — interaction style and thought process when applying racecar standards
Load: [shared/PERSONA.md](shared/PERSONA.md)

Topic: Architectural coherence — the four DAG-verifying checks (acyclicity, direction, layer integrity, depth-plus-one) and review lens
Load: [arch-coherence/CHECKS.md](arch-coherence/CHECKS.md)

Topic: Python architectural coherence — language-specific rules and enforcement
Load: [arch-coherence/PYTHON.md](arch-coherence/PYTHON.md)

Topic: Surfaces (`lib → api → {cli, rest, mcp}`); a surface is a thin adapter on `api`; named-file autodiscovery convention, the single gated `layers` contract plus the advisory detector, role-identification tiers, surfaces-vs-shapes orthogonality
Load: [arch-coherence/SURFACES.md](arch-coherence/SURFACES.md)

Topic: CLI surface — `__main__.py` patterns, `commands()` / `subcommands()` / `parser()` contracts, audit JSON schema
Load: [arch-coherence/CLI.md](arch-coherence/CLI.md)

Topic: Packaging & tooling — racecar's single packaging opinion, parameterized over the `PYTHON_LIBRARY × DJANGO_PROJECT` shape product (`src` / `src+server` / `server`; the `{packages,pypkg}/<pkg>/src/<pkg>` workspace form is a deferred future, not a current shape), shapes orthogonal to surfaces. `pyproject.toml` (PEP 517/518/621), `Makefile` contract, virtualenv discipline, optional `requirements.txt` lockfile (validate-if-present, not canon-generated), racecar's dev tool set, PSF/PyPA + community OSS governance (no VC-backed tooling).
Load: [arch-coherence/PACKAGING.md](arch-coherence/PACKAGING.md)

Topic: Django architectural coherence — framework-specific rules
Load: [arch-coherence/DJANGO.md](arch-coherence/DJANGO.md)

Topic: Surface generation — deriving a REST + MCP Django server over `api` from the CLI + binding; the Interface Manifest, MCP wire conformance, the write rail and the auth rail
Load: [arch-coherence/GENERATION.md](arch-coherence/GENERATION.md)

Topic: Auth rail — surfaces closed by default; one OAuth 2.1 opaque-bearer path, a WebAuthn hardware-key Authorization Server, per-tool scopes, no JWT
Load: [arch-coherence/AUTH.md](arch-coherence/AUTH.md)

Topic: Engineering review — wrapper around gstack `plan-eng-review`
Load: [eng-review/WORKFLOW.md](eng-review/WORKFLOW.md)

Topic: Python engineering hygiene — language-specific code-quality rules
Load: [eng-review/PYTHON.md](eng-review/PYTHON.md)

Topic: Django engineering hygiene — framework-specific code-quality rules
Load: [eng-review/DJANGO.md](eng-review/DJANGO.md)

Topic: Reconciliation scaffolds — replacing model-named golden tests with a few generic manifolds (tie / identity / integrity) over a private, gitignored catalog; when to choose this over golden tests, and the confidentiality/perimeter payoff.
Load: [eng-review/RECONCILIATION.md](eng-review/RECONCILIATION.md)

Topic: Documentation coherence — update protocol + review lens
Load: [doc-coherence/PROTOCOL.md](doc-coherence/PROTOCOL.md)

Topic: Documentation node graph — the `pnode` frontmatter taxonomy (each doc declares its parent once; children and peers are derived, never stored; the doc graph is held to a DAG by `check_doc_graph.py`) plus the reader-first layering convention
Load: [doc-coherence/DOC_GRAPH.md](doc-coherence/DOC_GRAPH.md)

Topic: LLM summary — produce a shareable single-file knowledge package for a downstream LLM working without the repo
Load: [llm-summary/SPEC.md](llm-summary/SPEC.md)

Topic: Ownership — tooling enables design and confirms correctness; responsibility stays with the owner
Load: [shared/OWNERSHIP.md](shared/OWNERSHIP.md)

Topic: Principles — the irreducible universal axioms every rule and lens derives from
Load: [shared/PRINCIPLES.md](shared/PRINCIPLES.md)

Topic: Drift — the doctrine for fighting entropy continuously
Load: [shared/DRIFT.md](shared/DRIFT.md)

Topic: Voice — shared conventions for prescriptive writing (standards and review outputs)
Load: [shared/VOICE.md](shared/VOICE.md)

Topic: Vocabulary — the literal severity and verdict tokens every review output must use (Blocker/Major/Minor/Nit, Ship/Revise/Rework)
Load: [shared/VOCABULARY.md](shared/VOCABULARY.md)

Topic: TODO list rendering format
Load: [shared/TODO_FORMAT.md](shared/TODO_FORMAT.md)

Topic: Operational discipline — agent execution rules ordered independent→dependent
Load: [shared/OPERATIONAL.md](shared/OPERATIONAL.md)

Topic: Glossary — shared terminology for the standards
Load: [shared/GLOSSARY.md](shared/GLOSSARY.md)

Topic: Commits — message convention, type→bump mapping, version-home rules
Load: [shared/COMMITS.md](shared/COMMITS.md)

Topic: Commit authoring — inventory the working tree and commit it as one conventional commit or a dependency-ordered series (decompose by default), each with a deterministic version bump
Load: [commit/SKILL.md](commit/SKILL.md)

Topic: Upgrade — bring an existing repo in line with current racecar with nuance (no clobber); classify each divergence Conform / Escalate (intentional-and-right divergence is kept in place with a comment, no override registry), owner-authorized, idempotent; optional surfaces uplift
Load: [upgrade/SKILL.md](upgrade/SKILL.md)

Topic: Doctor — verify install, wiring, and load layer by layer (deterministic checks + load-token challenge)
Load: [doctor/SKILL.md](doctor/SKILL.md)

Topic: Expert output mode — terse, high-density delivery for an expert operator (optional overlay, not a review lens; installed separately via `make expert`)
Load: [expert/README.md](expert/README.md)

Topic: Create package — scaffold the canon `src/<pkg>` library (lib/api/cli + root pyproject); the greenfield root of the deploy cascade
Load: [create-package/SKILL.md](create-package/SKILL.md)

Topic: Start Django project — scaffold a vanilla Django project (the `server/` shell); generic, no racecar knowledge
Load: [start-django-project/SKILL.md](start-django-project/SKILL.md)

Topic: Create server — generate the REST + MCP surfaces in `server/` over `src/<pkg>/api` (delegates the shell to start-django-project)
Load: [create-server/SKILL.md](create-server/SKILL.md)

Topic: Secure server — generate the OAuth 2.1 Authorization Server (WebAuthn hardware-key login) that closes the surfaces
Load: [secure-server/SKILL.md](secure-server/SKILL.md)

Topic: Deploy server — ship the generated server to a host: Apache vhosts, the per-surface processes, TLS, the AS (TODO; the edit/ship boundary)
Load: [deploy-server/SKILL.md](deploy-server/SKILL.md)

Topic: Normalize — sync the canonical check scripts into a project and run every checker, reporting findings to fix
Load: [normalize/SKILL.md](normalize/SKILL.md)

Topic: Commit preflight — dry-run the pre-commit hooks before committing
Load: [commit-preflight/SKILL.md](commit-preflight/SKILL.md)

Topic: Commit decompose — alias of commit authoring; splitting a working tree into an ordered commit series is now the default behavior of racecar-commit, kept so existing invocations still resolve
Load: [commit-decompose/SKILL.md](commit-decompose/SKILL.md)

## Enforcement

A project applies racecar by referencing this file from its own `CLAUDE.md` or equivalent agent-instruction file (the `./install` pointer block does this automatically; see [README.md](README.md) "Install"). Read this file first to find which component applies. Do not load component files speculatively — read only what the current task requires. If you arrived at a component file directly, return here first.

Enforce mechanically in the consuming repo: run `make arch` / `make check` and the pre-commit hooks. A failing check names a file and line; fix it before proceeding.

## Open work

Current state and the in-flight flight plan live in [TODO.md](TODO.md) (the one index), which resolves to [PLAN.md](PLAN.md).
