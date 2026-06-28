# racecar-start-django-project: the procedure

Accessed via [`SKILL.md`](SKILL.md). Doctrine home: [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)
(the shapes axis) and [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md) (the generated tree).

Mechanism: `render_shell(out)` in
[`../arch-coherence/scripts/scaffold_surfaces_templates.py`](../arch-coherence/scripts/scaffold_surfaces_templates.py),
invoked as `scaffold_surfaces.py --shell-only --out <server>`.

## What this skill is for

Scaffold a **vanilla Django project**: the `DJANGO_PROJECT` atom (`server/`). The output is a
generic, location-free, **bootable but empty** server in a standard Django layout: it knows no library
package, carries no surfaces, and serves nothing. `manage.py check` passes and `manage.py runserver`
runs an empty project. It is ready for `racecar-create-server` to compose the REST/MCP surfaces on top.
With a `src/<pkg>` library beside it the project is the `src+server` shape; on its own it is the
standalone `server` shape.

It owns the **vanilla** `server/` shell only. It does **not** generate surfaces or carry any surface,
host-guard, or auth machinery (that is `racecar-create-server`), and it does **not** touch the library
`src/<pkg>` (that is `racecar-create-package`).

## Where it sits: the cascade's generic delegate

start-django-project is **not** a cascade rung; it is the generic, reusable scaffold the lifecycle
cascade delegates to. The cascade is `create-package → create-server → secure-server → deploy-server`
(each idempotent, each ensuring its precondition by invoking the one below); `create-server` invokes
this skill to lay down `server/`, then composes the surfaces over `src/<pkg>/api`.

- `racecar-create-server`: needs a `server/` shell. If absent, it **invokes
  `racecar-start-django-project`**, then composes the surfaces over `src/<pkg>/api`.
- `racecar-start-django-project`, this skill: a vanilla Django scaffold, racecar-agnostic and reusable
  on its own; needs nothing below it.
- `racecar-create-package`: scaffolds the `src/<pkg>` library; the greenfield root of the cascade.

Running `racecar-create-server` therefore bootstraps the shell automatically; the library is the
project's own (`racecar-create-package` scaffolds a fresh one).

## What the vanilla shell is

```
server/
  manage.py                # the Django marker; DJANGO_SETTINGS_MODULE = project.settings
  pyproject.toml           # runtime group: django>=6, uvicorn (no [project]/[build-system])
  project/
    __init__.py
    settings.py            # single, generic, env-driven settings; db-light (sqlite default, mysql via DB_TYPE)
    urls.py                # empty urlconf (urlpatterns = [])
    asgi.py  wsgi.py       # ASGI/WSGI entrypoints (DJANGO_SETTINGS_MODULE = project.settings)
  apps/
    __init__.py            # empty apps package (create-server populates it)
```

No `settings/` package, no `surfaceguard`, no `auth.py`, no `run.sh`, no Apache vhosts. Those are the
two-process surface composition, and they are `racecar-create-server`'s. A single settings module and a
single ASGI process: a standard Django project, nothing racecar-specific.

## The vanilla → surfaces contract

The vanilla shell carries **no** surface seams. `racecar-create-server` does not edit `settings.py` or
`urls.py` in place; it **replaces** them:

1. `project/settings.py` (single module) → `project/settings/` package (shared base + per-surface
   `api.py` / `mcp.py`), removing the stale module.
2. `project/urls.py` (empty) → `project/urls/` package (`apiurls.py` / `mcpurls.py`), removing the
   stale module.
3. adds `project/surfaceguard.py`, `project/auth.py`, `project/sitemaps.py`, `project/views.py`,
   `run.sh`, the Apache vhosts, and the per-vertical `apps/<v>/` adapters.

`start-django-project` emits the generic project; `racecar-create-server` composes everything
racecar-specific on top. Keeping the vanilla form seam-free is what lets the two skills compose without
one editing the other's files ad hoc.

## Procedure

1. **Precondition.** None below it: it scaffolds the `server/` atom directly. No-op if a `server/`
   already exists (idempotent).
2. **Generate the vanilla shell:** `scaffold_surfaces.py --shell-only --out server`, writes
   `project/` (single `settings.py`, empty `urls.py`, asgi/wsgi), `manage.py`, the runtime
   `pyproject.toml`, and an empty `apps/`. No inputs: no package name, no manifest, no surfaces.
3. **Verify it boots empty.** `manage.py check` clean; `manage.py runserver` serves an empty project.
4. **Hand off.** `racecar-create-server` runs `render_project` with the full manifest, replacing the
   vanilla modules with the surface packages and writing the per-vertical adapters over `src/<pkg>/api`.

## Edges and limits

- **The vanilla `server/` atom only.** It scaffolds a generic Django project; every racecar surface
  addition is `racecar-create-server`'s, and the library `src/<pkg>` is `racecar-create-package`'s.
- **Faceless by design.** A freshly created server serves no data and carries no surfaces; that is
  correct, not incomplete.
- **Owner-authorized.** It adds a build-bearing tree (`server/` + the Django marker `manage.py`).

## Implementation

The static shell is a mirror tree at `../arch-coherence/templates/django-project/` whose layout matches
the generated `server/` exactly; `render_shell` copies it 1:1 via `render_tree`
([`../arch-coherence/scripts/scaffold_tree.py`](../arch-coherence/scripts/scaffold_tree.py)).
`racecar-create-server`'s `render_project` copies the separate `templates/server/` tree (dropping any
vanilla `settings.py`/`urls.py` first, so it composes whether or not the vanilla shell ran) and then
overlays the manifest-interpolated files. The skill is wired into `install` + `scripts/sync_claude_md.py`.

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).
