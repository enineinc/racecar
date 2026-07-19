---
pnode: []
content_blind: false  # racecar defines the content-blindness rule, so its docs must quote the forbidden figure shapes (rates, notionals) to explain them
---

# racecar

racecar is for a builder shipping real software with AI agents across more than one codebase, who refuses to let the architecture rot at AI speed. It is a set of code standards plus deterministic checks that an AI coding agent loads and applies to its own work, so you can trust the *structure* of what the agent writes without re-reading every line.

**Why it is built the way it is**, the trust thesis (mechanical over heuristic), the data-plane-dominant architecture (the library is the center, the ORM confined to the control plane), and the portfolio-OS frame, is argued in [`MANIFESTO.md`](MANIFESTO.md).

## The principles

racecar is twelve principles, held in force where you work: most by mechanical checks that fire at a file and line, the rest by construction and owner discipline. The contribution is not the ideas, which are old, but the binding: enforcing them together, without drift. Each has one home in [`shared/PRINCIPLES.md`](shared/PRINCIPLES.md), where it is stated as the axiom, what it rests on, the failure it prevents, the check that enforces it, and its origin. There are two kinds, both held with the same force: **known principles** (P), the established canon racecar adopts, and **racecar principles** (R), the stances racecar takes. Each group runs in dependency order, foundational first.

**Known principles** — established, and resting on a theorem, a tautology, or long-settled practice.

- **P-01. Dependencies form a directed acyclic graph.** Imports flow outward and downward, never up into a module's own root; no cycles. *The Acyclic Dependencies Principle (Martin), information hiding (Parnas), levelization (Lakos).*
- **P-02. One home per artifact.** Every fact, rule, or value lives in exactly one place; everything else points to it, and does not restate it. *DRY and single source of truth (Hunt and Thomas).*
- **P-03. Reconcile to source; do not re-derive from memory.** Verify a claim against the source's own mechanic, not a summary, an agent's report, or a green dashboard. *Dijkstra: testing shows the presence, not the absence, of bugs.*
- **P-04. Resolve drift at the largest frame that explains the symptom.** When a drift shows symptoms at several frames, fix it at the largest one that explains it, not the local symptom, which leaves the cause to resurface. *Root-cause over symptom (Ohno's five whys).*
- **P-05. Idempotent by default; re-running changes nothing.** A scaffolder, installer, sync, or gate is safe to run again; re-execution is the ordinary case, not the error path. *Long-standing in mathematics and distributed systems.*

**Racecar principles** — the stances racecar takes: chosen, some contrarian, defended by results.

- **R-01. A detector must have lower entropy than what it watches.** A generator cannot be its own gate; an observer as noisy as its subject cannot tell signal from its own variance. Checks-over-prose and model-last are both this law applied. *Requisite variety (Ashby) and the reproducibility instinct; the detector-entropy framing is racecar's, not an original law.*
- **R-02. Enforced, not professed; the enforced contract is truth.** A rule that matters is a check that fails by naming a file and a line; prose is not enforcement. When prose and the running check disagree, the check wins and the prose is the bug. *The lint and policy-as-code tradition; "the running system is the truth" is folk.*
- **R-03. Determinism; the model is last, never the gate.** Every gate is a script and an exit code. The AI is used last, to mechanize judgment or for the residue no rule can decide, never as the arbiter. *racecar's trust thesis; the reproducibility instinct is old, but the stance is not claimed as original.*
- **R-04. Scope honesty.** A name means exactly its contents; a file's location means exactly its role. A generic that carries specifics is a lie the reader cannot see. *Naming as a promise, and least astonishment; folk wisdom, no single owner.*
- **R-05. Ownership is not delegable.** Tooling enables and confirms; it does not authorize. A green check is confirmation, not a merge verdict, and enforcement runs on the owner's machine, never as a CI gate that decides. *"You build it, you run it" (Vogels), and Deming's refusal to inspect quality in after the fact.*
- **R-06. Make the right thing easy; help, not law.** The good shape is the default you receive, not a wall you are forced into. Gate genuine defects; surface choices. A rule that reads as a wall is a defect in the rule. *The paved road and the pit of success.*
- **R-07. Agent-grade software is data-plane-dominant.** The library is the center, holding the data plane; the ORM is confined to a control-plane server that never touches it. *racecar's architecture bet; the data-plane / control-plane split is standard systems vocabulary.*

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

- `/racecar-arch-coherence`: architecture: cycles, import direction, layer leaks, the surfaces shape.
- `/racecar-eng-review`: code quality: Python and Django hygiene, testing, the Definition of Done.
- `/racecar-doc-coherence`: documentation: drift, link integrity, cogency, one home per rule.

**Structure your code as one library, thin surfaces.** racecar's core shape is **`lib → api → surfaces`**:

- **`lib`** does the work (compute, fetch, transform, persist) and knows nothing about who calls it.
- **`api`** is the one home for orchestration: resolve inputs, apply defaults, seed credentials, dispatch to the worker.
- **surfaces** are thin wrappers on `api`, one per way you expose the library: a CLI (`__main__.py`), an MCP tool server (`mcp.py`), a Django app. A surface only translates its transport, calls `api`, and renders the result.

Keeping orchestration in `api` means it lives in one place instead of being copied into every entry point, where it drifts. The full doctrine and the checks that keep surfaces thin are in [`arch-coherence/SURFACES.md`](arch-coherence/SURFACES.md).

**Generate a deployable service from the library (the cascade).** Four rungs you invoke, each idempotent and writing only its own layer (the library is written once, then never touched again). The rungs chain downward — a later rung invokes the earlier one to satisfy its precondition — so you drive the whole flow from a single command:

```
create-package  ──►  create-server  ──►  secure-server  ──►  deploy-server
  src/<pkg>            server/              + Authorization     ship to a host:
  lib · api · cli      REST + MCP over      Server (OAuth 2.1   Apache vhosts,
  (the library)        src/<pkg>/api        + WebAuthn keys)    processes, TLS
                          │                                     (TODO, not built)
                          └─ delegates to start-django-project
                             (lays the vanilla server/ shell first;
                              generic, knows nothing about racecar)
```

- `/racecar-create-package`: scaffold the canon `src/<pkg>` library (lib/api/cli, its own pyproject). The library is yours; the generation rungs read it but never write `src/`.
- `/racecar-create-server`: generate the REST + MCP surfaces in `server/` over `src/<pkg>/api`. It invokes `/racecar-start-django-project` for the vanilla shell, then composes the surfaces on top; it refuses if `src/<pkg>/api` is absent.
- `/racecar-secure-server`: close the surfaces with an OAuth 2.1 Authorization Server (WebAuthn hardware-key login, opaque tokens, per-tool scopes). Invokes `/racecar-create-server` if no surface exists yet.
- `/racecar-deploy-server`: ship `server/` to a host: Apache vhosts, the per-surface processes, TLS *(planned; this skill is a TODO, not yet built)*.

`/racecar-start-django-project` is the generic delegate `create-server` calls, not a rung you run in sequence. Invoke it directly only for a bare Django project with no library and no surfaces (the standalone `server` shape).

**Adopt it in your own project.** Scaffold a new one with the shape already wired:

    make init ARGS="--shape src --name myapp --package myapp --dest ./myapp --vertical prices"

or bring an existing project up to standard with `/racecar-upgrade`, which folds racecar in without clobbering your customizations. After that the checks run where you work, in `make check` and your pre-commit hooks. The three adoption paths (new project, existing project with a local racecar clone, existing project without one) are written out in [`ADOPT.md`](ADOPT.md). To see a check fire before you adopt, `make demo` runs racecar against the deliberately-broken sample under [`examples/`](examples/README.md).

**What a check looks like.** `check_upward_imports` enforces that a business module never reaches up into its own root package (only `__init__.py` / `__main__.py` may):

    # athena/prices/loader.py  (business module)
    from athena import settings    # BLOCKED: upward import into own root

    # fix: read inherited state through the package's own config module
    from athena.prices.config import settings

**The rest of the toolkit.** Three review lenses (`arch-coherence/`, `eng-review/`, `doc-coherence/`) plus the `llm-summary/` brief generator, invoked as `/racecar-arch-coherence`, `/racecar-eng-review`, `/racecar-doc-coherence`, and `/racecar-llm-summary` (which packages a repo into one shareable file another LLM can interview without the source). A hardware-sizing lens `/racecar-sysadmin-hardware` proposes an EC2 instance type for a governed repo from evidence: a cheap telemetry probe records one resource-usage line per CLI run, and the lens combines that measured profile with a structural review of the four surfaces. A docs orchestrator `/racecar-docs` composes those generators and checkers into one re-runnable pipeline that stands up the required docs, regenerates the machine-derivable spine without clobbering hand-authored narrative, and closes with a content-blindness leak gate and the coherence gate. One of the generators it drives, `/racecar-cli-docs`, projects a package's `python -m <pkg>…` command tree into per-command `docs/cli/**` pages plus the README's `## CLI` block — generated from the same audit `make arch` runs, so the reference cannot drift from the commands. There are also commit helpers (`/racecar-commit`, `/racecar-commit-preflight`, `/racecar-commit-decompose`), an adoption auditor (`/racecar-normalize`), the nuanced upgrader (`/racecar-upgrade`), and a wiring doctor (`/racecar-doctor`). The always-on baseline (persona, drift doctrine, voice, ownership, commit rules) lives in `shared/`.

*For agents:* you do not read this file. Your machine baseline and the precise topic-to-file routing table live in [`CLAUDE.md`](CLAUDE.md), force-loaded into every session.

## When, where, and why it works this way

The rest is rationale; you do not need it to use racecar.

- **Why deterministic checks, not an AI reviewer.** A check either passes or names a file and a line, and it cannot drift the way an AI reviewer drifts, because the detector is far simpler than the code it watches. In a loop where AI writes the code, a verifier that shares the author's blind spots cannot catch the author's mistakes; a mechanical rule does not share them. So racecar mechanizes everything a rule can decide and leaves only the irreducible to judgment.
- **Where it runs: locally, not as a CI gate.** Enforcement is `pre-commit`, `lint-imports`, and `make check`, on your machine. The owner authorizes; the tooling confirms, it does not decide. A green check is confirmation, not a merge verdict.
- **The standards are falsifiable.** When a real project diverges because racecar's default is wrong, the standard changes, not the project. Racecar is corrected by the repos it is applied to, not the other way around.

## Releases

The current version is in [`VERSION`](VERSION); notable changes per release are in [`CHANGELOG.md`](CHANGELOG.md). racecar is pre-1.0, so a minor bump may carry breaking changes (the upgrade path is `racecar-upgrade`, which reconciles rather than clobbers).
