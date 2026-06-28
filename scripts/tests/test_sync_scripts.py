"""sync_scripts + racecar.mk: the Makefile fold (PACKAGING.md §7).

racecar.mk is identical in every repo and detects the project shape from the
filesystem at make-time. These tests cover four things:

  - sync installs racecar.mk as a verbatim copy of the canonical template;
  - racecar.mk's in-Make shape detection resolves the right variables for each
    layout (driven by real `make`);
  - that in-Make detection agrees with check_packaging.detect_shape on every
    layout (the coherence guard for the two detection homes, PACKAGING.md §"Scope");
  - a REAL init_project scaffold, run through real `make`, resolves the shape it
    was scaffolded as (the end-to-end realism gate that the original makefile-fold
    bug slipped through, because the synthetic fixtures were more complete than the
    scaffolder).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "arch-coherence" / "scripts"))
import check_packaging  # noqa: E402
import init_project  # noqa: E402
import sync_remote  # noqa: E402
import sync_scripts  # noqa: E402

TEMPLATE_RACECAR_MK = REPO_ROOT / "templates" / "classic" / "racecar.mk"

# layout name -> the files that make a repo that shape, and the shape make/Python
# must both resolve it to. "stock" (empty repo) is detect_shape's "unknown".
LAYOUTS = {
    "src": (["pyproject.toml", "src/mypkg/__init__.py"], "src"),
    "src+server": (
        ["pyproject.toml", "src/mypkg/__init__.py", "server/manage.py"],
        "src+server",
    ),
    "server": (["pyproject.toml", "server/manage.py"], "server"),
    # The gap: a server/ holding only a pyproject (no manage.py) is NOT Django. manage.py
    # is the marker; a bare server/ tree does not make a server, so this falls back to the
    # library shape.
    "server-no-manage": (
        ["pyproject.toml", "src/mypkg/__init__.py", "server/pyproject.toml"],
        "src",
    ),
    "stock": ([], "stock"),
}


def _seed(dest: Path, layout: str) -> None:
    """Create the files for a layout. Shape is governed by what is on disk, so there
    is no token to write — only the canonical files."""
    for rel in LAYOUTS[layout][0]:
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def _make_shape(dest: Path) -> dict[str, str]:
    """Install racecar.mk and ask real `make` what shape/vars it resolves."""
    sync_scripts._materialize_racecar_mk(dest, dry_run=False)
    (dest / "Makefile").write_text(
        'include racecar.mk\n_v:\n\t@echo "$(SHAPE)|$(SRC)|$(SERVER)|$(LIB_PYPROJECT)"\n',
        encoding="utf-8",
    )
    out = subprocess.run(
        ["make", "-s", "_v"], cwd=dest, capture_output=True, text=True, check=True
    ).stdout.strip()
    shape, src, server, lib = out.split("|")
    return {"SHAPE": shape, "SRC": src, "SERVER": server, "LIB_PYPROJECT": lib}


# ---------------------------------------------------------------------------
# sync installs the canonical file verbatim
# ---------------------------------------------------------------------------


def test_materialize_copies_canonical_racecar_mk(tmp_path: Path) -> None:
    assert sync_scripts._materialize_racecar_mk(tmp_path, dry_run=False) == "created"
    assert (tmp_path / "racecar.mk").read_text() == TEMPLATE_RACECAR_MK.read_text()


def test_materialize_is_idempotent(tmp_path: Path) -> None:
    assert sync_scripts._materialize_racecar_mk(tmp_path, dry_run=False) == "created"
    assert sync_scripts._materialize_racecar_mk(tmp_path, dry_run=False) == "unchanged"


def test_init_scaffolds_identical_racecar_mk(tmp_path: Path) -> None:
    """A scaffold ships the same canonical racecar.mk; sync is then a no-op on it."""
    init_project.scaffold(
        shape="server",
        name="potato",
        package="potato",
        dest=tmp_path,
        version="0.1.0",
        description="d",
        author="a",
        email="a@b.c",
    )
    assert (tmp_path / "racecar.mk").read_text() == TEMPLATE_RACECAR_MK.read_text()
    assert sync_scripts._materialize_racecar_mk(tmp_path, dry_run=False) == "unchanged"


# Shape -> (SHAPE, SRC, SERVER) the build must resolve for a real init scaffold.
_SCAFFOLD_RESOLVES = {
    "src": ("src", "src", ""),
    "src+server": ("src+server", "src", "server"),
    "server": ("server", "server", "server"),
}


@pytest.mark.parametrize("shape", list(_SCAFFOLD_RESOLVES))
def test_scaffolded_repo_resolves_its_own_shape_under_make(
    shape: str, tmp_path: Path
) -> None:
    """The realism gate, end to end: scaffold a REAL repo with init_project, run REAL
    `make` against it, and assert the build resolves the shape it was scaffolded as.

    This is the test the original makefile-fold bug needed and lacked. That bug (init
    shipped a server scaffold with no manage.py, so the build misdetected it as `src`)
    shipped GREEN because every shape test used a synthetic fixture that hand-seeded
    the markers the scaffolder forgot — a fixture more complete than reality. Coupling
    the real scaffold to real `make` closes that gap: delete init's manage.py creation
    and the server case fails here, where it should.
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
    sync_scripts._materialize_racecar_mk(
        tmp_path, dry_run=False
    )  # the `make sync` step
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        makefile.read_text() + '\n_v:\n\t@echo "$(SHAPE)|$(SRC)|$(SERVER)"\n',
        encoding="utf-8",
    )
    out = subprocess.run(
        ["make", "-s", "_v"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert tuple(out.split("|")) == _SCAFFOLD_RESOLVES[shape]


# ---------------------------------------------------------------------------
# racecar.mk detects the shape in Make (driven by real `make`)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layout", list(LAYOUTS))
def test_racecar_mk_resolves_shape(layout: str, tmp_path: Path) -> None:
    _seed(tmp_path, layout)
    expected_shape = LAYOUTS[layout][1]
    assert _make_shape(tmp_path)["SHAPE"] == expected_shape


def test_racecar_mk_src_variables(tmp_path: Path) -> None:
    _seed(tmp_path, "src")
    v = _make_shape(tmp_path)
    assert (v["SRC"], v["SERVER"], v["LIB_PYPROJECT"]) == ("src", "", "pyproject.toml")


def test_racecar_mk_src_server_variables(tmp_path: Path) -> None:
    _seed(tmp_path, "src+server")
    v = _make_shape(tmp_path)
    assert (v["SRC"], v["SERVER"], v["LIB_PYPROJECT"]) == (
        "src",
        "server",
        "pyproject.toml",
    )


def test_racecar_mk_server_variables(tmp_path: Path) -> None:
    """Standalone Django (server/manage.py, no library): SRC=server, SERVER=server."""
    _seed(tmp_path, "server")
    v = _make_shape(tmp_path)
    assert (v["SRC"], v["SERVER"], v["LIB_PYPROJECT"]) == (
        "server",
        "server",
        "pyproject.toml",
    )


# ---------------------------------------------------------------------------
# the two detection homes agree (PACKAGING.md §"Scope")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layout", list(LAYOUTS))
def test_make_and_detect_shape_agree(layout: str, tmp_path: Path) -> None:
    """The Make shape decision and check_packaging.detect_shape classify every
    layout identically. detect_shape's no-match sentinel is 'unknown'; racecar.mk's
    is 'stock' — same outcome, normalized here."""
    _seed(tmp_path, layout)
    make_shape = _make_shape(tmp_path)["SHAPE"]
    py_shape, _ = check_packaging.detect_shape(tmp_path)
    normalized = "stock" if py_shape.name == "unknown" else py_shape.name
    assert make_shape == normalized


# ---------------------------------------------------------------------------
# the delivered-file manifest is the one home both sync paths read
# ---------------------------------------------------------------------------


def test_manifest_is_current() -> None:
    """The committed manifest matches what the live scripts produce.

    The manifest (scripts/racecar-manifest.txt) is generated from CHECK_SCRIPTS via
    delivered_files; sync_remote fetches it instead of duplicating the list. If this
    fails, a script or a `_rules/` package module changed without regenerating:
    run `python scripts/sync_scripts.py --write-manifest`.
    """
    committed = (
        (REPO_ROOT / sync_scripts.MANIFEST_REL).read_text(encoding="utf-8").splitlines()
    )
    assert committed == sync_scripts.manifest()


def test_sync_remote_has_no_hardcoded_script_list() -> None:
    """The remote path must drive off the fetched manifest, not its own copy of the
    list (the two-home duplication that silently drifted and is the reason the manifest
    exists). It reads the same MANIFEST_REL sync_scripts writes."""
    assert not hasattr(sync_remote, "CHECK_SCRIPTS")
    assert sync_remote.MANIFEST_REL == sync_scripts.MANIFEST_REL


def test_manifest_includes_package_modules_and_django_tag() -> None:
    """The manifest expands `_rules/` package modules (so the no-clone path delivers
    them) and tags the Django-only check, the two things the old remote list lacked."""
    lines = sync_scripts.manifest()
    assert any("check_packaging_rules/" in line for line in lines)
    assert any(line.endswith(" django") for line in lines)
