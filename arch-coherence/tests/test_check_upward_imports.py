"""Tests for arch-coherence/scripts/check_upward_imports.py.

Builds a fake project under tmp_path with `pyproject.toml` declaring a
root package, then runs the script with each file as argv. Asserts that
business modules with `from <root> import ...` are caught, and that
`__init__.py` / `__main__.py` files are exempt even when they contain
the same import.

Run with:
    pytest arch-coherence/tests/test_check_upward_imports.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_upward_imports.py"


def _seed_project(tmp_path: Path, *, root: str = "myapp") -> Path:
    (tmp_path / "pyproject.toml").write_text(
        f'[tool.importlinter]\nroot_package = "{root}"\n',
        encoding="utf-8",
    )
    return tmp_path


def _run(repo: Path, *files: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(f) for f in files]],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_business_module_passes(tmp_path: Path) -> None:
    repo = _seed_project(tmp_path)
    f = repo / "myapp" / "core" / "service.py"
    f.parent.mkdir(parents=True)
    f.write_text("from myapp.core.helpers import x\nfrom os import path\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_upward_import_in_business_module_is_caught(tmp_path: Path) -> None:
    repo = _seed_project(tmp_path)
    f = repo / "myapp" / "core" / "service.py"
    f.parent.mkdir(parents=True)
    f.write_text("from myapp import CONFIG\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 1
    assert "upward import forbidden" in result.stdout
    assert "from myapp import CONFIG" in result.stdout


def test_init_py_is_exempt(tmp_path: Path) -> None:
    """__init__.py is the environment-layer channel — upward imports are allowed."""
    repo = _seed_project(tmp_path)
    f = repo / "myapp" / "core" / "__init__.py"
    f.parent.mkdir(parents=True)
    f.write_text("from myapp import CONFIG\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_main_py_is_exempt(tmp_path: Path) -> None:
    repo = _seed_project(tmp_path)
    f = repo / "myapp" / "cli" / "__main__.py"
    f.parent.mkdir(parents=True)
    f.write_text("from myapp import CONFIG\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_missing_pyproject_exits_two(tmp_path: Path) -> None:
    f = tmp_path / "stray.py"
    f.write_text("import os\n", encoding="utf-8")
    result = _run(tmp_path, f)
    assert result.returncode == 2
    assert "pyproject.toml not found" in result.stderr


def test_missing_root_package_key_exits_two(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.importlinter]\n# no root_package\n", encoding="utf-8"
    )
    f = tmp_path / "stray.py"
    f.write_text("import os\n", encoding="utf-8")
    result = _run(tmp_path, f)
    assert result.returncode == 2
    assert "root_package missing" in result.stderr


def test_unrelated_import_is_not_flagged(tmp_path: Path) -> None:
    repo = _seed_project(tmp_path, root="myapp")
    f = repo / "myapp" / "core" / "service.py"
    f.parent.mkdir(parents=True)
    f.write_text("from myapp_other import thing\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0
