---
name: racecar-arch-coherence
description: Architectural coherence review — verify the import graph is acyclic, imports flow outward/downward, layers do not leak, peer edges have a pure provider. Covers the four architectural checks (acyclicity; direction with the environment-layer exception; layer integrity with domain boundaries; depth-plus-one isolation) plus the reviewer-facing companion to `import-linter`. Use when asked to review architecture, check for import cycles, audit dependency direction, verify layer integrity, or check whether documented architecture matches the import graph. For Python-specific rules (module structure, `__init__.py` / `__main__.py` roles, CLI pattern, enforcement), PYTHON.md is loaded on demand; for Django, DJANGO.md.
---

# racecar-arch-coherence

Load [`CHECKS.md`](CHECKS.md) in full. It holds the four architectural checks (acyclicity, direction, layer integrity, depth-plus-one isolation) with their sub-axioms (environment-layer exception under direction; domain boundaries under layer integrity), mental models, red flags, decision patterns, feedback format, and invocation prompts.

Operational reminder: if `import-linter` is configured on the target project, run it first. Any broken contract is a Blocker and supersedes prose reasoning.

Language-specific:
- [`PYTHON.md`](PYTHON.md) — module structure, imports, CLI, enforcement.
- [`DJANGO.md`](DJANGO.md) — service layer, view layering.

Output format: numbered roots with severity (Blocker / Major / Minor / Nit), verdict line at the end (Ship / Revise / Rework). No preamble.
