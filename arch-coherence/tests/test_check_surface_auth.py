"""check_surface_auth: a generated surface must be closed by default + scope every command."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "arch-coherence" / "scripts"))
import check_surface_auth  # noqa: E402


def _make_server(root: Path, *, auth: bool, scope: bool) -> None:
    docs_api = root / "server" / "docs" / "api"
    docs_api.mkdir(parents=True)
    command = {"subcommand": "list"}
    if scope:
        command["scope"] = "pkg:ercot:read"
    manifest = {"package": "pkg", "verticals": [{"vertical": "pkg.ercot", "commands": [command]}]}
    (docs_api / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    proj = root / "server" / "project"
    proj.mkdir(parents=True)
    if auth:
        (proj / "auth.py").write_text("# auth gate\n", encoding="utf-8")


def test_no_server_is_a_noop(tmp_path):
    assert check_surface_auth.findings(tmp_path) == []


def test_closed_and_scoped_passes(tmp_path):
    _make_server(tmp_path, auth=True, scope=True)
    assert check_surface_auth.findings(tmp_path) == []


def test_anonymous_surface_fails(tmp_path):
    _make_server(tmp_path, auth=False, scope=True)
    problems = check_surface_auth.findings(tmp_path)
    assert problems and any("auth gate" in p for p in problems)


def test_unscoped_command_fails(tmp_path):
    _make_server(tmp_path, auth=True, scope=False)
    problems = check_surface_auth.findings(tmp_path)
    assert problems and any("no scope" in p for p in problems)
