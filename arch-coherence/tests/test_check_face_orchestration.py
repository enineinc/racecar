"""Tests for arch-coherence/scripts/check_face_orchestration.py.

The detector is ADVISORY (FACES.md §7): exit 0 by default, exit 1 only under
--strict when a Finding is reported. These tests build minimal src-shape faces
projects under tmp_path and assert the role-identification + restated-orchestration
findings fire (or stay silent) as FACES.md §5 specifies.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_face_orchestration.py"

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


# Canonical, clean vertical: faces -> api -> lib.
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


def test_face_bypassing_api_is_flagged(tmp_path: Path) -> None:
    """A face importing the lib directly is not gated, but is surfaced."""
    files = dict(_CLEAN)
    files["__main__.py"] = "import argparse\nfrom .lib import engine\ndef main():\n    engine()\n"
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert "api-not-cut-vertex" in result.stdout
    assert result.returncode == 0  # advisory by default


def test_strict_exits_nonzero_on_finding(tmp_path: Path) -> None:
    files = dict(_CLEAN)
    files["__main__.py"] = "import argparse\nfrom .lib import engine\ndef main():\n    engine()\n"
    repo = _seed(tmp_path, files)
    result = _run(repo, "--strict")
    assert result.returncode == 1
    assert "api-not-cut-vertex" in result.stdout


def test_non_classifiable_two_faces_no_api(tmp_path: Path) -> None:
    """Two faces touching the lib directly with no mediating api is the drift finding."""
    files = {
        "lib.py": "def engine():\n    return 1\n",
        "__main__.py": "import argparse\nfrom .lib import engine\ndef main():\n    engine()\n",
        "mcp.py": "import mcp\nfrom .lib import engine\ndef tool():\n    engine()\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert "non-classifiable" in result.stdout


def test_single_face_api_lib_collapse_is_ok(tmp_path: Path) -> None:
    """One face importing the lib directly: api==lib collapse is legitimate."""
    files = {
        "lib.py": "def engine():\n    return 1\n",
        "__main__.py": "import argparse\nfrom .lib import engine\ndef main():\n    engine()\n",
    }
    repo = _seed(tmp_path, files)
    result = _run(repo)
    assert result.returncode == 0
    assert "OK (advisory)" in result.stdout


def test_manifest_renames_roles(tmp_path: Path) -> None:
    """Non-canonical filenames classify via [tool.racecar.faces] (Tier 2)."""
    pyproject = PYPROJECT + (
        '\n[[tool.racecar.faces.vertical]]\n'
        'name = "prices"\n'
        'lib = "myapp.prices.engine"\n'
        'api = "myapp.prices.orchestrate"\n'
        'faces = ["myapp.prices.cli"]\n'
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
    """The same api-call sequence in two faces is one policy with two homes."""
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
