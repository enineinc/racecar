---
pnode: [SKILL.md]
---

# racecar-create-package: the procedure

Accessed via [`SKILL.md`](SKILL.md). Doctrine home: [`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)
(the shape) and [`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md) (lib → api → surfaces).

Mechanism: `scripts/init_project.py` scaffolds the canon `src` shape.

## What this skill is for

Create a new Python package in the **canon src layout**: `$REPO/src/<pkg>/`, with `pyproject.toml`
at the repo root. The library is django-free, installs as a wheel, and runs as `python -m <pkg>`. It
holds the `lib → api → cli` surfaces over one `api` cut; `rest` and `mcp` are added later, by
`racecar-create-server`, into a peer `server/`, never here.

It owns the library only. It does **not** scaffold the Django server (`racecar-create-server`), add
auth (`racecar-secure-server`), or ship it (`racecar-deploy-server`).

## The cascade

`create-package` → `create-server` → `secure-server` → `deploy-server`. This is the greenfield root:
it writes `src/<pkg>`; everything downstream reads `src/<pkg>/api` and writes only `server/`.

## What it lays down

```
$REPO/
  pyproject.toml          # PEP 621 [project] + PEP 735 dependency groups; the version lives here
  Makefile                # owned targets + `include racecar.mk`
  racecar.mk              # shape-derived SRC / PKG / SERVER (vendored, identical to templates/classic)
  .pre-commit-config.yaml # the racecar hook set
  src/<pkg>/
    __init__.py
    __main__.py           # the cli surface (commands() / subcommands() / parser())
    lib/                  # the domain logic
    api/                  # the cut vertex every surface wraps (ORM-free; the data plane)
```

## Procedure

1. **Precondition.** Greenfield, or a repo with no `src/<pkg>`. Idempotent: a no-op if `src/<pkg>`
   already exists (it never clobbers a real library).
2. **Scaffold** via `init_project.py` (shape `src`): the root `pyproject.toml`, `Makefile` +
   `racecar.mk`, pre-commit, and the `src/<pkg>` skeleton.
3. **Verify** `make check` is green on the empty skeleton and `python -m <pkg>` runs.
4. **Hand off.** `racecar-create-server` reads `src/<pkg>/api` to generate the surfaces in `server/`.

## Edges and limits

- **One library, by current design.** Canon is a single root `src/<pkg>`. Multiple co-versioned
  libraries would be the workspace form (`{packages,pypkg}/<pkg>/src/<pkg>`), which `detect_shape` does
  not yet recognize; that grouping ships when a repo genuinely holds a second co-versioned library, a
  trigger left deliberately unmet today.
- **Django-free.** The library never imports Django; the ORM is walled out of the data plane
  ([`../arch-coherence/PACKAGING.md`](../arch-coherence/PACKAGING.md)). That wall is why the CLI cannot
  fold into the server.
- **Owner-authorized.** It creates the build root (the root `pyproject.toml` + the package tree).

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).
