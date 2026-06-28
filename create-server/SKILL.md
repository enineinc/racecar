---
name: racecar-create-server
description: Stand up REST + MCP surfaces over a CLI-compliant `src/<pkg>` library — the surfaces axis. Delegates the Django shell to `racecar-start-django-project` (scaffolding `server/`), then generates thin REST (`api.*`) + MCP (`mcp.*`) adapters that wrap `src/<pkg>/api`, launched as two ASGI processes behind Apache. Reads `src/<pkg>/api`; writes only `server/`, never `src/`. Write verbs are gated off by default. Generic and parameterized; no project-specific values baked in. Owner-authorized, idempotent, regenerable. Use when asked to "expose the CLI as REST and MCP", "add a surface", "stand up the MCP server", "generate the REST API from the CLI", or "serve this behind Apache".
---

# racecar-create-server — REST + MCP surfaces over one library

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: every CLI capability becomes reachable as REST and MCP **without re-implementing orchestration anywhere**, because all surfaces route through one `api` cut vertex ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) §5). The generated Django app holds **zero orchestration**: each REST view and MCP tool handler translates transport input, calls `api`, renders. MCP is HTTP-delivered (Streamable HTTP), so it is a **route family in the surface, not a standalone `mcp.py`** — one Django project launched as two ASGI processes (one per surface, each vhost selecting its settings module at boot), behind Apache.

**One axis, delegated shell.** This skill owns the **surfaces axis** ([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md), [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md)): generate the REST + MCP surfaces over `src/<pkg>/api` and deliver behind Apache. The **Django shell** belongs to [`racecar-start-django-project`](../start-django-project/SKILL.md) — a vanilla Django project with no racecar knowledge; this skill invokes it to scaffold `server/`, then writes the surface adapters into it. The **library** (`src/<pkg>`: lib + api + cli) is the project's own — scaffold a fresh one with `racecar-create-package`. This skill reads `src/<pkg>/api` and writes only `server/`, never the library. The user runs one command; the shell scaffold is internal.

Owner-authorized: generating the surfaces mutates the `server/` tree (gated). Write verbs (any non-GET command) are OFF by default — enabled only by `RACECAR_ALLOW_WRITES=1` — so a no-tty surface fails safe. Idempotent and regenerable: re-running re-derives the manifest and re-emits the surfaces in `server/`; it reads but never writes `src/<pkg>/api`.
