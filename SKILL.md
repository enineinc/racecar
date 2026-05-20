---
name: racecar
description: Router for the racecar standards repo — an opinionated Python/Django review framework with three lenses. Use ONLY when the user explicitly says "racecar," asks to load racecar standards generally, or is unsure which lens applies. For specific concerns, invoke the lens skill directly — racecar-arch-coherence (architectural DAG, imports, layers), racecar-doc-coherence (doc drift, link integrity, cogency), or racecar-eng-review (code quality wrapping gstack plan-eng-review).
---

# racecar — Standards Router

This skill is a routing table, not content. Load [`README.md`](README.md) for the full resolver; it points at the three lens dirs and the shared conventions (`shared/OWNERSHIP.md`, `shared/VOICE.md`, `shared/TODO_FORMAT.md`).

The three lenses, each its own skill:

- **racecar-arch-coherence** → [`arch-coherence/README.md`](arch-coherence/README.md). four architectural checks (acyclicity; direction with env-layer exception; layer integrity with domain boundaries; depth-plus-one) plus the reviewer-facing companion to `import-linter`. Per-language specifics in [`arch-coherence/PYTHON.md`](arch-coherence/PYTHON.md) and [`arch-coherence/DJANGO.md`](arch-coherence/DJANGO.md).
- **racecar-doc-coherence** → [`doc-coherence/README.md`](doc-coherence/README.md). Doc update protocol + review lens + mechanical pre-pass (link / anchor / section-number drift).
- **racecar-eng-review** → [`eng-review/README.md`](eng-review/README.md). Three-phase wrapper: racecar pre-pass → gstack `/plan-eng-review` → racecar post-pass against Python/Django hygiene. Per-language specifics in [`eng-review/PYTHON.md`](eng-review/PYTHON.md) and [`eng-review/DJANGO.md`](eng-review/DJANGO.md).

Plus a generator (not a lens, but installed by `./install` alongside the lenses):

- **racecar-llm-summary** → [`llm-summary/README.md`](llm-summary/README.md). Produce a reconstruction-grade brief of a repository, structured as a queryable database for a downstream LLM: a slim Map (purpose, modules, vendors), an Implementation block (entities, relationships, external + internal contracts, flags, flows, weirdness), and a Live-Access block (environments, auth, example request/response). Source-derivable only — does not attempt strategy or org-chart views. Use when capturing a system snapshot for an agent that will work *without* the repo.

Do not load lens content speculatively. If the task is ambiguous, ask which concern applies before loading.

Optional overlay (not a lens): **racecar-expert-mode** → [`expert/README.md`](expert/README.md). Output discipline — terse, high-density delivery; lead with the result, no preamble/recap/hedging. Installed separately via `make expert` (skill symlink + managed `~/.claude/CLAUDE.md` pointer block); `make expert-uninstall` reverses it. Not part of `./install`.
