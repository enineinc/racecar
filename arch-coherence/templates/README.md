# arch-coherence/templates: generation mirror trees

Each subtree mirrors a target output tree 1:1: [`render_tree`](../scripts/scaffold_tree.py)
copies every file to the same relative path under the generated server, substituting
placeholders and making `*.sh` executable. The static bodies live here as real files (a
literal picture of what gets generated); the generators overlay only the manifest-interpolated
files on top.

- `django-project/`: the vanilla Django shell (racecar-start-django-project). Copied
  verbatim by `render_shell` in
  [`../scripts/scaffold_surfaces_templates.py`](../scripts/scaffold_surfaces_templates.py):
  `manage.py`, `pyproject.toml`, the single-module `project/` (settings, urls, asgi, wsgi),
  and an empty `apps/`. No placeholders.
- `server/`: the surface composition (racecar-create-server). Copied by `render_project`
  (`__API_PORT__` / `__MCP_PORT__` substituted), which then overlays the interpolated
  `project/settings/settings.py`, `project/urls/apiurls.py`, `project/sitemaps.py`, and the
  per-vertical `apps/<v>/` + `apps/mcp.py` + `docs/api/`.
- `authserver/`: the Authorization Server (racecar-secure-server). Copied by
  `render_authserver` in
  [`../scripts/scaffold_authserver.py`](../scripts/scaffold_authserver.py) (`__PORT__` and the
  login `{next_json}` substituted), which then overlays the interpolated
  `project/settings/auth.py` (the issuer).

The manifest-interpolated templates stay as builder functions in the generator scripts, since
their bodies depend on the project's verticals or issuer; everything static is a file in the
mirror trees above.
