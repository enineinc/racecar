---
pnode: [../README.md]
---

# Glossary

Accessed via [`../README.md`](../README.md), the human storefront. Agents receive this file force-loaded via `CLAUDE.md` and do not read README.

Terms used across these standards. Where a term has an authoritative external reference (Wikipedia, a spec, a paper), the link is provided; otherwise the definition is repo-local and internal cross-references point to where the concept is load-bearing.

## DAG — Directed Acyclic Graph

A graph in which edges have direction and no path returns to its start. The import graph required by these standards is a DAG — see [arch-coherence Acyclicity](../arch-coherence/CHECKS.md#1-acyclicity-root-axiom).

External: [Directed acyclic graph (Wikipedia)](https://en.wikipedia.org/wiki/Directed_acyclic_graph).

## Coherence

The architectural property that the dependency graph is acyclic and its direction rules hold: imports flow outward/downward, layers do not leak, peer edges have a pure provider. A coherent codebase is one where local reasoning survives growth — you can change one place and predict what else moves. See [arch-coherence/README.md](../arch-coherence/README.md) for the architectural review checks; the first principle they verify is [P-01](PRINCIPLES.md#p-01-dependencies-form-a-directed-acyclic-graph).

Related: [doc-coherence](../doc-coherence/README.md) — the analogous property applied to documentation.

## Cogency

Internal consistency of an artifact — definitions, examples, and claims agree with each other. A doc that defines a term one way in §2 and uses it differently in §5 lacks cogency. See [doc-coherence "The five document checks"](../doc-coherence/PROTOCOL.md#the-five-document-checks), check 1.

## Resolver

A short routing table that points a reader to the file handling a given topic. A resolver says "for X, see A; for Y, see B" — it does not explain X. [`../README.md`](../README.md) is the resolver for this repo. See [doc-coherence "Mental models"](../doc-coherence/PROTOCOL.md#mental-models).

## Depth-plus-one isolation

A layer describes only what it directly contains (immediate children), never its grandchildren. Each layer owns its own listing; renaming a grandchild should not require edits in a grandparent. See [arch-coherence "Depth-plus-one isolation"](../arch-coherence/CHECKS.md#4-depth-plus-one-isolation) and [arch-coherence/CLI.md](../arch-coherence/CLI.md).

## Outward-downward

The direction imports are allowed to flow: parent to child through the package tree. The inverse (upward) is forbidden for business logic; the environment layer is the sole carve-out. See [arch-coherence Direction](../arch-coherence/CHECKS.md#2-direction).

## Surface

A thin adapter that exposes the library's `api` over one transport, `cli` / `mcp` / `django`. A surface only translates its transport's input, calls `api`, and renders the result; it holds no orchestration policy. One home: [arch-coherence/SURFACES.md](../arch-coherence/SURFACES.md).

## Shape

The packaging form of a repo, computed from the layout rather than declared: `src` (library only), `src+server` (library plus a Django project), or `server` (project only). Orthogonal to surfaces. One home: [arch-coherence/PACKAGING.md](../arch-coherence/PACKAGING.md).

## Vertical

A feature submodule that co-locates one feature's roles, its `lib`, `api`, and surfaces, under `<pkg>/<vertical>/`, so features move independently. See [arch-coherence/SURFACES.md §3](../arch-coherence/SURFACES.md#3-per-vertical-co-location).

## Layer

A tier in the fixed dependency order that dependencies flow down through: `surfaces > api > lib > shared` in the racecar shape, or generically entry points > orchestrators > domain > utilities. Nothing lower imports from higher. See [arch-coherence Layer integrity](../arch-coherence/CHECKS.md#3-layer-integrity).

## Provider (pure)

A types-or-utilities module with no foreknowledge of its consumers, safe to import from any peer because consumption is only reading. A pure provider is the condition that makes a peer edge legal. See [arch-coherence Domain boundaries](../arch-coherence/CHECKS.md#domain-boundaries).

## Data plane / control plane

The data plane is where the bulk of records flow and transforms run; the control plane is the orchestration that routes them. racecar holds that agent-grade software is data-plane-dominant, most defects and most value live there, see [R-07](PRINCIPLES.md#r-07-agent-grade-software-is-data-plane-dominant).

## One-home-per-rule

Every rule lives in exactly one canonical place; other locations point to it, they do not restate it. See [doc-coherence "The five document checks"](../doc-coherence/PROTOCOL.md#the-five-document-checks), check 5.

## Scope honesty

Labels match contents. A file titled "language-agnostic" that is eighty percent one language lies about its scope; rename it. See [doc-coherence "The five document checks"](../doc-coherence/PROTOCOL.md#the-five-document-checks), check 2.

## Drift

Gradual divergence of a system from itself — between two places that should hold the same value (two documents stating one rule, a config value and a constant, two validators enforcing one invariant), or between what the system is and what it was meant to be. Drift is [frame-relative](#frame): the same fact reads as drift at one canvas size and noise at another, so local coherence can still be global drift. The doctrine for fighting it is [DRIFT.md](DRIFT.md).

## Frame

The canvas size at which drift is judged — function, module, or system. There is no "is this drift?" without "against what frame?" A defect's severity is assigned at the frame where its damage lands, which may be larger than the frame where its symptom shows. See [DRIFT.md "Drift is frame-relative"](DRIFT.md#drift-is-frame-relative).
