"""Tests for arch-coherence/scripts/check_packaging.py.

Seeds canonical project fixtures under tmp_path and asserts that violations
of each canon rule are reported, while clean canonical projects pass.

Covers the shapes from PACKAGING.md §"Scope" (PYTHON_LIBRARY x DJANGO_PROJECT):
  src           — root pyproject.toml + src/ (no server/)
  src+server   — root pyproject.toml + src/ + server/manage.py
  server         — root pyproject.toml + server/manage.py (standalone Django, no library)

Run with:
    pytest arch-coherence/tests/test_check_packaging.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_packaging.py"

sys.path.insert(0, str(SCRIPT.parent))
import check_packaging  # noqa: E402
from check_packaging_rules import check_optin  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import init_project  # noqa: E402


def test_optin_silent_when_no_agent_file(tmp_path: Path) -> None:
    # racecar does not scaffold or demand a per-repo CLAUDE.md; absent is silent.
    assert check_optin(tmp_path) == []


def test_optin_flags_agent_file_without_racecar(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# Project\n\nNo standards reference here.\n")
    findings = check_optin(tmp_path)
    assert [f.rule for f in findings] == ["missing-racecar-optin"]


def test_optin_passes_when_racecar_referenced(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# Project\n\nThis repo applies racecar.\n")
    assert check_optin(tmp_path) == []


@pytest.mark.parametrize("shape", ["src", "src+server", "server"])
def test_real_init_scaffold_passes_packaging_gate(shape: str, tmp_path: Path) -> None:
    """Realism gate: a project scaffolded by init_project — the real producer of the
    templates this checker validates — must pass the packaging gate (0 blockers).

    The CANON_* fixtures below are hand-written mirrors of templates/classic/,
    maintained separately from the real templates. That decoupling is exactly the
    makefile-fold failure mode: a fixture that drifts from the producer it stands in
    for. This couples the checker to the actual scaffold, so a template that drifts
    out of canon fails here, in CI, instead of silently in an adopter's repo. Advisory
    findings are allowed; only blockers fail the gate.
    """
    init_project.scaffold(
        shape=shape,
        name="potato",
        package="potato",
        dest=tmp_path,
        version="0.1.0",
        description="d",
        author="a",
        email="a@b.c",
    )
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout


def _layout(tmp_path: Path, *rel: str) -> Path:
    for r in rel:
        p = tmp_path / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    return tmp_path


def test_detect_shape_governed_by_what_is_on_disk(tmp_path: Path) -> None:
    """Shape is a pure function of the layout (PACKAGING.md §"Scope"), no declared
    value. The same decision racecar.mk makes in Make; a coherence test in
    scripts/tests/test_sync_scripts.py holds the two homes in lockstep."""
    # src: root pyproject + a src/ library, no Django (library only).
    src = check_packaging.detect_shape(
        _layout(tmp_path, "pyproject.toml", "src/pkg/__init__.py")
    )[0]
    assert (src.has_library, src.has_django) == (True, False)
    assert src.name == "src"
    # src+server: library (src/) x Django (server/manage.py).
    both = check_packaging.detect_shape(
        _layout(
            tmp_path / "b", "pyproject.toml", "src/pkg/__init__.py", "server/manage.py"
        )
    )[0]
    assert (both.has_library, both.has_django) == (True, True)
    assert both.name == "src+server"
    # server: standalone Django (server/manage.py, no library).
    srv = check_packaging.detect_shape(
        _layout(tmp_path / "c", "pyproject.toml", "server/manage.py")
    )[0]
    assert (srv.has_library, srv.has_django) == (False, True)
    assert srv.name == "server"
    # A root pyproject but NEITHER a src/ library nor a server/ Django project is the
    # (False, False) cell -> "unknown" with a finding, not silently "src".
    bare, bare_findings = check_packaging.detect_shape(
        _layout(tmp_path / "bare", "pyproject.toml")
    )
    assert (bare.has_library, bare.has_django) == (False, False)
    assert bare.name == "unknown"
    assert bare_findings  # the bare repo is flagged, not classified as a library
    # No pyproject at all -> also "unknown" (racecar.mk's "stock").
    assert check_packaging.detect_shape(tmp_path / "empty")[0].name == "unknown"


def test_detect_shape_locates_manage_py_per_shape(tmp_path: Path) -> None:
    """detect_shape exposes manage_py (the Django marker location) so checkers stop
    re-probing it: server/manage.py for src+server and server, None for non-Django.
    check_dj_model_ref_as_string reads this instead of a root-only probe."""
    sp = _layout(
        tmp_path / "sp", "pyproject.toml", "src/pkg/__init__.py", "server/manage.py"
    )
    assert check_packaging.detect_shape(sp)[0].manage_py == sp / "server" / "manage.py"
    dj = _layout(tmp_path / "dj", "pyproject.toml", "server/manage.py")
    assert check_packaging.detect_shape(dj)[0].manage_py == dj / "server" / "manage.py"
    src = _layout(tmp_path / "src", "pyproject.toml")
    assert check_packaging.detect_shape(src)[0].manage_py is None


# ---------------------------------------------------------------------------
# Canon fixtures
# ---------------------------------------------------------------------------


CANON_LIBRARY_PYPROJECT = """\
[project]
name = "myapp"
version = "0.2.0"
description = "test project"
readme = "README.md"
requires-python = ">=3.12"
authors = [{ name = "Test", email = "test@example.com" }]
dependencies = ["numpy>=2.0"]

[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[dependency-groups]
dev = [
    "black",
    "isort",
    "pylint",
    "pylint-pytest",
    "mypy",
    "pytest",
    "pytest-cov",
    "pytest-xdist",
    "pip-audit",
    "import-linter",
    "pre-commit",
    "validate-pyproject",
    "pyyaml>=6.0",
]

[tool.black]
target-version = ["py312"]

[tool.isort]
profile = "black"

[tool.pylint."MESSAGES CONTROL"]
disable = [
    "raw-checker-failed",
    "bad-inline-option",
    "locally-disabled",
    "file-ignored",
    "suppressed-message",
    "useless-suppression",
    "deprecated-pragma",
    "use-symbolic-message-instead",
    "duplicate-code",
    "too-few-public-methods",
    "use-implicit-booleaness-not-comparison-to-string",
    "use-implicit-booleaness-not-comparison-to-zero",
    "missing-module-docstring",
]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pylint.MASTER]
ignore-paths = ["^scripts/"]

[tool.importlinter]
root_package = "myapp"
"""

# The src+server library pyproject carries extra [tool.isort] and
# [tool.importlinter] coverage for the server source tree. profile="black"
# alone is a false green for this shape (isort cannot auto-detect first-party
# packages over the second server tree); see PACKAGING.md §7.
SRC_SERVER_LIBRARY_PYPROJECT = (
    CANON_LIBRARY_PYPROJECT.replace(
        '    "pyyaml>=6.0",\n]\n',
        '    "pyyaml>=6.0",\n]\n' 'django = [\n    "djhtml",\n    "pylint-django>=2.5",\n]\n',
    )
    .replace(
        '[tool.isort]\nprofile = "black"\n',
        '[tool.isort]\nprofile = "black"\n'
        'known_first_party = ["myapp", "apps", "core", "project"]\n'
        'src_paths = ["src", "server"]\n',
    )
    .replace(
        '[tool.importlinter]\nroot_package = "myapp"\n',
        '[tool.importlinter]\nroot_packages = ["myapp", "apps", "core", "project"]\n',
    )
)

CANON_SERVER_PYPROJECT = """\
[dependency-groups]
runtime = ["django>=5.0,<6.0"]
"""

CANON_MAKEFILE = """\
.PHONY: help venv install install-dev check check-full fix fmt fmt-check lint \\
        test coverage typecheck arch audit docs clean distclean system-deps

help: ## h
\t@awk '/^##@/{printf "\\n%s\\n",substr($$0,5)} /^[a-zA-Z_-]+:.*?## /{printf "  %-14s %s\\n",$$1,$$2}' $(MAKEFILE_LIST)

venv: ## v
\t@true

install: ## i
\t@true

install-dev: install ## i
\t$(PIP) install --group pyproject.toml:dev
\t$(BIN)/pre-commit install

check: fmt-check lint test ## fast gate
\t@true

check-full: ## full gate
\t@true

audit: ## a
\t@true

coverage: ## c
\t@true

fix: ## f
\t@true

fmt: ## f
\t$(PYTHON) -m isort .
\t$(PYTHON) -m black .

fmt-check: ## fc
\t@true

lint: ## l
\t@true

test: ## t
\t@true

typecheck: ## tc
\t@true

arch: ## a
\t$(PYTHON) scripts/check_upward_imports.py src
\t$(PYTHON) scripts/check_packaging.py

docs: ## d
\t$(PYTHON) scripts/check_docs.py
\t$(PYTHON) scripts/check_todo_format.py
\t$(PYTHON) scripts/check_file_placement.py

clean: ## c
\t@true

distclean: ## d
\t@true

system-deps: ## s
\tbash scripts/install_system_deps.sh
"""

# Under the Makefile fold (PACKAGING.md §7) the canonical targets live in racecar.mk
# (identical in every repo; it self-detects the shape from the layout). CANON_MAKEFILE
# above is that canonical body; THIN_MAKEFILE is the owned root that includes it.
THIN_MAKEFILE = "include racecar.mk\n"


def _racecar_mk(body: str = CANON_MAKEFILE) -> str:
    return body


CANON_PRECOMMIT = """\
repos:
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/seddonym/import-linter
    rev: v2.1
    hooks:
      - id: import-linter
  - repo: https://github.com/abravalheri/validate-pyproject
    rev: v0.25
    hooks:
      - id: validate-pyproject
  - repo: local
    hooks:
      - id: no-upward-imports-in-business-modules
        entry: x
        language: system
      - id: doc-coherence-mechanical-pre-pass
        entry: x
        language: system
      - id: todo-format
        entry: x
        language: system
      - id: file-placement
        entry: x
        language: system
"""

CANON_GITIGNORE = ".venv/\n__pycache__/\n"
CANON_REQUIREMENTS = "numpy==2.0.0\n"
CANON_CHANGELOG = "# Changelog\n\n## 0.2.0 - 2026-05-28\n\n### Added\n- thing\n"


def _seed_src(tmp_path: Path, **overrides: str | None) -> Path:
    """Seed a Shape src project (root pyproject.toml; no VERSION file in canon)."""
    files = {
        "pyproject.toml": CANON_LIBRARY_PYPROJECT,
        "requirements.txt": CANON_REQUIREMENTS,
        # the library package: makes src/ a real dir so detect_shape sees the library axis
        # (PYTHON_LIBRARY present) rather than the bare (False, False) no-shape cell.
        "src/myapp/__init__.py": "",
        ".gitignore": CANON_GITIGNORE,
        "Makefile": THIN_MAKEFILE,
        "racecar.mk": _racecar_mk(),
        ".pre-commit-config.yaml": CANON_PRECOMMIT,
        "CHANGELOG.md": CANON_CHANGELOG,
    }
    files.update(overrides)  # type: ignore[arg-type]
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.write_text(content, encoding="utf-8")
    return tmp_path


def _seed_src_server(tmp_path: Path, **overrides: str | None) -> Path:
    """Seed a Shape src+server project."""
    files = {
        "pyproject.toml": SRC_SERVER_LIBRARY_PYPROJECT,
        "requirements.txt": CANON_REQUIREMENTS,
        # the library package: makes src/ a real dir so detect_shape sees src+server, not server.
        "src/myapp/__init__.py": "",
        "server/pyproject.toml": CANON_SERVER_PYPROJECT,
        "server/requirements.txt": "django==5.0.0\n",
        "server/manage.py": "# stub manage.py\n",
        # server first-party packages: drive _server_first_party_roots().
        "server/apps/__init__.py": "",
        "server/core/__init__.py": "",
        "server/project/__init__.py": "",
        ".gitignore": CANON_GITIGNORE,
        "Makefile": THIN_MAKEFILE,
        "racecar.mk": _racecar_mk(),
        ".pre-commit-config.yaml": CANON_PRECOMMIT,
        "CHANGELOG.md": CANON_CHANGELOG,
    }
    files.update(overrides)  # type: ignore[arg-type]
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.write_text(content, encoding="utf-8")
    return tmp_path


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_canonical_src_project_passes(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path)
    result = _run(repo)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "packaging: OK" in result.stdout


def test_canonical_src_server_project_passes(tmp_path: Path) -> None:
    repo = _seed_src_server(tmp_path)
    result = _run(repo)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "packaging: OK" in result.stdout


def test_src_server_django_group_missing_djhtml_is_blocker(tmp_path: Path) -> None:
    """Django shape (manage.py present) must carry djhtml in the django dev group
    (PACKAGING.md §6). This is the lever that propagates the djhtml canon to every
    existing Django adopter: their gate flags the gap until they add it."""
    no_djhtml = SRC_SERVER_LIBRARY_PYPROJECT.replace(
        'django = [\n    "djhtml",\n    "pylint-django>=2.5",\n]\n',
        'django = [\n    "pylint-django>=2.5",\n]\n',
    )
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": no_djhtml})
    result = _run(repo)
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "[dependency-groups].django" in result.stdout
    assert "djhtml" in result.stdout


# ---------------------------------------------------------------------------
# Shape detection
# ---------------------------------------------------------------------------


def test_no_pyproject_anywhere_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{"pyproject.toml": None})  # type: ignore[arg-type]
    result = _run(repo)
    assert result.returncode == 1
    assert "missing-file" in result.stdout


# ---------------------------------------------------------------------------
# pyproject.toml — PEP 735 dev group
# ---------------------------------------------------------------------------


def test_wrong_requires_python_is_blocker(tmp_path: Path) -> None:
    bad = CANON_LIBRARY_PYPROJECT.replace(
        'requires-python = ">=3.12"', 'requires-python = ">=3.10"'
    )
    repo = _seed_src(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "requires-python" in result.stdout
    assert ">=3.12" in result.stdout


def test_missing_canon_dev_tool_is_blocker(tmp_path: Path) -> None:
    bad = CANON_LIBRARY_PYPROJECT.replace('"pip-audit",\n', "")
    repo = _seed_src(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "dependency-groups" in result.stdout
    assert "pip-audit" in result.stdout


def test_type_stub_append_to_dev_is_permitted(tmp_path: Path) -> None:
    """Type-stub packages (PEP 561 ``<pkg>-stubs`` and typeshed ``types-<pkg>``) may be
    appended to dev without a standards change (PACKAGING.md §6): mypy needs them to
    typecheck a dependency that ships no ``py.typed``. They are not beyond canon, so they
    do not trip even under ``--strict`` (which turns Findings into Blockers)."""
    good = CANON_LIBRARY_PYPROJECT.replace(
        '"pyyaml>=6.0",\n',
        '"pyyaml>=6.0",\n    "pandas-stubs",\n    "types-requests",\n',
    )
    repo = _seed_src(tmp_path, **{"pyproject.toml": good})
    result = _run(repo, "--strict")
    assert result.returncode == 0, result.stdout
    assert "beyond canon" not in result.stdout


def test_non_stub_extra_dev_tool_is_flagged(tmp_path: Path) -> None:
    """The stub exemption is narrow: a non-stub extra (flake8) is still beyond canon."""
    extra = CANON_LIBRARY_PYPROJECT.replace(
        '"pyyaml>=6.0",\n', '"pyyaml>=6.0",\n    "flake8",\n'
    )
    repo = _seed_src(tmp_path, **{"pyproject.toml": extra})
    result = _run(repo, "--strict")
    assert result.returncode == 1
    assert "beyond canon" in result.stdout
    assert "flake8" in result.stdout


def test_dev_in_old_optional_dependencies_location_is_blocker(tmp_path: Path) -> None:
    """PEP 735 supersedes [project.optional-dependencies].dev."""
    bad = CANON_LIBRARY_PYPROJECT.replace(
        "[dependency-groups]\ndev = [",
        "[project.optional-dependencies]\ndev = [",
    )
    repo = _seed_src(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "deprecated location" in result.stdout
    assert "[project.optional-dependencies].dev" in result.stdout


def test_forbidden_tool_uv_block_is_blocker(tmp_path: Path) -> None:
    bad = CANON_LIBRARY_PYPROJECT + "\n[tool.uv]\nworkspace = true\n"
    repo = _seed_src(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "[tool.uv]" in result.stdout


def test_mypy_not_strict_is_blocker(tmp_path: Path) -> None:
    bad = CANON_LIBRARY_PYPROJECT.replace("strict = true", "strict = false")
    repo = _seed_src(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "[tool.mypy].strict" in result.stdout


# ---------------------------------------------------------------------------
# server pyproject — PEP 735 runtime group
# ---------------------------------------------------------------------------


def test_server_missing_runtime_group_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src_server(tmp_path, **{"server/pyproject.toml": "# empty\n"})
    result = _run(repo)
    assert result.returncode == 1
    assert "server/pyproject.toml" in result.stdout
    assert "[dependency-groups].runtime" in result.stdout


def test_src_server_missing_server_pyproject_is_blocker(tmp_path: Path) -> None:
    """Shape src+server detected via server/manage.py but server/pyproject.toml
    absent: the server runtime deps have no canonical home. Must Blocker, not
    silently skip server validation (the false-green the audit surfaced)."""
    repo = _seed_src_server(tmp_path, **{"server/pyproject.toml": None})  # type: ignore[arg-type]
    result = _run(repo)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "server/pyproject.toml" in result.stdout
    assert "missing-file" in result.stdout
    assert "src+server" in result.stdout


def test_server_with_project_block_is_finding(tmp_path: Path) -> None:
    bad = (
        '[project]\nname = "myapp-server"\nversion = "0.0.1"\n\n' + CANON_SERVER_PYPROJECT
    )
    repo = _seed_src_server(tmp_path, **{"server/pyproject.toml": bad})
    result = _run(repo)
    # Finding only, not Blocker
    assert result.returncode == 0
    assert "server/pyproject.toml" in result.stdout
    assert "[project]" in result.stdout


def test_server_with_tool_block_is_finding(tmp_path: Path) -> None:
    bad = CANON_SERVER_PYPROJECT + "\n[tool.black]\nline-length = 100\n"
    repo = _seed_src_server(tmp_path, **{"server/pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 0  # finding only
    assert "[tool.*]" in result.stdout


# ---------------------------------------------------------------------------
# src+server: isort/import-linter must cover the server source tree.
# profile="black" alone is a FALSE GREEN for this multi-root shape.
# ---------------------------------------------------------------------------


def test_src_server_profile_only_isort_is_blocker(tmp_path: Path) -> None:
    """The bug: a src+server lib pyproject with only profile="black" (no
    known_first_party / src_paths) used to pass. It must now Blocker."""
    # profile-only isort, singular root_package; the src/ + server/ layout makes
    # detection classify it src+server, so the multi-root isort coverage check fires.
    bad = CANON_LIBRARY_PYPROJECT  # profile-only isort, singular root_package
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "[tool.isort].src_paths" in result.stdout
    assert "[tool.isort].known_first_party" in result.stdout


def test_src_server_isort_missing_src_paths_is_blocker(tmp_path: Path) -> None:
    bad = SRC_SERVER_LIBRARY_PYPROJECT.replace(
        'src_paths = ["src", "server"]\n', ""
    )
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "[tool.isort].src_paths" in result.stdout


def test_src_server_isort_src_paths_without_server_is_blocker(tmp_path: Path) -> None:
    bad = SRC_SERVER_LIBRARY_PYPROJECT.replace(
        'src_paths = ["src", "server"]', 'src_paths = ["src"]'
    )
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "[tool.isort].src_paths" in result.stdout


def test_src_server_isort_known_first_party_missing_root_is_blocker(
    tmp_path: Path,
) -> None:
    """known_first_party omits 'core' -> isort would misclassify it third-party."""
    bad = SRC_SERVER_LIBRARY_PYPROJECT.replace(
        'known_first_party = ["myapp", "apps", "core", "project"]',
        'known_first_party = ["myapp", "apps", "project"]',
    )
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "[tool.isort].known_first_party" in result.stdout
    assert "core" in result.stdout


def test_src_server_importlinter_only_library_is_blocker(tmp_path: Path) -> None:
    """import-linter naming only the library root never audits server."""
    bad = SRC_SERVER_LIBRARY_PYPROJECT.replace(
        'root_packages = ["myapp", "apps", "core", "project"]',
        'root_package = "myapp"',
    )
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "[tool.importlinter]" in result.stdout


def test_src_server_importlinter_server_root_via_contract_is_ok(tmp_path: Path) -> None:
    """A contract referencing a server root satisfies coverage (no root_packages)."""
    body = SRC_SERVER_LIBRARY_PYPROJECT.replace(
        'root_packages = ["myapp", "apps", "core", "project"]',
        'root_package = "myapp"',
    ) + (
        "\n[[tool.importlinter.contracts]]\n"
        'name = "apps layering"\n'
        'type = "layers"\n'
        'modules = ["apps", "core", "project"]\n'
    )
    repo = _seed_src_server(tmp_path, **{"pyproject.toml": body})
    result = _run(repo)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "packaging: OK" in result.stdout


def test_src_shape_isort_profile_only_still_passes(tmp_path: Path) -> None:
    """Single-root shapes are unaffected: profile-only isort stays OK
    (isort auto-detects first-party over the one tree)."""
    repo = _seed_src(tmp_path)  # uses profile-only CANON_LIBRARY_PYPROJECT
    result = _run(repo)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "packaging: OK" in result.stdout


# ---------------------------------------------------------------------------
# Legacy VERSION file: emits Finding, not Blocker
# ---------------------------------------------------------------------------


def test_legacy_version_file_present_is_finding(tmp_path: Path) -> None:
    """A VERSION file at repo root is the pre-v4 pattern; checker should flag it."""
    repo = _seed_src(tmp_path)
    (repo / "VERSION").write_text("0.2.0\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0  # Finding only, no Blocker
    assert "deprecated-file" in result.stdout
    assert "VERSION" in result.stdout


def test_legacy_version_file_with_strict_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path)
    (repo / "VERSION").write_text("0.2.0\n", encoding="utf-8")
    result = _run(repo, "--strict")
    assert result.returncode == 1
    assert "deprecated-file" in result.stdout


def test_no_project_version_means_version_file_not_flagged(tmp_path: Path) -> None:
    """A repo with no [project].version (a non-package repo: docs / scripts /
    standards framework, which has no [project] table) keeps VERSION as its
    legitimate version home -- the deprecated-file Finding must NOT fire even
    when a VERSION file is present. See PACKAGING.md §8."""
    no_project = (
        "[dependency-groups]\n"
        'dev = ["black", "isort", "pylint", "pytest"]\n\n'
        "[tool.black]\nline-length = 88\n\n"
        '[tool.isort]\nprofile = "black"\n'
    )
    repo = _seed_src(tmp_path, **{"pyproject.toml": no_project})
    (repo / "VERSION").write_text("0.5.0\n", encoding="utf-8")
    result = _run(repo)
    assert "deprecated-file" not in result.stdout, (result.stdout, result.stderr)


# ---------------------------------------------------------------------------
# Forbidden lockfiles
# ---------------------------------------------------------------------------


def test_uv_lock_present_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path)
    (repo / "uv.lock").write_text("# uv.lock\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 1
    assert "uv.lock" in result.stdout


# ---------------------------------------------------------------------------
# Lockfile content: must be real pip-compile output, not empty/placeholder
# ---------------------------------------------------------------------------


def test_empty_requirements_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{"requirements.txt": ""})
    result = _run(repo)
    assert result.returncode == 1
    assert "not-a-lockfile" in result.stdout


def test_comments_only_requirements_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{"requirements.txt": "# just a comment\n# another\n"})
    result = _run(repo)
    assert result.returncode == 1
    assert "not-a-lockfile" in result.stdout


def test_pip_compile_header_is_accepted(tmp_path: Path) -> None:
    header = (
        "#\n"
        "# This file is autogenerated by pip-compile with Python 3.12\n"
        "# by the following command:\n"
        "#\n"
        "#    pip-compile pyproject.toml\n"
        "#\n"
    )
    repo = _seed_src(tmp_path, **{"requirements.txt": header})
    result = _run(repo)
    assert result.returncode == 0
    assert "packaging: OK" in result.stdout


def test_real_pin_without_header_is_accepted(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{"requirements.txt": "numpy==2.0.0\npandas==2.2.0\n"})
    result = _run(repo)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Lockfile location per shape
# ---------------------------------------------------------------------------


def test_src_server_no_requirements_txt_is_ok(tmp_path: Path) -> None:
    """Lockfiles are optional in canon; absence is fine."""
    repo = _seed_src_server(
        tmp_path,
        **{"server/requirements.txt": None, "requirements.txt": None},  # type: ignore[arg-type]
    )
    result = _run(repo)
    assert result.returncode == 0
    assert "packaging: OK" in result.stdout


def test_src_server_empty_committed_lockfile_is_blocker(tmp_path: Path) -> None:
    """If committed, requirements.txt must be a real lockfile -- not empty."""
    repo = _seed_src_server(tmp_path, **{"requirements.txt": ""})
    result = _run(repo)
    assert result.returncode == 1
    assert "not-a-lockfile" in result.stdout
    assert "requirements.txt" in result.stdout


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------


def test_missing_venv_rule_in_gitignore_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{".gitignore": "__pycache__/\n"})
    result = _run(repo)
    assert result.returncode == 1
    assert "missing-venv-rule" in result.stdout


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------


def test_missing_makefile_target_is_blocker(tmp_path: Path) -> None:
    import re as _re

    bad = _re.sub(r"docs: ## d\n(?:\t[^\n]*\n)+\n?", "", CANON_MAKEFILE)
    bad = bad.replace(" docs", "")
    repo = _seed_src(tmp_path, **{"racecar.mk": _racecar_mk(bad)})
    result = _run(repo)
    assert result.returncode == 1
    assert "missing-target:docs" in result.stdout


def test_uv_invocation_in_makefile_is_blocker(tmp_path: Path) -> None:
    bad = CANON_MAKEFILE + "\nuv-install:\n\tuv pip install -e .\n"
    repo = _seed_src(tmp_path, **{"racecar.mk": _racecar_mk(bad)})
    result = _run(repo)
    assert result.returncode == 1
    assert "non-canon-tool:uv" in result.stdout


def test_legacy_single_file_makefile_nudges_to_sync(tmp_path: Path) -> None:
    """A pre-fold repo (full Makefile, no racecar.mk) still passes, with a sync nudge."""
    repo = _seed_src(tmp_path, Makefile=CANON_MAKEFILE, **{"racecar.mk": None})
    result = _run(repo)
    assert result.returncode == 0
    assert "no-racecar-mk" in result.stdout


def test_thin_makefile_missing_racecar_mk_is_blocker(tmp_path: Path) -> None:
    """Owned Makefile includes racecar.mk but the generated file is gone -> one blocker."""
    repo = _seed_src(
        tmp_path, **{"racecar.mk": None}
    )  # Makefile defaults to the thin include
    result = _run(repo)
    assert result.returncode == 1
    assert "racecar.mk" in result.stdout
    assert "make sync" in result.stdout


def test_racecar_mk_present_but_not_included_is_blocker(tmp_path: Path) -> None:
    """The half-migrated state an upgrade leaves: sync drops racecar.mk beside a
    monolithic Makefile that never includes it, so the canonical build is inert. The
    checker keyed fold adoption off rcmk.exists() alone and false-greened here."""
    repo = _seed_src(tmp_path, Makefile=CANON_MAKEFILE)  # racecar.mk present, not incl.
    result = _run(repo)
    assert result.returncode == 1
    assert "racecar-mk-not-included" in result.stdout


# ---------------------------------------------------------------------------
# pre-commit
# ---------------------------------------------------------------------------


def test_missing_required_hook_is_blocker(tmp_path: Path) -> None:
    bad = CANON_PRECOMMIT.replace("      - id: import-linter\n", "")
    repo = _seed_src(tmp_path, **{".pre-commit-config.yaml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "missing-hook:import-linter" in result.stdout


def test_stale_make_var_is_blocker(tmp_path: Path) -> None:
    # A repo-owned pre-commit config that survived the djapp->server rename: the hook id is
    # present, but its body still calls the retired `make -s print-DJAPP` (resolves to empty,
    # silently breaking import-linter). A hook-id-only check misses it; the staleness rule does not.
    bad = CANON_PRECOMMIT.replace("entry: x", "entry: bash -c 'make -s print-DJAPP'", 1)
    assert "DJAPP" in bad  # guard: the fixture actually contains the stale reference
    repo = _seed_src(tmp_path, **{".pre-commit-config.yaml": bad})
    result = _run(repo)
    assert result.returncode == 1
    assert "stale-make-var:DJAPP" in result.stdout


# ---------------------------------------------------------------------------
# CHANGELOG
# ---------------------------------------------------------------------------


def test_missing_changelog_is_finding_not_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{"CHANGELOG.md": None})  # type: ignore[arg-type]
    result = _run(repo)
    assert result.returncode == 0
    assert "CHANGELOG.md" in result.stdout


def test_missing_changelog_with_strict_is_blocker(tmp_path: Path) -> None:
    repo = _seed_src(tmp_path, **{"CHANGELOG.md": None})  # type: ignore[arg-type]
    result = _run(repo, "--strict")
    assert result.returncode == 1
    assert "CHANGELOG.md" in result.stdout


def test_unreleased_only_changelog_passes_strict(tmp_path: Path) -> None:
    """A freshly-scaffolded `# Changelog` + `## [Unreleased]` is honest and clean."""
    repo = _seed_src(tmp_path, **{"CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n"})
    result = _run(repo, "--strict")
    assert result.returncode == 0, result.stdout


# ---------------------------------------------------------------------------
# racecar.mk PKG derivation — the canonical Makefile resolves the importable
# package dir, not the namespace source root. check_cli_commands rejects a bare
# source root (no __init__.py), so PKG must descend src -> src/<pkg>.
# ---------------------------------------------------------------------------

RACECAR_MK = Path(__file__).resolve().parents[2] / "templates" / "classic" / "racecar.mk"


def _resolve_make_var(tmp_path: Path, layout: dict[str, str], var: str) -> str:
    """Seed `layout` under tmp_path with the REAL racecar.mk and return `print-<var>`."""
    for name, content in layout.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "racecar.mk").write_text(
        RACECAR_MK.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "Makefile").write_text("include racecar.mk\n", encoding="utf-8")
    result = subprocess.run(
        ["make", "-s", f"print-{var}"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.mark.skipif(shutil.which("make") is None, reason="make not on PATH")
@pytest.mark.parametrize(
    "label,layout,expected_pkg",
    [
        ("src", {"pyproject.toml": "", "src/gfem/__init__.py": ""}, "src/gfem"),
        (
            "src+server",
            {
                "pyproject.toml": "",
                "src/gfem/__init__.py": "",
                "server/manage.py": "",
            },
            "src/gfem",
        ),
        # SRC is itself the package (flat layout): PKG stays at SRC.
        ("flat-src", {"pyproject.toml": "", "src/__init__.py": ""}, "src"),
        # Standalone server (server/manage.py, no library): SRC=server, PKG falls back to SRC.
        ("standalone-server", {"pyproject.toml": "", "server/manage.py": ""}, "server"),
        # No package found under the namespace root: fall back to SRC.
        ("empty-src", {"pyproject.toml": "", "src/.keep": ""}, "src"),
    ],
)
def test_racecar_mk_pkg_descends_to_package_dir(
    tmp_path: Path, label: str, layout: dict[str, str], expected_pkg: str
) -> None:
    """racecar.mk derives PKG as the package dir under SRC for every shape, so the
    CLI/coverage audits receive `src/<pkg>` rather than the namespace root."""
    assert _resolve_make_var(tmp_path, layout, "PKG") == expected_pkg, label


@pytest.mark.skipif(shutil.which("make") is None, reason="make not on PATH")
def test_racecar_mk_pkg_honors_owned_override(tmp_path: Path) -> None:
    """An owned `PKG :=` before the include wins over the derivation (?=)."""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "src" / "gfem").mkdir(parents=True)
    (tmp_path / "src" / "gfem" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "racecar.mk").write_text(
        RACECAR_MK.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "Makefile").write_text(
        "PKG := src/custom\ninclude racecar.mk\n", encoding="utf-8"
    )
    result = subprocess.run(
        ["make", "-s", "print-PKG"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "src/custom"
