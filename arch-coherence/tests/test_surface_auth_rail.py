"""Stage 5: the resource-surface auth rail. A regenerated surface is closed by default —
project/auth.py validates the bearer token, every adapter checks the command's scope, and
check_surface_auth (the Stage 3 gate that failed the anonymous surface) now passes."""

from __future__ import annotations

import compileall
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "arch-coherence" / "scripts"))
import check_surface_auth  # noqa: E402
import scaffold_surfaces  # noqa: E402
import scaffold_surfaces_templates as templates  # noqa: E402


def _manifest(*, scope: str):
    """A minimal one-command manifest, scoped or not, in the shape render_project wants."""
    command = {
        "subcommand": "list",
        "api_module": "pkg.ercot.api",
        "api_callable": "list_datasets",
        "method": "GET",
        "http_path": "/api/v1/pkg/ercot/list",
        "route": "list",
        "mcp_tool": "pkg_ercot_list",
        "description": "List datasets.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "is_write": False,
        "scope": scope,
    }
    return {
        "package": "pkg",
        "mcp_protocol_version": "2025-11-25",
        "verticals": [
            {
                "vertical": "pkg.ercot",
                "app": "ercot",
                "api_module": "pkg.ercot.api",
                "http_prefix": "api/v1/pkg/ercot/",
                "commands": [command],
            }
        ],
    }


def test_shell_emits_the_resource_validator(tmp_path):
    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    auth = (tmp_path / "server" / "project" / "auth.py").read_text()
    assert "def check(" in auth
    assert "introspect" in auth  # RFC 7662 validation
    assert "fail closed" in auth.lower() or "FAILS CLOSED" in auth


def test_rest_adapter_enforces_token_and_scope(tmp_path):
    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    views = (tmp_path / "server" / "apps" / "ercot" / "views" / "apiviews.py").read_text()
    assert "from project import auth" in views
    assert "auth.check" in views and 'spec["scope"]' in views
    assert "WWW-Authenticate" in views


def test_mcp_adapter_enforces_and_advertises_the_as(tmp_path):
    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    mcp = (tmp_path / "server" / "apps" / "mcp.py").read_text()
    assert "WWW-Authenticate" in mcp
    assert "protected_resource_metadata" in mcp  # RFC 9728
    assert "auth.check" in mcp and "request, None" in mcp  # endpoint-level token gate


def test_openapi_carries_security(tmp_path):
    import json

    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    doc = json.loads((tmp_path / "server" / "docs" / "api" / "openapi.json").read_text())
    assert "oauth2" in doc["components"]["securitySchemes"]
    op = doc["paths"]["/api/v1/pkg/ercot/list"]["get"]
    assert op["security"] == [{"oauth2": ["pkg:ercot:read"]}]
    assert "401" in op["responses"] and "403" in op["responses"]


def test_check_surface_auth_passes_a_scoped_surface(tmp_path):
    # The Stage 3 gate failed the anonymous gfem surface; a regenerated scoped surface
    # (auth.py present + every command scoped) now passes it.
    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    assert check_surface_auth.findings(tmp_path) == []


def test_check_surface_auth_still_bites_an_unscoped_surface(tmp_path):
    templates.render_project(_manifest(scope=""), tmp_path / "server")
    problems = check_surface_auth.findings(tmp_path)
    assert problems and any("no scope" in p for p in problems)


def test_generated_surface_is_syntactically_valid(tmp_path):
    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    # Syntax-check every generated .py (no imports executed): catches template defects.
    assert compileall.compile_dir(
        str(tmp_path / "server"), quiet=1, force=True
    )


def test_surface_logs_each_decision(tmp_path):
    # Stage 6: per-call audit at the surface is the log (database-light), not a table.
    templates.render_project(_manifest(scope="pkg:ercot:read"), tmp_path / "server")
    auth = (tmp_path / "server" / "project" / "auth.py").read_text()
    assert "logging.getLogger" in auth
    assert '_log.warning("deny' in auth and '_log.info("allow' in auth


def test_scope_is_auto_derived_from_the_verb(monkeypatch):
    # Stage 6, decision 1: when the binding omits a scope, derive pkg:vertical:read|write
    # from the method (read for GET, write otherwise); an explicit binding scope overrides.
    mod = types.ModuleType("fakepkg.ercot.api")

    def list_datasets():
        """List datasets."""

    def sync():
        """Sync."""

    def derive():
        """Derive."""

    mod.list_datasets, mod.sync, mod.derive = list_datasets, sync, derive
    monkeypatch.setitem(sys.modules, "fakepkg.ercot.api", mod)
    audit = {
        "pkg": "fakepkg.ercot",
        "subcommands": [{"name": "list"}, {"name": "sync"}, {"name": "derive"}],
        "children": [],
    }
    binding = {
        "package": "fakepkg",
        "verticals": {
            "fakepkg.ercot": {
                "api_module": "fakepkg.ercot.api",
                "commands": {
                    "list": {"api": "list_datasets", "method": "GET"},
                    "sync": {"api": "sync", "method": "POST"},
                    "derive": {"api": "derive", "method": "POST", "scope": "custom:scope"},
                },
            }
        },
    }
    manifest = scaffold_surfaces.build_manifest(audit, binding)
    by_sub = {c["subcommand"]: c for c in manifest["verticals"][0]["commands"]}
    assert by_sub["list"]["scope"] == "fakepkg:ercot:read"   # GET -> read
    assert by_sub["sync"]["scope"] == "fakepkg:ercot:write"  # non-GET -> write
    assert by_sub["derive"]["scope"] == "custom:scope"       # explicit override wins
