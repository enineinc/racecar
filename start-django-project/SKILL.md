---
name: racecar-start-django-project
description: Scaffold a vanilla Django project — the DJANGO_PROJECT shape atom (`server/`). A generic, location-free, bootable vanilla Django server: the project/ composition root (a single settings.py, an empty urls.py, asgi/wsgi), manage.py (the Django marker), the runtime pyproject (django>=6 + uvicorn), and an empty apps/ package — database-light, knows no library package. `manage.py check` passes and it serves nothing. It does NOT carry any surface, host-guard, or auth machinery and does NOT generate the REST/MCP surfaces (that is racecar-create-server, which invokes this and then composes the surfaces on top) and does NOT touch the library (`src/<pkg>` is racecar-create-package's). Owner-authorized; idempotent (no-op if `server/` already exists). Use when asked to "create the django project", "scaffold the Django app", "add the server shell", or as the step before create-server.
---

# racecar-start-django-project — the vanilla Django shell (the `server/` atom)

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

**Mechanism:** the vanilla shell pass is `render_shell` in
[`../arch-coherence/scripts/scaffold_surfaces_templates.py`](../arch-coherence/scripts/scaffold_surfaces_templates.py),
invoked as `scaffold_surfaces.py --shell-only --out server`. It needs no package name, no audit, and
no binding — it is generic and location-free. `racecar-create-server` later composes the REST/MCP
surfaces on top by running `render_project` with the full manifest.

This is a **generic, racecar-agnostic** scaffold: a standalone reusable skill that lays down a
vanilla Django project anywhere, knowing nothing about `src/`, `api`, or surfaces. The lifecycle
cascade `racecar-create-package → racecar-create-server → racecar-secure-server → racecar-deploy-server`
(each idempotent) **delegates** to it: `racecar-create-server` invokes it to lay down `server/`, then
composes the REST + MCP surfaces on top.

The core: this skill scaffolds the **DJANGO_PROJECT atom** ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md))
— a generic, **bootable but empty** Django project at `server/`, in a standard Django layout. With a
`src/<pkg>` library beside it the project is the `src+server` shape; on its own it is the standalone
`server` shape. Either way this skill owns only the `server/` tree, and only its vanilla form:

- **Owns the vanilla shell:** the `project/` composition root in its generic form — a single
  `settings.py` (env-driven, database-light: sqlite default, mysql via `DB_TYPE`), an empty `urls.py`,
  `asgi.py`/`wsgi.py` (all pointing at `project.settings`); plus `manage.py` (the Django marker), the
  runtime `pyproject.toml` (django>=6 + uvicorn), and an empty `apps/` package. No surface, host-guard,
  or auth machinery; `django_extensions` is the only DEBUG-gated dev tool.
- **Does not own:** the two-process surface composition — the per-surface settings package
  (`settings/{settings,api,mcp}.py`), the per-surface urlconfs, the `surfaceguard` host-guard,
  `project/auth.py`, `run.sh`, the Apache vhosts, and the REST/MCP surface content
  (`apps/<v>/`, `apps/mcp.py`, OpenAPI/ENDPOINTS/manifest). All of that is **racecar-create-server**,
  which invokes this then composes the surfaces over `src/<pkg>/api`. Nor the library (`src/<pkg>`) —
  that is **racecar-create-package**.

**Where it sits: the cascade's generic delegate.** start-django-project is not a cascade rung; it is
the reusable scaffold the cascade delegates to. **racecar-create-server** invokes it when no `server/`
exists, then composes the surfaces over `src/<pkg>/api`. This skill needs nothing below it and knows
nothing above it; the library is the project's own (`racecar-create-package`
scaffolds a fresh one). Re-running anywhere in the chain is safe.

**The vanilla → surfaces transform (the composition's key design point).** The vanilla shell is fully
independent of any surface: it has a single `settings.py` and an empty `urls.py`, nothing more.
`racecar-create-server` does not edit those files — it **replaces** them, swapping the single
`settings.py`/`urls.py` modules for `settings/` and `urls/` packages (the per-surface forms) and adding
`surfaceguard`, `auth.py`, `run.sh`, and the vhosts. Keeping the vanilla form free of surface seams is
what makes the two skills cleanly composable: start-django-project owns a standard Django project,
create-server owns every racecar-specific addition on top.

Doctrine home: [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md) (the shapes axis)
and [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md) (the generated tree).
