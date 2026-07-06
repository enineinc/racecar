---
pnode: [../README.md]
---

# Ownership

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first

Tooling in this framework enables design and confirms correctness. It does not authorize.

Formatters, linters, type checkers, `import-linter`, and the review lenses — [`../arch-coherence/README.md`](../arch-coherence/README.md), [`../doc-coherence/README.md`](../doc-coherence/README.md), [`../eng-review/README.md`](../eng-review/README.md) — catch classes of error mechanically. They are confirmation the owner can rely on — not gates that replace the owner's judgment. A passing lint does not authorize a merge; a failing lint does not, by itself, veto one.

Ownership and responsibility go hand in hand. Responsibility for what ships stays with the human owner and cannot be delegated away, even to good tooling. Automated gates that make decisions transfer authority away from the owner; this framework deliberately stops short of that. Enforcement is local (`pre-commit`, `lint-imports`, `make check`) rather than CI-as-gate because local tooling lets the owner see the result and decide, while pipeline gates decide without the owner in the loop.

The pattern generalizes beyond lint. A review-lens output is confirmation the reviewer can act on, not a verdict that binds. A typed signature is a claim the author is making, not a proof. Tools narrow what could go wrong; they do not replace the owner's accountability for what does.

Breaking the rules works the same way. Needing permission to break the rules is an indication of unpreparedness to break them for the right reason. This framework deliberately does not document escape-hatch procedures — owner judgment is no more delegable to a break-glass clause than to a merge gate.
