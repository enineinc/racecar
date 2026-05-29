# Django — Engineering Hygiene

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

Django-specific runtime and security hygiene. For Django architectural coherence (module structure, service-layer separation, view layering), see [`../arch-coherence/DJANGO.md`](../arch-coherence/DJANGO.md). For general Python hygiene, see [`PYTHON.md`](PYTHON.md).

## 1. Database & Performance

Runtime patterns.

- **N+1 prevention.** Querysets must use `.select_related()` (FK/OneToOne) or `.prefetch_related()` (ManyToMany).
- **Timezone safety.** Never use `datetime.now()`. Use `django.utils.timezone.now()`.
- **No database queries in `Model.__init__` or property accessors.**

## 2. Security

Cross-cutting concern.

- **No secrets in code.** Environment variables via `.env` / `os.environ`.
- **Access control on views.** Use `LoginRequiredMixin` and `PermissionRequiredMixin` on Class-Based Views. See [`../arch-coherence/DJANGO.md` §1 Module Structure](../arch-coherence/DJANGO.md#1-module-structure) for the CBV pattern this plugs into.

## 3. Linting

`pylint` is the racecar linter (see [`PYTHON.md` §3](PYTHON.md#3-formatting)), but it has no Django-aware rules out of the box. `pylint-django` fills that gap: it understands model fields, queryset types, and `get_user_model()` — things a plain linter cannot infer without a Django runtime.

**Django projects must load it:**

```
pylint --load-plugins pylint_django src/
```

Add to the library pyproject:

```toml
[tool.pylint.main]
load-plugins = ["pylint_django"]

[tool.pylint."MESSAGES CONTROL"]
# Project-specific disables go here; keep this list short and justified.
# disable = []
```

The Definition of Done in [`PYTHON.md` §6](PYTHON.md#6-definition-of-done) covers the general lint gate; the `pylint-django` plugin is an additional requirement for Django projects only.
