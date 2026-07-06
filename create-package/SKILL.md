---
name: racecar-create-package
description: Scaffold a new Python package in the canon src layout — `$REPO/src/<pkg>/` with the lib/api/cli surfaces, its own PEP 621/735 `pyproject.toml` at the repo root, and the racecar `Makefile` + pre-commit wiring. The greenfield entry to the cascade: the library that every surface wraps, django-free and `python -m <pkg>`-runnable. Idempotent — a no-op when `src/<pkg>/` already exists. Writes only the library; the REST + MCP deployment is `racecar-create-server`, its auth is `racecar-secure-server`. Use when asked to "start a new package", "scaffold a python library", "create the src/<pkg> skeleton", or as the first step before exposing surfaces.
---

# racecar-create-package — the canon `src/<pkg>` library

This skill is a routing pointer, not content. Load [`README.md`](README.md) for the full procedure.

The core: a racecar project begins as one importable library in the **canon PyPA src layout** —
`$REPO/src/<pkg>/`, `pyproject.toml` at the repo root. The library is django-free and
`python -m <pkg>`-runnable, and it carries the three mandatory surfaces over one `api`
([`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md)): **cli** (in-process, serverless),
and — once a server exists — **rest** and **mcp**. This skill lays down that library skeleton; nothing
more.

**Where it sits in the cascade.** `create-package` → `create-server` → `secure-server` →
`deploy-server`. It is the only step that writes `src/<pkg>`; everything downstream reads the library's
`api` and writes only `server/`. The library is the architectural center — the data plane the agentic
surfaces consume — and it is kept structurally free of Django's ORM
([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)).

**Shape.** Canon single-package layout is root `src/<pkg>`. A repo that grew a second co-versioned
library would move to the workspace form `{packages,pypkg}/<pkg>/src/<pkg>`, which `detect_shape` does
not yet recognize (`_shape.py`: "not yet recognized"). That grouping ships when the second library is
real, not before; single-library-per-repo is the current design stance, so the trigger is
intentionally unmet.

Mechanism: `scripts/init_project.py` lays down the `src/<pkg>` skeleton, the root `pyproject.toml`, the
`Makefile` (owned + `racecar.mk` include), and the pre-commit config. Idempotent; owner-authorized (it
creates the build root). Doctrine home: [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md).
