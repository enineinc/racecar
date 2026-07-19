"""Tests for scripts/instrument_telemetry.py — the mechanical usage-telemetry instrumenter.

Verifies the two mechanical operations (deliver the probe, wrap the compliant guard), that it
reads the callable name from the AST, that it acts only where it is provably safe (surfacing
the rest), and that it is idempotent and honors --check.

Run with:
    pytest scripts/tests/test_instrument_telemetry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
import instrument_telemetry as it  # noqa: E402


def _pkg(root: Path, guard_body: str, *, sub: str = "") -> Path:
    """Build a package `pkg` (optionally a submodule) with a given run-guard body; return the __main__.py."""
    pkg_dir = root / "src" / "pkg"
    (pkg_dir / (sub or "")).mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    target_dir = pkg_dir / sub if sub else pkg_dir
    if sub:
        (target_dir / "__init__.py").write_text("", encoding="utf-8")
    main_py = target_dir / "__main__.py"
    main_py.write_text(
        "from pkg.cli import main\n\nif __name__ == \"__main__\":\n" + guard_body,
        encoding="utf-8",
    )
    return main_py


def test_wraps_sys_exit_form(tmp_path: Path) -> None:
    main_py = _pkg(tmp_path, "    sys.exit(main())\n")
    it.main(["--dest", str(tmp_path)])
    text = main_py.read_text(encoding="utf-8")
    assert "from pkg._telemetry import run" in text
    assert "run(main)" in text
    assert "sys.exit(main())" not in text  # the dispatch was replaced


def test_reads_callable_name_from_ast(tmp_path: Path) -> None:
    main_py = _pkg(tmp_path, "    raise SystemExit(cli())\n")
    it.main(["--dest", str(tmp_path)])
    assert "run(cli)" in main_py.read_text(encoding="utf-8")  # not hard-coded 'main'


def test_delivers_probe_at_top_package(tmp_path: Path) -> None:
    _pkg(tmp_path, "    main()\n", sub="deep")
    it.main(["--dest", str(tmp_path)])
    probe = tmp_path / "src" / "pkg" / "_telemetry.py"  # top package, not the submodule
    assert probe.is_file()
    # the submodule entrypoint imports from the TOP package
    sub_main = (tmp_path / "src" / "pkg" / "deep" / "__main__.py").read_text(encoding="utf-8")
    assert "from pkg._telemetry import run" in sub_main


def test_surfaces_non_standard_guard_unchanged(tmp_path: Path) -> None:
    body = "    print('boot')\n    main()\n"  # more than a single dispatch
    main_py = _pkg(tmp_path, body)
    before = main_py.read_text(encoding="utf-8")
    it.main(["--dest", str(tmp_path)])
    assert main_py.read_text(encoding="utf-8") == before  # never edited


def test_idempotent(tmp_path: Path) -> None:
    main_py = _pkg(tmp_path, "    sys.exit(main())\n")
    it.main(["--dest", str(tmp_path)])
    once = main_py.read_text(encoding="utf-8")
    it.main(["--dest", str(tmp_path)])  # second run
    assert main_py.read_text(encoding="utf-8") == once  # no double-wrap


def test_check_mode_writes_nothing_and_flags(tmp_path: Path) -> None:
    main_py = _pkg(tmp_path, "    sys.exit(main())\n")
    before = main_py.read_text(encoding="utf-8")
    rc = it.main(["--dest", str(tmp_path), "--check"])
    assert rc == 1  # an un-instrumented compliant entrypoint exists
    assert main_py.read_text(encoding="utf-8") == before  # untouched
    assert not (tmp_path / "src" / "pkg" / "_telemetry.py").exists()  # nothing delivered


def test_main_not_in_package_is_skipped(tmp_path: Path) -> None:
    loose = tmp_path / "tools"
    loose.mkdir()
    main_py = loose / "__main__.py"  # no __init__.py alongside
    main_py.write_text('if __name__ == "__main__":\n    main()\n', encoding="utf-8")
    before = main_py.read_text(encoding="utf-8")
    it.main(["--dest", str(tmp_path)])
    assert main_py.read_text(encoding="utf-8") == before  # cannot import from a package: skipped
