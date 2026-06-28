"""Rendered file bodies for scaffold_surfaces.py — qjango-shaped server.

`render_project` writes a Django ASGI `server/` tree, vertical-first: a
composition-root `project/` package, and one Django app per api vertical under
`apps/<name>/` that co-locates BOTH surfaces over that vertical's api:

  apps/<v>/commands.py        the transport-neutral binding over <pkg>.<v>.api
  apps/<v>/views/apiviews.py  REST views built from commands
  apps/<v>/views/mcpviews.py  MCP tool table built from commands
  apps/<v>/urls/apiurls.py    REST routes
  apps/mcp.py                 the single MCP endpoint, aggregating every mcpviews

Import DAG: commands -> <pkg>.<v>.api; apiviews/mcpviews -> commands; apiurls ->
{commands, apiviews}; apps/mcp.py -> apps/<v>/views/mcpviews; project -> apps;
nothing imports project. The two surfaces are siblings over `commands` (the binding
is the shared ancestor) -- mcp never imports the REST surface. The binding lives in
exactly one place, so the bulky `input_schema` is written once per command, not
once per surface. Database-light: empty models/admin, no qux.
"""

import json
from pathlib import Path

from scaffold_surfaces_docs import endpoints_md, openapi_doc, sitemaps_py
from scaffold_tree import render_tree

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
API_PORT = 8001
MCP_PORT = 8002

# --------------------------------------------------------------------------
# builder functions: the manifest-interpolated .py templates (settings base, urlconf
# includes, per-vertical adapters, the MCP endpoint). The static bodies are the mirror
# trees under templates/{django-project,server}/, copied verbatim by render_tree.
# --------------------------------------------------------------------------


def _settings_py(manifest: dict) -> str:
    apps_block = "\n".join(f'    "apps.{v["app"]}",' for v in manifest["verticals"])
    return f'''"""Shared base settings (racecar-create-server). One process per surface:
each vhost launches its own settings module (project.settings.api /
project.settings.mcp), and that module sets ROOT_URLCONF to its surface's urlconf.
This base holds everything common; the surface modules add only what differs.
Database-light (sqlite default, no domain models, no qux).

django_extensions is surface-agnostic (no urls) and lives here; debug_toolbar is
api-only and is added in project.settings.api, because it mounts __debug__/ in
project.urls.api and would otherwise reverse `djdt` against a urlconf without it.

Install dev tools with `make install-dev` (the library `django` group);
`make install` installs the server runtime (django, uvicorn)."""
import os
from pathlib import Path

# settings.py -> settings/ -> project/ -> server root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-deploy-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,api.localhost,mcp.localhost"
).split(",")
USE_X_FORWARDED_HOST = os.environ.get("DJANGO_USE_X_FORWARDED_HOST", "1") == "1"
INTERNAL_IPS = ["127.0.0.1"]

# Dev tools, DEBUG-gated (the house DEBUG_APPS pattern). debug_toolbar is added
# per-surface in project.settings.api, not here. Single assignment (no augmented +=)
# so pylint keeps INSTALLED_APPS a module constant.
DEBUG_APPS = ["django_extensions"]
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    *(DEBUG_APPS if DEBUG else []),
{apps_block}
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "project.surfaceguard.SurfaceHostMiddleware",
]

# Default surface + urlconf. project.settings.{{api,mcp}} override both per process;
# this default lets bare `project.settings.settings` (e.g. manage.py fallbacks)
# resolve urls.
SURFACE = "api"
ROOT_URLCONF = "project.urls.apiurls"
WSGI_APPLICATION = "project.wsgi.application"

TEMPLATES = [
    {{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {{"context_processors": ["django.template.context_processors.request"]}},
    }}
]

# Database — the house pattern (xenocrates): sqlite (db.sqlite3) by default,
# mysql when DB_TYPE=mysql, env-driven. Database-light, but Django's machinery
# (migrations, sessions) needs a real ENGINE.
MYSQL_SETTINGS = {{
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.getenv("DB_NAME", None),
    "USER": os.getenv("DB_USERNAME", None),
    "PASSWORD": os.getenv("DB_PASSWORD", None),
    "HOST": os.getenv("DB_HOST", "localhost"),
    "PORT": os.getenv("DB_PORT", ""),
    "OPTIONS": {{"charset": "utf8mb4", "ssl": {{"ca": os.getenv("DB_SSL_CERT", None)}}}},
}}
SQLITE_SETTINGS = {{
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}}
if os.getenv("DB_TYPE", "sqlite").lower() == "mysql":
    DATABASES = {{"default": MYSQL_SETTINGS}}
else:
    DATABASES = {{"default": SQLITE_SETTINGS}}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Write verbs (any non-GET command) are refused unless this is enabled out of
# band. A no-tty surface cannot prompt, so it fails safe.
RACECAR_ALLOW_WRITES = os.environ.get(
    "RACECAR_ALLOW_WRITES", ""
).lower() in ("1", "true", "yes", "on")

# Resource-server auth (AUTH.md): a surface validates a bearer token by introspection
# (RFC 7662) against the Authorization Server, with its own client credential (the
# "introspection" scope). Unset -> the surface fails closed (project.auth refuses calls).
AUTH_INTROSPECTION_URL = os.environ.get("AUTH_INTROSPECTION_URL", "")
AUTH_INTROSPECTION_CLIENT_ID = os.environ.get("AUTH_INTROSPECTION_CLIENT_ID", "")
AUTH_INTROSPECTION_CLIENT_SECRET = os.environ.get("AUTH_INTROSPECTION_CLIENT_SECRET", "")
AUTH_INTROSPECTION_CACHE_SECONDS = float(
    os.environ.get("AUTH_INTROSPECTION_CACHE_SECONDS", "30")
)
# The Authorization Server issuer URL, advertised to MCP clients via the protected-resource
# metadata (RFC 9728) so they can find where to authenticate.
AUTH_ISSUER = os.environ.get("AUTH_ISSUER", "")
'''




def _urls_api_py(manifest: dict) -> str:
    # The /api/v1/<vertical-path>/ taxonomy lives here, once per vertical, as the
    # include prefix; each vertical's apiurls then route bare command names.
    includes = "\n".join(
        f'    path("{v["http_prefix"]}", include("apps.{v["app"]}.urls.apiurls")),'
        for v in manifest["verticals"]
    )
    return f'''"""REST surface urlconf (api process). Mounts each vertical's routes under its
versioned taxonomy prefix /api/v1/<vertical-path>/, plus the OpenAPI document
(/api/v1/openapi.json) and the endpoint sitemap (/sitemap/, /sitemap.xml/)."""
from django.conf import settings
from django.urls import include, path

from project.sitemaps import ApiEndpointSitemap, custom_sitemap
from project.views import openapi

_SITEMAPS = {{"endpoints": ApiEndpointSitemap()}}

urlpatterns = [
    path("api/v1/openapi.json", openapi, name="openapi"),
    path("sitemap.xml/", custom_sitemap, {{"sitemaps": _SITEMAPS}}, name="sitemap_xml"),
    path("sitemap/", custom_sitemap, {{"sitemaps": _SITEMAPS}}, name="sitemap"),
{includes}
]

# debug_toolbar mounts its endpoints only under DEBUG (the house pattern). This
# urlconf is loaded only by the api surface, which is where debug_toolbar lives.
if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
'''


# --------------------------------------------------------------------------
# per-vertical app (apps/<name>/) — both surfaces over its own api, vertical-first
# --------------------------------------------------------------------------

APP_CONFIG_PY = '''from django.apps import AppConfig


class {cls}(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{name}"
'''

EMPTY_MODELS_PY = '''"""Database-light: this surface holds no models."""
'''

EMPTY_ADMIN_PY = '''"""Database-light: nothing registered with the admin."""
'''


def _commands_registry(vertical: dict) -> str:
    """The COMMANDS dict body. `route` is the bare command name; the versioned
    /api/v1/<vertical-path>/ prefix is applied by project/urls/apiurls.py."""
    rows = []
    for c in vertical["commands"]:
        rows.append(
            f'    "{c["subcommand"]}": {{\n'
            f'        "tool": "{c["mcp_tool"]}",\n'
            f'        "func": {c["api_callable"]},\n'
            f'        "schema": {c["input_schema"]!r},\n'
            f'        "write": {c["is_write"]},\n'
            f'        "method": "{c["method"].upper()}",\n'
            f'        "route": "{c["route"]}",\n'
            f'        "scope": {c.get("scope", "")!r},\n'
            f'        "description": {c["description"]!r},\n'
            f"    }},"
        )
    return "COMMANDS = {\n" + "\n".join(rows) + "\n}\n"


def _commands_py(vertical: dict) -> str:
    """apps/<v>/commands.py: the transport-neutral binding over the vertical's api.
    The single home for the command table; both surfaces import COMMANDS from here."""
    imports = "\n".join(
        f"from {vertical['api_module']} import {name}"
        for name in dict.fromkeys(c["api_callable"] for c in vertical["commands"])
    )
    registry = _commands_registry(vertical)
    return f'''"""Command bindings for the {vertical["vertical"]} vertical -- the transport-neutral
table over its api. One home for the binding: apiviews (REST) and mcpviews (MCP)
both import COMMANDS from here, so neither surface derives from the other and the
schema is written once per command.
"""
# COMMANDS embeds api-authored descriptions as string literals; black cannot wrap a
# single string token, so a long description may exceed the line length. Generated
# data, not hand-formatted code.
# pylint: disable=line-too-long
{imports}

{registry}'''


def _apiviews_py(vertical: dict) -> str:
    """apps/<v>/views/apiviews.py: REST views, thin async adapters built from COMMANDS."""
    return f'''"""REST views for the {vertical["vertical"]} vertical -- thin async adapters over its
api, built from the vertical's COMMANDS binding. Each coerces transport input, calls
the api callable off the event loop, and renders JSON.
"""
import json

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from project import auth

from ..commands import COMMANDS


def _err(message, status_code):
    resp = JsonResponse({{"error": message}}, status=status_code)
    if status_code == 401:
        resp["WWW-Authenticate"] = "Bearer"
    return resp


def _coerce_query(schema, query):
    out = {{}}
    for key, spec in schema.get("properties", {{}}).items():
        if key not in query and not query.getlist(key):
            continue
        kind = spec.get("type")
        if kind == "boolean":
            out[key] = query.get(key, "").lower() in ("1", "true", "yes", "on")
        elif kind == "integer":
            out[key] = int(query.get(key))
        elif kind == "number":
            out[key] = float(query.get(key))
        elif kind == "array":
            out[key] = query.getlist(key) or query.get(key, "").split(",")
        else:
            out[key] = query.get(key)
    return out


def _make_view(spec):
    schema = spec["schema"]

    @csrf_exempt
    async def _view(request):
        if request.method != spec["method"]:
            return _err("method not allowed", 405)
        # Closed by default (AUTH.md): require a valid bearer token carrying this
        # command's scope before anything else. 401 unauthenticated, 403 out-of-scope.
        denied = await sync_to_async(auth.check)(request, spec["scope"])
        if denied:
            return _err(denied[1], denied[0])
        if spec["write"] and not settings.RACECAR_ALLOW_WRITES:
            return _err("writes disabled; set RACECAR_ALLOW_WRITES=1", 403)
        if request.method == "GET":
            try:
                kwargs = _coerce_query(schema, request.GET)
            except (ValueError, TypeError) as exc:
                return _err(f"invalid query parameter: {{exc}}", 400)
        else:
            try:
                kwargs = json.loads(request.body or b"{{}}")
            except json.JSONDecodeError:
                return _err("invalid JSON body", 400)
            if not isinstance(kwargs, dict):
                return _err("body must be a JSON object", 400)
        missing = [r for r in schema.get("required", []) if r not in kwargs or kwargs[r] is None]
        if missing:
            return _err(f"missing required: {{missing}}", 400)
        try:
            result = await sync_to_async(spec["func"], thread_sensitive=False)(**kwargs)
        except ValueError as exc:
            # Contract (SURFACES.md): the api raises ValueError only for caller-input
            # problems, so its message is safe to return as a 400. An internal fault must
            # raise a non-ValueError, which surfaces as a 500 (not echoed to the caller).
            return _err(str(exc), 400)
        return JsonResponse(result, safe=not isinstance(result, list))

    return _view


VIEWS = {{name: _make_view(spec) for name, spec in COMMANDS.items()}}
'''


def _mcpviews_py(vertical: dict) -> str:
    """apps/<v>/views/mcpviews.py: the MCP projection of COMMANDS, keyed by tool name."""
    return f'''"""MCP tool specs for the {vertical["vertical"]} vertical: the MCP
projection of its COMMANDS binding, keyed by tool name. apps/mcp.py aggregates
every vertical's TOOLS into the single endpoint.
"""
from ..commands import COMMANDS

TOOLS = {{spec["tool"]: spec for spec in COMMANDS.values()}}
'''


def _apiurls_py(vertical: dict) -> str:
    """apps/<v>/urls/apiurls.py: bare command routes (the versioned prefix is in
    project/urls/apiurls.py)."""
    return f'''"""REST routes for the {vertical["vertical"]} vertical, built from COMMANDS. The
versioned /api/v1/<vertical-path>/ prefix is added by project/urls/apiurls.py."""
from django.urls import path

from ..commands import COMMANDS
from ..views.apiviews import VIEWS

urlpatterns = [
    path(spec["route"], VIEWS[name], name=spec["tool"]) for name, spec in COMMANDS.items()
]
'''


# --------------------------------------------------------------------------
# apps/mcp.py — the single MCP endpoint, aggregating every vertical's mcpviews
# --------------------------------------------------------------------------


def _mcp_endpoint_py(manifest: dict) -> str:
    """apps/mcp.py: one Streamable-HTTP endpoint. Imports each vertical's TOOLS
    (apps/mcp.py -> apps/<v>/views/mcpviews; the verticals never import back)."""
    imports = "\n".join(
        f"from apps.{v['app']}.views.mcpviews import TOOLS as _{v['app']}_tools"
        for v in manifest["verticals"]
    )
    agg = ", ".join(f"_{v['app']}_tools" for v in manifest["verticals"])
    return f'''"""MCP surface: one Streamable-HTTP endpoint exposing every vertical's tools. It
aggregates each vertical's TOOLS (apps/mcp.py -> apps/<v>/views/mcpviews; the
verticals never import back). Tools-only, request/response: every POST gets
application/json; GET -> 405. Wire shapes per MCP revision {manifest["mcp_protocol_version"]}.
"""
import json

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from project import auth

{imports}

PROTOCOL_VERSION = "{manifest["mcp_protocol_version"]}"


def _www_authenticate(request):
    base = f"{{request.scheme}}://{{request.get_host()}}"
    meta = f"{{base}}/.well-known/oauth-protected-resource"
    return f'Bearer resource_metadata="{{meta}}"'


def protected_resource_metadata(request):
    """RFC 9728: tell an MCP client which Authorization Server protects this resource."""
    base = f"{{request.scheme}}://{{request.get_host()}}"
    issuer = getattr(settings, "AUTH_ISSUER", "")
    return JsonResponse(
        {{"resource": base, "authorization_servers": [issuer] if issuer else []}}
    )

# tool name -> spec (func, schema, write, description). Each vertical's mcpviews
# already keys its TOOLS by tool name; this unions them.
_TOOLS = {{}}
for _tools in ({agg},):
    _dup = set(_TOOLS) & set(_tools)
    if _dup:  # fail fast: a silently-overwritten tool would shadow another vertical's
        raise RuntimeError(f"duplicate MCP tool name(s) across verticals: {{sorted(_dup)}}")
    _TOOLS.update(_tools)


def _result(req_id, result):
    return JsonResponse({{"jsonrpc": "2.0", "id": req_id, "result": result}})


def _error(req_id, code, message):
    return JsonResponse(
        {{"jsonrpc": "2.0", "id": req_id, "error": {{"code": code, "message": message}}}}
    )


def _tool_result(req_id, text, is_error):
    content = [{{"type": "text", "text": text}}]
    return _result(req_id, {{"content": content, "isError": is_error}})


def _tool_list():
    tools = []
    for name, spec in _TOOLS.items():
        tools.append(
            {{
                "name": name,
                "description": spec["description"] or name,
                "inputSchema": spec["schema"],
                "annotations": {{"readOnlyHint": not spec["write"]}},
            }}
        )
    return {{"tools": tools}}


async def _tool_call(request, req_id, params):
    name = (params or {{}}).get("name")
    spec = _TOOLS.get(name)
    if spec is None:
        return _error(req_id, -32602, f"Unknown tool: {{name}}")
    # Per-tool scope (AUTH.md, default-deny). Re-runs auth.check (token + this tool's
    # scope); the endpoint already introspected, so this is a cache hit, not a second AS
    # round-trip. -32001 mirrors an OAuth insufficient_scope.
    denied = await sync_to_async(auth.check)(request, spec["scope"])
    if denied:
        return _error(req_id, -32001, denied[1])
    if spec["write"] and not settings.RACECAR_ALLOW_WRITES:
        return _tool_result(req_id, "writes disabled; set RACECAR_ALLOW_WRITES=1", True)
    arguments = (params or {{}}).get("arguments") or {{}}
    try:
        result = await sync_to_async(spec["func"], thread_sensitive=False)(**arguments)
    except ValueError as exc:
        return _tool_result(req_id, str(exc), True)
    return _tool_result(req_id, json.dumps(result, default=str), False)


@csrf_exempt
async def endpoint(request):
    """The single MCP Streamable-HTTP endpoint: dispatch one JSON-RPC message."""
    if request.method != "POST":
        return JsonResponse({{"error": "method not allowed"}}, status=405)
    try:
        msg = json.loads(request.body or b"{{}}")
    except json.JSONDecodeError:
        return _error(None, -32700, "Parse error")
    method, req_id = msg.get("method"), msg.get("id")
    # Closed by default (AUTH.md): every message needs a valid bearer token. An
    # unauthenticated client gets 401 + WWW-Authenticate pointing at the protected-
    # resource metadata, which is how it discovers the Authorization Server.
    denied = await sync_to_async(auth.check)(request, None)
    if denied:
        resp = _error(req_id, -32001, denied[1])
        resp.status_code = denied[0]
        if denied[0] == 401:  # only an auth challenge carries the WWW-Authenticate hint
            resp["WWW-Authenticate"] = _www_authenticate(request)
        return resp
    if req_id is None and method and method.startswith("notifications/"):
        return HttpResponse(status=202)
    if method == "initialize":
        return _result(
            req_id,
            {{
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {{"tools": {{"listChanged": False}}}},
                "serverInfo": {{"name": "{manifest["package"]}-mcp", "version": "0.1.0"}},
            }},
        )
    if method == "tools/list":
        return _result(req_id, _tool_list())
    if method == "tools/call":
        return await _tool_call(request, req_id, msg.get("params"))
    return _error(req_id, -32601, f"Method not found: {{method}}")
'''

# --------------------------------------------------------------------------
# renderer
# --------------------------------------------------------------------------


def _app_class(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_")) + "Config"


def _write_surfaces(manifest: dict, out: Path, docs_api: Path) -> None:
    """The per-vertical SURFACE adapters (racecar-create-server): apps/<v>/ (commands +
    apiviews/mcpviews + urls), the single apps/mcp.py endpoint, and the OpenAPI +
    ENDPOINTS docs. Assumes the shell already carries the verticals in its seams."""
    for v in manifest["verticals"]:
        app = out / "apps" / v["app"]
        (app / "views").mkdir(parents=True, exist_ok=True)
        (app / "urls").mkdir(parents=True, exist_ok=True)
        (app / "__init__.py").write_text("")
        (app / "apps.py").write_text(
            APP_CONFIG_PY.format(cls=_app_class(v["app"]), name=f"apps.{v['app']}")
        )
        (app / "models.py").write_text(EMPTY_MODELS_PY)
        (app / "admin.py").write_text(EMPTY_ADMIN_PY)
        (app / "commands.py").write_text(_commands_py(v))
        (app / "views" / "__init__.py").write_text("")
        (app / "views" / "apiviews.py").write_text(_apiviews_py(v))
        (app / "views" / "mcpviews.py").write_text(_mcpviews_py(v))
        (app / "urls" / "__init__.py").write_text("")
        (app / "urls" / "apiurls.py").write_text(_apiurls_py(v))
    (out / "apps" / "mcp.py").write_text(_mcp_endpoint_py(manifest))
    (docs_api / "openapi.json").write_text(openapi_doc(manifest))
    (docs_api / "ENDPOINTS.md").write_text(endpoints_md(manifest))


def render_shell(out: Path) -> None:
    """racecar-start-django-project entry: copy the vanilla Django shell tree
    (templates/django-project) to `out` -- generic, location-free, bootable; no surfaces,
    no auth. `manage.py check` passes and it serves nothing. racecar-create-server composes
    the surfaces on top via render_project."""
    render_tree(_TEMPLATES / "django-project", out)


def render_project(manifest: dict, out: Path, *, manifest_only: bool = False) -> None:
    """Write the qjango-shaped server tree: copy the static surface tree (templates/server),
    then overlay the manifest-interpolated files and the per-vertical adapters. The manifest
    IR is always written first; --manifest-only stops there."""
    (out / "project").mkdir(parents=True, exist_ok=True)
    (out / "apps").mkdir(parents=True, exist_ok=True)
    docs_api = out / "docs" / "api"
    docs_api.mkdir(parents=True, exist_ok=True)
    (docs_api / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if manifest_only:
        return
    # A prior vanilla shell left single settings.py/urls.py modules; the surface form needs
    # packages, so drop the stale modules before copying the surface tree over them.
    (out / "project" / "settings.py").unlink(missing_ok=True)
    (out / "project" / "urls.py").unlink(missing_ok=True)
    render_tree(
        _TEMPLATES / "server",
        out,
        {"__API_PORT__": str(API_PORT), "__MCP_PORT__": str(MCP_PORT)},
    )
    # Overlay the manifest-interpolated files (not part of the static mirror tree).
    (out / "project" / "settings" / "settings.py").write_text(_settings_py(manifest))
    (out / "project" / "urls" / "apiurls.py").write_text(_urls_api_py(manifest))
    (out / "project" / "sitemaps.py").write_text(sitemaps_py(manifest))
    _write_surfaces(manifest, out, docs_api)
