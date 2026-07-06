---
pnode: [README.md]
---

# Django — Architectural Coherence

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Django-specific architectural coherence — how the app layers. Django implies Python; for general Python coherence see [`PYTHON.md`](PYTHON.md). For Django engineering hygiene (database/performance, security), see [`../eng-review/DJANGO.md`](../eng-review/DJANGO.md). For the language-agnostic checks, see [`CHECKS.md`](CHECKS.md).

Service-layer separation and layered request flow apply the [domain-boundaries](CHECKS.md#domain-boundaries) and [layer-integrity](CHECKS.md#3-layer-integrity) axioms at the framework level.

This file is intentionally sparse. Standards here are added only when a concrete pattern has emerged in the project; we do not manufacture content ahead of need.

## 1. Module Structure

How Django code is organized. Independent of runtime behavior.

**Service layer.** All business logic resides in `services/<service_name>.py` — not in views, not in models. The app stays a single deployable unit with clear internal module boundaries.

**Models.** Handle data persistence only. No business logic.

**Views.** Handle HTTP request/response only. Use Class-Based Views (CBVs). For access-control mixins on CBVs (`LoginRequiredMixin`, `PermissionRequiredMixin`), see [`../eng-review/DJANGO.md` §2 Security](../eng-review/DJANGO.md#2-security).

## 2. ORM Relations

How models reference each other across modules.

**No cross-module string references in `ForeignKey`, `OneToOneField`, or `ManyToManyField`.** Pass the imported model class — never `'app.Model'` or `'Model'` referring to a model defined in another module. Cross-module string references are the ORM analog of a lazy import: they let two modules reference each other without either import appearing in the graph, papering over a cycle that violates [`CHECKS.md` §1 Acyclicity](CHECKS.md#1-acyclicity-root-axiom). If you cannot import the target model without a cycle, the relation is the symptom; the cycle is the bug. Fix it structurally — extract the shared concept to a parent module both can import, split the model, or move the FK to the side that already imports the other.

**Exempt forms** (no module boundary crossed, so no cycle can hide):

- **`settings.AUTH_USER_MODEL`** — the swappable user FK. Django resolves it at app-ready time; this is environment-layer access (see [`CHECKS.md` Environment layer exception](CHECKS.md#environment-layer-exception)), not an inter-module import.
- **`"self"`** — the only way to self-reference inside a class body.
- **Same-file unqualified strings** — `models.ForeignKey("Foo", ...)` where `Foo` is defined later in the same file is a forward reference inside one module. Architecturally inert. Reorder the class definitions if you want the symbol form; the detector ignores these.
- **Files under `migrations/`** — Django generates these mechanically and `app_label.model` strings are how migrations serialize relationships. Not hand-written architectural choices; the detector skips them.

**Detection.** `scripts/check_dj_model_ref_as_string.py` enforces this rule across every package listed in `[tool.importlinter].root_packages`. It takes the contract from the library pyproject (via the project shape) and globs each named package from the project tree, finding it wherever it lives across the source roots rather than assuming the repo root. It cross-references Django's `INSTALLED_APPS` (read via `manage.py shell`) and the layered DAG from `[tool.importlinter].contracts`, then reports two sections:

- **LIVE** — file's app is in `INSTALLED_APPS`. Each entry is annotated with the file's DAG layer and, when the target app resolves, the target's layer plus an `UPWARD DAG cross` flag if the target sits above the file. A Blocker.
- **NOOP** — file's app is NOT in `INSTALLED_APPS`. Django will not load these models; the violation is dead code. Decide between deletion and registration.
