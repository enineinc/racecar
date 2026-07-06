---
pnode: [SKILL.md]
---

# Documentation Coherence

The lens that keeps docs honest: links resolve, section numbers match, a rule lives in exactly one home, and a filename describes its function. It pairs an update protocol (what to do when you touch a doc) with a review lens (what to verify before it ships).

Run it with `/racecar-doc-coherence`, or `make check-docs` for the mechanical pre-pass (`make docs` in a consuming project, which also runs the subsystem, TODO, placement, and brief checks).

**When to reach for it:** reviewing docs, checking link integrity, auditing doc-vs-code drift, or before shipping any documentation change.

**What a finding looks like:** a script docstring says "enforces §4" but the rule moved to §3: the pointer lies. *Major: fix the pointer the moment the rule moves.*

## What's here

| Doc | Covers |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | **Start here.** The lens: the update protocol (PRESERVE / ADD / UPDATE / DELETE / REVIEW), the mechanical pre-pass, the five document checks, documentation placement, feedback format. |
| [`DOC_GRAPH.md`](DOC_GRAPH.md) | The `pnode` frontmatter node-graph standard: each doc declares its parent once, children and peers are derived, and the whole doc graph is held to a DAG. |

The mechanical checks live under `scripts/`: `check_docs.py` (links, section refs, vocabulary), `check_doc_graph.py` (the `pnode` graph: targets exist, the graph is acyclic, `Accessed via` agrees with `pnode`), `check_file_placement.py` (resolver reachability: every doc must be reachable by link from a README, the root CLAUDE.md, or a SKILL.md), `check_subsystem_docs.py`, and `check_todo_format.py`. `PROTOCOL.md` and `DOC_GRAPH.md` document what each enforces.

Pair with [`../arch-coherence/README.md`](../arch-coherence/README.md) for architecture and [`../eng-review/README.md`](../eng-review/README.md) for code. The human storefront is the repo [`../README.md`](../README.md).
