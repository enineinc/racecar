---
pnode: [../README.md]
---

<!-- Title alternatives for the author to pick: "Make it a DAG" / "Acyclicity is coherence" -->

# Everything you can trust is a DAG

I have built systems across unrelated domains, from energy markets to regulated data, and the ones that held up shared a shape I did not notice for years. Coherent ideas, the representations that carry them, and the implementations that run them all want to be the same thing: a directed acyclic graph. Not as a coding rule. As the structural form of anything you can order, complete, verify, and reproduce. A cycle is where the trouble enters: ambiguity, drift, and entropy all come in through the same door.

This is a claim across three levels at once. An idea is a DAG. A representation is a DAG. An implementation is a DAG. The levels rhyme because one property governs all three, and that property is worth stating precisely before we use it.

## The one property

A directed acyclic graph has a topological order: an arrangement of its nodes where every edge points forward, so no node ever depends on something later in the line. A graph has such an order exactly when it has no cycle. That single fact buys four things, and they are the four things trust is made of.

You can evaluate it deterministically. Resolve the nodes in dependency order and every input a node needs is already settled before you reach it. There is one canonical order to work in, so there is one answer.

You can complete it. A finite acyclic graph terminates. Walk it in order and you reach an end, because you never revisit a node, so the traversal cannot run forever. Finishing is guaranteed by the shape, not by luck.

You can verify it. Check each node against its predecessors, the nodes it actually depends on, and once you have checked all of them you have checked the whole. Verification is local and it composes.

You can reason locally. A node depends only on its ancestors, so you can understand it by understanding what feeds it, without holding the entire graph in your head.

A cycle destroys all four at once. There is no canonical order, because every candidate order puts some edge backward. There is no termination guarantee, because the traversal can loop. Nothing grounds out, because following dependencies never bottoms into something settled. And you cannot reason piecewise, because the nodes in the cycle depend on each other mutually, so none can be understood before the others. That is why a cycle is the entropy entry point. A DAG is low-entropy by construction: the topological order pins down how things resolve, which is exactly what low entropy means, few allowed outcomes. A cycle injects entropy by removing that order. The shape is the discipline.

## Ideas

A sound argument is a DAG. It grounds out in premises, the nodes with no incoming edges, and each claim rests on prior claims, never on itself. Trace any conclusion back and you reach the premises in finite steps. That is what it means for an argument to ground out: the regress ends.

Circular reasoning is literally a cycle in that graph, a claim that depends, eventually, on itself. It is the oldest named failure of thought, begging the question, and the name has survived because the failure is structural, not stylistic. A good explanation has the same shape: it runs from primitives the reader already accepts to the conclusion you want, with no step that secretly assumes its own output. I will not overstate this. Not every act of thinking is a clean DAG, and minds wander. But when you want an idea someone can check, you give it this form. This essay is ordered most-independent-first for that reason: the property section before the three levels that lean on it. Same discipline, applied to prose.

## Representations

The things we use to hold knowledge are DAGs when they work: taxonomies, type hierarchies, schemas, dependency specifications, knowledge graphs. Each is a set of nodes with directed dependence and no loop.


My clearest case is a taxonomy of subject matter built as a directed acyclic graph. Every concept is a node, every dependency a directed edge, and there are no cycles. The structure is the hard, human part: defining the nodes and edges so the whole graph stays coherent. That acyclic structure is exactly what let a model populate the taxonomy completely without losing coherence. The human defines the shape, and the shape guarantees coherence, because a new entry can only attach to nodes and edges that already exist and can be checked against them. The model supplies completeness at scale, filling the graph far faster than hand curation ever would. A representation with a cycle cannot offer either guarantee. You cannot complete it, because there is no order in which to fill it, and you cannot query it coherently, because a question about one node routes back through itself. The acyclicity is not decoration on the taxonomy. It is what makes the taxonomy trustworthy.

## Implementations

Robust infrastructure is DAGs almost everywhere, and the exceptions are where it hurts. The import or module graph is the plainest example: a cyclic import is the canonical rot, the thing that makes a codebase impossible to load in a defined order or reason about in pieces. racecar enforces acyclicity on that graph as a hard rule, because the cycle is not a style nit, it is the loss of all four guarantees in the code itself.

The pattern repeats once you look. Build systems are DAGs: make and Bazel resolve targets in dependency order and refuse cycles, which is what lets a build be reproducible and incremental. Data pipelines are DAGs when they are sound: a sync step that pulls from the world, then a derive step downstream, no back-edges from derive into sync. Task and workflow graphs are DAGs. Even version history is one: a git commit points back to its parents, never forward, which is what lets you order history and replay it. The places that resist this shape, mutable shared state, tangled service call graphs, are precisely the places that are hard to test, hard to reproduce, and hard to trust.

## The honest boundary

The obvious objection is that the world has cycles. Feedback loops, recursion, social graphs where A follows B follows A, supply chains that loop, domains that are genuinely circular. This is true and I am not going to deny it.

The discipline is not to pretend cycles do not exist. It is to represent a real cycle as explicit data, one stored edge you can point at, and derive everything else from it, rather than letting the cycle live implicitly in your dependency structure or your evaluation order. Keep the machinery acyclic even while modeling a cyclic domain. Push the cycle into data you can see, count, and check, and out of the control flow you cannot. A concrete form of this: a self-referential tree stores the single edge that defines the relation and derives the rest on demand, never caching the derived part back into the definition. The cycle becomes one visible fact instead of a loop hidden in how the system resolves. You lose nothing about the domain and keep the four guarantees about the system.

## The companion

This is the structural method underneath an argument I have made elsewhere, the instrument-not-the-answer essay, about what AI-native actually means. That essay turns on determinism and coherence: build the low-entropy structure by hand, let the model fill it. A DAG is how those two properties are bought. AI populates DAGs, which is completeness at scale. Humans define them, which is coherence. And a cycle is exactly where you would lose both at once, because the order that gives coherence and the termination that gives completeness are the same topological order a cycle removes. The two essays are one claim seen from two sides: there I argued where to put the model, here I am arguing what shape to put it into.

## The test

So here is the discipline as something you can apply before you commit. Before you trust an idea, a model, or a system, ask whether it is a DAG. Can you name a topological order, an arrangement where everything depends only on what came before? If yes, you can evaluate it, finish it, check it, and reason about its parts. If it has a cycle, you have an ungrounded loop, and that is where the entropy lives: the ambiguity, the drift, the thing that will not reproduce. Then you have two honest moves. Make it acyclic. Or make the cycle explicit data, one edge you can see, and keep the machinery around it acyclic. Everything you can trust has a topological order. That is not a metaphor. It is the test.
