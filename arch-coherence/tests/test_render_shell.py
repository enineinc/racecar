"""#12: racecar-start-django-project emits a VANILLA, location-free Django shell.

The shell carries no surface or auth machinery (no surfaceguard, no project/auth.py, no
per-surface settings package); that is racecar-create-server's composition, added on top by
render_project. These tests lock that split: render_shell stays vanilla, and render_project
over the same tree replaces the vanilla single modules with the surface packages."""

from __future__ import annotations

import compileall
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "arch-coherence" / "scripts"))
import scaffold_surfaces_templates as templates  # noqa: E402


def _empty_manifest() -> dict:
    return {"package": "gfem", "mcp_protocol_version": "2025-11-25", "verticals": []}


def test_render_shell_is_vanilla(tmp_path):
    """The vanilla shell is single-module settings/urls with no surface or auth files."""
    server = tmp_path / "server"
    templates.render_shell(server)
    proj = server / "project"
    assert (proj / "settings.py").is_file()
    assert (proj / "urls.py").is_file()
    assert not (proj / "settings").exists()  # no per-surface settings package
    assert not (proj / "urls").exists()  # no per-surface urls package
    assert not (proj / "surfaceguard.py").exists()
    assert not (proj / "auth.py").exists()
    # Bootable shape: manage.py + asgi/wsgi + an empty apps/ package.
    assert (server / "manage.py").is_file()
    assert (proj / "asgi.py").is_file() and (proj / "wsgi.py").is_file()
    assert (server / "apps" / "__init__.py").is_file()


def test_render_shell_carries_no_library_name(tmp_path):
    """Location-free: the shell points at project.settings, never a library package."""
    server = tmp_path / "server"
    templates.render_shell(server)
    assert 'DJANGO_SETTINGS_MODULE", "project.settings"' in (server / "manage.py").read_text()
    assert "surfaceguard" not in (server / "project" / "settings.py").read_text()


def test_render_shell_byte_compiles(tmp_path):
    """The vanilla shell's Python is importable/compilable."""
    server = tmp_path / "server"
    templates.render_shell(server)
    assert compileall.compile_dir(str(server / "project"), quiet=1)


def test_create_server_replaces_vanilla_modules(tmp_path):
    """render_project over a vanilla shell swaps the single modules for surface packages."""
    server = tmp_path / "server"
    templates.render_shell(server)  # start-django-project
    templates.render_project(_empty_manifest(), server)  # create-server, cascade order
    proj = server / "project"
    assert (proj / "settings").is_dir() and not (proj / "settings.py").exists()
    assert (proj / "urls").is_dir() and not (proj / "urls.py").exists()
    assert (proj / "surfaceguard.py").is_file()
    assert (proj / "auth.py").is_file()
