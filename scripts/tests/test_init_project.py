"""Tests for scripts/init_project.py.

The scaffolder copies templates/classic/ into a fresh project tree for one of
the four racecar shapes, substituting placeholders and setting the Makefile's
shape variables. These tests scaffold into tmp_path and assert:

  - Each of the four shapes lands the library pyproject at the shape-correct
    path with the root package substituted in.
  - The djapp pyproject appears only for pypkg+djapp.
  - The Makefile carries the shape-correct SRC / PKG / DJAPP / LIB_PYPROJECT /
    DJAPP_PYPROJECT values.
  - .gitignore and .pre-commit-config.yaml are written at root (with the
    leading dot) for every shape.
  - scripts/ carries the check scripts the Makefile arch:/docs: targets invoke,
    copied verbatim from their canonical racecar homes, for every shape.
  - No `<placeholder>` token survives in the rendered library pyproject's
    active (non-comment) lines, and the file parses as TOML.
  - Scaffolding refuses to clobber a non-empty destination.
  - A bad --shape is rejected with a non-zero exit.

Run with:
    pytest scripts/tests/test_init_project.py
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "init_project.py"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Derived from the ONE home (sync_scripts), not hand-maintained here — the scaffold
# must copy every script init delivers (sync's canonical set + the Django check,
# which init copies for all shapes), each verbatim.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import sync_scripts  # noqa: E402

EXPECTED_CHECK_SCRIPTS = {
    Path(s).name: s for s in sync_scripts.CHECK_SCRIPTS + sync_scripts.DJANGO_SCRIPTS
}

# Shape -> (library pyproject relative path, expected SRC value).
SHAPE_LIB_PYPROJECT = {
    "src": ("pyproject.toml", "src"),
    "pypkg": ("pypkg/src/pyproject.toml", "pypkg/src"),
    "pypkg+djapp": ("pypkg/src/pyproject.toml", "pypkg/src"),
    "djapp": ("pyproject.toml", "djapp"),
}


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _scaffold(dest: Path, shape: str, package: str = "foo") -> subprocess.CompletedProcess[str]:
    return _run(
        "--shape",
        shape,
        "--name",
        f"{package}-pkg",
        "--package",
        package,
        "--dest",
        str(dest),
        "--author",
        "Jane Doe",
        "--email",
        "jane@example.com",
    )


def _makefile_vars(makefile: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in makefile.read_text().splitlines():
        for var in ("SRC", "PKG", "DJAPP", "LIB_PYPROJECT", "DJAPP_PYPROJECT"):
            prefix = f"{var} "
            stripped = line.lstrip()
            if stripped.startswith(prefix) and "?=" in stripped:
                out[var] = stripped.split("?=", 1)[1].strip()
    return out


def test_vertical_scaffolds_canonical_files(tmp_path: Path) -> None:
    """--vertical pre-wires lib.py/api.py/__main__.py that the faces detector
    classifies cleanly (FACES.md §10 make-the-right-thing-easy)."""
    dest = tmp_path / "proj"
    result = _run(
        "--shape", "src", "--name", "athena", "--package", "athena",
        "--dest", str(dest), "--vertical", "prices",
    )
    assert result.returncode == 0, result.stderr
    vdir = dest / "src" / "athena" / "prices"
    for fname in ("__init__.py", "lib.py", "api.py", "__main__.py"):
        assert (vdir / fname).is_file(), f"missing {fname}"
    # api imports lib; __main__ imports api (the lib -> api -> cli wiring).
    assert "from .lib import run" in (vdir / "api.py").read_text()
    assert "from . import api" in (vdir / "__main__.py").read_text()
    # __init__ is namespace-only (docstring only, no code) per FACES.md §6.
    assert (vdir / "__init__.py").read_text().count("\n") == 1

    # The scaffold's own faces detector classifies the vertical cleanly.
    detector = dest / "scripts" / "check_face_orchestration.py"
    out = subprocess.run(
        [sys.executable, str(detector), "--root", str(dest)],
        capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, out.stdout
    assert "OK (advisory)" in out.stdout


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_shape_lands_library_pyproject_at_correct_path(shape: str, tmp_path: Path) -> None:
    dest = tmp_path / "proj"
    result = _scaffold(dest, shape)
    assert result.returncode == 0, result.stderr

    rel_pyproject, _ = SHAPE_LIB_PYPROJECT[shape]
    lib_pyproject = dest / rel_pyproject
    assert lib_pyproject.is_file(), f"{rel_pyproject} not created for shape {shape}"

    data = tomllib.loads(lib_pyproject.read_text())
    assert data["project"]["name"] == "foo-pkg"
    assert data["tool"]["importlinter"]["root_package"] == "foo"


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_makefile_shape_variables(shape: str, tmp_path: Path) -> None:
    dest = tmp_path / "proj"
    assert _scaffold(dest, shape).returncode == 0

    vars_ = _makefile_vars(dest / "Makefile")
    rel_pyproject, expected_src = SHAPE_LIB_PYPROJECT[shape]
    assert vars_["SRC"] == expected_src
    assert vars_["PKG"] == f"{expected_src}/foo"
    assert vars_["LIB_PYPROJECT"] == rel_pyproject

    if shape in ("pypkg+djapp", "djapp"):
        assert vars_["DJAPP"] == "djapp"
    else:
        assert vars_["DJAPP"] == ""

    if shape == "pypkg+djapp":
        assert vars_["DJAPP_PYPROJECT"] == "djapp/pyproject.toml"
    else:
        assert vars_["DJAPP_PYPROJECT"] == ""


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_dotfiles_and_source_skeleton(shape: str, tmp_path: Path) -> None:
    dest = tmp_path / "proj"
    assert _scaffold(dest, shape).returncode == 0

    assert (dest / ".gitignore").is_file()
    assert (dest / ".pre-commit-config.yaml").is_file()
    assert (dest / "Makefile").is_file()

    _, expected_src = SHAPE_LIB_PYPROJECT[shape]
    assert (dest / expected_src / "foo" / "__init__.py").is_file()


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_scripts_dir_carries_check_scripts(shape: str, tmp_path: Path) -> None:
    """Every shape gets scripts/ populated with the check scripts the Makefile
    arch:/docs: targets invoke, copied byte-for-byte from their canonical homes.
    Without these, `make arch` / `make docs` fail with file-not-found."""
    dest = tmp_path / "proj"
    assert _scaffold(dest, shape).returncode == 0

    for basename, rel_source in EXPECTED_CHECK_SCRIPTS.items():
        copied = dest / "scripts" / basename
        assert copied.is_file(), f"scripts/{basename} not created for shape {shape}"
        canonical = (REPO_ROOT / rel_source).read_text(encoding="utf-8")
        assert copied.read_text(encoding="utf-8") == canonical, (
            f"scripts/{basename} diverges from canonical {rel_source} (must be verbatim)"
        )

    # Support scripts the Makefile invokes beyond the check set — without these the
    # scaffold's own `make clean` / `make system-deps` fail file-not-found.
    assert (dest / "scripts" / "clean_files.sh").is_file(), f"clean_files.sh missing ({shape})"
    assert (dest / "scripts" / "install_system_deps.sh").is_file(), (
        f"install_system_deps.sh missing ({shape})"
    )


def test_djapp_pyproject_only_for_pypkg_djapp(tmp_path: Path) -> None:
    for shape in ("src", "pypkg", "djapp"):
        dest = tmp_path / f"no-djapp-{shape.replace('+', '_')}"
        assert _scaffold(dest, shape).returncode == 0
        assert not (dest / "djapp" / "pyproject.toml").exists()

    dest = tmp_path / "with-djapp"
    assert _scaffold(dest, "pypkg+djapp").returncode == 0
    djapp_pyproject = dest / "djapp" / "pyproject.toml"
    assert djapp_pyproject.is_file()
    data = tomllib.loads(djapp_pyproject.read_text())
    assert "runtime" in data["dependency-groups"]
    assert "project" not in data


def test_no_placeholder_survives_in_active_lines(tmp_path: Path) -> None:
    dest = tmp_path / "proj"
    assert _scaffold(dest, "src").returncode == 0
    active = [
        line
        for line in (dest / "pyproject.toml").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    for line in active:
        assert "<" not in line or ">" not in line, f"placeholder left in active line: {line!r}"


def test_refuses_to_clobber_non_empty_dest(tmp_path: Path) -> None:
    dest = tmp_path / "proj"
    assert _scaffold(dest, "src").returncode == 0

    # Second run into the same (now non-empty) dest must refuse.
    result = _scaffold(dest, "src")
    assert result.returncode != 0
    assert "not empty" in result.stderr or "refusing" in result.stderr


def test_empty_dest_is_allowed(tmp_path: Path) -> None:
    dest = tmp_path / "empty"
    dest.mkdir()
    assert _scaffold(dest, "src").returncode == 0
    assert (dest / "pyproject.toml").is_file()


def test_bad_shape_is_rejected(tmp_path: Path) -> None:
    result = _run(
        "--shape",
        "monorepo",
        "--name",
        "foo",
        "--package",
        "foo",
        "--dest",
        str(tmp_path / "proj"),
    )
    assert result.returncode != 0
    assert "monorepo" in result.stderr or "invalid choice" in result.stderr
