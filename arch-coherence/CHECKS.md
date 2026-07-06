---
pnode: [README.md]
---

# Architectural Coherence — Axioms & Review Lens

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Apply this lens to verify a system's architectural DAG: imports are acyclic, dependencies flow in a single direction, layers do not leak, peer edges do not form cycles. For Python, `import-linter` mechanizes the properties; this lens is the reviewer-facing version and also checks whether the documented architecture matches what the code actually does.

## The architecture racecar prescribes: one library, many surfaces

The axioms below protect a specific shape. State the shape first, in plain terms, because every rule in this file exists to serve it.

**What the shape is.** A racecar project is one library exposed through several thin surfaces. Three tiers, each with one job:

- **`lib`, the worker.** The engine: compute, fetch, transform, persist. It does the actual work and knows nothing about who calls it. No input parsing, no credential prompting, no defaulting.
- **`api`, the orchestration.** The worker plus the policy that makes it callable without ceremony: resolve inputs, seed credentials, apply defaults, dispatch to the right worker. This is the one home for that policy.
- **surfaces, the adapters.** `cli`, `mcp`, `django`, and any other entry point. A surface does exactly three things: translate input from its transport, call `api`, render the result in its transport's idiom. No policy lives here.

```
                   ┌──> cli  (__main__)
   lib ──> api ────┼──> mcp
                   └──> django
```

The arrow reads "provides for": `lib` provides for `api`, `api` provides for each surface. The import edges run the reverse (a surface imports `api`, `api` imports `lib`), and the resulting graph is a DAG.

**Why the shape is this and not flatter.** Remove the `api` tier and the orchestration policy has nowhere to live but inside each surface. With three surfaces that is three copies of "resolve inputs, seed credentials, default, dispatch," and three copies is three places the policy drifts out of sync (Tier 1 drift, see [../shared/DRIFT.md](../shared/DRIFT.md)). The `api` tier exists so that policy has exactly one home and the surfaces hold none of it. That is the entire reason for the structure. The four axioms below are how a reviewer verifies the structure stays honest.

The full doctrine (a surface is a wrapper on `api`; the canonical file names that make surfaces autodiscoverable; the single gated `layers` contract plus the advisory detector that *surfaces* — not walls — surface-reaches-past-`api` choices; the role-identification tiers; and the placement principle) lives in [SURFACES.md](SURFACES.md).

These axioms assume a single rooted package tree. Multi-root monorepos are not addressed here; guidance will appear when a concrete pattern emerges.

Pair with [eng-review](../eng-review/README.md) for software-engineering hygiene and [doc-coherence](../doc-coherence/README.md) for prose, cross-references, and file naming.

For language-specific coherence, see [PYTHON.md](PYTHON.md) (module structure, imports, enforcement) and [DJANGO.md](DJANGO.md) (service layer, view layering). The CLI contract — `__main__.py` patterns plus `commands()` / `subcommands()` / `parser()` plus audit JSON schema — has its own document: [CLI.md](CLI.md). The surfaces doctrine introduced above is detailed in full in [SURFACES.md](SURFACES.md). The project-shell contract — `pyproject.toml` (PEP 517/518/621), `Makefile`, virtualenv discipline, an optional `requirements.txt` lockfile (validate-if-present, not canon-generated), racecar's dev tool set, and the PSF/PyPA + community OSS governance rule that excludes VC-backed tooling — lives in [PACKAGING.md](PACKAGING.md). PACKAGING.md is one opinion of how to package, parameterized over the `PYTHON_LIBRARY × DJANGO_PROJECT` shape product (the shapes and their cells live there, one home) sharing the same infrastructure (pyproject.toml at repo root, `make check` gate, racecar dev tool set, no VC-backed tooling).

## How to use this file

1. Load this file in full.
2. If `import-linter` is configured, run it first. Any broken contract is a Blocker and supersedes prose reasoning.
3. Apply the **four axioms and their checks**, in order. If an earlier check fails, later checks are moot — fix upstream first.
4. Scan the **architectural red flags**.
5. Group findings by root cause when one defect has many surface occurrences (one cycle can show up as N lazy-import lines).
6. For prose hygiene, file naming, link integrity, or rule testability → [doc-coherence](../doc-coherence/README.md). For code-level hygiene → [eng-review](../eng-review/README.md).
7. If the artifact passes all four checks and trips no red flags, say so in one line and stop.

Do not summarize the artifact. Go straight to issues.

## The axioms and their checks (DAG-ordered)

Everything below derives from one axiom: **the import graph is acyclic.**

### 1. Acyclicity (root axiom)

The import graph must be a DAG. Any cycle — including one papered over by a lazy import — is a Blocker. **This is non-negotiable.**

When `A` imports `B` which imports `A`, the cycle is an architectural bug. At every level — packages, modules, functions — the dependency graph is a DAG. The fix is structural: extract the shared dependency into a third module that both can import, or move the function to the side that already has the import.

Lazy imports (imports inside functions) are the usual symptom — the quickest way to get a circular import to "compile" is to defer it, which hides the real bug. The rules below describe preferred directions that make acyclicity clear at a glance. They are not stricter than the axiom — they are its practical form.

### 2. Direction

Imports flow outward (parent → child) through the package tree or sideways between peers. Business-logic upward imports are forbidden; the environment layer is the only carve-out.

```
fubar/                ← root package
  foo/                ← child of fubar
    alpha/            ← child of foo; leaf package
      data            ← leaf module
  baz/                ← child of fubar; peer of foo
    alpha/
      data
    bravo/
      calculator
```

**Outward / downward (parent → child).** Always allowed. A parent package imports from its subtree. `fubar` imports from `fubar.foo`. This is the default direction.

**Upward (child → parent).** Forbidden for business logic. The environment-layer exception below is the only carve-out.

**Peer-to-peer (sibling → sibling).** Permitted. Check 1's no-cycles rule is the only constraint. Once `foo` imports `baz`, any return edge from `baz` to `foo` creates a cycle and is rejected by check 1 — no separate peer rule is needed.

#### Environment layer exception

Configuration derived from outside the project — environment variables, `.env` files, CLI flags parsed at the top — is an environment layer. It typically lives in the root package's entry file (in Python: `__init__.py` — see [PYTHON.md §1 Module Structure](PYTHON.md#1-module-structure)) or a dedicated `config`/`core` module. Any module in the tree may import from the environment layer; this is semantically equivalent to importing external state. The outward rule applies to business-logic dependencies, not to environment access.

**Constraint on the environment layer.** The environment layer must not import from its children at module load. Read env, compute constants, done. Importing a child during the layer's initialization reintroduces the very circularity the axiom prevents — the child will try to import back to get its configuration, and the layer is not yet fully initialized.

### 3. Layer integrity

The system has a fixed layer order. Dependencies flow downward through the layered graph:

```
Entry points            ← top layer; imports orchestrators and domain
  Orchestrators         ← coordinates; imports domain
    Domain modules      ← business logic; imports utilities
      Pure utilities    ← math, format, I/O helpers; imports external only
```

Nothing in a lower layer imports from a higher one. A utility that needs orchestration logic is misplaced; move it up, don't reach down.

An *orchestrator* is a module that coordinates domain modules to produce a feature-level outcome — for example, a build script that calls compute, database, and export in sequence; a request handler that composes several services; or a CLI entry point that routes to sub-commands. Orchestrators are stateful in the sense that they know which pieces to run in which order; domain modules and utilities are not.

These four generic tiers are named concretely in the racecar surfaces shape as `surfaces → api → lib → shared` ([SURFACES.md](SURFACES.md)): an *orchestrator* is `api`, *domain modules* are `lib`, *pure utilities* are `shared`, and *entry points* are the surfaces. Same stack, one language-agnostic and one racecar-specific.

#### Domain boundaries

Packages should be loosely coupled, even where peer imports are allowed. Before adding a peer edge:

- Does the graph stay acyclic? (Check 1 is non-negotiable.)
- Is the direction consistent with existing peer edges at that level?
- Would the shared concept fit better one layer up? If two peers would genuinely need to depend on each other mutually, extract to a common parent or a shared utilities module.

Peer imports work when the provider has no foreknowledge of its consumer — a pure types-or-utilities module (shared enums, coordinates, currency types) is safe to import from anywhere because consumption is just reading; the provider needs nothing from the importer. Peer imports fail when consumption requires mutual foreknowledge — the consumer must know the provider's lifecycle, and the provider must know it is being consumed to cooperate. That is "both peers orchestrating each other," the canonical failure mode.

### 4. Depth-plus-one isolation

Each layer enumerates only its immediate children — never grandchildren. The test: can a grandchild be renamed without touching the grandparent's code or docs?

## Mental models

**Outward-downward dependency.** Imports and references flow parent to child, never upward, never across sibling subtrees. If a child names its parent, the boundary is wrong — the shared concept belongs one layer up, or the child is actually a sibling.

**Peer edges need a pure provider.** Peer imports work when one peer is a types/utilities provider and the others consume. They fail when both peers orchestrate each other.

**Env-layer access is not an upward import.** Reading the environment layer is semantically equivalent to reading external state. The outward rule applies to business logic, not to env access.

**Root causes beat surface counts.** A single architectural defect — one cycle, one upward import, one layer leak — often surfaces as many errors. Report the defect once; list the symptoms as children.

## Red flags — architectural

- Lazy imports (imports inside functions, methods, or conditional blocks) — usually paper over a cycle.
- A utility module that imports a domain or orchestration module.
- Peer packages that mutually orchestrate — extract to a common parent.
- Symbols re-exported up through a parent's `__init__.py` to satisfy an upward importer (the upward importer is the bug).
- Tests that exercise architecture (import reachability) rather than logic.
- `import-linter` contract claims a layer that the code no longer matches.
- A grandchild's internal structure enumerated in a grandparent's CLI listing or doc.
- Environment-layer module that imports from children at load time.

## Decision patterns — architectural

- **Evidence over vibes.** If a cycle is claimed, cite the `import-linter` contract output or the two offending lines.
- **Structural fix over lazy import.** The lazy import is the loan; the structural fix is the repayment. Don't take the loan.
- **Challenge the layer placement.** If a utility needs orchestration logic, the logic is misplaced. If an orchestrator reaches down to a utility that then needs upward access, the utility is misplaced.
- **Roll up before reporting.** One cycle that produces N lazy-import lines is one issue with N occurrences.

## Feedback format

- Group findings by root cause. One root per numbered block; children listed beneath as indented occurrences.
- Each root: `File/Topic — severity — one-sentence description`.
- Severity values are literal: **Blocker / Major / Minor / Nit**. Cycles and upward-import violations default to Blocker; layer slips default to Major; depth-plus-one leaks default to Minor. These are defaults; frame can override them — grade at the frame where the damage lands ([../shared/DRIFT.md](../shared/DRIFT.md#drift-is-frame-relative)).
- No preamble. Start with root 1.
- End with a single verdict line. Verdict values are literal: **Ship / Revise / Rework**.

Example (shape only — substitute the artifacts under review):

```
1. Root: import cycle fubar.foo ↔ fubar.baz — Blocker — fubar/foo/x.py imports fubar.baz at module load; fubar/baz/y.py imports fubar.foo via lazy import in get_config().
   - fubar/baz/y.py:42 — `from fubar.foo import X` inside get_config().
   - fubar/foo/x.py:7 — `from fubar.baz import Y` at module scope.
2. Root: utility imports orchestration — Major — fubar/utils/date.py imports fubar.billing.invoice. Utilities must not reach upward.
   - fubar/utils/date.py:5 — upward import.
3. fubar/__main__.py — Minor — Root CLI listing enumerates grandchildren of fubar.foo.alpha; depth-plus-one violation.

Verdict: Rework. Root 1 must resolve before anything else; root 2 next; issue 3 on the follow-up.
```

## Enforcement

For how the axioms above are verified mechanically in Python projects, see [PYTHON.md §4 Enforcement](PYTHON.md#4-enforcement).

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).

## Invocation

> Load `arch-coherence/AXIOMS.md`. Review this architecture for cycles, upward imports, and layer violations. Run `import-linter` first if configured.

> Using `arch-coherence/AXIOMS.md`, check whether the architecture the docs describe matches the import graph the code actually has.

If the artifact passes all four checks and trips no architectural red flags, say so in one line and stop.
