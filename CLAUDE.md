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

Topic: Architectural coherence — DAG axioms and review lens
Load: [arch-coherence/README.md](arch-coherence/README.md)

Topic: Python architectural coherence — language-specific rules and enforcement
Load: [arch-coherence/PYTHON.md](arch-coherence/PYTHON.md)

Topic: Faces (`lib → api → {cli, mcp, web/django}`); a face is a wrapper on `api`; named-file autodiscovery convention, the single gated `layers` contract plus the advisory detector, role-identification tiers, faces-vs-shapes orthogonality
Load: [arch-coherence/FACES.md](arch-coherence/FACES.md)

Topic: CLI surface — `__main__.py` patterns, `commands()` / `subcommands()` / `parser()` contracts, audit JSON schema
Load: [arch-coherence/CLI.md](arch-coherence/CLI.md)

Topic: Packaging & tooling — racecar's single packaging opinion, parameterized over four supported project shapes (`src`, `pypkg`, `pypkg+djapp`, `djapp`): `pyproject.toml` (PEP 517/518/621), `Makefile` contract, virtualenv discipline, optional `requirements.txt` lockfile (validate-if-present, not canon-generated), racecar's dev tool set, PSF/PyPA + community OSS governance (no VC-backed tooling).
Load: [arch-coherence/PACKAGING.md](arch-coherence/PACKAGING.md)

Topic: Django architectural coherence — framework-specific rules
Load: [arch-coherence/DJANGO.md](arch-coherence/DJANGO.md)

Topic: Engineering review — wrapper around gstack `plan-eng-review`
Load: [eng-review/README.md](eng-review/README.md)

Topic: Python engineering hygiene — language-specific code-quality rules
Load: [eng-review/PYTHON.md](eng-review/PYTHON.md)

Topic: Django engineering hygiene — framework-specific code-quality rules
Load: [eng-review/DJANGO.md](eng-review/DJANGO.md)

Topic: Documentation coherence — update protocol + review lens
Load: [doc-coherence/README.md](doc-coherence/README.md)

Topic: LLM summary — produce a shareable single-file knowledge package for a downstream LLM working without the repo
Load: [llm-summary/README.md](llm-summary/README.md)

Topic: Ownership — tooling enables design and confirms correctness; responsibility stays with the owner
Load: [shared/OWNERSHIP.md](shared/OWNERSHIP.md)

Topic: Drift — the doctrine for fighting entropy continuously
Load: [shared/DRIFT.md](shared/DRIFT.md)

Topic: Voice — shared conventions for prescriptive writing (standards and review outputs)
Load: [shared/VOICE.md](shared/VOICE.md)

Topic: TODO list rendering format
Load: [shared/TODO_FORMAT.md](shared/TODO_FORMAT.md)

Topic: Operational discipline — agent execution rules ordered independent→dependent
Load: [shared/OPERATIONAL.md](shared/OPERATIONAL.md)

Topic: Glossary — shared terminology for the standards
Load: [shared/GLOSSARY.md](shared/GLOSSARY.md)

Topic: Commits — message convention, type→bump mapping, version-home rules
Load: [shared/COMMITS.md](shared/COMMITS.md)

Topic: Commit authoring — procedure for drafting a conventional commit with deterministic version bump from the staged diff
Load: [commit/SKILL.md](commit/SKILL.md)

Topic: Upgrade — bring an existing repo in line with current racecar with nuance (no clobber); classify each divergence Conform / Declare / Escalate, owner-authorized, idempotent; optional faces uplift
Load: [upgrade/SKILL.md](upgrade/SKILL.md)

Topic: Doctor — verify install, wiring, and load layer by layer (deterministic checks + load-token challenge)
Load: [doctor/SKILL.md](doctor/SKILL.md)

Topic: Expert output mode — terse, high-density delivery for an expert operator (optional overlay, not a review lens; installed separately via `make expert`)
Load: [expert/README.md](expert/README.md)

## Enforcement

A project applies racecar by referencing this file from its own `CLAUDE.md` or equivalent agent-instruction file (the `./install` pointer block does this automatically; see [README.md](README.md) "Install"). Read this file first to find which component applies. Do not load component files speculatively — read only what the current task requires. If you arrived at a component file directly, return here first.

Enforce mechanically in the consuming repo: run `make arch` / `make check` and the pre-commit hooks. A failing check names a file and line; fix it before proceeding.
