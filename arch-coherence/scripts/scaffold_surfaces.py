#!/usr/bin/env python3
"""scaffold_surfaces.py — generate a Django ASGI surface (REST + MCP) over `api`.

Reads two inputs and emits one Django 6 ASGI project that exposes every bound
`api` callable as both a REST route (host `api.*`) and an MCP tool (host
`mcp.*`), each a thin adapter that translates transport input, calls `api`, and
renders. The surfaces hold zero orchestration (SURFACES.md §1).

Inputs
------
1. The CLI audit tree (`check_cli_commands.py --json <pkg>`) — the **exposure
   allow-list**: which verticals and subcommands exist, hence what to expose.
2. A binding JSON — per vertical, the `api` module and, per CLI subcommand, the
   bound `api` callable + HTTP method:

     {
       "package": "gfem",
       "verticals": {
         "gfem.data.ercot": {
           "api_module": "gfem.data.ercot.api",
           "commands": {
             "list":   {"api": "list_datasets", "method": "GET"},
             "status": {"api": "status",        "method": "GET"},
             "sync":   {"api": "sync",          "method": "POST"},
             "derive": {"api": "derive",        "method": "POST"}
           }
         }
       }
     }

The **parameter schema** for each command is introspected from the bound `api`
callable's signature + type hints (v1: api is the richer, correct surface; the
argparse surface only gates exposure). Run this with the *target project's*
interpreter so the api modules import.

Output
------
`<out>/` — a `src+server`-shape `server/` tree, vertical-first: manage.py,
project/ (settings/{settings,api,mcp}.py, urls/{apiurls,mcpurls}.py, surfaceguard.py,
sitemaps.py, views.py, asgi.py), apps/<vertical>/ (commands.py +
views/{apiviews,mcpviews}.py + urls/apiurls.py), apps/mcp.py (the single MCP
endpoint), docs/api/{manifest.json, openapi.json, ENDPOINTS.md}, pyproject.toml,
run.sh, plus apache/{api,mcp}.vhost.conf snippets.

Idempotent: re-running re-derives the manifest and re-emits every file. It never
writes into the api modules.
"""

import argparse
import importlib
import inspect
import json
import tomllib
import types
import typing
from pathlib import Path

from scaffold_surfaces_templates import render_project, render_shell

# --------------------------------------------------------------------------
# signature -> JSON Schema (2020-12), the shape MCP inputSchema + OpenAPI share
# --------------------------------------------------------------------------

_SCALAR = {str: "string", bool: "boolean", int: "integer", float: "number"}
_NoneType = type(None)


def _strip_optional(annotation):
    """Unwrap `X | None` / `Optional[X]` -> (inner, is_optional)."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in typing.get_args(annotation) if a is not _NoneType]
        is_opt = len(args) != len(typing.get_args(annotation))
        inner = args[0] if len(args) == 1 else args
        return inner, is_opt
    return annotation, False


def _json_type(annotation) -> dict:
    """Best-effort JSON Schema fragment for a parameter annotation."""
    inner, _ = _strip_optional(annotation)
    # date is carried as a string with format hint (argparse parses YYYY-MM-DD)
    name = getattr(inner, "__name__", str(inner))
    if name == "date":
        return {"type": "string", "format": "date"}
    origin = typing.get_origin(inner)
    if origin in (list, tuple):
        args = typing.get_args(inner)
        item = _json_type(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item}
    if isinstance(inner, list):  # X | Y | None collapsed to [X, Y]
        return {"type": "string"}  # heterogeneous union -> permissive string
    if inner in _SCALAR:
        return {"type": _SCALAR[inner]}
    return {"type": "string"}


def schema_for_callable(func) -> dict:
    """Introspect a callable -> JSON Schema object for its keyword params."""
    sig = inspect.signature(func)
    try:
        hints = typing.get_type_hints(func)
    except Exception:  # pylint: disable=broad-exception-caught
        hints = {}
    props: dict = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        if pname == "self" or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        ann = hints.get(pname, param.annotation)
        frag = (
            _json_type(ann)
            if ann is not inspect.Parameter.empty
            else {"type": "string"}
        )
        doc = ""
        props[pname] = {**frag, **({"description": doc} if doc else {})}
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    schema: dict = {
        "type": "object",
        "properties": props,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


# --------------------------------------------------------------------------
# manifest: the derived Interface Manifest the surfaces consume
# --------------------------------------------------------------------------


def collect_subcommands(audit: dict) -> dict[str, set[str]]:
    """{vertical_pkg: {subcommand names}} from the CLI audit tree."""
    found: dict[str, set[str]] = {}

    def walk(node):
        subs = node.get("subcommands") or []
        if subs:
            found[node["pkg"]] = {s["name"] for s in subs}
        for child in node.get("children") or []:
            walk(child)

    walk(audit)
    return found


def build_manifest(audit: dict, binding: dict) -> dict:
    """Build the Interface Manifest: per-vertical commands with schema + bind target."""
    exposed = collect_subcommands(audit)
    verticals = []
    for vpkg, vbind in binding["verticals"].items():
        api_mod = importlib.import_module(vbind["api_module"])
        # REST taxonomy: /api/v1/<package>/<vertical-path>/<command>, where
        # <package>/<vertical-path> is the vertical's full dotted name
        # (gfem.data.ercot -> gfem/data/ercot). `/api/v1/<package>/<vertical-path>/`
        # is the per-vertical include prefix (versioned, legible in
        # project/urls/apiurls.py); the command is the per-vertical route.
        http_prefix = f"api/v1/{vpkg.replace('.', '/')}/"
        commands = []
        for sub, cb in vbind["commands"].items():
            if vpkg in exposed and sub not in exposed[vpkg]:
                continue  # not in the CLI allow-list -> not exposed
            func = getattr(api_mod, cb["api"])
            tool = f"{vpkg.replace('.', '_')}_{sub}"
            method = cb.get("method", "POST").upper()
            # Per-tool scope (AUTH.md). Default-deny, but ergonomic: derive
            # pkg:vertical:read|write from the verb when the binding omits a scope;
            # an explicit binding scope overrides. read for GET, write otherwise.
            verb = "read" if method == "GET" else "write"
            default_scope = f"{binding['package']}:{vpkg.split('.')[-1]}:{verb}"
            commands.append(
                {
                    "subcommand": sub,
                    "api_module": vbind["api_module"],
                    "api_callable": cb["api"],
                    "method": cb.get("method", "POST"),
                    "http_path": f"/{http_prefix}{sub}",
                    "route": sub,
                    "mcp_tool": tool,
                    "description": (inspect.getdoc(func) or "").split("\n", maxsplit=1)[0],
                    "input_schema": schema_for_callable(func),
                    "is_write": method != "GET",
                    "scope": cb.get("scope") or default_scope,
                }
            )
        verticals.append(
            {
                "vertical": vpkg,
                "app": vbind.get("app", vpkg.split(".")[-1]),
                "api_module": vbind["api_module"],
                "http_prefix": http_prefix,
                "commands": commands,
            }
        )
    return {
        "package": binding["package"],
        "mcp_protocol_version": "2025-11-25",
        "verticals": verticals,
    }


# --------------------------------------------------------------------------
# rendering: the manifest-interpolated Django 6 ASGI builders (the static bodies are
# mirror-tree files under templates/, copied verbatim by render_tree)
# --------------------------------------------------------------------------

# NOTE: the manifest-interpolated builders live in scaffold_surfaces_templates.py to
# keep this file focused on the manifest. That module pulls in only json + pathlib (no
# Django), so the top-level import is safe and --manifest-only stays Django-free.


def scaffold_binding(audit: dict) -> str:
    """Derive a `[tool.racecar.surface]` binding STUB from the CLI audit tree.

    Enumerates every vertical (a leaf/own-CLI node) and its subcommands so the
    author fills in api callables + methods instead of writing the binding from
    scratch. Unknown read/write classification defaults to POST (write) — the
    fail-safe default, since writes are gated off until the author marks a
    command GET. This is the friction-reducer for standing up a new package.
    """
    lines = ["[tool.racecar.surface]", f'package = "{audit["pkg"]}"', ""]
    verticals: list[tuple[str, list[str]]] = []

    def walk(node):
        if node.get("pattern") in ("pattern-2", "pattern-3"):
            verticals.append(
                (node["pkg"], [s["name"] for s in (node.get("subcommands") or [])])
            )
        for child in node.get("children") or []:
            walk(child)

    walk(audit)
    for vpkg, subs in verticals:
        # Suggested scope namespace per vertical (AUTH.md: pkg:vertical:read|write); the
        # author tightens read vs write. Default-deny: a command needs a scope to be reachable.
        scope = f"{audit['pkg']}:{vpkg.split('.')[-1]}:write"
        lines.append(f'[tool.racecar.surface.verticals."{vpkg}"]')
        lines.append(
            f'api_module = "{vpkg}.api"  # TODO: module holding the bound api callables'
        )
        if subs:
            for sub in subs:
                lines.append(
                    f'commands.{sub} = {{ api = "{sub}", method = "POST", scope = "{scope}" }}'
                    "  # TODO: callable; GET + :read scope if read-only"
                )
        else:
            lines.append(
                f'commands.run = {{ api = "TODO", method = "POST", scope = "{scope}" }}'
                "  # flag-leaf: TODO callable; GET + :read scope if read-only"
            )
        lines.append("")
    return "\n".join(lines)


def load_binding(path: Path) -> dict:
    """Load the binding from `pyproject.toml` ([tool.racecar.surface]) or a JSON file.

    The pyproject form is the one-home default (the binding is project config, so
    it belongs beside the rest of it); the JSON form is the equivalent structure
    for projects that prefer a standalone file.
    """
    if path.suffix == ".toml":
        data = tomllib.loads(path.read_text())
        return data["tool"]["racecar"]["surface"]
    return json.loads(path.read_text())


def main() -> None:
    """CLI entry: audit + binding -> manifest -> render the server surface."""
    ap = argparse.ArgumentParser(
        description="Generate a Django ASGI REST+MCP surface over `api`."
    )
    ap.add_argument(
        "--audit",
        type=Path,
        help="CLI audit JSON (check_cli_commands --json); required unless --shell-only",
    )
    ap.add_argument(
        "--binding",
        type=Path,
        help="binding: pyproject.toml ([tool.racecar.surface]) or a standalone JSON file",
    )
    ap.add_argument("--out", type=Path, help="server output root")
    ap.add_argument(
        "--manifest-only", action="store_true", help="emit only docs/api/manifest.json"
    )
    ap.add_argument(
        "--scaffold-binding",
        action="store_true",
        help="print a binding stub derived from the audit tree, then exit (no generation)",
    )
    ap.add_argument(
        "--shell-only",
        action="store_true",
        help="start-django-project: write only the vanilla, location-free Django shell",
    )
    args = ap.parse_args()

    # racecar-start-django-project: the vanilla shell pass — a generic, location-free,
    # bootable Django project. No audit/binding/package needed; it knows no library and
    # carries no surfaces (those are racecar-create-server's job, composed on top).
    if args.shell_only:
        if not args.out:
            ap.error("--shell-only requires --out")
        render_shell(args.out)
        print(f"vanilla Django shell (no surfaces) -> {args.out}")
        return

    if not args.audit:
        ap.error("--audit is required unless --shell-only is given")
    audit = json.loads(args.audit.read_text())

    if args.scaffold_binding:
        print(scaffold_binding(audit))
        return

    if not args.binding or not args.out:
        ap.error("--binding and --out are required unless --scaffold-binding is given")
    binding = load_binding(args.binding)
    manifest = build_manifest(audit, binding)

    render_project(manifest, args.out, manifest_only=args.manifest_only)
    n = sum(len(v["commands"]) for v in manifest["verticals"])
    print(
        f"surfaces: {n} command(s) across {len(manifest['verticals'])} vertical(s) -> {args.out}"
    )


if __name__ == "__main__":
    main()
