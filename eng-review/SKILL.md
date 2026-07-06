---
name: racecar-eng-review
description: Engineering review wrapper — runs a racecar pre-pass (scope honesty of names, operational traceability, red-flag scan), delegates to gstack `/plan-eng-review` for the broader architectural/execution review, then runs a racecar post-pass against Python/Django hygiene (naming, formatting, testing, linting, Definition of Done; DB/performance, security). Findings tagged `[pre]` / `[gstack]` / `[post]`. Use when asked to review code for engineering quality, wrap gstack's eng review, audit Python/Django idiosyncrasies, or check for stubs/mocks/type-hint lies/ops gaps.
---

# racecar-eng-review

Load [`WORKFLOW.md`](WORKFLOW.md) in full. It holds the three-phase workflow, the two engineering checks, red flags, mental models, decision patterns, feedback format, and invocation prompts.

Operational reminder: this is a wrapper, not a standalone lens. The three phases must run in order:

1. **Pre-pass (racecar):** apply the two checks + red flags. Fix any Blocker before step 2 — gstack's broader review drowns in noise on dirty code.
2. **gstack `/plan-eng-review`:** invoke gstack for the broader architectural/execution review.
3. **Post-pass (racecar):** apply [`PYTHON.md`](PYTHON.md) and [`DJANGO.md`](DJANGO.md) as applicable for language-specific idiosyncrasies gstack does not opine on.

Per-language content (loaded on demand in the post-pass):
- [`PYTHON.md`](PYTHON.md) — language-specific code-quality rules.
- [`DJANGO.md`](DJANGO.md) — framework-specific code-quality rules.

Topic companion (loaded on demand when reviewing tests/fixtures):
- [`RECONCILIATION.md`](RECONCILIATION.md) — when reconciliation tests should be a scaffold of generic manifolds over a private catalog instead of model-named golden tests.

Output format: numbered entries tagged `[pre]` / `[gstack]` / `[post]` with severity (Blocker / Major / Minor / Nit), verdict line at the end (Ship / Revise / Rework). No preamble.
