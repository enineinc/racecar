---
pnode: [SKILL.md]
---

# Engineering Review

The code-quality lens: a racecar pre-pass and post-pass wrapped around gstack's `/plan-eng-review`. It catches engineering defects that pass tests but cost later: stubs and mocks left in, type-hint lies, missing operational traceability, Python and Django hygiene slips.

Run it with `/racecar-eng-review`.

**When to reach for it:** reviewing code for engineering quality, wrapping gstack's eng review with racecar's Python/Django checks, or auditing for stubs, mocks, and ops gaps before shipping.

**What a finding looks like:** a service-layer function named `get_active_users()` that also writes an audit row: the name claims a read, the body does a write. *Major: the name lies about the side effect.*

## What's here

| Doc | Covers |
|---|---|
| [`WORKFLOW.md`](WORKFLOW.md) | **Start here.** The review procedure: the three-phase workflow (pre-pass → gstack → post-pass), the two engineering checks, red flags, feedback format. |
| [`PYTHON.md`](PYTHON.md) | Python hygiene: naming, formatting, testing, linting, the Definition of Done. |
| [`DJANGO.md`](DJANGO.md) | Django hygiene: DB and query performance, security, framework idioms. |
| [`RECONCILIATION.md`](RECONCILIATION.md) | When reconciliation tests should be a scaffold of generic manifolds (tie / identity / integrity) over a private catalog, instead of model-named golden tests that expose data and duplicate. |

Pair with [`../arch-coherence/README.md`](../arch-coherence/README.md) for the import graph and [`../doc-coherence/README.md`](../doc-coherence/README.md) for docs. The human storefront is the repo [`../README.md`](../README.md).
