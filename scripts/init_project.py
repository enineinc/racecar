#!/usr/bin/env python3
"""Scaffold a new racecar-conforming project from templates/classic/.

Automates the copy-and-substitute adoption procedure documented in
arch-coherence/PACKAGING.md §3 (and PYTHON.md §4): create the shape-correct
directory layout, copy each canonical template to its shape-correct
destination, and substitute every `<placeholder>` token. racecar.mk is copied
verbatim (it is identical in every repo and detects the shape from the layout
this scaffold creates; the owned Makefile is a thin `include racecar.mk`).

Four shapes (PACKAGING.md §"Scope"):

    src           root pyproject.toml + src/<pkg>/
    pypkg         pypkg/src/pyproject.toml (no djapp/)
    pypkg+djapp   pypkg/src/pyproject.toml + djapp/pyproject.toml
    djapp         root pyproject.toml (no pypkg/), djapp/

Per-shape destinations (PACKAGING.md §3 "Reference templates" table):

    template                    src / djapp          pypkg / pypkg+djapp
    library-pyproject.toml  ->  pyproject.toml        pypkg/src/pyproject.toml
    djapp-pyproject.toml    ->  (none)                djapp/pyproject.toml (pypkg+djapp only)
    Makefile                ->  Makefile (thin owned root, all shapes)
    racecar.mk              ->  racecar.mk (canonical, identical in every shape)
    pre-commit-config.yaml  ->  .pre-commit-config.yaml (root, all shapes)
    gitignore               ->  .gitignore (root, all shapes)

Safety: refuses to write into a non-empty destination directory (matching
racecar's install philosophy — refuse rather than clobber). Use a fresh or
empty --dest.

Usage:
    python scripts/init_project.py --shape src --name widgets --package widgets --dest /tmp/widgets
    python scripts/init_project.py --shape src --name athena --package athena --dest ./athena \\
        --vertical prices --vertical dispatch   # pre-wired lib->api->cli verticals (FACES.md)
    python scripts/init_project.py --shape pypkg+djapp --name athena --package athena \\
        --dest ./athena --description "Weather model" --author "Jane Doe" \\
        --email jane@example.com --version 0.1.0

Exit codes: 0 ok; 2 bad arguments / clobber refusal (argparse uses 2 for
arg errors, so we reuse it for the destination-conflict refusal too).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sync_scripts  # sibling in scripts/; the one home for the adopter-script set

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "classic"

SHAPES = ("src", "pypkg", "pypkg+djapp", "djapp")

# The scripts a scaffolded project's Makefile / pre-commit invoke, copied verbatim
# from their canonical homes (these scripts ARE the canon). ONE home for the list:
# sync_scripts (which the staleness hook reads too) — init derives its set from
# there rather than keeping a second copy that drifts (it did, once: a script lived
# in one manifest and not the other). init differs from sync only in policy: it
# copies the Django check (check_dj_model_ref_as_string) and clean_files.sh for
# EVERY shape, because the Makefile guards the Django check's runtime invocation and
# copying it lets any shape grow a djapp later (PYTHON.md §4 presents it
# unconditionally with a runtime skip); sync gates it on a real manage.py instead.
ADOPTER_SCRIPTS = sync_scripts.CHECK_SCRIPTS + sync_scripts.DJANGO_SCRIPTS


def template_text(name: str) -> str:
    """Read a template file from templates/classic/ as text."""
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


# Minimal Django manage.py for the djapp scaffold. Its presence is the marker that
# racecar.mk / check_packaging use to detect the djapp shape; the author points
# DJANGO_SETTINGS_MODULE at the real settings module once it exists.
_MANAGE_PY = '''\
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{package}.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''


def library_layout(shape: str) -> dict[str, str]:
    """Placement facts for a shape: where the source package and the pyproject(s) go.

    init only needs to lay the canonical files in the right places; it does not set
    Makefile shape variables. `racecar.mk` is identical in every repo and detects the
    shape from this layout at make-time (templates/classic/racecar.mk), so a scaffold
    is configured purely by *what init creates*, not by a written shape value.
    """
    if shape in ("pypkg", "pypkg+djapp"):
        src_dir, lib_dest, where = "pypkg/src", "pypkg/src/pyproject.toml", "."
    else:  # src, djapp — library pyproject at repo root
        src_dir, lib_dest, where = (
            ("djapp" if shape == "djapp" else "src"),
            "pyproject.toml",
            "src",
        )
    return {
        "src_dir": src_dir,
        "lib_pyproject_dest": lib_dest,
        "djapp_pyproject_dest": (
            "djapp/pyproject.toml" if shape == "pypkg+djapp" else ""
        ),
        "where": where,
    }


def render_library_pyproject(
    *,
    name: str,
    package: str,
    version: str,
    description: str,
    author: str,
    email: str,
    where: str,
    shape: str,
) -> str:
    """Fill the `<placeholder>` tokens in library-pyproject.toml.

    `<runtime dep>` is removed entirely (a fresh project has no direct runtime
    deps yet, and a literal placeholder would fail validate-pyproject); the
    layered-DAG contract is replaced with a single-layer placeholder naming the
    root package, so import-linter has a valid contract out of the box.

    For Shape pypkg+djapp the `[tool.isort]` block is expanded with the
    multi-root `src_paths` / `known_first_party` keys the canon requires (see
    PACKAGING.md §7 "Multi-root first-party detection"); `profile = "black"`
    alone is a false green there.
    """
    text = template_text("library-pyproject.toml")
    text = text.replace("<project_name>", name)
    text = text.replace("<x.y.z>", version)
    text = text.replace("<one-line description>", description)
    text = text.replace("<your name>", author)
    text = text.replace("<email>", email)
    text = text.replace("<root>", package)
    text = text.replace('where = ["<where>"]', f'where = ["{where}"]')

    # Drop the `"<runtime dep>",` placeholder line — a new project declares no
    # direct runtime deps, and the literal token is not a valid requirement.
    lines = [ln for ln in text.splitlines() if '"<runtime dep>"' not in ln]
    text = "\n".join(lines) + "\n"

    # Replace the layered-DAG contract layers (which reference <consumer_a>,
    # <data_a>, <leaf>, ...) with a single concrete layer naming the root, so
    # `lint-imports` has a valid contract from the start. The author fleshes
    # out the real layers as the package grows.
    text = _replace_contract_layers(text, package)

    if shape == "pypkg+djapp":
        text = _expand_isort_multiroot(text)
    return text


def _expand_isort_multiroot(text: str) -> str:
    """Add the multi-root isort keys required for Shape pypkg+djapp.

    The shared template carries only `profile = "black"`, which is correct for
    the single-root shapes (src / pypkg / djapp) where isort auto-detects
    first-party packages over its one tree. Shape pypkg+djapp runs isort over
    both `pypkg/src` and `djapp` from a config rooted only in `pypkg/src`, so it
    must name the second root explicitly: `src_paths` must include `"djapp"`,
    and `known_first_party` must list djapp's top-level packages. The fresh
    scaffold has no djapp packages yet, so `known_first_party` starts empty;
    the author populates it (and the import-linter djapp coverage) as the djapp
    grows — see PACKAGING.md §7.
    """
    addition = (
        'profile = "black"\n'
        "# Shape pypkg+djapp: isort runs over both source roots from this one\n"
        "# config; name the second root and djapp's first-party packages so they\n"
        "# are not misclassified as third-party (see racecar's PACKAGING.md,\n"
        '# "Multi-root first-party detection").\n'
        'src_paths = ["src", "djapp"]\n'
        'known_first_party = []  # add each djapp top-level package, e.g. "apps", "core"\n'
    )
    return text.replace('profile = "black"\n', addition, 1)


def _replace_contract_layers(text: str, package: str) -> str:
    """Rewrite the `[[tool.importlinter.contracts]]` layers block.

    The template's layers list carries `<root>.<consumer_a>`-style placeholders.
    Replace the whole `layers = [ ... ]` array with a one-entry list naming the
    root package, leaving a comment for the author to expand.
    """
    out: list[str] = []
    in_layers = False
    for line in text.splitlines():
        if line.strip().startswith("layers = ["):
            in_layers = True
            out.append("layers = [")
            out.append(
                "    # Fill in the project's real peer/leaf arrangement as it grows;"
            )
            out.append(
                "    # see racecar's arch-coherence/PACKAGING.md. One layer naming the root"
            )
            out.append("    # package is a valid starting contract.")
            out.append(f'    "{package}",')
            continue
        if in_layers:
            if line.strip() == "]":
                in_layers = False
                out.append("]")
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def _ensure_writable_dest(dest: Path) -> None:
    """Refuse to scaffold into a non-empty directory (clobber safety)."""
    if dest.exists():
        if not dest.is_dir():
            raise SystemExit(
                f"init_project: {dest} exists and is not a directory; refusing."
            )
        if any(dest.iterdir()):
            raise SystemExit(
                f"init_project: {dest} is not empty; refusing to clobber. "
                "Choose a fresh --dest or empty this one."
            )


def _write(path: Path, content: str, created: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(path)


def _render_leaf_main(dotted: str, verb: str) -> str:
    """A Pattern 3 leaf `__main__.py` (CLI.md): `python -m <dotted>` is the whole CLI.

    Conforms to the §3 contract the audit (`check_cli_commands`) enforces: `commands()`
    returns `[]` (a leaf composes no sub-packages), `parser()` is the factory the audit
    introspects for the argument surface, and `main()` is a thin dispatcher. No
    subparsers here, so no `subcommands()` is declared.
    """
    return (
        f'"""{verb} cli face: a thin wrapper on api (FACES.md §1; CLI.md Pattern 3 leaf).\n\n'
        f"`python -m {dotted}` runs this leaf. commands() is empty; parser() exposes the\n"
        "argument surface so the CLI audit can read it; main() only dispatches.\n"
        '"""\n\n'
        "import argparse\n\n"
        "from . import api\n\n\n"
        "def commands() -> list[tuple[str, str]]:\n"
        '    """Leaf: no sub-packages to compose (CLI.md `commands()`, required everywhere)."""\n'
        "    return []\n\n\n"
        "def parser() -> argparse.ArgumentParser:\n"
        '    """Build the parser WITHOUT parsing — the factory the audit introspects."""\n'
        f'    p = argparse.ArgumentParser(prog="python -m {dotted}", description="{verb} CLI")\n'
        f'    p.add_argument("--value", help="input for {verb}")\n'
        "    return p\n\n\n"
        "def main(argv: list[str] | None = None) -> None:\n"
        "    args = parser().parse_args(argv)\n"
        "    print(api.execute(args.value))\n\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def _render_root_main(package: str, verbs: list[str]) -> str:
    """A Pattern 1 discovery `__main__.py` for the package root: lists its verticals.

    `python -m <package>` prints the listing and exits; each entry is its own
    `python -m <package>.<verb>` leaf. Per CLI.md, a Pattern 1 node exposes
    `commands()` and `_print_commands()` and nothing else (no parser, no subcommands).
    """
    rows = "\n".join(
        f'        ("{v}", "{v} vertical: [one-line description]"),' for v in verbs
    )
    return (
        f'"""{package} CLI root (FACES.md; CLI.md Pattern 1 — pure discovery).\n\n'
        "Lists the verticals this package composes; each is its own leaf CLI. Register a\n"
        "new vertical by adding it to commands() (explicit registration, CLI.md §Registration).\n"
        '"""\n\n'
        "import sys\n\n\n"
        "def commands() -> list[tuple[str, str]]:\n"
        '    """The immediate `python -m <pkg>.<name>` children this root composes."""\n'
        "    return [\n"
        f"{rows}\n"
        "    ]\n\n\n"
        "def _print_commands() -> None:\n"
        '    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]\n'
        "    width = max(len(p) for p, _ in entries)\n"
        '    print(f"python -m {__package__}\\n")\n'
        "    for path, desc in entries:\n"
        '        print(f"  {path.ljust(width)}   {desc}")\n'
        '    print("\\nAppend --help to any command for its options.")\n\n\n'
        'if __name__ == "__main__":\n'
        "    _print_commands()\n"
        "    sys.exit(0)\n"
    )


def _render_lib(label: str) -> str:
    return (
        f'"""{label} worker: pure capability — no input/credential/default policy.\n\n'
        "The lib role (FACES.md §1). It does the work and knows nothing about who\n"
        'calls it. Replace the stub with the real engine.\n"""\n\n\n'
        "def run(value: str) -> str:\n"
        f'    """The engine for {label}."""\n'
        "    return value\n"
    )


def _render_api(label: str) -> str:
    return (
        f'"""{label} orchestration: the one home for resolve / default / dispatch.\n\n'
        "The api role (FACES.md §1). Faces call into here; they hold no policy of\n"
        'their own. api imports lib, never the reverse.\n"""\n\n'
        "from .lib import run\n\n\n"
        "def execute(value: str | None = None) -> str:\n"
        '    """Resolve inputs and defaults, then dispatch to the worker."""\n'
        "    if value is None:\n"
        '        value = "default"\n'
        "    return run(value)\n"
    )


def _scaffold_cli_unit(
    target_dir: Path, dotted: str, label: str, created: list[Path], *, write_init: bool
) -> None:
    """Write one conformant `lib -> api -> cli` unit (FACES.md §2-§3) into target_dir.

    The `__main__.py` is a CLI.md Pattern 3 leaf, so the unit passes both the faces
    detector AND check_cli_commands. `write_init=False` for the single-CLI-at-root
    case, where the package `__init__.py` already exists.
    """
    if write_init:
        _write(
            target_dir / "__init__.py",
            f'"""{label} vertical: lib -> api -> faces (FACES.md). Namespace only."""\n',
            created,
        )
    _write(target_dir / "lib.py", _render_lib(label), created)
    _write(target_dir / "api.py", _render_api(label), created)
    _write(target_dir / "__main__.py", _render_leaf_main(dotted, label), created)


def scaffold_vertical(
    pkg_dir: Path, package: str, verb: str, created: list[Path]
) -> None:
    """Scaffold one canonical vertical: lib.py -> api.py -> __main__.py (FACES.md §2-§3).

    The good shape is the default you receive (FACES.md §10, "make the right thing
    easy" — the startapp equivalent): the files are pre-wired so `lib -> api -> cli`
    already holds, the canonical file names make `check_face_orchestration.py`
    classify the roles exactly (Tier 1, FACES.md §5), and the `__main__.py` conforms
    to the CLI.md Pattern 3 leaf contract. The author replaces the stub bodies.
    """
    _scaffold_cli_unit(
        pkg_dir / verb, f"{package}.{verb}", verb, created, write_init=True
    )


def scaffold(
    *,
    shape: str,
    name: str,
    package: str,
    dest: Path,
    version: str,
    description: str,
    author: str,
    email: str,
    verticals: list[str] | None = None,
    cli: bool = False,
) -> list[Path]:
    """Create the shape-correct project tree under `dest`. Returns the files
    created (in creation order).

    CLI surface (CLI.md): `cli=True` scaffolds a single-surface CLI — the package
    root is one Pattern 3 leaf, `python -m <pkg>`. `verticals=[...]` scaffolds a
    nested surface — a Pattern 1 discovery root that lists each `python -m
    <pkg>.<verb>` leaf. The two are mutually exclusive.
    """
    if cli and verticals:
        raise SystemExit(
            "init_project: --cli (single CLI surface) and --vertical (nested surface) "
            "are mutually exclusive; pick one."
        )
    _ensure_writable_dest(dest)
    layout = library_layout(shape)
    created: list[Path] = []

    # Library pyproject.
    lib_pyproject = render_library_pyproject(
        name=name,
        package=package,
        version=version,
        description=description,
        author=author,
        email=email,
        where=layout["where"],
        shape=shape,
    )
    _write(dest / layout["lib_pyproject_dest"], lib_pyproject, created)

    # djapp pyproject (pypkg+djapp only) — copied verbatim (no placeholders).
    if layout["djapp_pyproject_dest"]:
        _write(
            dest / layout["djapp_pyproject_dest"],
            template_text("djapp-pyproject.toml"),
            created,
        )

    # Makefile fold (PACKAGING.md §7): thin owned root + canonical racecar.mk.
    # racecar.mk is identical in every repo (it detects the shape from the layout
    # this scaffold creates), so it is copied verbatim. pre-commit and gitignore at root.
    _write(dest / "Makefile", template_text("Makefile"), created)
    _write(dest / "racecar.mk", template_text("racecar.mk"), created)
    _write(
        dest / ".pre-commit-config.yaml",
        template_text("pre-commit-config.yaml"),
        created,
    )
    _write(dest / ".gitignore", template_text("gitignore"), created)

    # System-deps helper the Makefile `system-deps` target invokes; without it a
    # fresh scaffold's `make system-deps` fails file-not-found.
    _write(
        dest / "scripts" / "install_system_deps.sh",
        template_text("install_system_deps.sh"),
        created,
    )

    # Human README skeleton: the standard who-what -> Getting Started -> Using ->
    # when/where/why shape (a received default, not an enforced checklist). Only
    # <project_name> is filled; the prose placeholders are author prompts.
    _write(
        dest / "README.md",
        template_text("README.md").replace("<project_name>", name),
        created,
    )

    # Source package skeleton so `make check` has something to point at.
    pkg_dir = dest / layout["src_dir"] / package
    init_doc = f'"""Top-level package for {name}."""\n'
    _write(pkg_dir / "__init__.py", init_doc, created)

    # Both Django shapes get djapp/manage.py — the one marker racecar.mk and
    # check_packaging use to recognize Django. manage.py, never a bare djapp/ dir, is
    # what makes a djapp; without it the scaffold misdetects (djapp -> src, pypkg+djapp
    # -> pypkg). The djapp pyproject alone is not enough.
    if shape in ("djapp", "pypkg+djapp"):
        _write(
            dest / "djapp" / "manage.py", _MANAGE_PY.format(package=package), created
        )

    # CLI surface (CLI.md). Single surface: the package root IS a Pattern 3 leaf.
    # Nested surface: a Pattern 1 discovery root over Pattern 3 leaf verticals. Both
    # pass check_cli_commands; the good shape is the default you receive (FACES.md §10).
    if cli:
        _scaffold_cli_unit(pkg_dir, package, package, created, write_init=False)
    for verb in verticals or ():
        scaffold_vertical(pkg_dir, package, verb, created)
    if verticals:
        _write(
            pkg_dir / "__main__.py",
            _render_root_main(package, list(verticals)),
            created,
        )

    # Check scripts the Makefile arch:/docs: targets invoke as scripts/<name>.py.
    # Without these, `make arch` / `make docs` / `make check-full` fail with
    # file-not-found in every scaffolded project. Copy verbatim (canonical
    # source) into the project's scripts/ directory.
    copy_check_scripts(dest, created)

    return created


def copy_check_scripts(dest: Path, created: list[Path]) -> None:
    """Copy each canonical adopter script into the scaffold's scripts/ directory.

    The scripts are copied byte-for-byte from their racecar homes (ADOPTER_SCRIPTS,
    derived from sync_scripts) to dest/scripts/<basename>. They are the canonical
    source; the scaffold must not diverge from them.

    A check script may carry its implementation in a sibling `<stem>_rules/`
    package (the thin-entry + impl-package split, e.g. check_packaging.py +
    check_packaging_rules/). `sync_scripts.delivered_files` is the one home for
    that convention: it expands each entry to the entry plus its package modules,
    so the scaffolder, `make sync`, and the staleness hook deliver the same set.
    """
    for rel_source in ADOPTER_SCRIPTS:
        for source, dest_rel in sync_scripts.delivered_files(rel_source):
            _write(
                dest / "scripts" / dest_rel,
                source.read_text(encoding="utf-8"),
                created,
            )


def parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the scaffolder."""
    p = argparse.ArgumentParser(
        description="Scaffold a racecar-conforming project from templates/classic/.",
    )
    p.add_argument(
        "--shape",
        required=True,
        choices=SHAPES,
        help="Project shape (PACKAGING.md §Scope).",
    )
    p.add_argument("--name", required=True, help="Distribution name ([project].name).")
    p.add_argument(
        "--package", required=True, help="Top-level importable package (root_package)."
    )
    p.add_argument(
        "--dest",
        type=Path,
        default=Path.cwd(),
        help="Destination directory (default: cwd).",
    )
    p.add_argument(
        "--version", default="0.1.0", help="Initial [project].version (default: 0.1.0)."
    )
    p.add_argument(
        "--description",
        default="A racecar-conforming Python project.",
        help="One-line [project].description.",
    )
    p.add_argument("--author", default="TODO", help="Author name ([project].authors).")
    p.add_argument(
        "--email", default="todo@example.com", help="Author email ([project].authors)."
    )
    p.add_argument(
        "--vertical",
        action="append",
        metavar="VERB",
        help="Nested CLI surface: scaffold a canonical vertical (lib/api/__main__) "
        "under a Pattern 1 discovery root, per FACES.md + CLI.md. Repeatable: "
        "--vertical prices --vertical dispatch. Mutually exclusive with --cli.",
    )
    p.add_argument(
        "--cli",
        action="store_true",
        help="Single CLI surface: make the package root one CLI.md Pattern 3 leaf "
        "(`python -m <pkg>`). Mutually exclusive with --vertical.",
    )
    return p


def main(argv: list[str]) -> int:
    """Parse arguments, scaffold the project, and print the next-steps summary."""
    args = parser().parse_args(argv)
    dest = args.dest.expanduser().resolve()
    created = scaffold(
        shape=args.shape,
        name=args.name,
        package=args.package,
        dest=dest,
        version=args.version,
        description=args.description,
        author=args.author,
        email=args.email,
        verticals=args.vertical,
        cli=args.cli,
    )
    print(f"init_project: scaffolded shape {args.shape!r} into {dest}")
    for path in created:
        print(f"  created {path.relative_to(dest)}")
    print(f"init_project: {len(created)} file(s) created.")
    print("Next:")
    print(f"  1. cd {dest}")
    print("  2. Edit [tool.importlinter] in the library pyproject — replace the")
    print("     placeholder layer with your real package layout (PACKAGING.md §9).")
    print("  3. make install-dev")
    print("  4. .venv/bin/pre-commit install")
    print("  5. make check-full")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
