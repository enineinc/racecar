"""Tests for arch-coherence/scripts/check_upward_imports.py.

Builds a fake project under tmp_path with a library `pyproject.toml` declaring
one or more root packages, then runs the script with each file as argv. Asserts
that a business module reaching up into the top-level of ITS OWN root package
(`from <own-root> import ...`) is caught, that the same import in `__init__.py`
/ `__main__.py` is exempt, and — crucially — that a file under root A importing
`from B import ...` (B another configured root) is a cross-root dependency and
is NOT flagged (that is import-linter's concern, not this script's). Covers both
the singular `root_package` (string) config and the plural `root_packages`
(list) config, and the src+server shape where the library pyproject lives at
src/ (no root pyproject).

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


def _seed_project_plural(tmp_path: Path, *roots: str) -> Path:
    listed = ", ".join(f'"{r}"' for r in roots)
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.importlinter]\nroot_packages = [{listed}]\n",
        encoding="utf-8",
    )
    return tmp_path


def _seed_src_server(tmp_path: Path, *roots: str) -> Path:
    """src+server shape: root library pyproject + src/ + a Django server/.

    detect_shape resolves src+server by root pyproject.toml + src/ + server/manage.py.
    The root package(s) are read from the root library pyproject.
    """
    (tmp_path / "src" / "myapp").mkdir(parents=True)  # library package -> src/ is a dir
    listed = ", ".join(f'"{r}"' for r in roots)
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.importlinter]\nroot_packages = [{listed}]\n",
        encoding="utf-8",
    )
    server = tmp_path / "server"
    server.mkdir()
    (server / "manage.py").write_text("# manage\n", encoding="utf-8")
    (server / "pyproject.toml").write_text(
        "[dependency-groups]\nruntime = []\n", encoding="utf-8"
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
    assert "root_package" in result.stderr


def test_unrelated_import_is_not_flagged(tmp_path: Path) -> None:
    repo = _seed_project(tmp_path, root="myapp")
    f = repo / "myapp" / "core" / "service.py"
    f.parent.mkdir(parents=True)
    f.write_text("from myapp_other import thing\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0


def test_root_packages_plural_is_read(tmp_path: Path) -> None:
    """A config that uses the plural `root_packages` list resolves correctly."""
    repo = _seed_project_plural(tmp_path, "myapp", "apps")
    f = repo / "apps" / "core" / "service.py"
    f.parent.mkdir(parents=True)
    f.write_text("from apps import CONFIG\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 1
    assert "from apps import CONFIG" in result.stdout


def test_per_root_violation_detection_across_two_roots(tmp_path: Path) -> None:
    """With two roots, a direct import from EITHER root is a violation."""
    repo = _seed_project_plural(tmp_path, "myapp", "apps")
    a = repo / "myapp" / "core" / "a.py"
    a.parent.mkdir(parents=True)
    a.write_text("from myapp import X\n", encoding="utf-8")
    b = repo / "apps" / "core" / "b.py"
    b.parent.mkdir(parents=True)
    b.write_text("from apps import Y\n", encoding="utf-8")
    result = _run(repo, a, b)
    assert result.returncode == 1
    assert "from myapp import X" in result.stdout
    assert "from apps import Y" in result.stdout


def test_cross_root_import_is_not_flagged(tmp_path: Path) -> None:
    """A file under root A importing `from B import ...` (B another configured
    root) is a CROSS-ROOT dependency, not an upward import — import-linter's
    concern, not this script's. It must NOT be flagged."""
    repo = _seed_project_plural(tmp_path, "apps", "curricula")
    f = repo / "apps" / "accounts" / "serializers.py"
    f.parent.mkdir(parents=True)
    f.write_text("from curricula import registry\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_own_root_caught_but_cross_root_ignored_same_file(tmp_path: Path) -> None:
    """In one file under root A: `from A import x` IS a violation; `from B
    import x` (B another root) is NOT."""
    repo = _seed_project_plural(tmp_path, "apps", "curricula")
    f = repo / "apps" / "accounts" / "views.py"
    f.parent.mkdir(parents=True)
    f.write_text(
        "from curricula import registry\nfrom apps import CONFIG\n",
        encoding="utf-8",
    )
    result = _run(repo, f)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "from apps import CONFIG" in result.stdout
    assert "from curricula import registry" not in result.stdout


def test_file_under_no_configured_root_is_skipped(tmp_path: Path) -> None:
    """A file outside every configured root's tree is skipped, not crashed on."""
    repo = _seed_project_plural(tmp_path, "apps", "curricula")
    f = repo / "scripts" / "tool.py"
    f.parent.mkdir(parents=True)
    f.write_text("from apps import CONFIG\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_src_server_resolves_library_pyproject(tmp_path: Path) -> None:
    """src+server shape: no root pyproject; roots read from src/pyproject.toml."""
    repo = _seed_src_server(tmp_path, "myapp", "apps", "core", "project")
    f = repo / "apps" / "billing" / "views.py"
    f.parent.mkdir(parents=True)
    f.write_text("from apps import SETTINGS\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "from apps import SETTINGS" in result.stdout


def test_src_server_clean_passes(tmp_path: Path) -> None:
    repo = _seed_src_server(tmp_path, "myapp", "apps", "core", "project")
    f = repo / "core" / "models.py"
    f.parent.mkdir(parents=True)
    f.write_text("from core.helpers import h\nfrom django.db import models\n", encoding="utf-8")
    result = _run(repo, f)
    assert result.returncode == 0, (result.stdout, result.stderr)
