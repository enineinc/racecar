# Standards — Resolver

This is a routing table. Load the file that applies to the task at hand. Do not load all files.

Topic: Agent persona — interaction style and thought process when applying racecar standards
Load: [shared/PERSONA.md](shared/PERSONA.md)

Topic: Architectural coherence — four checks (acyclicity, direction, layer integrity, depth-plus-one isolation) with sub-axioms (environment-layer exception, domain boundaries), plus review lens
Load: [arch-coherence/README.md](arch-coherence/README.md)

Topic: Python architectural coherence — module structure, imports, CLI, enforcement
Load: [arch-coherence/PYTHON.md](arch-coherence/PYTHON.md)

Topic: Django architectural coherence — service layer, view layering
Load: [arch-coherence/DJANGO.md](arch-coherence/DJANGO.md)

Topic: Engineering review — wrapper around gstack `plan-eng-review` with racecar-specific pre/post passes
Load: [eng-review/README.md](eng-review/README.md)

Topic: Python engineering hygiene — mindset, naming, formatting, testing, linting, Definition of Done
Load: [eng-review/PYTHON.md](eng-review/PYTHON.md)

Topic: Django engineering hygiene — database/performance, security
Load: [eng-review/DJANGO.md](eng-review/DJANGO.md)

Topic: Documentation coherence — update protocol + review lens (links, section numbers, file naming, cogency, scope honesty, rule testability, one-home-per-rule)
Load: [doc-coherence/README.md](doc-coherence/README.md)

Topic: LLM summary — generate a reconstruction-grade repo brief (queryable database of entities, relationships, contracts, flags, flows, plus a live-access block for clients calling the deployed system) for a downstream agent working without the repo; source-derivable only, no strategy or org views
Load: [llm-summary/README.md](llm-summary/README.md)

Topic: Ownership — tooling enables design and confirms correctness; responsibility stays with the owner
Load: [shared/OWNERSHIP.md](shared/OWNERSHIP.md)

Topic: Voice — shared conventions for prescriptive writing (standards and review outputs)
Load: [shared/VOICE.md](shared/VOICE.md)

Topic: TODO list rendering format
Load: [shared/TODO_FORMAT.md](shared/TODO_FORMAT.md)

Topic: Operational discipline — agent execution rules ordered independent→dependent (check before mutate, parallel independent reads, audit before fix, group failure modes, script mechanical changes, test suite is not a debugger)
Load: [shared/OPERATIONAL.md](shared/OPERATIONAL.md)

Topic: Glossary — DAG, coherence, cogency, resolver, depth-plus-one, outward-downward, one-home-per-rule, scope honesty, drift
Load: [shared/GLOSSARY.md](shared/GLOSSARY.md)

Topic: Commits — Conventional Commits format, valid VERSION increments, VERSION bump convention
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
3. **Hooks** in `~/.claude/settings.json` (or `$CLAUDE_SETTINGS_PATH`): a `PreToolUse` Bash hook (`hooks/compound-command-allow.sh`) and a `PostToolUse` Read hook (`hooks/claude_racecar_hook.sh`). The Read hook re-fires the pointer sync whenever the agent reads `racecar/README.md`, so the pointer self-heals if the checkout moves.

Re-run `./install` any time you move the checkout. Nothing else updates per-machine state.

**Optional overlay — expert output mode.** `make expert` installs the `racecar-expert-mode` skill (symlink `~/.claude/skills/racecar-expert-mode` → `expert/`) plus a managed pointer block in `~/.claude/CLAUDE.md` delimited by `<!-- BEGIN racecar-expert-mode pointer (managed) -->` / `<!-- END racecar-expert-mode pointer (managed) -->`. `make expert-uninstall` reverses both. Not run by `./install`; see [`expert/README.md`](expert/README.md).

## Bootstrap check

After reading this file: verify that `~/.claude/settings.json` contains a `PostToolUse` hook entry whose `command` path ends with `hooks/claude_racecar_hook.sh`. If it is absent, run `./install`. Do not proceed silently.
