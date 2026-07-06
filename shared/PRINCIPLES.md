---
pnode: [../README.md]
---

# Principles

Accessed via [`../README.md`](../README.md), the human storefront. Agents receive this file force-loaded via `CLAUDE.md` and do not read README.

The irreducible first principles racecar is built on. Every rule, lens, and check in this repo
derives from one of the axioms below. Every axiom is a principle, of two kinds. A **known
principle** (P-nn) is established and rests on a theorem, a tautology, or long-settled practice;
racecar adopts it. A **racecar principle** (R-nn) is a stance racecar takes, chosen and defended
by its results. Both are held and enforced with the same conviction; the split names where a
principle comes from, not how firmly it is held. Within each group the axioms run in dependency
order, foundational first, so this file is itself a DAG (P-01), the axiom applied to the axioms
that contain it.

This file names the axioms and points to the home that enforces each; it does not restate those
homes (that would be a second home, the drift this framework exists to prevent). Terminology:
[GLOSSARY.md](GLOSSARY.md). The frame for *why*, argued at length, is
[`../MANIFESTO.md`](../MANIFESTO.md).

Each axiom holds wherever it applies. One a given project never exercises (the data-plane
racecar principle in a control-plane-only app, the acyclicity axiom in a project with no cycle to make) is
vacuously satisfied, not demoted; an axiom cannot be made untrue by a context that never reaches
it. Another portfolio's own principles (the gfinfra portfolio- and engine-level axioms) live in
that portfolio and cross-reference this file rather than restate it.

Each axiom is stated in five parts: the **axiom** (one line), what it **rests on** (the theorem,
tautology, or chosen value that grounds it, and the ground is what sorts it into a known or a
racecar principle), the **why** (the failure it prevents), **enforced by** (the mechanical check or
concrete manifestation, so the axiom is testable rather than aspirational), and its **origin**
(the prior art it descends from, credited where an author is known and marked folk where none is;
racecar originates none of them).

## Known principles

Established, and borrowed. Each rests on a theorem, a tautology, or long-settled practice; only
whether you want the payoff is chosen.

### P-01. Dependencies form a directed acyclic graph

The import graph is a DAG. Imports flow outward and downward (parent to child) or sideways
between peers, never upward; lower layers never import higher ones. The environment layer is the
sole carve-out. Direction and layer integrity are not stricter than acyclicity; they are its
practical, legible form.

- **Rests on.** A topological order and change-locality exist if and only if the graph is acyclic.
  A cycle is an objective, decidable fact.
- **Why.** A cycle, including one papered over by a lazy import, destroys local reasoning: you
  can no longer change one place and predict what else moves. Upward imports and layer leaks
  reintroduce the cycle the axiom forbids.
- **Enforced by.** The single `import-linter` `layers` contract ([`../arch-coherence/CHECKS.md`](../arch-coherence/CHECKS.md),
  [`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §4); `check_upward_imports`; the
  depth-plus-one isolation rule (a layer enumerates only its immediate children). A cycle defaults
  to Blocker and supersedes prose reasoning.
- **Origin.** The Acyclic Dependencies Principle (Robert C. Martin), on Parnas's "uses" hierarchy
  and Lakos's levelization.

### P-02. One home per artifact

Every artifact, data, function, rule, config value, version, lives in exactly one canonical
place; every other location points to it and does not restate it.

- **Rests on.** Two independently edited copies have a nonzero divergence probability; one copy
  has none.
- **Why.** Two homes for one fact is two places it diverges, which is zero places it holds
  reliably. Duplication is drift in waiting; eliminating the surface is the only tier that
  prevents drift rather than detecting it after ([DRIFT.md](DRIFT.md) Tier 1).
- **Enforced by.** doc-coherence one-home-per-rule check and vocabulary-identity check
  ([`../doc-coherence/PROTOCOL.md`](../doc-coherence/PROTOCOL.md), `scripts/check_docs.py`); the
  single version home ([COMMITS.md](COMMITS.md), `scripts/check_version_bump.py`); shape computed
  from the layout rather than a declared `shape =` key ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)
  §Scope); `__init__.py` is namespace-only so no symbol gets a second home
  ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §6); TODO federation by concern
  with `TODO.md` as a resolver, not a second copy ([TODO_FORMAT.md](TODO_FORMAT.md)).
- **Corollary — bounded test surface.** One home applied to test artifacts: hand-written test
  *code* stays O(1) in models (a few generic manifolds plus one driver), while test *instances* are
  bounded by configs × transforms and realized as catalog data, not new files per model. That
  product is the ceiling: any count above it is duplication (this axiom), and any fixture that
  carries a real model to reach it is exposure ([scope honesty](#r-04-scope-honesty)). The
  mechanism, the manifolds, and the private catalog are homed in
  [`../eng-review/RECONCILIATION.md`](../eng-review/RECONCILIATION.md) (not restated here).
- **Origin.** DRY and single source of truth (Hunt and Thomas, *The Pragmatic Programmer*).

### P-03. Reconcile to source; do not re-derive from memory

Verify a claim against the source's own mechanic, not against activity, a summary, or memory.
Trace to the source; do not reinvent it.

- **Rests on.** A finite passing test suite does not entail correctness (Dijkstra), and memory is
  lossy, so re-derivation can diverge from the source.
- **Why.** Re-derivation from memory fabricates a plausible-but-wrong second model. Tests
  passing, agents returning, and dashboards reading green are evidence of activity, not proof of
  correctness.
- **Enforced by.** Completion-claim guardrails: numbers that should be equal across agents get
  compared, workaround keywords are stop signals, tests that route around production are bugs
  ([OPERATIONAL.md](OPERATIONAL.md) rules 8, 9, 11). The engine manifestation is the reconcile-to-an-
  extracted-oracle discipline in the gfinfra model engine (`grid == cube`, see
  `gfinfra/PRINCIPLES.md`).
- **Origin.** Dijkstra: testing shows the presence, not the absence, of bugs. The trace-to-source
  discipline itself is folk engineering, no single owner.

### P-04. Resolve drift at the largest frame that explains the symptom

When a drift shows symptoms at several frames, resolve it at the largest frame that explains the
symptom, and fix there. A local symptom and its root often sit at different frames; tidying the
symptom leaves the cause.

- **Rests on.** A defect and its symptom can occupy different frames; removing the symptom does not
  remove the cause, so the defect regenerates from the frame left untouched.
- **Why.** Tidying a local symptom destroys the evidence that pointed at the global root, and the
  root, still there, resurfaces elsewhere. Grading and fixing at the frame where the damage lands is
  what makes a fix hold rather than recur.
- **Enforced by.** The frame-aware severity rule, grade at the frame where the damage lands
  ([DRIFT.md](DRIFT.md)); and, planned but not yet built, a drift ledger to float to the top
  anything whose subject changed since its last verification ([DRIFT.md](DRIFT.md) "The ledger"
  frames it as the aspirational clock).
- **Origin.** Root-cause over symptom (Ohno's five whys, Toyota).

### P-05. Idempotent by default; re-running changes nothing

An operation applied twice leaves the state it left when applied once. Scaffolders, installers, syncs,
and gates are safe to re-run; re-execution is the ordinary case, not the error path. An operation that
cannot be idempotent says so and refuses a blind repeat rather than double-applying.

- **Rests on.** f applied twice equals f applied once is a definition; safe-to-re-run follows from
  it.
- **Why.** A step unsafe to repeat forces the operator to remember whether it already ran, the exact
  invisible state the framework refuses to trust ([reconcile to source](#p-03-reconcile-to-source-do-not-re-derive-from-memory)).
  After a partial failure, non-idempotent tooling makes recovery a gamble, so drift accumulates in the
  one place automation was meant to remove it. Idempotency is also what lets a gate run continuously at
  no cost ([enforced, not professed](#r-02-enforced-not-professed-the-enforced-contract-is-truth)) and a scaffold be re-applied as the
  canon evolves ([make the right thing easy](#r-06-make-the-right-thing-easy-help-not-law)).
- **Enforced by.** The scaffolding cascade writes only its own layer and refuses when its precondition
  is absent, never clobbering or double-writing (`create-package` / `create-server` / `secure-server`,
  [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md)); `./install` and
  `sync_claude_md.py` refuse to overwrite a present-but-wrong file instead of blindly rewriting it; the
  check scripts are read-only and exit-code-pure, so re-running a gate has no side effect; `render_tree`
  is a copy-plus-overlay projection, re-runnable, not a patch.
- **Origin.** Idempotence is mathematics (an idempotent element) and distributed-systems practice
  (HTTP method semantics); no single owner.

## Racecar principles

Stances racecar takes: chosen, some contrarian, held with the same force as a known one and
defended by results, not proof.

### R-01. A detector must have lower entropy than what it watches

A detector must have lower entropy than the thing it watches. A generator cannot be its own gate,
and an observer as noisy as its subject cannot separate signal from its own variance.

- **Rests on.** An instrument must be more stable than what it measures; an observer with entropy
  equal to or above its subject adds noise rather than reading it.
- **Why.** If the detector varies as much as the watched thing, a real finding is indistinguishable
  from the detector having a different day. This is the keystone: checks-over-prose
  ([R-02](#r-02-enforced-not-professed-the-enforced-contract-is-truth)) and model-last
  ([R-03](#r-03-determinism-over-heuristic-the-model-is-last-never-the-gate)) are both this law
  applied, and the permanence argument ([`../MANIFESTO.md`](../MANIFESTO.md)) rests entirely on it.
- **Enforced by.** Every gate is a deterministic script with an exit code, auditable once and then
  trusted; the model is confined to the residue no predicate can decide and is never the arbiter
  (R-02, R-03); a generator (an LLM) is never wired to gate its own output ([DRIFT.md](DRIFT.md):
  the detector must have lower entropy than the thing it watches).
- **Origin.** Requisite variety (Ashby, cybernetics) and the reproducibility instinct (reproducible
  builds; control theory keeps a nondeterministic component out of the loop). The detector-entropy
  framing is racecar's operative statement of it, not an original law.

### R-02. Enforced, not professed; the enforced contract is truth

A rule that matters is a deterministic check that fails at `file:line`; prose is not enforcement.
When prose and the mechanically-enforced contract disagree, the contract is truth and the prose is
the bug.

- **Rests on.** An unexecuted rule gives no runtime signal, and a rule that gives no signal rots;
  the executed contract is what runs, by definition, while prose is only a claim about it.
- **Why.** A professed rule rots silently: entropy rises on every commit while a rule nobody runs
  stays green in the reader's imagination only. The contract is executed continuously; prose is
  verified only when someone remembers, and a defense that is discrete and pull-triggered cannot
  keep pace. A check either passes or names the violation.
- **Enforced by.** `make check` / `make check-full` / `make arch`; `import-linter`,
  `check_upward_imports`, `check_docs`, the pre-commit hook suite
  ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md) §9); "the truth is the
  `import-linter` contract, not the prose" applied across the portfolio (gfinfra `CLAUDE.md`). The
  corollary rule for claiming completion: no `done` without the production-path command and its exit
  code ([OPERATIONAL.md](OPERATIONAL.md) rules 7 to 12); a falsifiable doc invariant must have a test
  that fails when it is violated ([OPERATIONAL.md](OPERATIONAL.md) rule 10).
- **Origin.** The lint and policy-as-code tradition; "the running system is the truth" is folk, no
  single owner.

### R-03. Determinism over heuristic; the model is last, never the gate

No LLM in the constant, trustworthy loop. Every gate is a script and an exit code. The model
is used to *mechanize* judgment or for the residue no predicate can decide, fed by deterministic
pre-filtering, never as the arbiter.

- **Rests on.** [R-01](#r-01-a-detector-must-have-lower-entropy-than-what-it-watches): a detector
  must have lower entropy than the thing it watches, so a generator cannot be its own gate.
- **Why.** An LLM watching an LLM is a second source of the same noise (R-01): it runs the check
  differently every time, and you cannot tell a real finding from the model having a different day.
- **Enforced by.** Every Tier-2 check is stdlib Python plus exit codes, zero model calls
  ([DRIFT.md](DRIFT.md) Tier 2); role identification is deterministic (name, then manifest), never
  an LLM guess ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md)
  §5); the model is confined to the periodic sweep, fed by the mechanical pre-pass
  ([DRIFT.md](DRIFT.md) Tier 3).
- **Origin.** The reproducibility instinct (reproducible builds; control theory keeps a
  nondeterministic component out of the loop). Turning it on the model in the loop is racecar's
  stance, not an original idea.

### R-04. Scope honesty

A label means exactly its contents; a file's location means exactly its role. A generic that
carries specifics, or a name that overstates, is a lie the reader cannot see.

- **Rests on.** A name is a promise; a label that overstates is a lie the reader cannot see.
- **Why.** A misnamed artifact is drift that no local check catches, because every part is
  locally clean while the whole diverges from what its name promises. Local coherence can be
  global drift ([DRIFT.md](DRIFT.md)).
- **Enforced by.** doc-coherence scope-honesty and file-naming checks
  ([`../doc-coherence/PROTOCOL.md`](../doc-coherence/PROTOCOL.md) checks 2 and 3); role
  identification by declare-then-verify — a name or manifest declares each role and the advisory
  detector surfaces an `api` fronting no `lib` or orchestration restated across surfaces
  ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §5, §7). A declared `api` that
  is not the structural cut vertex is drift a reviewer catches, not a mechanized gate.
- **Origin.** Naming as a promise and the principle of least astonishment; folk, no single owner.
  Adjacent to Parnas's information hiding.

### R-05. Ownership is not delegable

Tooling enables design and confirms correctness. It does not authorize. A green check is
confirmation, not a merge verdict; a failing check does not by itself veto a ship. Enforcement is
local, not a CI gate that decides without the owner in the loop.

- **Rests on.** A gate that decides moves accountability off the human who ships.
- **Why.** An automated gate that makes decisions transfers authority away from the human who is
  accountable for what ships. Responsibility and ownership go together and cannot be moved onto a
  gate, or onto a break-glass clause.
- **Enforced by.** Enforcement is `pre-commit`, `lint-imports`, `make check`, run on the owner's
  machine, never CI-as-gate ([OWNERSHIP.md](OWNERSHIP.md)); racecar deliberately documents no
  escape-hatch procedure, because needing permission to break a rule is unpreparedness to break it.
- **Origin.** "You build it, you run it" (Werner Vogels), and Deming's refusal to inspect quality
  in after the fact.

### R-06. Make the right thing easy; help, not law

The good shape is the default you receive, not a wall you are forced into. Gate genuine defects;
surface choices. A rule that reads as a wall is a defect in the rule.

- **Rests on.** A wall produces compliance, not understanding.
- **Why.** A wall produces compliance, not understanding, and so fails the second aim (help
  others write good code). Convention spreads where enforcement does not because scaffolding pays
  back on day one, while a gate only ever tells you what you did wrong.
- **Enforced by.** `scripts/init_project.py` hands you the canonical shape pre-wired
  ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §10); advisory detectors exit 0
  by default and report Findings, not Blockers (`check_surface_orchestration`, `--strict` opt-in).
  The test for any check: does the forbidden state ever have a legitimate instance? If yes, detect
  and surface; if never, gate.
- **Origin.** The paved road / golden path (Netflix, Spotify) and the pit of success (Rico
  Mariani); affordances (Donald Norman).

### R-07. Agent-grade software is data-plane-dominant

Agent-grade software connects to real data: broad in volume, shallow in complexity. The more
useful the package, the more data it moves and the smaller the ORM-governed fraction becomes. So
the library is the center, holding the data plane, and the ORM is confined to a control-plane
server that never touches it.

- **Rests on.** The more useful the package, the more data it moves and the smaller the
  ORM-governed fraction becomes.
- **Why.** The ORM is a control-plane tool (auth, config, audit, identity: low-volume,
  relational), right for that and wrong for a shallow high-volume firehose. A repo that puts the
  ORM at the center governs the part that shrinks as the system gets more useful, and neglects the
  part that grows.
- **Enforced by.** The `src` / `server` shape split (the library Django-free at `src/<pkg>`, the
  ORM confined to `server/`), read off disk by the shape detector
  ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)); surfaces are thin adapters
  over one `api`.
- **Origin.** The data-plane / control-plane split is standard systems vocabulary, no single
  owner; the claim that agent-grade software is data-plane-dominant is racecar's stance, held as a
  bet.

## Tensions

Two axioms in genuine tension, and how the framework resolves each.

1. **Enforced-not-professed (R-02) vs help-not-law (R-06).** If everything mechanical becomes a
   hard gate, choices get walled and the framework produces compliance, not understanding. The
   discriminator resolves it: *does the forbidden state ever have a legitimate instance?* Always a
   defect (a cycle) earns a gate; sometimes legitimate (a surface reaching past `api`) earns an
   advisory Finding. Ownership (R-05) breaks the residual tie: the check confirms, the owner
   authorizes.

2. **One home (P-02) vs the deliberately duplicated shape decision.** The shape logic lives in
   two places, `check_packaging.py` (Python) and `racecar.mk` (Make), on purpose: the build must
   determine its own shape with nothing but `make` present, so a foundation cannot depend on an
   external process to know what it is. The resolution is not to wave the duplication away but to
   bound it with a coherence test that holds the two copies in lockstep. One home is the default;
   a forcing constraint is the only license to duplicate, and the copies are then gated by an
   identity check (the same pattern as the inline vocabulary literals, [VOCABULARY.md](VOCABULARY.md)).

## Voice

Common voice: [VOICE.md](VOICE.md).
