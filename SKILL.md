---
name: racecar
description: Router for the racecar standards repo — an opinionated Python/Django review framework with three lenses. Use ONLY when the user explicitly says "racecar," asks to load racecar standards generally, or is unsure which lens applies. For specific concerns, invoke the lens skill directly — racecar-arch-coherence (architectural DAG, imports, layers), racecar-doc-coherence (doc drift, link integrity, cogency), or racecar-eng-review (code quality wrapping gstack plan-eng-review).
---

# racecar — Standards Router

This skill is a routing table, not content. Load [`CLAUDE.md`](CLAUDE.md) for the full resolver (racecar's machine baseline, force-loaded every session); it points at the lens dirs and the shared conventions (`shared/OWNERSHIP.md`, `shared/VOICE.md`, `shared/TODO_FORMAT.md`). [`README.md`](README.md) is the human-facing storefront.

The three lenses, each its own skill:

- **racecar-arch-coherence** → [`arch-coherence/README.md`](arch-coherence/README.md). four architectural checks (acyclicity; direction with env-layer exception; layer integrity with domain boundaries; depth-plus-one) plus the reviewer-facing companion to `import-linter`. Per-language specifics in [`arch-coherence/PYTHON.md`](arch-coherence/PYTHON.md), the CLI contract in [`arch-coherence/CLI.md`](arch-coherence/CLI.md), Django in [`arch-coherence/DJANGO.md`](arch-coherence/DJANGO.md).
- **racecar-doc-coherence** → [`doc-coherence/README.md`](doc-coherence/README.md). Doc update protocol + review lens + mechanical pre-pass.
- **racecar-eng-review** → [`eng-review/README.md`](eng-review/README.md). Three-phase wrapper: racecar pre-pass → gstack `/plan-eng-review` → racecar post-pass against Python/Django hygiene. Per-language specifics in [`eng-review/PYTHON.md`](eng-review/PYTHON.md) and [`eng-review/DJANGO.md`](eng-review/DJANGO.md).

Plus a generator (not a lens, but installed by `./install` alongside the lenses):

- **racecar-llm-summary** → [`llm-summary/README.md`](llm-summary/README.md). Produce a single-file Markdown knowledge package for a downstream LLM; shareable, not reconstruction-grade. Use when capturing a system snapshot for an agent that will work *without* the repo.

And a docs orchestrator (also installed by `./install`):

- **racecar-docs** → [`docs-orchestrator/README.md`](docs-orchestrator/README.md). Compose the doc generators and checkers into one re-runnable pipeline (generate missing required docs, regenerate the machine spine no-clobber-but-repair, content-blindness gate, coherence gate). Re-implements nothing; owns only the required-docs manifest and the content-blindness contract. Use to stand up, refresh, or verify a repo's whole documentation set.

And a CLI-docs generator it drives (also installed by `./install`):

- **racecar-cli-docs** → [`cli-docs/SKILL.md`](cli-docs/SKILL.md). Project a repo's `python -m <pkg>…` CLI tree into per-command `docs/cli/**` pages plus the README `## CLI` block, generated from `check_cli_commands.py`'s audit (a projection, never a second home). Use to build or refresh a package's command reference.

And a hardware-sizing lens (also installed by `./install`):

- **racecar-sysadmin-hardware** → [`sysadmin-hardware/README.md`](sysadmin-hardware/README.md). Propose an EC2 instance type for a governed repo from evidence: the `_telemetry` probe's per-command resource profile plus a structural review of the four surfaces. Use when sizing a box, picking an instance, or deciding burstable vs sustained.

Do not load lens content speculatively. If the task is ambiguous, ask which concern applies before loading.

Optional overlay (not a lens): **racecar-expert-mode** → [`expert/README.md`](expert/README.md). Output discipline — terse, high-density delivery; lead with the result, no preamble/recap/hedging. Installed separately via `make expert` (skill symlink + managed `~/.claude/CLAUDE.md` pointer block); `make expert-uninstall` reverses it. Not part of `./install`.
