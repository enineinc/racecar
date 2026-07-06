---
summary: The frontmatter node-graph standard — every non-CLAUDE doc declares its parent once (pnode); children and peers are derived, never stored; a checker holds the whole doc graph to a DAG.
pnode: [README.md]
---

# The documentation node graph

Every tracked text doc except `CLAUDE.md` carries a small YAML frontmatter block that places it in a graph: it names its **parent** and nothing else about its edges. Children and peers are *computed* from everyone's parent pointer, never written down, so there is one edge to maintain per doc and nothing to keep in sync. A checker assembles the graph and holds it to a single invariant: it is acyclic. This is the [DAG axiom](../shared/PRINCIPLES.md) (P-01) turned on the documentation itself, and [one home](../shared/PRINCIPLES.md) (P-02) applied to the doc tree.

The pattern is generic. Racecar's docs are one instantiation of it; any repo with a node graph in frontmatter is another. This file is the domain-free description; the racecar rollout is its first consumer.

## The reader-first layering

A doc is ordered so a human reading top to bottom meets the most general content first and the machine detail last:

1. **Frontmatter** (this block) — machine-queryable metadata: `summary`, `pnode`, optional `see_also`.
2. **Human lead** — the H1 and a one-to-three sentence plain-language summary of what the doc is and who it is for, before any table, deep section, or script reference. A larger doc adds a short orientation paragraph.
3. **Body** — ordered by decreasing generality: concepts and rationale before reference tables and enforcement wiring.
4. **Machine floor** — the dense, maintainer-facing detail last (script names, section-ref tables, anchors).

`CLAUDE.md` is exempt: it is machine-first by mandate, the force-loaded agent baseline.

## The stored edge, and everything derived from it

- **`pnode`** (parent node) is the one stored edge: the doc(s) this one is *accessed via* / owned by, as relative paths from the doc's own directory. A root (the storefront `README.md`) declares `pnode: []`.
- **Children** are the inverse: every doc that names this one as its `pnode`. Derived by scanning, never stored.
- **Peers** are co-children of the same parent (siblings). Derived, never stored.
- An edge A→B (B's parent is A) is written exactly once, in B's `pnode`. The reverse direction is computed. Storing it twice (a `children:` or `nnode:` list) is a denormalised cache of derived data and is forbidden: it is a second home that drifts (P-02).

This is the correction a prior repo made the hard way: it shipped an `nnode` cache, found it drifting, and retired it. Store the parent; compute the rest.

## Cross-cutting references are orthogonal, not hierarchy

A genuine "see also" to a doc that is neither parent nor child (a lens citing `GLOSSARY.md`) is not a graph edge. It goes in an optional `see_also:` list, a flat cross-cutting layer, added only where a doc really has one. The hierarchy carries ownership; `see_also` carries lateral reference. Keep them apart, and never smuggle a peer or a child into either.

## The checker: `check_doc_graph.py`

Deterministic, stdlib only, no model. Subchecks:

- **types** — every `pnode` (and `see_also`) entry is a relative path that resolves to an existing file (a `SKILL.md` or `CLAUDE.md` target is allowed even though those are exempt from carrying their own `pnode`).
- **dag** — the graph assembled from all `pnode` edges is acyclic.
- **consistency** — where a doc's body carries an `Accessed via` link, that link's target path is among its declared `pnode`. The prose is the human echo of the machine edge; the checker keeps them agreed so neither drifts.

`CLAUDE.md` and each `SKILL.md` are exempt (the machine baseline and the skill definitions, each with its own frontmatter schema); an excluded file may still be a `pnode` *target*. Vendored template trees, the demo, and the generated briefs are out of scope. Every other in-scope doc declares `pnode`, and one missing it is a Finding. The checker reads only the `pnode` and `see_also` lines, so a doc whose other frontmatter is not strict YAML still validates.

## pnode derivation convention (for the migration and for new docs)

- A sub-doc under a lens or skill directory → its directory's `README.md` (e.g. `eng-review/PYTHON.md` → `[README.md]`).
- A skill's `README.md` → its sibling `SKILL.md` (e.g. `create-server/README.md` → `[SKILL.md]`).
- A `shared/*.md` baseline doc → the root storefront (`[../README.md]`).
- A lens or directory `README.md`, and the root `README.md` → resolve to the storefront; the root `README.md` is the graph root with `pnode: []`.
- When a doc already declares `Accessed via [X]`, that `X` is authoritative; the derivation only fills the gap where no such line exists.

## Adding a doc

Declare `pnode` in frontmatter (and `summary` where the reader-first layering wants one), write the human lead, sink the machine detail. Run `check_doc_graph.py`. Do not add a `children`/`nnode` field, ever; children and peers are derived by the checker, never stored.
