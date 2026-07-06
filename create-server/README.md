---
pnode: [SKILL.md]
---

# racecar-create-server: the procedure

Accessed via [`SKILL.md`](SKILL.md). Doctrine homes this skill executes against:
[`SURFACES.md`](../arch-coherence/SURFACES.md) (the `lib → api → surfaces` axis),
[`PACKAGING.md`](../arch-coherence/PACKAGING.md) (the shapes axis),
[`CLI.md`](../arch-coherence/CLI.md) (the compliant format this reads from).

## What this skill is for

One library, exposed through N surfaces. The CLI already exists. This skill adds two
more surfaces, a REST API and an MCP server, and makes all three route through one
`api` vertex so orchestration has exactly one home. The surfaces are generated from
the CLI's own audit tree; nothing is hand-restated.

It is built to run **across many projects**: every step is parameterized by the
package name `<pkg>` and the vertical names, and reads the project's shape off disk
(PACKAGING.md §"How the shape is determined"). No project-specific value is baked in.

## What this skill owns (surfaces axis), and what it stacks on

This skill owns the **surfaces axis**: generating the REST + MCP surfaces over
`src/<pkg>/api` (the api-face and the mcp-face) and delivering them behind Apache. It does
**not** scaffold the Django shell, and it does **not** touch the library.

- The **Django shell** (`server/`) is [`racecar-start-django-project`](../start-django-project/SKILL.md)'s
  job: a vanilla Django project with no racecar knowledge. This skill invokes it, then writes the
  surface adapters into `server/`.
- The **library** (`src/<pkg>`: lib + api + cli) is the project's own; scaffold a fresh one with
  `racecar-create-package`. It is never modified here: this skill reads `src/<pkg>/api` and writes
  only `server/`.
- The general drift-classification and Makefile-fold work is [`racecar-upgrade`](../upgrade/SKILL.md);
  the import-graph gate is [`racecar-arch-coherence`](../arch-coherence/SKILL.md). It calls those, it
  does not reimplement them.

## Preconditions

- The project is racecar-CLI-compliant: each `__main__.py` exposes `commands()` /
  `subcommands()` / `parser()` and `check_cli_commands.py --json <pkg>` emits a clean
  enriched tree (CLI.md). **The audit tree is the exposure spec and the arg schema.**
- The CLI surface is the curated allow-list of what gets exposed. A capability not
  reachable from the CLI is not exposed by REST or MCP. Widening exposure is a
  deliberate CLI registration, not a side effect of this skill.

## The pipeline

Each step is mechanical. Everything `create-server` writes lands in `server/` and is
regenerable and idempotent; it writes **zero bytes to `src/`**. The one working-code change
is the `api` seam (step 3), which is **not** this skill's to make: it is a precondition the
author establishes as arch-coherent code, verified here and refused if absent.

### 1. Scaffold the `server/` shell (*via racecar-start-django-project*)

The surfaces live in a Django project at `server/`. This skill invokes
[`racecar-start-django-project`](../start-django-project/SKILL.md) to scaffold a vanilla Django
`server/` (manage.py, a single `project/settings.py` + empty `project/urls.py`, asgi/wsgi, an empty
`apps/`), idempotent: a no-op if `server/` already exists. This skill then composes the surfaces on
top, replacing the vanilla `settings.py`/`urls.py` modules with the per-surface `settings/`/`urls/`
packages. The library stays at canon root `src/<pkg>`: no shape migration, no wrapper directory. `racecar.mk`
re-derives `SRC` / `PKG` / `SERVER` from the on-disk markers, no edit.

### 2. Create the `server/` surface if absent

The Django ASGI project, rendered by `scaffold_surfaces.py` from the manifest
(§4), **vertical-first**: one Django app per vertical under `apps/<v>/`, plus a
`project/` composition root:

- `server/manage.py` (the shape marker that makes it `src+server`).
- `server/pyproject.toml` from the `templates/server/` mirror tree: **no
  `[project]` block, no `[build-system]`** (PACKAGING.md §"server pyproject"); it runs
  via `manage.py`, it is not a wheel.
- `server/project/asgi.py`: the single ASGI entrypoint (not `wsgi.py`; see Delivery);
  each process picks its surface's settings at boot.
- `server/project/settings/{settings,api,mcp}.py`, `project/urls/{apiurls,mcpurls}.py`,
  `project/surfaceguard.py`, `project/views.py` (serves the OpenAPI doc),
  `project/sitemaps.py`.
- `server/apps/<v>/` per vertical: `commands.py` (the transport-neutral binding),
  `views/{apiviews,mcpviews}.py`, `urls/apiurls.py`, and a Django app stub
  (`apps.py`, `models.py`, `admin.py`).
- `server/apps/mcp.py`: the single MCP Streamable-HTTP endpoint, unioning every
  vertical's `mcpviews.TOOLS`.
- The generated server's runtime is `django` + `uvicorn` (`server/pyproject.toml`);
  there is no DRF. The OpenAPI 3.1 document is generated from the manifest, not
  introspected from views, and is not runtime-validated by the server (§5).

The server imports the installable `<pkg>` and holds zero orchestration.

### 3. Precondition: the `api` cut vertex exists per vertical (*verified, not generated*)

`create-server` **reads** `src/<pkg>/api` and writes only `server/`; it never writes
`src/`. If `src/<pkg>/api` is absent it **refuses with a clear error** pointing at
arch-coherence, rather than synthesizing the seam.

Establishing the seam is the author's arch-coherent work (SURFACES.md §5, the articulation
point), done once when the library is written, not a step this skill performs:

- For each vertical, `<pkg>/<verb>/api.py` holds the orchestration (input resolution,
  credential seeding, defaulting, dispatch); `__main__.py` is thinned to translate argparse
  input, call `api`, render.
- The one `layers` contract in `[tool.importlinter]` (SURFACES.md §4) holds the structure:
  `lint-imports` → `Contracts: N kept, 0 broken`.
- `check_surface_orchestration.py` (advisory) flags a non-classifiable vertical or a
  declared-`api` that is not the cut vertex.

`api` is the **bind target** for the generated surfaces. The surfaces call `api` functions;
nothing subprocesses `python -m`. The only writer of `src/` is the author (and
`racecar-create-package`); `create-server` is a pure `server/` writer.

### 4. Build the Interface Manifest

The generation seam: one derived JSON binding each exposed command to its `api`
callable and its arg schema. Built from two sources, one home each:

- **Exposure set + arg schema**: the CLI audit tree (`check_cli_commands.py --json`).
  Its `oneOf` arg shape is already JSON-Schema (CLI.md §"mutex groups borrow oneOf"),
  which is what both OpenAPI parameters and MCP `inputSchema` consume.
- **Call target**: the `api` callable for each command, with the arg→parameter
  mapping.

The manifest is derived, never hand-maintained. Its formal IR spec, the binding
format, and the api-vs-argparse schema-source reconciliation are the doctrine in
[`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md).

### 5. Generate the two surfaces, co-located per vertical

Both are thin Django adapters over `api`, emitted from the manifest. Each vertical
holds both: `apps/<v>/commands.py` is the single transport-neutral binding, and the
two surfaces are **siblings over it** (mcp never imports the REST surface):

- **REST** on `api.*`: `apps/<v>/views/apiviews.py` built from `commands`, mounted
  by `project/urls/apiurls.py` under the versioned taxonomy
  `/api/v1/<package>/<vertical-path>/<command>` (the vertical's full dotted name;
  `gfem.data.ercot list` → `/api/v1/gfem/data/ercot/list`). Args map to query/body
  parameters; `oneOf` carries through unchanged. The OpenAPI 3.1.0 document is built
  from the manifest and served from `project/views.py` at `/api/v1/openapi.json`.
- **MCP** on `mcp.*`: `apps/<v>/views/mcpviews.py` builds each vertical's `TOOLS`
  table; `apps/mcp.py` unions them behind one Streamable HTTP endpoint exposing one
  MCP tool per command, each command's arg schema becoming the tool's `inputSchema`.

> Verify the current MCP Streamable HTTP transport spec before emitting the MCP
> endpoint. Do not assume the request/response and SSE-upgrade contract from memory.

Each view/handler translates, calls `api`, renders. No re-resolution, no defaulting,
no credential handling in the surface (SURFACES.md §9, the placement principle).

The same manifest also renders the generated docs in `server/docs/api/`
(`manifest.json`, `openapi.json`, `ENDPOINTS.md`) plus a `/sitemap/` of the GET
surface, so the spec never drifts from the routes. GENERATION.md §"Generated API
docs" is the doctrine. There is no `web/` directory.

### 6. Emit Apache delivery

Host-based virtual hosts (the default; path-based is the no-subdomain fallback):

```
Apache (TLS + name-based vhosts: api.* , mcp.* )
   ├─ api.*  ─ mod_proxy_http ─> uvicorn :8001  (DJANGO_SETTINGS_MODULE=project.settings.api)
   └─ mcp.*  ─ mod_proxy_http ─> uvicorn :8002  (DJANGO_SETTINGS_MODULE=project.settings.mcp)
         one Django project (project/asgi.py), two processes; each settings
         module fixes ROOT_URLCONF to its surface's urlconf
```

One Django project, launched as **two processes**, one per surface. `django.conf.settings`
is a process-global singleton, so the host split is per-process at **boot**
(`DJANGO_SETTINGS_MODULE` per vhost → `ROOT_URLCONF` per surface), not a per-request
`request.get_host()` check. A `surfaceguard` middleware attaches `request.surface` and
`404`s a wrong-surface host, but never swaps the urlconf. The skill emits the two vhost
snippets and `run.sh` (both uvicorns); it does not own TLS material or DNS.

**Why ASGI, not mod_wsgi.** The MCP ecosystem is async-native and LLM-facing traffic
is slow-I/O-bound and SSE-capable; mod_wsgi pins a worker thread per in-flight
request and handles SSE badly. Apache stays as the TLS-terminating reverse proxy;
each surface runs as its own ASGI (uvicorn) process, so MCP can grow SSE without
touching REST.

## Idempotence and re-runs

Steps 4–6 are regenerable: re-running re-derives the manifest and re-emits the
per-vertical `commands`/views/urls, the `apps/mcp.py` endpoint, the `project/`
composition root, the generated docs (`docs/api/{manifest,openapi}.json`,
`ENDPOINTS.md`), and the vhost snippets. It **never writes the library**: `src/<pkg>` is the
project's own; this skill reads `src/<pkg>/api` and writes only `server/`.

## Gated points (owner signoff)

This skill is additive: it scaffolds `server/` (via `racecar-start-django-project`) and generates
the surfaces into it, idempotently. It writes only `server/` and never the library, so there is no
structural mutation of `src/` to gate, only the initial engage to stand the server up.
