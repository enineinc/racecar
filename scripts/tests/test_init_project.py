"""Tests for scripts/init_project.py.

The scaffolder copies templates/classic/ into a fresh project tree for one of
the four racecar shapes, substituting placeholders. These tests scaffold into
tmp_path and assert:

  - Each of the four shapes lands the library pyproject at the shape-correct
    path with the root package substituted in.
  - The djapp pyproject appears only for pypkg+djapp; the djapp shape ships a
    manage.py (the Django marker the shape detection keys on).
  - The owned Makefile is a thin include and racecar.mk is the canonical file,
    byte-identical in every shape (shape is detected from the layout, not stored).
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

import os
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


def _scaffold(
    dest: Path, shape: str, package: str = "foo"
) -> subprocess.CompletedProcess[str]:
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


def test_vertical_scaffolds_canonical_files(tmp_path: Path) -> None:
    """--vertical pre-wires lib.py/api.py/__main__.py that the faces detector
    classifies cleanly (FACES.md §10 make-the-right-thing-easy)."""
    dest = tmp_path / "proj"
    result = _run(
        "--shape",
        "src",
        "--name",
        "athena",
        "--package",
        "athena",
        "--dest",
        str(dest),
        "--vertical",
        "prices",
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
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stdout
    assert "OK (advisory)" in out.stdout


@pytest.mark.parametrize(
    "extra",
    [["--cli"], ["--vertical", "prices", "--vertical", "dispatch"]],
    ids=["single-surface", "nested-surface"],
)
def test_scaffolded_cli_passes_check_cli_commands(
    extra: list[str], tmp_path: Path
) -> None:
    """Realism coupling (the sweep's second gap): a real scaffold's CLI surface must
    pass `check_cli_commands`, the CLI command-tree audit `make arch` runs. Both shapes:
    single = one Pattern 3 leaf at the package root (`--cli`); nested = a Pattern 1
    discovery root over leaf verticals (`--vertical`). This is the test the original
    non-conformant scaffold failed (it emitted a `__main__.py` with no `commands()`);
    a future scaffold that drops the contract fails here, in CI."""
    dest = tmp_path / "proj"
    assert (
        _run(
            "--shape",
            "src",
            "--name",
            "athena",
            "--package",
            "athena",
            "--dest",
            str(dest),
            *extra,
        ).returncode
        == 0
    )
    cli = dest / "scripts" / "check_cli_commands.py"
    env = {**os.environ, "PYTHONPATH": str(dest / "src")}  # as after `make install`
    out = subprocess.run(
        [sys.executable, str(cli), "src/athena"],
        cwd=dest,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stdout


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_shape_lands_library_pyproject_at_correct_path(
    shape: str, tmp_path: Path
) -> None:
    dest = tmp_path / "proj"
    result = _scaffold(dest, shape)
    assert result.returncode == 0, result.stderr

    rel_pyproject, _ = SHAPE_LIB_PYPROJECT[shape]
    lib_pyproject = dest / rel_pyproject
    assert lib_pyproject.is_file(), f"{rel_pyproject} not created for shape {shape}"

    data = tomllib.loads(lib_pyproject.read_text())
    assert data["project"]["name"] == "foo-pkg"
    assert data["tool"]["importlinter"]["root_package"] == "foo"


_TEMPLATE_RACECAR_MK = REPO_ROOT / "templates" / "classic" / "racecar.mk"


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_makefile_fold_owned_include_plus_identical_racecar_mk(
    shape: str, tmp_path: Path
) -> None:
    """The owned Makefile is a thin include; racecar.mk is the canonical file,
    byte-identical in every shape (it self-detects the shape from the layout)."""
    dest = tmp_path / "proj"
    assert _scaffold(dest, shape).returncode == 0
    assert "include racecar.mk" in (dest / "Makefile").read_text()
    assert (dest / "racecar.mk").read_text() == _TEMPLATE_RACECAR_MK.read_text()


@pytest.mark.parametrize("shape", list(SHAPE_LIB_PYPROJECT))
def test_library_pyproject_declares_no_shape(shape: str, tmp_path: Path) -> None:
    """Shape is governed by what is on disk, not a declared value: the scaffold writes
    no `[tool.racecar].shape` (no shape token to set, forget, or let go stale)."""
    dest = tmp_path / "proj"
    assert _scaffold(dest, shape).returncode == 0
    rel_pyproject, _ = SHAPE_LIB_PYPROJECT[shape]
    data = tomllib.loads((dest / rel_pyproject).read_text())
    assert "shape" not in data.get("tool", {}).get("racecar", {})


def test_djapp_scaffold_writes_manage_py(tmp_path: Path) -> None:
    """The djapp shape ships a manage.py — the Django marker racecar.mk and
    detect_shape both key on. Without it the scaffold would read as the `src` shape."""
    dest = tmp_path / "proj"
    assert _scaffold(dest, "djapp").returncode == 0
    manage = dest / "djapp" / "manage.py"
    assert manage.is_file()
    assert "DJANGO_SETTINGS_MODULE" in manage.read_text()


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
        assert (
            copied.read_text(encoding="utf-8") == canonical
        ), f"scripts/{basename} diverges from canonical {rel_source} (must be verbatim)"

    # Support scripts the Makefile invokes beyond the check set — without these the
    # scaffold's own `make clean` / `make system-deps` fail file-not-found.
    assert (
        dest / "scripts" / "clean_files.sh"
    ).is_file(), f"clean_files.sh missing ({shape})"
    assert (
        dest / "scripts" / "install_system_deps.sh"
    ).is_file(), f"install_system_deps.sh missing ({shape})"


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
        assert (
            "<" not in line or ">" not in line
        ), f"placeholder left in active line: {line!r}"


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


def test_bare_scaffold_writes_no_main(tmp_path: Path) -> None:
    """Negative space: with neither --cli nor --vertical, the scaffold must NOT emit
    any `__main__.py`. The non-conformant scaffold this suite hardened against shipped
    a bare `__main__.py` (no `commands()`) by default; a bare main here would both fail
    check_cli_commands and read as a faces vertical with no worker. Absence is correct."""
    dest = tmp_path / "proj"
    assert _scaffold(dest, "src").returncode == 0
    mains = list((dest / "src" / "foo").rglob("__main__.py"))
    assert mains == [], f"bare scaffold emitted a __main__.py: {mains}"


def test_vertical_leaf_main_is_not_a_bare_main(tmp_path: Path) -> None:
    """Negative space: the vertical's leaf `__main__.py` must NOT be the bare,
    contract-less main the original scaffold shipped — it must declare `commands()`,
    `parser()`, and `main()`. A regression that drops the CLI.md contract (emitting a
    bare main again) is caught here, not just by the integration run."""
    dest = tmp_path / "proj"
    assert (
        _run(
            "--shape", "src", "--name", "athena", "--package", "athena",
            "--dest", str(dest), "--vertical", "prices",
        ).returncode
        == 0
    )
    leaf = (dest / "src" / "athena" / "prices" / "__main__.py").read_text()
    for token in ("def commands(", "def parser(", "def main("):
        assert token in leaf, f"leaf __main__ missing the CLI.md contract token {token!r}"


def test_cli_and_vertical_are_mutually_exclusive(tmp_path: Path) -> None:
    """Negative space: --cli (single surface) and --vertical (nested surface) must NOT
    both apply. Passing both is refused with a non-zero exit; no tree is scaffolded."""
    dest = tmp_path / "proj"
    result = _run(
        "--shape", "src", "--name", "foo", "--package", "foo",
        "--dest", str(dest), "--cli", "--vertical", "prices",
    )
    assert result.returncode != 0
    assert "mutually exclusive" in result.stderr


def test_non_djapp_shapes_write_no_manage_py(tmp_path: Path) -> None:
    """Negative space: only the Django shapes ship manage.py — its presence is the
    sole Django marker. A non-Django shape that emitted one would misdetect as djapp,
    so the marker must be ABSENT for `src` and `pypkg`."""
    for shape in ("src", "pypkg"):
        dest = tmp_path / f"no-manage-{shape}"
        assert _scaffold(dest, shape).returncode == 0
        assert not (dest / "djapp" / "manage.py").exists()
        assert list(dest.rglob("manage.py")) == []


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
