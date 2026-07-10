"""Tests for doc-coherence/scripts/check_subsystem_docs.py.

Builds a fake repo under tmp_path with a `.git` marker, a `pyproject.toml`
declaring an `[tool.importlinter]` contract, and source directories of
varying size. Each test asserts the script's exit code and the expected
message in stdout.

Run with:
    pytest doc-coherence/tests/test_check_subsystem_docs.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_subsystem_docs.py"

# Tiny loc_threshold keeps fixtures small while still exercising the LOC branch.
PYPROJECT_TEMPLATE = """\
[tool.racecar.subsystem-docs]
loc_threshold = 5

[[tool.importlinter.contracts]]
name = "fake layers"
type = "layers"
containers = ["fake"]
layers = ["cli", "core"]
"""


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _seed_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


def _write_doc(path: Path, body: str = "## Heading\n\nbody.\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _seed_layered_repo(tmp_path: Path) -> Path:
    """Repo with a `fake` package containing `cli` and `core` layers.

    `core` has subdirs (always major). `cli` has only modules and uses the
    LOC branch via the small `loc_threshold` in PYPROJECT_TEMPLATE.
    """
    repo = _seed_repo(tmp_path)
    (repo / "pyproject.toml").write_text(PYPROJECT_TEMPLATE, encoding="utf-8")
    (repo / "fake").mkdir()
    (repo / "fake" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "fake" / "cli").mkdir()
    # ~8 non-blank lines, exceeds loc_threshold=5
    (repo / "fake" / "cli" / "__init__.py").write_text(
        "\n".join(f"x = {i}" for i in range(8)) + "\n", encoding="utf-8"
    )
    (repo / "fake" / "core").mkdir()
    (repo / "fake" / "core" / "inner").mkdir()
    (repo / "fake" / "core" / "inner" / "mod.py").write_text("y = 1\n", encoding="utf-8")
    return repo


def test_no_pyproject_exits_zero(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    result = _run(repo)
    assert result.returncode == 0
    assert "no import-linter contracts found" in result.stdout


def test_pyproject_without_importlinter_exits_zero(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    (repo / "pyproject.toml").write_text("[tool.black]\nline-length = 88\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0
    assert "no import-linter contracts found" in result.stdout


def test_clean_repo_with_docs_exits_zero(tmp_path: Path) -> None:
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_missing_doc_is_caught(tmp_path: Path) -> None:
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    (repo / "fake" / "cli" / "CLAUDE.md").unlink()
    result = _run(repo)
    assert result.returncode == 1
    assert "missing" in result.stdout
    assert "fake/cli/CLAUDE.md" in result.stdout


def test_empty_doc_is_caught(tmp_path: Path) -> None:
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    (repo / "fake" / "core" / "README.md").write_text("   \n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1
    assert "empty" in result.stdout
    assert "fake/core/README.md" in result.stdout


def test_doc_without_h2_is_caught(tmp_path: Path) -> None:
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    (repo / "fake" / "core" / "README.md").write_text(
        "# Top only\n\nNo H2 here.\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 1
    assert "no H2 heading" in result.stdout


def test_excluded_dir_is_skipped(tmp_path: Path) -> None:
    """A `tests/` directory under a layer must not require docs."""
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    # Add a tests dir with subdirs (would be major if not excluded).
    (repo / "fake" / "core" / "tests").mkdir()
    (repo / "fake" / "core" / "tests" / "fixtures").mkdir()
    (repo / "fake" / "core" / "tests" / "fixtures" / "f.py").write_text("z = 1\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_small_leaf_dir_is_skipped(tmp_path: Path) -> None:
    """A leaf directory below the LOC threshold without subdirs is not major."""
    repo = _seed_repo(tmp_path)
    (repo / "pyproject.toml").write_text(PYPROJECT_TEMPLATE, encoding="utf-8")
    (repo / "fake").mkdir()
    (repo / "fake" / "__init__.py").write_text("", encoding="utf-8")
    # Tiny leaf: 1 line, no subdirs → not major.
    (repo / "fake" / "cli").mkdir()
    (repo / "fake" / "cli" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "fake" / "core").mkdir()
    (repo / "fake" / "core" / "__init__.py").write_text("y = 1\n", encoding="utf-8")
    # `fake` has subdirs → major; needs docs. `cli` and `core` are leaves below
    # threshold → not major; do not need docs.
    _write_doc(repo / "fake" / "README.md")
    _write_doc(repo / "fake" / "CLAUDE.md")
    result = _run(repo)
    assert result.returncode == 0, result.stdout


def test_sourceless_asset_dir_is_skipped(tmp_path: Path) -> None:
    """A subdir-bearing directory with no source in its subtree (a templates/ or
    static/ tree) is not a subsystem and must not require docs, even though it has
    subdirs (the `has subdirs -> major` rule is gated on source presence)."""
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    # A templates/ tree under a real layer: subdirs, but only non-source files.
    (repo / "fake" / "core" / "templates" / "core").mkdir(parents=True)
    (repo / "fake" / "core" / "templates" / "core" / "page.html").write_text(
        "<div>{% block x %}{% endblock %}</div>\n", encoding="utf-8"
    )
    result = _run(repo)
    assert result.returncode == 0, result.stdout
    assert "templates" not in result.stdout


def test_contracts_in_root_pyproject_are_found(tmp_path: Path) -> None:
    """The library pyproject is at the repo root in every shape; the package sits
    under src/<pkg>. The probe must find its [tool.importlinter] contracts so
    subsystems are validated, and a missing CLAUDE.md must be caught -- proving the
    contracts were read and acted on, not silently ignored.
    """
    repo = _seed_repo(tmp_path)
    (repo / "pyproject.toml").write_text(PYPROJECT_TEMPLATE, encoding="utf-8")
    # Package + layers under src/<pkg>/...
    base = repo / "src" / "fake"
    base.mkdir(parents=True)
    (base / "__init__.py").write_text("", encoding="utf-8")
    (base / "core").mkdir()
    (base / "core" / "inner").mkdir()
    (base / "core" / "inner" / "mod.py").write_text("y = 1\n", encoding="utf-8")
    (base / "cli").mkdir()
    (base / "cli" / "__init__.py").write_text(
        "\n".join(f"x = {i}" for i in range(8)) + "\n", encoding="utf-8"
    )
    for sub in ("", "core", "core/inner", "cli"):
        d = base / sub if sub else base
        _write_doc(d / "README.md")
        _write_doc(d / "CLAUDE.md")
    # Remove one CLAUDE.md: the check must fire, proving contracts were found.
    (base / "cli" / "CLAUDE.md").unlink()
    result = _run(repo)
    assert result.returncode == 1, result.stdout
    assert "missing" in result.stdout
    assert "cli/CLAUDE.md" in result.stdout


def test_dir_unreferenced_by_any_contract_needs_no_docs(tmp_path: Path) -> None:
    """Negative space: a directory is policed for docs ONLY if it is reachable from an
    import-linter contract package. A sizeable, subdir-bearing directory that NO contract
    references is never walked, so its missing README/CLAUDE must NOT be flagged. The
    contract list is the reachability frontier; absence outside it is correct."""
    repo = _seed_layered_repo(tmp_path)
    for sub in ("fake", "fake/cli", "fake/core", "fake/core/inner"):
        _write_doc(repo / sub / "README.md")
        _write_doc(repo / sub / "CLAUDE.md")
    # A major dir (has subdirs) NOT named by any contract, with no docs at all.
    (repo / "unrelated" / "big" / "sub").mkdir(parents=True)
    (repo / "unrelated" / "big" / "sub" / "mod.py").write_text("z = 1\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stdout
    assert "unrelated" not in result.stdout


def test_unresolvable_package_emits_info(tmp_path: Path) -> None:
    """A contract pointing at a non-existent package exits 0 with info."""
    repo = _seed_repo(tmp_path)
    (repo / "pyproject.toml").write_text(
        "[[tool.importlinter.contracts]]\n"
        'name = "ghost"\n'
        'type = "forbidden"\n'
        'source_modules = ["nonexistent_pkg"]\n'
        'forbidden_modules = ["other_ghost"]\n',
        encoding="utf-8",
    )
    result = _run(repo)
    assert result.returncode == 0
    assert "no resolvable major subsystems" in result.stdout
