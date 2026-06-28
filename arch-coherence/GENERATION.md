# Generation: cli-tree + api → REST + MCP surface

Accessed via [`README.md`](README.md). If you arrived here directly, read that
first. This file is the home for **surface generation**: how racecar mechanically
produces a REST API and an MCP server from a project that already has a
CLI-compliant surface ([`CLI.md`](CLI.md)) and an `api` vertex
([`SURFACES.md`](SURFACES.md)). The executing skill is
[`racecar-create-server`](../create-server/SKILL.md): it delegates the **vanilla** Django shell to
[`racecar-start-django-project`](../start-django-project/SKILL.md), then composes every surface
addition (the per-surface settings/urls packages, `surfaceguard`, `project/auth.py`, the adapters,
`run.sh`, the vhosts) on top. This file is the doctrine it conforms to.

The one-line thesis: **a surface is a thin adapter over `api` (SURFACES.md §1), so
sibling surfaces are derivable, not hand-written.** Given `api` and the CLI's
declaration of what is exposed, the REST and MCP surfaces are a deterministic
projection. Derive successors, never cache them.

## 1. The pipeline

```
   cli audit tree  ──(exposure allow-list)──┐
                                             ├──> Interface Manifest ──> REST routes ─┐
   api signatures  ──(schema + bind target)─┘     (derived JSON)      └─> MCP tools  ─┴─> two ASGI processes (one per surface) ─> Apache
```

Two inputs, one home each:

- **The CLI audit tree** (`check_cli_commands.py --json <pkg>`) is the
  **exposure allow-list**. A command reachable from the CLI is exposable; one
  that is not is not. This reuses the CLI's existing curation — explicit
  registration is "what the system can do" (CLI.md §Registration) — as the
  curation for the surfaces too. No second allow-list.
- **The `api` callables** are the **schema source and the bind target**. The
  parameter schema is introspected from each bound callable's signature + type
  hints; the generated surface *calls that callable*. Nothing subprocesses the
  CLI.

Everything downstream is derived from the **Interface Manifest** (§3), a single
JSON document. Both surfaces read it; neither holds command knowledge of its own.

## 2. Why api is the schema source, not the argparse surface

The locked decision early in this work was "CLI tree = exposure spec + arg
schema; api = bind target." Building it surfaced a correction, recorded here so
it is not re-litigated:

**The parameter schema comes from `api` signatures, not argparse.** Reasons,
in order:

1. **argparse is a lossy projection.** Everything stringifies; `type` is a
   best-effort callable name; there are no return types and no nested objects.
   REST and MCP express richer typed bodies that argparse cannot. Sourcing the
   schema from argparse caps every surface at argparse's expressiveness — the
   lowest-common-denominator surface becomes the ceiling for all surfaces.
2. **`api` is the superset (SURFACES.md §1).** It already holds the typed, curated
   surface. The CLI is *itself* a surface over it. Generating sibling surfaces from
   `api` keeps them siblings; generating them from the CLI's surface would make
   `mcp` and `rest` depend on a third surface, inverting the DAG SURFACES.md gates.
3. **Less brittle glue.** Translating flat argparse args (mutex `oneOf`,
   `nargs`, `store_true`, custom `type=`) into `api` kwargs per command is
   fragile. Introspecting the `api` signature is one general mechanism.

The CLI tree keeps the job it is best at — **declaring what is exposed**. It
does not define the shape. This is the placement principle (SURFACES.md §9) applied
to schema: the schema lives at the most central layer that holds it richly,
which is `api`.

**Edge / future work.** A project that wants the REST/MCP surface to mirror an
argparse shape the `api` signature does not capture (e.g. surface a mutex group
as JSON-Schema `oneOf`) declares that in the binding, or enriches the `api`
signature. The argparse `oneOf` convention (CLI.md §"mutex groups borrow oneOf")
is the same JSON-Schema vocabulary, so the two can be reconciled when a real
case needs it. Until then: api signature is the schema. (Discrete-first: this is
deterministic introspection, no model in the loop.)

## 3. The Interface Manifest (the IR)

The derived seam. One JSON file (`docs/api/manifest.json`), regenerated, never
hand-maintained. Shape:

```
Manifest = {
  "package":               str,            # the library package
  "mcp_protocol_version":  str,            # the MCP revision the mcp surface speaks
  "verticals": [
    {
      "vertical":    str,                  # e.g. "gfem.data.ercot"
      "api_module":  str,                  # dotted module holding the api callables
      "commands": [ Command, ... ]
    }
  ]
}

Command = {
  "subcommand":    str,                    # the CLI verb this mirrors (allow-list key)
  "api_module":    str,
  "api_callable":  str,                    # the bound function in api_module
  "method":        "GET" | "POST",         # REST verb (read -> GET, write -> POST)
  "http_path":     str,                    # REST route, e.g. "/api/v1/gfem/data/ercot/list"
  "mcp_tool":      str,                    # MCP tool name, e.g. "gfem_data_ercot_list"
  "description":   str,                    # first line of the callable's docstring
  "input_schema":  JSONSchema              # 2020-12 object; MCP inputSchema + REST params share it
}
```

`input_schema` is the same JSON-Schema object MCP's `inputSchema` requires and
OpenAPI parameters consume — one schema, two surfaces. It is introspected from the
callable (§2).

### The binding

The manifest is built from the audit tree plus a small **binding** the project
declares — per vertical, the api module and, per exposed CLI subcommand, the
bound callable + HTTP method. **Its one home is `pyproject.toml` under
`[tool.racecar.surface]`** (the binding is project config; it belongs beside the
rest of it, not in a stray sidecar file):

```toml
[tool.racecar.surface]
package = "gfem"

[tool.racecar.surface.verticals."gfem.data.ercot"]
api_module = "gfem.data.ercot.api"
commands.list   = { api = "list_datasets", method = "GET" }
commands.status = { api = "status",        method = "GET" }
commands.sync   = { api = "sync",          method = "POST" }
```

A standalone JSON file of the same structure (`{package, verticals: {...}}`) is
the equivalent for projects that prefer it; the generator accepts either
(`--binding pyproject.toml` or `--binding b.json`).

The binding is the one declared thing (the CLI verb names need not match the
`api` callable names — the curated surfaces differ legitimately). A subcommand
in the binding but absent from the CLI allow-list is dropped (the audit tree
gates exposure). Adding a vertical or command is a binding edit plus a
regenerate, never a surface edit.

## 4. The surface: two ASGI processes, one per surface

The shipped target is the `django` surface (SURFACES.md §8) in the `src+server` shape
([`PACKAGING.md`](PACKAGING.md) §"Scope"). One Django **project** — composition
root `project/`, one Django app per vertical under `apps/<v>/` — is launched as
**two processes**, one per surface. Vertical-first: each `apps/<v>/` co-locates both
surfaces over that vertical's `api`, and the binding is written once:

- `apps/<v>/commands.py` — the transport-neutral binding over `<pkg>.<v>.api`
  (callable, schema, write flag, method, route, tool, description). The shared
  ancestor both surfaces read; the bulky `input_schema` is written once, not per surface.
- `apps/<v>/views/apiviews.py` — REST views built from `commands`.
- `apps/<v>/views/mcpviews.py` — the MCP tool table built from `commands`.
- `apps/mcp.py` — the single MCP endpoint, aggregating every vertical's `mcpviews`.

The two surfaces are **siblings over `commands`**, not a chain: `mcp` never imports
the REST surface. Each process picks its urlconf at boot:

- **REST** — `project.settings.api` sets `ROOT_URLCONF = project.urls.apiurls`,
  which mounts each vertical under the versioned taxonomy
  `/api/v1/<package>/<vertical-path>/<command>` (the vertical's full dotted name;
  `gfem.data.ercot list` → `/api/v1/gfem/data/ercot/list`). Each view coerces transport
  input to the command's `input_schema`, calls the bound `api` callable off the
  event loop (`sync_to_async`), and renders JSON. The browsable surface: it carries
  `debug_toolbar`, serves its OpenAPI 3.1 document at `/api/v1/openapi.json`, and a
  sitemap of the GET surface at `/sitemap/`.
- **MCP** — `project.settings.mcp` sets `ROOT_URLCONF = project.urls.mcpurls`:
  one Streamable-HTTP endpoint (`/mcp`) exposing one MCP tool per command; each
  tool's `inputSchema` is the command's schema; `tools/call` dispatches to the
  bound callable. The machine surface; no browsable extras.

**HTTP-delivered mcp is a route family in the surface, not a standalone
`mcp.py`.** SURFACES.md §2 reserves `mcp.py` for a stdio tool server; an
HTTP-served MCP surface is Django routing, so it collapses into the surface. (See
the SURFACES.md §2 amendment.)

**Host split at boot, not per request.** `django.conf.settings` is a
process-global singleton, so per-surface settings ⟹ per-surface process: each Apache
vhost launches its own `DJANGO_SETTINGS_MODULE` (`project.settings.api` |
`project.settings.mcp`), and that module fixes `ROOT_URLCONF` to its surface's
urlconf. The split lives in the deploy wiring, not in Python — there is no
per-request `request.urlconf` swap. A `surfaceguard` middleware attaches
`request.surface` and `404`s a wrong-surface host, but it never assigns
`request.urlconf`. This is also what keeps the standard Django dev tools working:
`debug_toolbar` lives only on the api process (whose urlconf mounts `__debug__/`),
so it never reverses `djdt` against a urlconf without it. The surfaces hold **zero
orchestration**: strip the transport and `api` remains.

### MCP wire conformance

The mcp surface speaks the MCP **Streamable HTTP** transport, tools-only,
request/response: every POSTed JSON-RPC request gets an `application/json`
reply; `GET` returns `405` (the surface offers no server-initiated SSE stream,
which the spec permits). It implements `initialize`, `notifications/initialized`
(→ `202`), `tools/list`, and `tools/call`. Streaming (SSE) is deferred until a
tool needs it — at which point the mcp process grows SSE while the REST process
is unaffected (the per-process split makes the divergence free). The protocol
version is pinned in the manifest (`mcp_protocol_version`), not hardcoded in the
view.

### Write-verb safety rail

A surface can trigger real mutations (a `sync` that writes, a `derive` that
persists). Because it has no tty it cannot prompt for confirmation, and it may be
reachable without auth. So **write verbs (any non-`GET` command) are OFF by
default** and execute only when the owner sets `RACECAR_ALLOW_WRITES=1`
out of band. With writes off, a write route returns `403` (REST) or an
`isError` tool result (MCP); reads are unaffected. This is the placement
principle again: the no-tty surface cannot relocate confirmation outward, so it
**fails safe** and requires the capability to be provisioned explicitly. The MCP
`tools/list` also annotates each tool with `readOnlyHint` (true for `GET`
commands) so a client sees which tools mutate. The rail is deterministic and
owner-authorized — a gate, not a heuristic.

### Auth rail

The identity analog of the write rail, and the same fail-closed stance: a surface is **closed by
default**, refusing any request that lacks a valid credential and the scope the command requires. The
doctrine (one OAuth 2.1 opaque-bearer path on both surfaces, a separate WebAuthn hardware-key
Authorization Server, per-tool scopes, no JWT) is [`AUTH.md`](AUTH.md); it is enforced by
[`scripts/check_surface_auth.py`](scripts/check_surface_auth.py), which fails a surface that ships
anonymous or a command with no scope.

Two halves, generated separately. The **issuer** (the Authorization Server that runs the WebAuthn
login and mints the opaque tokens) is `racecar-secure-server`. The **validators** are generated here, in
the surfaces: a per-command `scope` rides in the binding and the manifest, and create-server's
composition root carries `project/auth.py`, which extracts the bearer token and validates it by
introspection (RFC 7662)
against the AS, cached briefly. The REST adapter answers 401 (no/invalid token) or 403 (out of scope);
the MCP adapter gates every message, returns 401 + `WWW-Authenticate`, and serves
`/.well-known/oauth-protected-resource` (RFC 9728) so a client can find the AS. With introspection
unconfigured the surface refuses every call: closed by default is the boot state, not a deploy step.

### Generated API docs — one source, three surfaces

The same manifest that renders the surfaces also renders the documentation, so the
spec can never drift from the routes:

- **`docs/api/openapi.json`** — an OpenAPI 3.1 document for the REST surface,
  conformant to the [OpenAPI Specification](https://www.openapis.org/) (validated
  by `openapi-spec-validator`). GET commands become query parameters; non-GET
  commands take the `input_schema` as a JSON request body; writes carry a `403`
  response. Served at `/api/v1/openapi.json`.
- **`/sitemap/` + `/sitemap.xml/`** — a `django.contrib.sitemaps` sitemap of the
  REST GET surface (the crawlable endpoints), house-style: the domain comes from
  the request host, no `django.contrib.sites` dependency.
- **`docs/api/ENDPOINTS.md`** — the human/LLM endpoint list: one table of REST
  routes, one of MCP tools. This is also the source the [`llm-summary`](../llm-summary/SPEC.md)
  bundle reads for its `external_surface` (`http_routes` + `mcp_tools`) and §3
  OpenAPI, rather than re-deriving from the views.

### Why ASGI, not mod_wsgi

The MCP ecosystem is async-native and LLM-facing traffic is slow-I/O-bound and
SSE-capable; mod_wsgi pins a worker thread per in-flight request and handles SSE
badly. Apache stays as the TLS-terminating reverse proxy; each surface runs as its
own ASGI (uvicorn) process. So MCP can grow SSE without touching REST — no later
substrate migration.

## 5. Enforcement posture: generate, don't gate

Consistent with [`OWNERSHIP.md`](../shared/OWNERSHIP.md) and the SURFACES.md north
star, generation is **scaffolding, not a wall**. The generator emits a working
surface; the owner authorizes the structural moves it depends on (the shape
migration and the `api` insertion are gated — they mutate working code). The
generated surfaces are regenerable: re-running re-derives the manifest and re-emits
every file, and **never writes into the `api` modules** — the one place humans
own. This is the §10 "make the right thing easy" half of SURFACES.md applied to the
surfaces: the good shape is the default you receive.

## 6. The scripts

- [`scripts/scaffold_surfaces.py`](scripts/scaffold_surfaces.py) — builds the
  Interface Manifest (audit tree + binding + api introspection) and renders the
  project.
- [`scripts/scaffold_surfaces_templates.py`](scripts/scaffold_surfaces_templates.py)
  — the manifest-interpolated Django 6 ASGI builders: per-vertical `commands.py` +
  `views/{apiviews,mcpviews}.py` + `urls/apiurls.py`, the `apps/mcp.py` endpoint, the
  `project/settings/settings.py` base, the api urlconf, and the sitemap. It copies the
  static bodies from the mirror trees via `render_tree`, then overlays these.
- [`scripts/scaffold_tree.py`](scripts/scaffold_tree.py) — `render_tree`: mirrors a
  template tree into the output 1:1, substituting placeholders, `*.sh` made executable.
- [`scripts/scaffold_surfaces_docs.py`](scripts/scaffold_surfaces_docs.py) — the OpenAPI
  document, the `ENDPOINTS.md` list, and the sitemap body.
- `templates/{django-project,server,authserver}/` — the static mirror trees whose layout
  matches the generated output (`surfaceguard`, `run.sh`, the vhosts, the settings/urls
  packages, the AS app, the ceremony HTML); see [`templates/README.md`](templates/README.md).

Run with the *target project's* interpreter so the `api` modules import. `--manifest-only`
emits just `docs/api/manifest.json` (no Django needed) for inspection.

## 7. How to apply to a project

0. **Scaffold the binding** from the CLI surface — the friction-reducer.
   `scaffold_surfaces.py --audit <cli.json> --scaffold-binding` walks the audit
   tree and prints a `[tool.racecar.surface]` stub enumerating every vertical
   and command, so you fill callables instead of writing the binding by hand.
   Unknown read/write defaults to `POST` (fail-safe: gated off until you mark a
   command `GET`).
1. **Have an `api` vertex.** Per SURFACES.md §11, the surfaces route through `api`. If
   the package already has an orchestration surface the cli wraps (an
   `orchestrate.py`, a `pipeline.py`), point the binding at it or add a thin
   kwargs adapter — you do not re-extract orchestration. Only a package whose
   `__main__` reaches into the lib directly needs the full insertion.
   (the `api` seam is the library's own arch-coherent code in `src/<pkg>/api`, not a
   skill insertion: `racecar-create-server` **reads** it and writes only `server/`, and
   **refuses with a clear error** if `src/<pkg>/api` is absent rather than synthesizing it.
   Invariant: `create-server` / `secure-server` / `deploy-server` write zero bytes to
   `src/`; `src/` is read-only input to everything downstream of the library scaffold.)
2. **Fill the binding** (§3): per vertical, the api module and per exposed
   subcommand the bound callable + method. Prune commands you do not want
   exposed (the scaffold lists everything the cli has).
3. **Generate.** `scaffold_surfaces.py --audit <cli.json> --binding
   pyproject.toml --out server`.
4. **Fly it.** `./run.sh` starts both processes (REST on `:8001` via
   `project.settings.api`, MCP on `:8002` via `project.settings.mcp`); test REST
   via `Host: api.localhost`, MCP via `Host: mcp.localhost`.
5. **Deploy.** The emitted `apache/{api,mcp}.vhost.conf` reverse-proxy each
   subdomain to its surface's ASGI process.

### Friction scales with how surfaces-shaped the package already is

The generator, the Django ASGI app, the MCP wire impl, the write rail, and the
per-surface settings + `surfaceguard` are **package-agnostic** — they are identical
across projects. The
only per-package work is the binding (mechanical, scaffolded by step 0) and the
`api` surface (step 1), and that second cost depends entirely on the package:

- **Push-button** — `__main__` already wraps a clean callable with web-friendly
  kwargs: scaffold binding, point it at that callable, generate. No new code.
- **Light** — an orchestration module exists (`orchestrate.py` / `pipeline.py`)
  but its functions take domain objects: add a thin per-vertical `api` adapter
  (kwargs → construct the config object → call orchestrate). No orchestration
  extraction, no shape migration.
- **Heavier** — `__main__` reaches into the lib directly: insert `api` (extract
  the orchestration). This is the irreducible judgment step, and it is the
  *only* part that is not mechanical. It is needed exactly to the extent the
  package has not already separated orchestration from its cli.

The doctrine decisions (schema from `api`, ASGI, the MCP revision, the write
rail) are settled here once and do not re-litigate per package — so a second
package is binding + adapter, not a design conversation.

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).

## Status and known gaps

This doctrine and its generator are a **working stub**, proven end to end on gfem
(four verticals, REST + MCP live, the DAG held and runtime-validated) but not yet
complete. Honest gaps, for the follow-up tracked against `racecar-create-server`:

- **Library-pyproject §7 config is not emitted.** Adopting `src+server` requires
  the library pyproject to gain the `django` dev-group, isort dual-root
  (`src_paths` + `known_first_party`), and `import-linter` coverage of the server
  roots (PACKAGING.md §7). The generator writes `server/` but does not patch the
  library pyproject; those edits were applied by hand on gfem. The skill should
  emit them.
- **The project > mcp > apps DAG is generated, not gated.** It is correct by
  construction, but no `import-linter` `layers` contract enforces it. Add one so
  a future hand-edit cannot silently invert `mcp -> apps`.
- **The generated app is database-light.** Empty `models.py`/`admin.py`, no qux
  integration option. The settings are a real house-shaped `project/settings/`
  package (sqlite/mysql per the `DB_TYPE` pattern, `django_extensions` +
  `debug_toolbar` DEBUG-gated), but there are no domain models. Fine for a machine
  API; revisit if a surface needs auth/admin/ORM.
- **`docs/api/manifest.json` is the IR snapshot**, emitted beside the generated
  `openapi.json` / `ENDPOINTS.md`. The runtime does not read it — each app's
  `commands.py` is the source — but it is the artifact `--manifest-only` produces
  and a useful diff target across regenerations.

## Invocation

> Load `arch-coherence/GENERATION.md`. This project exposes its CLI surface as
> REST + MCP via a generated Django ASGI surface. Verify the Interface Manifest
> is derived (not hand-edited), the surfaces hold no orchestration, the schema is
> introspected from `api` (not argparse), and the mcp surface speaks the pinned
> Streamable HTTP revision.
