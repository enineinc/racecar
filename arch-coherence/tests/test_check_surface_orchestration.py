"""Tests for arch-coherence/scripts/check_surface_orchestration.py.

The detector is ADVISORY (SURFACES.md §7): exit 0 by default, exit 1 only under
--strict when a Finding is reported. These tests build minimal src-shape surfaces
projects under tmp_path and assert the role-identification + restated-orchestration
findings fire (or stay silent) as SURFACES.md §5 specifies.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_surface_orchestration.py"

PYPROJECT = """\
[project]
name = "myapp"
version = "0.1.0"
description = "x"
requires-python = ">=3.12"
authors = [{name = "t"}]
dependencies = []

[tool.importlinter]
root_package = "myapp"
"""


def _seed(tmp_path: Path, files: dict[str, str], pyproject: str = PYPROJECT) -> Path:
    (tmp_path / "pyproject.toml").write_text(pyproject)
    src = tmp_path / "src" / "myapp"
    (src / "prices").mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "prices" / "__init__.py").write_text("")
    for name, body in files.items():
        (src / "prices" / name).write_text(body)
    return tmp_path


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True, text=True, check=False,
    )


# Canonical, clean vertical: surfaces -> api -> lib.
_CLEAN = {
    "lib.py": "def engine():\n    return 1\n",
    "api.py": "from .lib import engine\ndef run():\n    return engine()\n",
    "__main__.py": "import argparse\nfrom . import api\ndef main():\n    api.run()\n",
    "mcp.py": "import mcp\nfrom . import api\ndef tool():\n    api.run()\n",
}


def test_clean_vertical_passes(tmp_path: Path) -> None:
    repo = _seed(tmp_path, _CLEAN)
    result = _run(repo)
    assert result.returncode == 0
    assert "OK (advisory)" in result.stdout


def test_api_without_lib_is_flagged(tmp_path: Path) -> None:
    """A unit with a surface and a named `api` but no `lib` (named or mapped) is the one
    structural finding: the api fronts nothing. Name/mapping only, no guessing."""
    files = {
        "api.py": "def run():\n    return 1\n",
        "__main__.py": "import argparse\nfrom . import api\ndef main():\n    api.run()\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert "api-without-lib" in result.stdout
    assert result.returncode == 0  # advisory by default


def test_strict_exits_nonzero_on_finding(tmp_path: Path) -> None:
    files = {
        "api.py": "def run():\n    return 1\n",
        "__main__.py": "import argparse\nfrom . import api\ndef main():\n    api.run()\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo, "--strict")
    assert result.returncode == 1
    assert "api-without-lib" in result.stdout


def test_two_surfaces_no_api_is_silent(tmp_path: Path) -> None:
    """Two surfaces importing the lib directly with no `api` named/mapped: silent. The api
    is the anchor -- with none declared there is no chain to verify and nothing to restate
    (the detector never guesses one structurally)."""
    files = {
        "lib.py": "def engine():\n    return 1\n",
        "__main__.py": "import argparse\nfrom .lib import engine\ndef main():\n    engine()\n",
        "mcp.py": "import mcp\nfrom .lib import engine\ndef tool():\n    engine()\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert result.returncode == 0
    assert "api-without-lib" not in result.stdout
    assert "restated-orchestration" not in result.stdout


def test_single_face_api_lib_collapse_is_ok(tmp_path: Path) -> None:
    """One surface importing the lib directly: api==lib collapse is legitimate."""
    files = {
        "lib.py": "def engine():\n    return 1\n",
        "__main__.py": "import argparse\nfrom .lib import engine\ndef main():\n    engine()\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert result.returncode == 0
    assert "OK (advisory)" in result.stdout


def test_manifest_renames_roles(tmp_path: Path) -> None:
    """Non-canonical filenames classify via [tool.racecar.roles] (Tier 2)."""
    pyproject = PYPROJECT + (
        '\n[[tool.racecar.roles.vertical]]\n'
        'name = "prices"\n'
        'lib = "myapp.prices.engine"\n'
        'api = "myapp.prices.orchestrate"\n'
        'surfaces = ["myapp.prices.cli"]\n'
    )
    files = {
        "engine.py": "def go():\n    return 1\n",
        "orchestrate.py": "from .engine import go\ndef run():\n    return go()\n",
        "cli.py": "import argparse\nfrom . import orchestrate\ndef main():\n    orchestrate.run()\n",
        "__main__.py": "from .cli import main\nmain()\n",
    }
    repo = _seed(tmp_path, files, pyproject=pyproject)
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_restated_orchestration_across_faces(tmp_path: Path) -> None:
    """The same api-call sequence in two surfaces is one policy with two homes."""
    files = dict(_CLEAN)
    seq = "from . import api\ndef f():\n    api.resolve()\n    api.seed()\n    api.run()\n"
    files["__main__.py"] = "import argparse\n" + seq
    files["mcp.py"] = "import mcp\n" + seq
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert "restated-orchestration" in result.stdout


def test_no_verticals_is_noop(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    src = tmp_path / "src" / "myapp"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "helpers.py").write_text("def x():\n    return 1\n")
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "nothing to check" in result.stdout


def test_bare_main_only_is_not_a_vertical(tmp_path: Path) -> None:
    """Negative space (the bug this session): a package whose ONLY role file is
    `__main__.py` (no co-located lib/api/mcp worker, no second sibling module) is NOT
    a surfaces vertical — it is a CLI node (CLI.md Pattern 1 discovery root or a single-file
    tool), with no lib->api structure to classify. The detector must NOT discover it,
    and must NOT emit a non-classifiable / missing-api finding for it."""
    files = {
        "__main__.py": "import argparse\nif __name__ == '__main__':\n    pass\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert result.returncode == 0
    assert "nothing to check" in result.stdout
    assert "non-classifiable" not in result.stdout
    assert "Findings" not in result.stdout


def test_clean_vertical_emits_no_findings(tmp_path: Path) -> None:
    """Negative space: a clean surfaces -> api -> lib vertical produces NO finding of any
    rule — not just exit 0. Guards against a false api-not-cut-vertex / restated /
    non-classifiable firing on a correctly wired tree."""
    repo = _seed(tmp_path, _CLEAN)
    result = _run(repo)
    for rule in (
        "api-not-cut-vertex",
        "non-classifiable",
        "ambiguous-api",
        "restated-orchestration",
    ):
        assert rule not in result.stdout
    assert "OK (advisory)" in result.stdout


def test_dispatcher_root_with_shared_layer_is_silent(tmp_path: Path) -> None:
    """A `__main__`-only package that names no `api`/`lib`, composes children, and reaches
    no deeper in-package layer (a dispatcher / discovery root co-residing with a shared
    layer) is out of scope. No surface->api->lib chain to classify -> silent."""
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    root = tmp_path / "src" / "myapp"
    root.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (root / "__main__.py").write_text(
        "import argparse\nfrom . import flights, dashboard\n"
        "def main():\n    argparse.ArgumentParser()\n"
    )
    (root / "auth.py").write_text("SECRET = 'x'\n")
    (root / "config.py").write_text("DEBUG = True\n")
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Findings" not in result.stdout


def test_dispatcher_reaching_siblings_is_silent(tmp_path: Path) -> None:
    """The tolerance is the point: a `__main__` composing same-dir siblings (no `api`/`lib`
    named, no deeper import) is a dispatcher, not a defective vertical. Under the old
    structural detector this was flagged non-classifiable; the name/mapping model correctly
    leaves it silent -- a new shape under src/<pkg>/ is not a defect."""
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    root = tmp_path / "src" / "myapp"
    root.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (root / "__main__.py").write_text(
        "import argparse\nfrom . import config, auth\n"
        "def main():\n    print(config.DEBUG, auth.SECRET)\n"
    )
    (root / "auth.py").write_text("SECRET = 'x'\n")
    (root / "config.py").write_text("DEBUG = True\n")
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "Findings" not in result.stdout
