---
pnode: [SKILL.md]
---

# Docs Orchestrator

The orchestrator (not a review lens): it composes the doc generators and checkers that already exist into one re-runnable pipeline, and adds only the three pieces nothing else owns. It generates the missing required docs, regenerates the machine-derivable spine without clobbering hand-authored narrative, applies the content-blindness gate, and closes with the coherence and link gate.

Run it with `/racecar-docs`, or `make docs` for the deterministic backbone.

**When to reach for it:** you want the full documentation set stood up, refreshed, and verified in one pass; you are onboarding a repo to racecar's doc standard; or you are publishing a repo content-blind and want the leak guard wired in.

**Not for:** reviewing a single doc for cogency (that is [`../doc-coherence/README.md`](../doc-coherence/README.md)), or writing one shareable brief by hand (that is [`../llm-summary/README.md`](../llm-summary/README.md)). This skill calls both; it does not replace them.

## Composition, not re-implementation

Every capability the orchestrator runs has a home; it owns only the orchestration and the two contracts below. It re-implements nothing, because re-implementing a rule that already has a home is exactly the drift [`../doc-coherence/README.md`](../doc-coherence/README.md) exists to prevent (one home per rule).

| Capability | Composed from |
|---|---|
| Shareable brief (`docs/summary/$REPO.md`) | [`../llm-summary/README.md`](../llm-summary/README.md) (`/racecar-llm-summary`, `check_brief.py`) |
| CLI / REST / MCP surface docs | [`../arch-coherence/scripts/scaffold_surfaces_docs.py`](../arch-coherence/scripts/scaffold_surfaces_docs.py), `check_cli_commands.py` |
| Links, doc graph, subsystem coverage, placement | [`../doc-coherence/README.md`](../doc-coherence/README.md) (`check_docs.py`, `check_doc_graph.py`, `check_subsystem_docs.py`, `check_file_placement.py`) |

## What's here

| Doc | Covers |
|---|---|
| [`ORCHESTRATION.md`](ORCHESTRATION.md) | **Start here.** The required-docs manifest, the four-stage sequence, the no-clobber-but-repair generation contract, and the composition table. |
| [`CONTENT_BLINDNESS.md`](CONTENT_BLINDNESS.md) | The content-blindness contract: the one-home rule definition, the README-frontmatter policy schema, the reusable guard, and how generation becomes content-blind-aware. |

The scripts live under `scripts/`: [`docs_orchestrate.py`](scripts/docs_orchestrate.py) (the composed pipeline runner), [`check_required_docs.py`](scripts/check_required_docs.py) (the repo-root doc spine), and [`check_content_blind.py`](scripts/check_content_blind.py) (the frontmatter-parameterized leak guard). ORCHESTRATION.md and CONTENT_BLINDNESS.md document what each enforces.

Pair with the review lenses under [`../arch-coherence/README.md`](../arch-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md), and [`../doc-coherence/README.md`](../doc-coherence/README.md). The human storefront is the repo [`../README.md`](../README.md).
