# Glossary

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Terms used across these standards. Where a term has an authoritative external reference (Wikipedia, a spec, a paper), the link is provided; otherwise the definition is repo-local and internal cross-references point to where the concept is load-bearing.

## DAG — Directed Acyclic Graph

A graph in which edges have direction and no path returns to its start. The import graph required by these standards is a DAG — see [arch-coherence Acyclicity](../arch-coherence/README.md#1-acyclicity-root-axiom).

External: [Directed acyclic graph (Wikipedia)](https://en.wikipedia.org/wiki/Directed_acyclic_graph).

## Coherence

The architectural property that the dependency graph is acyclic and its direction rules hold: imports flow outward/downward, layers do not leak, peer edges have a pure provider. A coherent codebase is one where local reasoning survives growth — you can change one place and predict what else moves. See [arch-coherence/README.md](../arch-coherence/README.md) for the axioms and review checks.

Related: [doc-coherence](../doc-coherence/README.md) — the analogous property applied to documentation.

## Cogency

Internal consistency of an artifact — definitions, examples, and claims agree with each other. A doc that defines a term one way in §2 and uses it differently in §5 lacks cogency. See [doc-coherence "The five document checks"](../doc-coherence/README.md#the-five-document-checks), check 1.

## Resolver

A short routing table that points a reader to the file handling a given topic. A resolver says "for X, see A; for Y, see B" — it does not explain X. [`../README.md`](../README.md) is the resolver for this repo. See [doc-coherence "Mental models"](../doc-coherence/README.md#mental-models).

## Depth-plus-one isolation

A layer describes only what it directly contains (immediate children), never its grandchildren. Each layer owns its own listing; renaming a grandchild should not require edits in a grandparent. See [arch-coherence "Depth-plus-one isolation"](../arch-coherence/README.md#4-depth-plus-one-isolation) and [arch-coherence/PYTHON.md §3 CLI](../arch-coherence/PYTHON.md#3-cli).

## Outward-downward

The direction imports are allowed to flow: parent to child through the package tree. The inverse (upward) is forbidden for business logic; the environment layer is the sole carve-out. See [arch-coherence Direction](../arch-coherence/README.md#2-direction).

## One-home-per-rule

Every rule lives in exactly one canonical place; other locations point to it, they do not restate it. See [doc-coherence "The five document checks"](../doc-coherence/README.md#the-five-document-checks), check 5.

## Scope honesty

Labels match contents. A file titled "language-agnostic" that is eighty percent one language lies about its scope; rename it. See [doc-coherence "The five document checks"](../doc-coherence/README.md#the-five-document-checks), check 2.

## Drift

Gradual divergence between two places that should hold the same value — two documents stating the same rule, a config value and a constant, two validators enforcing the same invariant. Duplication is drift waiting to happen. See [doc-coherence "Mental models"](../doc-coherence/README.md#mental-models), "Duplication is drift."
