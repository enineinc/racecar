# racecar

Racecar is a deterministic, agent-loaded code-review framework for Python and Django. Its checks are stdlib Python scripts the agent runs, not LLM judgment: each one is a small, low-entropy detector that either passes or names a violation with a file and line. It ships as a Claude Code skills bundle (`/racecar*` slash commands) plus a set of checkers a project wires into its `Makefile` and pre-commit.

**The problem it solves.** AI coding agents produce code that passes tests but rots the architecture: import cycles, modules reaching up into their own root package, layer leaks across boundaries. Tests assert behavior, not structure, and an LLM reviewer drifts the same way the LLM author did. A mechanical check does not: the detector has lower entropy than the thing it watches, so it catches the drift that tests and LLM-reviewers miss.

## Quickstart

    git clone <this-repo>
    ./install

Then use the `/racecar*` slash commands in Claude Code (`/racecar` routes; `/racecar-arch-coherence`, `/racecar-doc-coherence`, `/racecar-eng-review`, `/racecar-llm-summary` are the lenses). To adopt the standards in your own project, scaffold it with `make init <shape>` (the project-scaffolding entry point) and read [`arch-coherence/PACKAGING.md`](arch-coherence/PACKAGING.md), which defines the four supported project shapes.

## A check catching a violation

`check_upward_imports` enforces that a business module never reaches up into its own root package (only `__init__.py` / `__main__.py` may). A module under package `athena` does:

    # athena/prices/loader.py  (business module)
    from athena import settings    # BLOCKED: upward import into own root

    # fix: read inherited state through the package's own __init__.py
    from athena.prices import settings

`check_cli_commands` catches the structural counterpart: a `__main__.py` that declares no `commands()` / `subcommands()` / `parser()` contract, or a package with a CLI but no `__main__.py` entry point, is flagged as an orphan rather than left to discover at runtime.

## Resolver (for the agent)

This is a routing table. Load the file that applies to the task at hand. Do not load all files.

Topic: Agent persona — interaction style and thought process when applying racecar standards
Load: [shared/PERSONA.md](shared/PERSONA.md)

Topic: Architectural coherence — DAG axioms and review lens
Load: [arch-coherence/README.md](arch-coherence/README.md)

Topic: Python architectural coherence — language-specific rules and enforcement
Load: [arch-coherence/PYTHON.md](arch-coherence/PYTHON.md)

Topic: CLI surface — `__main__.py` patterns, `commands()` / `subcommands()` / `parser()` contracts, audit JSON schema
Load: [arch-coherence/CLI.md](arch-coherence/CLI.md)

Topic: Packaging & tooling — racecar's single packaging opinion, parameterized over four supported project shapes (`src`, `pypkg`, `pypkg+djapp`, `djapp`): `pyproject.toml` (PEP 517/518/621), `Makefile` contract, virtualenv discipline, `requirements.txt` via `pip-compile`, racecar's dev tool set, PSF/PyPA + community OSS governance (no VC-backed tooling).
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

Topic: Commits — message convention and VERSION rules
Load: [shared/COMMITS.md](shared/COMMITS.md)

Topic: Expert output mode — terse, high-density delivery for an expert operator (optional overlay, not a review lens; installed separately via `make expert`)
Load: [expert/README.md](expert/README.md)

## Enforcement

Reference this file from your project's `CLAUDE.md` or equivalent agent-instruction file. Read it first to find which component applies. Do not load component files speculatively — read only what the current task requires. If you arrived at a component file directly, return here first.

## Install

From a fresh clone:

    ./install

Bash entrypoint, idempotent. Requires `python3` on `PATH` (stdlib only); the script checks upfront and prints an install hint if it's missing. It does three things, all rooted at this checkout's absolute path:

1. **Symlinks** `~/.claude/skills/racecar`, `racecar-arch-coherence`, `racecar-doc-coherence`, `racecar-eng-review`, `racecar-llm-summary` into the matching directories here, so the `/racecar*` slash commands resolve. An existing symlink pointing somewhere else, or a regular file at one of those paths, is refused — never clobbered.
2. **Pointer block** in `~/.claude/CLAUDE.md` (or `$CLAUDE_MD_PATH`), delimited by `<!-- BEGIN racecar pointer (managed) -->` / `<!-- END racecar pointer (managed) -->` and rewritten in place. Content outside the markers is preserved.
3. **Hooks** in `~/.claude/settings.json` (or `$CLAUDE_SETTINGS_PATH`), six total: a `PreToolUse` Bash hook (`hooks/compound-command-allow.sh`); a `PostToolUse` Read hook (`hooks/claude_racecar_hook.sh`, which re-fires the pointer sync whenever the agent reads `racecar/README.md`, so the pointer self-heals if the checkout moves); the **decision-log pair** — a `PreCompact` hook (`hooks/precompact_history.py`, matcher `""` = manual + auto) that appends a deterministic compaction marker, and a `SessionStart` hook (`hooks/session_compact_history.py`, matcher `compact`) that prompts the agent to reconcile the log from the transcript after compaction (both target `<repo>/.claude/HISTORY.md`, found by walking up to `.git`, mirror to `~/.claude/history/<repo-kebab>.md`, and **no-op unless that project has a `.claude/HISTORY.md`**, so a project opts in simply by creating one); and the **SessionStart pair** wired on matchers startup/resume/clear/compact — `hooks/session_load_standards.py`, which force-loads racecar's baseline (this README plus every `*.md` under `shared/`) as `additionalContext` so the standards are present whether or not the agent followed the pointer, and `hooks/session_discover_cli.py`, which runs `check_cli_commands.py --json` against the consuming repo and injects the summarized CLI-surface audit tree as `additionalContext` (it discovers CLI roots by scanning the filesystem for direct-child packages of the repo and its `src/` that have both `__init__.py` and `__main__.py`, deliberately ignoring `[project].name` since distribution and import names routinely differ, and no-ops when none are found), so the agent lands already knowing the repo's `python -m <pkg>` surface.

Re-run `./install` any time you move the checkout. Nothing else updates per-machine state.

**Optional overlay — expert output mode.** `make expert` installs the `racecar-expert-mode` skill (symlink `~/.claude/skills/racecar-expert-mode` → `expert/`) plus a managed pointer block in `~/.claude/CLAUDE.md` delimited by `<!-- BEGIN racecar-expert-mode pointer (managed) -->` / `<!-- END racecar-expert-mode pointer (managed) -->`. `make expert-uninstall` reverses both. Not run by `./install`; see [`expert/README.md`](expert/README.md).

## Bootstrap check

After reading this file: verify that `~/.claude/settings.json` contains a `PostToolUse` hook entry whose `command` path ends with `hooks/claude_racecar_hook.sh`. If it is absent, run `./install`. Do not proceed silently.
