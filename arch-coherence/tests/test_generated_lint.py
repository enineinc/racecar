"""The generated server passes a consumer's own lint, not just racecar's.

racecar emits django code (REST + MCP surfaces + the WebAuthn Authorization Server) but is
not itself a django project, so its default test env cannot lint that output, and a generator
regression that would fail a consumer's lint (a too-branchy view, a missing docstring) goes
unseen. `make install-dev` installs the `django` group (the pylint_django plugin + the django /
DOT / webauthn runtime). With it present, this test renders the full server and runs pylint at
the canonical consumer bar (templates/classic/library-pyproject.toml + pylint_django), so such a
regression fails racecar's own `make test` first. Skipped when the stack is absent."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("pylint_django")
pytest.importorskip("pylint_pytest")  # loaded by the consumer rcfile's [tool.pylint] load-plugins

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "arch-coherence" / "scripts"))
import scaffold_authserver  # noqa: E402
import scaffold_surfaces_templates as templates  # noqa: E402

_RCFILE = REPO_ROOT / "templates" / "classic" / "library-pyproject.toml"


def _manifest() -> dict:
    """A minimal one-vertical, one-command manifest in the shape render_project wants."""
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
        "scope": "pkg:ercot:read",
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


def _write_fixture_library(lib: Path) -> None:
    """A minimal importable `pkg.ercot.api` (so generated imports resolve) plus a lint-only
    django settings module (so pylint_django is configured and does not emit
    django-not-configured, an environment signal rather than a code-quality finding)."""
    ercot = lib / "pkg" / "ercot"
    ercot.mkdir(parents=True)
    (lib / "pkg" / "__init__.py").write_text("")
    (ercot / "__init__.py").write_text("")
    (ercot / "api.py").write_text('def list_datasets():\n    """List datasets."""\n    return []\n')
    (lib / "_lintsettings.py").write_text('SECRET_KEY = "lint-only"\nINSTALLED_APPS = []\nUSE_TZ = True\n')


def test_generated_server_passes_a_consumer_lint(tmp_path):
    server = tmp_path / "server"
    templates.render_project(_manifest(), server)
    scaffold_authserver.render_authserver(server, issuer="https://auth.example.com")
    _write_fixture_library(tmp_path / "lib")

    # Include migrations: they must be lint-clean via the rcfile's ignore-paths (auto-generated
    # django migrations otherwise trip invalid-name / missing-class-docstring), not by this test
    # filtering them out. This proves the canonical library-pyproject excludes them.
    files = [str(p) for p in sorted(server.rglob("*.py"))]
    proc = subprocess.run(
        [sys.executable, "-m", "pylint", "--rcfile", str(_RCFILE),
         "--load-plugins", "pylint_django", *files],
        cwd=str(server),
        env={
            **os.environ,
            "PYTHONPATH": f"{server}{os.pathsep}{tmp_path / 'lib'}",
            "DJANGO_SETTINGS_MODULE": "_lintsettings",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        "the generated server is not lint-clean at the consumer bar "
        f"(library-pyproject + pylint_django):\n{proc.stdout}\n{proc.stderr}"
    )
