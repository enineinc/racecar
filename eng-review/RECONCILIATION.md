---
pnode: [README.md]
---

# Reconciliation: a scaffold of manifolds over a private catalog

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

When an engine's output must be tied to reference data, encode reconciliation as a small fixed set of generic operations (manifolds) driven by a private, gitignored catalog, not as one golden test per reference model. This doc is the one home for that pattern: the abstraction, the security partition, the decision rule for choosing it over golden tests, and the honest limits. For general test hygiene, see [`PYTHON.md` §4 Testing](PYTHON.md#4-testing); for naming discipline, [`PYTHON.md` §2 Naming](PYTHON.md#2-naming).

Sections are ordered as a DAG: the abstraction first, the decision rule and the limits last.

## 1. The abstraction

A reconciliation check is one of three general operations run over a catalog, never one bespoke test per model. Three manifolds replace an open-ended pile of per-model files. Adding a model is adding a catalog row, not a test.

- **Tie.** Per catalog entry, produce a series from the engine and the matching authoritative series; assert agreement within tolerance. Parameterized by *producer* (which engine output) and *oracle source* (where the authoritative output comes from — see below). This is the bulk of a golden suite re-expressed as one operation.
- **Identity.** Per entry, assert an accounting or algebraic law holds inside the engine's own output, with no reference needed (cross-foot, decomposition identities such as parts summing to the whole). An invariant is the second manifold, not an exception to generalization.
- **Integrity.** Per reference surface, assert its own structural soundness: expected shape, provenance hashes, no duplicate keys, sentinel values. This validates the extractor independent of any config.

### Oracle sources: handcrafted checksums and real ties

A golden is defined by the provenance of its expected output: an output established *independently of the pipeline*, not one the pipeline emitted. A tie is only as strong as that provenance. The oracle comes from one of two sources, and both are true goldens — they differ only in where the authoritative output originates and whether it can ship.

- **Handcrafted synthetic checksum.** A small `(crafted input, derived output)` pair per transform, where the input is *constructed* to sit on an edge or corner and the output is *derived by hand* from what the transform must do. The oracle is your derivation, so it bears correctness; a self-generated snapshot (output captured from the engine under test) does not. Prefer crafted edges over real examples for two independent reasons. First, real data clusters in the typical region and under-samples the boundaries where transforms actually fail: zero, empty, negative, single element, duplicate key, boundary timestamp, sign flip, rounding at the half, max precision. Second, only an input simple enough to solve by hand yields a genuine independent oracle — a messy real record's "correct" output is almost never hand-derived, so a real-world "golden" quietly degrades into a snapshot. These fixtures name nothing, ship tracked, and run always-on. They pin each transform's logic the way a checksum flips on a single-bit change.
- **Real reference surface.** The engine's configured, end-to-end output tied to an external known-correct model. This is the only proof the whole assembly is right for an actual model. It is confidential, so it lives in the private catalog and runs only where that catalog is present.

| Oracle source | Provenance | Confidential | Proves |
|---|---|---|---|
| Handcrafted synthetic checksum | your independent derivation | no — tracked, always-on | each transform's logic on the hard cases |
| Real reference surface | external known-correct model | yes — private catalog | the configured, end-to-end result for an actual model |

The handcrafted layer certifies each gear is milled right; the real tie certifies the gears are assembled into the right machine for this actual model. The layering is load-bearing, not redundant: per-transform checksums, plus identity invariants on the composition, plus the real tie for config-and-distribution truth, each covering what the others structurally cannot.

## 2. The catalog

The catalog (a manifest) is data, not code. Each entry names a reference surface, the config that drives the engine, and which checks apply with what tolerances. Per-model specifics stop being code and become catalog data that lives outside the repo. "Less specific code" is literal: the specificity moves out of the test tree and out of version control.

- The catalog *schema* is tracked; the catalog *instance* is private.
- One driver iterates the catalog and dispatches each entry to its manifolds. There is one engine, not one test file per model.

This is one home ([`../shared/PRINCIPLES.md`](../shared/PRINCIPLES.md) P-02) applied to test artifacts — the bounded-test-surface corollary: hand-written test code stays constant in the number of models while instances become catalog rows, so the pattern is the enforcement home for that ceiling.

## 3. The partition (the security property)

Split every artifact into tracked and private on one line: does it name a real model or carry real reference data. This partition is the whole security property.

| Tracked (shippable, names nothing) | Private, gitignored (may name anything) |
|---|---|
| the manifold logic (tie / identity / integrity) | the reference data (source models and their extracts) |
| the catalog schema | the catalog instance (which models, surfaces, checks) |
| the extractor and the driver | real config surfaces for actual models |
| unit tests on synthetic fixtures | any check too bespoke to be catalog data yet |

- Tracked code names no model, no model count, no corpus scale.
- A check that has not yet been generalized into catalog data is relocated to the private tree and run locally, never deleted silently.

## 4. The perimeter guarantee

The driver iterates the catalog and nothing else. This yields a two-state guarantee.

- **No catalog present** (fresh clone, CI, anyone outside the perimeter): the driver has nothing to iterate. It reconciles nothing, passes green, and discloses nothing: not the models, not their contents, not that a reference corpus was ever tied.
- **Operator's private catalog present**: the same machinery runs the full real reconciliation locally.

One engine; the content is supplied from outside version control. The always-on tracked run must never depend on private data being present.

## 5. The decision rule: scaffold vs golden tests

Choose the scaffold when ANY of these holds:

1. You have many near-duplicate fixture-driven tests differing only by data (model name, rows, tolerances). Repetition is not coverage.
2. The reference data, or the fact of reconciling against real models, is confidential and must not ship.
3. You reconcile engine output against external reference models that live outside the repo.

Keep plain golden tests when a small, stable, NON-confidential set of fixtures pins behavior and the indirection of a catalog would cost more than it saves. The pattern is not a blanket replacement; state both directions honestly. A handful of committed goldens that name nothing sensitive and rarely change are simpler than a driver plus a schema plus a private manifest.

## 6. Honest limits (veracity and coherence)

Name a tracked test as what it is. Overclaiming is the failure mode here.

- **"Synthetic" and "self-generated" are orthogonal; only the second forfeits correctness.** A self-generated snapshot, whose expected output was captured from the engine under test, can catch *change* but never wrongness. A handcrafted fixture, whose output was derived independently (§1), bears correctness on the corners it covers even though no real data touches it. So the always-on tracked guarantee is stronger than "the manifolds run": it is "each transform is correct on its handcrafted edge cases, the identity invariants hold, and the unit tests pass." What stays conditional on the operator's private catalog narrows to exactly one thing — correctness on the real-world data distribution and the real configurations.
- **Handcrafted checksums prove only the corners you thought of.** They do not certify the enumeration is complete, nor that composition and config wiring are right. That residual is why the real tie is not redundant with them.
- **Name each tracked test as what it is.** Manifold, handcrafted checksum, or snapshot — never "reconciles to the penny." A test that cannot see the real reference and claims to tie to it lies in its name; a snapshot that calls itself a golden overclaims a correctness it does not hold.
- **Number-level disguise cannot hide structure.** A de-identified duplicate that runs the same code carries the same model skeleton; renaming and perturbing magnitudes still exposes it. Keeping the real reference private beats shipping a lookalike.
- **If a disguised fixture is ever used, perturb input leaves only** and recompute downstream in full. Perturb an output and the accounting identities break: either the test fails or the identity was never real.

## 7. Naming discipline

Tracked names, targets, and comments reveal only "a generic reconciliation harness," never a specific historical corpus, model count, or deal name. Use neutral terms: *reference surface*, *catalog*, *manifold*, *tie*, *identity*, *integrity*. This is the scope-honesty rule ([`PYTHON.md` §2 Naming](PYTHON.md#2-naming)) applied to a confidentiality perimeter: the name must not disclose what the tracked tree deliberately withholds.
