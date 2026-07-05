# Principles

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

The irreducible first principles racecar is built on. Every rule, lens, and check in this
repo derives from one of the axioms below. This file names the axioms and points to the home
that enforces each; it does not restate those homes (that would be a second home, the drift
this framework exists to prevent). Terminology: [GLOSSARY.md](GLOSSARY.md). The frame for
*why*, argued at length, is [`../MANIFESTO.md`](../MANIFESTO.md).

Scope of this file is **universal**: axioms that hold in every racecar project regardless of
domain. Domain-specific first principles belong in the project that owns the domain, not here
(that is [scope honesty](#i-5-scope-honesty), applied to this document). The gfinfra portfolio's
portfolio- and engine-level axioms live in `gfinfra/PRINCIPLES.md` and cross-reference this
file rather than restate it.

Each axiom is stated in three parts: the **axiom** (one line), the **why** (the failure it
prevents), and **enforced by** (the mechanical check or concrete manifestation, so the axiom is
testable rather than aspirational).

## The axioms

### I-1. One home per artifact

Every artifact, data, function, rule, config value, version, lives in exactly one canonical
place; every other location points to it and does not restate it.

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

### I-2. Enforced, not professed

A rule that matters is a deterministic check that fails at `file:line`. Prose is not
enforcement.

- **Why.** A professed rule rots silently: entropy rises on every commit while a rule nobody
  runs stays green in the reader's imagination only. A check either passes or names the
  violation.
- **Enforced by.** `make check` / `make check-full` / `make arch`; `import-linter`,
  `check_upward_imports`, `check_docs`, the pre-commit hook suite
  ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md) §9). The corollary rule for
  claiming completion: no `done` without the production-path command and its exit code
  ([OPERATIONAL.md](OPERATIONAL.md) rules 7 to 12); a falsifiable doc invariant must have a test
  that fails when it is violated ([OPERATIONAL.md](OPERATIONAL.md) rule 10).

### I-3. Determinism over heuristic; the model is last, never the gate

No LLM in the constant, trustworthy loop. Every gate is a script and an exit code. The model
is used to *mechanize* judgment or for the residue no predicate can decide, fed by deterministic
pre-filtering, never as the arbiter.

- **Why.** The detector must have lower entropy than the thing it watches. An LLM watching an
  LLM is a second source of the same noise: it runs the check differently every time, and you
  cannot tell a real finding from the model having a different day.
- **Enforced by.** Every Tier-2 check is stdlib Python plus exit codes, zero model calls
  ([DRIFT.md](DRIFT.md) Tier 2); role identification is deterministic (name, then manifest, then
  structural inference), never an LLM guess ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md)
  §5); the model is confined to the periodic sweep, fed by the mechanical pre-pass
  ([DRIFT.md](DRIFT.md) Tier 3).

### I-4. Dependencies form a directed acyclic graph

The import graph is a DAG. Imports flow outward and downward (parent to child) or sideways
between peers, never upward; lower layers never import higher ones. The environment layer is the
sole carve-out. Direction and layer integrity are not stricter than acyclicity; they are its
practical, legible form.

- **Why.** A cycle, including one papered over by a lazy import, destroys local reasoning: you
  can no longer change one place and predict what else moves. Upward imports and layer leaks
  reintroduce the cycle the axiom forbids.
- **Enforced by.** The single `import-linter` `layers` contract ([`../arch-coherence/AXIOMS.md`](../arch-coherence/AXIOMS.md),
  [`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §4); `check_upward_imports`; the
  depth-plus-one isolation rule (a layer enumerates only its immediate children). A cycle defaults
  to Blocker and supersedes prose reasoning.

### I-5. Scope honesty

A label means exactly its contents; a file's location means exactly its role. A generic that
carries specifics, or a name that overstates, is a lie the reader cannot see.

- **Why.** A misnamed artifact is drift that no local check catches, because every part is
  locally clean while the whole diverges from what its name promises. Local coherence can be
  global drift ([DRIFT.md](DRIFT.md)).
- **Enforced by.** doc-coherence scope-honesty and file-naming checks
  ([`../doc-coherence/PROTOCOL.md`](../doc-coherence/PROTOCOL.md) checks 2 and 3); role
  identification by declare-then-verify, where a declared `api` that is not the cut vertex is a
  Finding and a vertical you cannot classify is itself the drift
  ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §5).

### I-6. The enforced contract is truth; resolve drift at the largest frame

When prose and the mechanically-enforced contract disagree, the contract is truth and the prose
is the bug. When a drift has symptoms at several frames, resolve it at the largest frame that
explains the symptom, and fix there.

- **Why.** The contract is executed continuously; prose is verified only when someone remembers.
  A defense that is discrete and pull-triggered cannot keep pace with entropy that rises on every
  change. And tidying a local symptom destroys the evidence that pointed at the global root.
- **Enforced by.** "The truth is the `import-linter` contract, not the prose" applied across the
  portfolio (gfinfra `CLAUDE.md`); the frame-aware severity rule, grade at the frame where the
  damage lands ([DRIFT.md](DRIFT.md)); the drift ledger, which floats to the top anything whose
  subject changed since its last verification.

### I-7. Reconcile to source; do not re-derive from memory

Verify a claim against the source's own mechanic, not against activity, a summary, or memory.
Trace to the source; do not reinvent it.

- **Why.** Re-derivation from memory fabricates a plausible-but-wrong second model. Tests
  passing, agents returning, and dashboards reading green are evidence of activity, not proof of
  correctness.
- **Enforced by.** Completion-claim guardrails: numbers that should be equal across agents get
  compared, workaround keywords are stop signals, tests that route around production are bugs
  ([OPERATIONAL.md](OPERATIONAL.md) rules 8, 9, 11). The engine manifestation is the reconcile-to-an-
  extracted-oracle discipline in the gfinfra model engine (`grid == cube`, see
  `gfinfra/PRINCIPLES.md`).

### I-8. Ownership is not delegable

Tooling enables design and confirms correctness. It does not authorize. A green check is
confirmation, not a merge verdict; a failing check does not by itself veto a ship. Enforcement is
local, not a CI gate that decides without the owner in the loop.

- **Why.** An automated gate that makes decisions transfers authority away from the human who is
  accountable for what ships. Responsibility and ownership go together and cannot be moved onto a
  gate, or onto a break-glass clause.
- **Enforced by.** Enforcement is `pre-commit`, `lint-imports`, `make check`, run on the owner's
  machine, never CI-as-gate ([OWNERSHIP.md](OWNERSHIP.md)); racecar deliberately documents no
  escape-hatch procedure, because needing permission to break a rule is unpreparedness to break it.

### I-9. Make the right thing easy; help, not law

The good shape is the default you receive, not a wall you are forced into. Gate genuine defects;
surface choices. A rule that reads as a wall is a defect in the rule.

- **Why.** A wall produces compliance, not understanding, and so fails the second aim (help
  others write good code). Convention spreads where enforcement does not because scaffolding pays
  back on day one, while a gate only ever tells you what you did wrong.
- **Enforced by.** `scripts/init_project.py` hands you the canonical shape pre-wired
  ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §10); advisory detectors exit 0
  by default and report Findings, not Blockers (`check_surface_orchestration`, `--strict` opt-in).
  The test for any check: does the forbidden state ever have a legitimate instance? If yes, detect
  and surface; if never, gate.

## Tensions

Two axioms in genuine tension, and how the framework resolves each.

1. **Enforced-not-professed (I-2) vs help-not-law (I-9).** If everything mechanical becomes a
   hard gate, choices get walled and the framework produces compliance, not understanding. The
   discriminator resolves it: *does the forbidden state ever have a legitimate instance?* Always a
   defect (a cycle) earns a gate; sometimes legitimate (a surface reaching past `api`) earns an
   advisory Finding. Ownership (I-8) breaks the residual tie: the check confirms, the owner
   authorizes.

2. **One home (I-1) vs the deliberately duplicated shape decision.** The shape logic lives in
   two places, `check_packaging.py` (Python) and `racecar.mk` (Make), on purpose: the build must
   determine its own shape with nothing but `make` present, so a foundation cannot depend on an
   external process to know what it is. The resolution is not to wave the duplication away but to
   bound it with a coherence test that holds the two copies in lockstep. One home is the default;
   a forcing constraint is the only license to duplicate, and the copies are then gated by an
   identity check (the same pattern as the inline vocabulary literals, [VOCABULARY.md](VOCABULARY.md)).

## Voice

Common voice: [VOICE.md](VOICE.md).
