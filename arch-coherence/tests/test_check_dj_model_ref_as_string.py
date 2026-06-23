"""Tests for scripts/check_dj_model_ref_as_string.py.

Builds a fake project under tmp_path with `[tool.importlinter].root_packages`
and a `layers` DAG contract in pyproject.toml. Each test seeds violations
across LIVE apps (in INSTALLED_APPS) and NOOP apps (on disk but not
registered) and asserts the report sections match exactly.

INSTALLED_APPS is injected via the `STRING_RELATIONS_INSTALLED_APPS` env var
so tests do not require a working `manage.py`.

Most fixtures put the project at the tmp_path root (the standalone-djapp layout,
where the repo root and the Django home coincide). The `test_pypkg_djapp_*` pair
builds the harder pypkg+djapp layout, where the pyproject and the app packages
live under `djapp/` beside `manage.py` and NOT at the repo root, as a good tree
(clean, exits 0) and a bad tree (one cross-module string ref, exits 1). They
prove the check anchors every read to the Django home; a repo-root probe exits 2
on the good tree and never reaches the violation on the bad one.

Run with:
    pytest arch-coherence/tests/test_check_dj_model_ref_as_string.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_dj_model_ref_as_string.py"


_PYPROJECT = """\
[tool.importlinter]
root_packages = ["apps", "core"]

[[tool.importlinter.contracts]]
name = "layered DAG"
type = "layers"
layers = [
    "apps.activity",
    "apps.sessions",
    "core",
]
"""

_INSTALLED = "apps.activity.ib,apps.sessions,core.llm"

# pypkg+djapp adds a library root to root_packages (xenocrates and meridian both do:
# "xenocrates" / "meridian" beside the django apps), so root_packages spans two source
# roots. The library package is not a registered Django app, so its violations land in
# NOOP, which is what lets the bad-tree test prove both roots were walked.
_PYPROJECT_PD = _PYPROJECT.replace(
    'root_packages = ["apps", "core"]',
    'root_packages = ["lib", "apps", "core"]',
)

_CLEAN_MODELS = """\
from django.conf import settings
from django.db import models

from apps.other.models import Other


class Clean(models.Model):
    other = models.ForeignKey(Other, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
"""

_INTRA_APP = """\
from django.db import models


class Foo(models.Model):
    other = models.ForeignKey("Other", on_delete=models.CASCADE)
"""

_SAME_FILE_FORWARD = """\
from django.db import models


class Front(models.Model):
    later = models.ForeignKey("Back", on_delete=models.CASCADE)


class Back(models.Model):
    pass
"""

_SELF_REF = """\
from django.db import models


class Tree(models.Model):
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True)
"""

_UPWARD_CROSS = """\
from django.db import models


class LlmThing(models.Model):
    s = models.ForeignKey("sessions.Session", on_delete=models.CASCADE)
"""

_BROKEN_LABEL = """\
from django.db import models


class LlmThing(models.Model):
    s = models.ForeignKey("xeno_sessions.Session", on_delete=models.CASCADE)
"""

_NOOP_VIOLATION = """\
from django.db import models


class Dead(models.Model):
    other = models.ForeignKey("apps.activity.ib.Other", on_delete=models.CASCADE)
"""


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _seed_pypkg_djapp(
    tmp_path: Path,
    *,
    library: dict[str, str] | None = None,
    djapp: dict[str, str] | None = None,
) -> None:
    """Dup the real pypkg+djapp shape (xenocrates / meridian) under tmp_path. The
    importlinter contract (root_packages, layers) lives in the LIBRARY pyproject at
    `pypkg/src/`, per PACKAGING.md; root_packages spans a library package under
    `pypkg/src/` AND Django apps under `djapp/` beside `manage.py`. So the contract
    and the packages sit in two different roots, neither the repo root: the case the
    repo-root probe could never handle. `library` maps paths under `pypkg/src/`,
    `djapp` maps paths under `djapp/`."""
    _write(tmp_path / "pypkg" / "src" / "pyproject.toml", _PYPROJECT_PD)
    _write(tmp_path / "djapp" / "manage.py", "")
    for rel, body in (library or {}).items():
        _write(tmp_path / "pypkg" / "src" / rel, body)
    for rel, body in (djapp or {}).items():
        _write(tmp_path / "djapp" / rel, body)


def _run(cwd: Path, *, installed: str | None = _INSTALLED) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if installed is not None:
        env["STRING_RELATIONS_INSTALLED_APPS"] = installed
    else:
        env.pop("STRING_RELATIONS_INSTALLED_APPS", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_clean_tree_passes(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _CLEAN_MODELS)
    _write(tmp_path / "core" / "llm" / "models.py", _CLEAN_MODELS)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_intra_app_violation_is_live_no_cross(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _INTRA_APP)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert result.stdout == (
        "LIVE violations (file's app is in INSTALLED_APPS):\n"
        "  apps/activity/ib/models.py:5: ForeignKey string reference forbidden: 'Other' "
        "[file layer: apps.activity]\n"
    )


def test_same_file_forward_ref_is_exempt(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _SAME_FILE_FORWARD)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_migrations_dir_is_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "migrations" / "0001_initial.py", _UPWARD_CROSS)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_self_ref_is_exempt(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _SELF_REF)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_upward_cross_is_flagged(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "core" / "llm" / "models.py", _UPWARD_CROSS)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "UPWARD DAG cross" in result.stdout
    assert "target layer: apps.sessions" in result.stdout


def test_unknown_app_label_is_flagged(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "core" / "llm" / "models.py", _BROKEN_LABEL)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "target app label 'xeno_sessions' not in INSTALLED_APPS" in result.stdout


def test_noop_module_is_separated(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "ghost" / "models.py", _NOOP_VIOLATION)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert result.stdout.startswith("NOOP modules")
    assert "apps/ghost/models.py:5" in result.stdout


def test_live_and_noop_both_reported(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _INTRA_APP)
    _write(tmp_path / "apps" / "ghost" / "models.py", _NOOP_VIOLATION)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "LIVE violations" in result.stdout
    assert "NOOP modules" in result.stdout
    live_idx = result.stdout.index("LIVE violations")
    noop_idx = result.stdout.index("NOOP modules")
    assert live_idx < noop_idx


def test_violation_outside_root_packages_is_not_scanned(tmp_path: Path) -> None:
    """Negative space: the walk covers ONLY the dirs named in [tool.importlinter].
    root_packages. A models.py carrying a textbook cross-module string ref but living
    OUTSIDE every declared root package (here `outside/`, with only `apps`/`core`
    declared) is never read, so it raises no finding. root_packages is the scan
    frontier; absence outside it is the contract."""
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    # Only `apps`/`core` are root packages — but seed the violation under neither,
    # and seed nothing under apps/core so they are absent on disk too.
    _write(tmp_path / "outside" / "models.py", _NOOP_VIOLATION)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout
    assert result.stdout == ""


def test_exempt_forms_are_not_flagged(tmp_path: Path) -> None:
    """Negative space: the three exempt relation forms — `settings.AUTH_USER_MODEL`
    (attribute, not a string), `'self'`, and a same-file forward-ref class name — must
    NOT be flagged even though `_CLEAN_MODELS` also imports a real model by symbol. A
    clean live module produces no finding and exits 0."""
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _SELF_REF)
    _write(tmp_path / "core" / "llm" / "models.py", _CLEAN_MODELS)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_missing_root_packages_key_errors(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[tool.other]\nx = 1\n")

    result = _run(tmp_path)

    assert result.returncode == 2
    assert "root_packages missing" in result.stderr


def test_missing_pyproject_errors(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.returncode == 2
    assert "pyproject.toml not found" in result.stderr


def test_missing_installed_apps_source_skips(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", _PYPROJECT)
    _write(tmp_path / "apps" / "activity" / "ib" / "models.py", _CLEAN_MODELS)

    result = _run(tmp_path, installed=None)

    assert result.returncode == 0
    assert "not a Django project" in result.stdout


def test_pypkg_djapp_good_tree_passes(tmp_path: Path) -> None:
    """Good pypkg+djapp tree: clean models in BOTH roots, a library package under
    pypkg/src/ and django apps under djapp/. The contract is read from the library
    pyproject and each root_package resolved across both source roots. A repo-root
    probe finds no pyproject at the root and exits 2 instead of passing."""
    _seed_pypkg_djapp(
        tmp_path,
        library={"lib/models.py": _CLEAN_MODELS},
        djapp={
            "apps/activity/ib/models.py": _CLEAN_MODELS,
            "core/llm/models.py": _CLEAN_MODELS,
        },
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


def test_pypkg_djapp_bad_tree_walks_both_source_roots(tmp_path: Path) -> None:
    """Bad pypkg+djapp tree with a violation in EACH root: a LIVE one under
    djapp/apps/ (a registered app) and a NOOP one under pypkg/src/lib/ (the library,
    not in INSTALLED_APPS). Both must be reported, which proves the walk resolves
    root_packages across both source roots, not the repo root. Before the fix the
    contract pyproject was unreadable at the root (exit 2); fixing only that left the
    walk repo-root-anchored, where neither root lives, so it false-greened. This pair
    is the regression guard for the whole class of shape-blindness."""
    _seed_pypkg_djapp(
        tmp_path,
        library={"lib/models.py": _INTRA_APP},
        djapp={"apps/activity/ib/models.py": _INTRA_APP},
    )

    result = _run(tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "LIVE violations" in result.stdout
    assert "djapp/apps/activity/ib/models.py:5:" in result.stdout
    assert "NOOP modules" in result.stdout
    assert "pypkg/src/lib/models.py:5:" in result.stdout
