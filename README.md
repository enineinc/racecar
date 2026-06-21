# racecar

racecar is for one builder shipping real software with AI agents across more than one codebase, who refuses to let the architecture rot at AI speed. It is a set of code standards plus deterministic checks that an AI coding agent loads and applies to its own work, so you can trust the *structure* of what the agent writes without re-reading every line.

## What it does for you

AI agents write code that passes tests and quietly rots the architecture: import cycles, modules reaching up into their own root, layers leaking across boundaries, one library smeared across a dozen entry points. Tests do not see structure, and a second AI asked to "review the architecture" drifts the same way the first one did. racecar catches that class of defect mechanically, at the moment it is introduced, so an expensive future refactor becomes a cheap present fix.

The payoff is trust at velocity. Across many codebases one person cannot re-read everything; racecar's checks let you trust the shape of agent output and spend your scarce attention on the parts that actually need judgment.

## Getting Started

1. **Install** (about 30 seconds; needs `python3` on your `PATH`):

       git clone <this-repo>
       ./install

2. **Confirm it loaded.** In Claude Code the `/racecar*` slash commands are now live. Run `make doctor` (or `/racecar-doctor`) to verify the standards are wired and force-loaded into every session. If it reports failures, re-run `./install`.

That is the whole setup. `./install` is idempotent: it symlinks the skills, writes a managed pointer block into `~/.claude/CLAUDE.md` (your other content is preserved), and wires the SessionStart hooks that load racecar's baseline. Re-run it any time you move the checkout.

## Using racecar

**Review with the lenses.** `/racecar` routes to the right tool; or call one directly:

- `/racecar-arch-coherence` — architecture: cycles, import direction, layer leaks, the faces shape.
- `/racecar-eng-review` — code quality: Python and Django hygiene, testing, the Definition of Done.
- `/racecar-doc-coherence` — documentation: drift, link integrity, cogency, one home per rule.

**Structure your code as one library, thin faces.** racecar's core shape is **`lib → api → faces`**:

- **`lib`** does the work (compute, fetch, transform, persist) and knows nothing about who calls it.
- **`api`** is the one home for orchestration: resolve inputs, apply defaults, seed credentials, dispatch to the worker.
- **faces** are thin wrappers on `api`, one per way you expose the library: a CLI (`__main__.py`), an MCP tool server (`mcp.py`), a Django app. A face only translates its transport, calls `api`, and renders the result.

Keeping orchestration in `api` means it lives in one place instead of being copied into every entry point, where it drifts. The full doctrine and the checks that keep faces thin are in [`arch-coherence/FACES.md`](arch-coherence/FACES.md).

**Adopt it in your own project.** Scaffold a new one with the shape already wired:

    make init ARGS="--shape src --name myapp --package myapp --dest ./myapp --vertical prices"

or bring an existing project up to standard with `/racecar-upgrade`, which folds racecar in without clobbering your customizations. After that the checks run where you work, in `make check` and your pre-commit hooks.

**What a check looks like.** `check_upward_imports` enforces that a business module never reaches up into its own root package (only `__init__.py` / `__main__.py` may):

    # athena/prices/loader.py  (business module)
    from athena import settings    # BLOCKED: upward import into own root

    # fix: read inherited state through the package's own __init__.py
    from athena.prices import settings

**The rest of the toolkit.** Four review lenses live under `arch-coherence/`, `eng-review/`, `doc-coherence/`, and `llm-summary/` (which packages a repo into one shareable file another LLM can interview without the source). There are also commit helpers (`/racecar-commit`, `/racecar-commit-preflight`, `/racecar-commit-decompose`), an adoption auditor (`/racecar-normalize`), and the nuanced upgrader (`/racecar-upgrade`). The always-on baseline (persona, drift doctrine, voice, ownership, commit rules) lives in `shared/`.

*For agents:* you do not read this file. Your machine baseline and the precise topic-to-file routing table live in [`CLAUDE.md`](CLAUDE.md), force-loaded into every session.

## When, where, and why it works this way

The rest is rationale; you do not need it to use racecar.

- **Why deterministic checks, not an AI reviewer.** A check either passes or names a file and a line, and it cannot drift the way an AI reviewer drifts, because the detector is far simpler than the code it watches. In a loop where AI writes the code, a verifier that shares the author's blind spots cannot catch the author's mistakes; a mechanical rule does not share them. So racecar mechanizes everything a rule can decide and leaves only the irreducible to judgment.
- **Where it runs: locally, not as a CI gate.** Enforcement is `pre-commit`, `lint-imports`, and `make check`, on your machine. The owner authorizes; the tooling confirms, it does not decide. A green check is confirmation, not a merge verdict.
- **The standards are falsifiable.** When a real project diverges because racecar's default is wrong, the standard changes, not the project. Racecar is corrected by the repos it is applied to, not the other way around.
