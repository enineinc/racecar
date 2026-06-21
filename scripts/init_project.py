#!/usr/bin/env python3
"""Scaffold a new racecar-conforming project from templates/classic/.

Automates the copy-and-substitute adoption procedure documented in
arch-coherence/PACKAGING.md §3 (and PYTHON.md §4): create the shape-correct
directory layout, copy each canonical template to its shape-correct
destination, substitute every `<placeholder>` token, and set the Makefile's
SRC / PKG / DJAPP / LIB_PYPROJECT / DJAPP_PYPROJECT variables for the chosen
shape.

Four shapes (PACKAGING.md §"Scope"):

    src           root pyproject.toml + src/<pkg>/
    pypkg         pypkg/src/pyproject.toml (no djapp/)
    pypkg+djapp   pypkg/src/pyproject.toml + djapp/pyproject.toml
    djapp         root pyproject.toml (no pypkg/), djapp/

Per-shape destinations (PACKAGING.md §3 "Reference templates" table):

    template                    src / djapp          pypkg / pypkg+djapp
    library-pyproject.toml  ->  pyproject.toml        pypkg/src/pyproject.toml
    djapp-pyproject.toml    ->  (none)                djapp/pyproject.toml (pypkg+djapp only)
    Makefile                ->  Makefile (root, all shapes)
    pre-commit-config.yaml  ->  .pre-commit-config.yaml (root, all shapes)
    gitignore               ->  .gitignore (root, all shapes)

Safety: refuses to write into a non-empty destination directory (matching
racecar's install philosophy — refuse rather than clobber). Use a fresh or
empty --dest.

Usage:
    python scripts/init_project.py --shape src --name widgets --package widgets --dest /tmp/widgets
    python scripts/init_project.py --shape src --name athena --package athena --dest ./athena \\
        --vertical prices --vertical dispatch   # pre-wired lib->api->cli verticals (FACES.md)
    python scripts/init_project.py --shape pypkg+djapp --name athena --package athena --dest ./athena \\
        --description "Weather model" --author "Jane Doe" --email jane@example.com --version 0.1.0

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


def library_layout(shape: str, package: str) -> dict[str, str]:
    """Return the Makefile shape variables (SRC / PKG / DJAPP / *_PYPROJECT)
    and the library/djapp pyproject destinations for a shape.

    Mirrors the PACKAGING.md §"Scope" shape->layout table.
    """
    if shape == "src":
        return {
            "SRC": "src",
            "PKG": f"src/{package}",
            "DJAPP": "",
            "LIB_PYPROJECT": "pyproject.toml",
            "DJAPP_PYPROJECT": "",
            "lib_pyproject_dest": "pyproject.toml",
            "djapp_pyproject_dest": "",
            "where": "src",
        }
    if shape == "pypkg":
        return {
            "SRC": "pypkg/src",
            "PKG": f"pypkg/src/{package}",
            "DJAPP": "",
            "LIB_PYPROJECT": "pypkg/src/pyproject.toml",
            "DJAPP_PYPROJECT": "",
            "lib_pyproject_dest": "pypkg/src/pyproject.toml",
            "djapp_pyproject_dest": "",
            "where": ".",
        }
    if shape == "pypkg+djapp":
        return {
            "SRC": "pypkg/src",
            "PKG": f"pypkg/src/{package}",
            "DJAPP": "djapp",
            "LIB_PYPROJECT": "pypkg/src/pyproject.toml",
            "DJAPP_PYPROJECT": "djapp/pyproject.toml",
            "lib_pyproject_dest": "pypkg/src/pyproject.toml",
            "djapp_pyproject_dest": "djapp/pyproject.toml",
            "where": ".",
        }
    # djapp
    return {
        "SRC": "djapp",
        "PKG": f"djapp/{package}",
        "DJAPP": "djapp",
        "LIB_PYPROJECT": "pyproject.toml",
        "DJAPP_PYPROJECT": "",
        "lib_pyproject_dest": "pyproject.toml",
        "djapp_pyproject_dest": "",
        "where": "src",
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
        '# Shape pypkg+djapp: isort runs over both source roots from this one\n'
        '# config; name the second root and djapp\'s first-party packages so they\n'
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
            out.append("    # Fill in the project's real peer/leaf arrangement as it grows;")
            out.append("    # see racecar's arch-coherence/PACKAGING.md. One layer naming the root")
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


def render_makefile(layout: dict[str, str]) -> str:
    """Set the Makefile's shape variables for the chosen shape.

    The template carries `SRC ?= src` (etc.) defaults; rewrite the assignment
    line for each shape variable so the copied Makefile is shape-correct
    without the consumer hand-editing it.
    """
    text = template_text("Makefile")
    replacements = {
        "SRC ?= src": f"SRC ?= {layout['SRC']}",
        "PKG ?= $(SRC)": f"PKG ?= {layout['PKG']}",
        "DJAPP ?=": f"DJAPP ?= {layout['DJAPP']}".rstrip(),
        "LIB_PYPROJECT   ?= pyproject.toml": f"LIB_PYPROJECT   ?= {layout['LIB_PYPROJECT']}",
        "DJAPP_PYPROJECT ?=": f"DJAPP_PYPROJECT ?= {layout['DJAPP_PYPROJECT']}".rstrip(),
    }
    for old, new in replacements.items():
        if old not in text:
            raise SystemExit(
                f"init_project: Makefile template missing expected line {old!r}; "
                "template drift — update init_project.py"
            )
        text = text.replace(old, new, 1)
    return text


def _ensure_writable_dest(dest: Path) -> None:
    """Refuse to scaffold into a non-empty directory (clobber safety)."""
    if dest.exists():
        if not dest.is_dir():
            raise SystemExit(f"init_project: {dest} exists and is not a directory; refusing.")
        if any(dest.iterdir()):
            raise SystemExit(
                f"init_project: {dest} is not empty; refusing to clobber. "
                "Choose a fresh --dest or empty this one."
            )


def _write(path: Path, content: str, created: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(path)


def scaffold_vertical(pkg_dir: Path, package: str, verb: str, created: list[Path]) -> None:
    """Scaffold one canonical vertical: lib.py -> api.py -> __main__.py (FACES.md §2-§3).

    The good shape is the default you receive (FACES.md §10, "make the right thing
    easy" — the startapp equivalent): the files are pre-wired so `lib -> api -> cli`
    already holds, the canonical file names make `check_face_orchestration.py`
    classify the roles exactly (Tier 1, FACES.md §5), and the layers contract has
    real tier modules to name. The author replaces the stub bodies; the shape is a
    default received, not a wall imposed.
    """
    verb_dir = pkg_dir / verb
    dotted = f"{package}.{verb}"
    files = {
        "__init__.py": f'"""{verb} vertical: lib -> api -> faces (FACES.md). Namespace only."""\n',
        "lib.py": (
            f'"""{verb} worker: pure capability — no input/credential/default policy.\n\n'
            "The lib role (FACES.md §1). It does the work and knows nothing about who\n"
            'calls it. Replace the stub with the real engine.\n"""\n\n\n'
            "def run(value: str) -> str:\n"
            f'    """The engine for {verb}."""\n'
            "    return value\n"
        ),
        "api.py": (
            f'"""{verb} orchestration: the one home for resolve / default / dispatch.\n\n'
            "The api role (FACES.md §1). Faces call into here; they hold no policy of\n"
            'their own. api imports lib, never the reverse.\n"""\n\n'
            "from .lib import run\n\n\n"
            "def execute(value: str | None = None) -> str:\n"
            '    """Resolve inputs and defaults, then dispatch to the worker."""\n'
            "    if value is None:\n"
            '        value = "default"\n'
            "    return run(value)\n"
        ),
        "__main__.py": (
            f'"""{verb} cli face: a thin wrapper on api (FACES.md §1 face role).\n\n'
            "Translate argv -> api call -> rendered output. No orchestration here;\n"
            f"strip argparse and this module collapses into a call to {dotted}.api.\n"
            '"""\n\n'
            "import argparse\n\n"
            "from . import api\n\n\n"
            "def main(argv: list[str] | None = None) -> None:\n"
            f'    parser = argparse.ArgumentParser(prog="python -m {dotted}")\n'
            f'    parser.add_argument("--value", help="input for {verb}")\n'
            "    args = parser.parse_args(argv)\n"
            "    print(api.execute(args.value))\n\n\n"
            'if __name__ == "__main__":\n'
            "    main()\n"
        ),
    }
    for fname, body in files.items():
        _write(verb_dir / fname, body, created)


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
) -> list[Path]:
    """Create the shape-correct project tree under `dest`. Returns the files
    created (in creation order)."""
    _ensure_writable_dest(dest)
    layout = library_layout(shape, package)
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

    # Makefile (shape variables set), pre-commit, gitignore — all at root.
    _write(dest / "Makefile", render_makefile(layout), created)
    _write(dest / ".pre-commit-config.yaml", template_text("pre-commit-config.yaml"), created)
    _write(dest / ".gitignore", template_text("gitignore"), created)

    # System-deps helper the Makefile `system-deps` target invokes; without it a
    # fresh scaffold's `make system-deps` fails file-not-found.
    _write(dest / "scripts" / "install_system_deps.sh", template_text("install_system_deps.sh"), created)

    # Human README skeleton: the standard who-what -> Getting Started -> Using ->
    # when/where/why shape (a received default, not an enforced checklist). Only
    # <project_name> is filled; the prose placeholders are author prompts.
    _write(dest / "README.md", template_text("README.md").replace("<project_name>", name), created)

    # Source package skeleton so `make check` has something to point at.
    pkg_dir = dest / layout["SRC"] / package
    init_doc = f'"""Top-level package for {name}."""\n'
    _write(pkg_dir / "__init__.py", init_doc, created)

    # Canonical verticals, pre-wired lib -> api -> cli (FACES.md §10). Optional:
    # the good shape is the default you receive, not a wall imposed.
    for verb in verticals or ():
        scaffold_vertical(pkg_dir, package, verb, created)

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
    """
    for rel_source in ADOPTER_SCRIPTS:
        source = REPO_ROOT / rel_source
        text = source.read_text(encoding="utf-8")
        _write(dest / "scripts" / Path(rel_source).name, text, created)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scaffold a racecar-conforming project from templates/classic/.",
    )
    p.add_argument("--shape", required=True, choices=SHAPES, help="Project shape (PACKAGING.md §Scope).")
    p.add_argument("--name", required=True, help="Distribution name ([project].name).")
    p.add_argument("--package", required=True, help="Top-level importable package (root_package).")
    p.add_argument("--dest", type=Path, default=Path.cwd(), help="Destination directory (default: cwd).")
    p.add_argument("--version", default="0.1.0", help="Initial [project].version (default: 0.1.0).")
    p.add_argument(
        "--description",
        default="A racecar-conforming Python project.",
        help="One-line [project].description.",
    )
    p.add_argument("--author", default="TODO", help="Author name ([project].authors).")
    p.add_argument("--email", default="todo@example.com", help="Author email ([project].authors).")
    p.add_argument(
        "--vertical",
        action="append",
        metavar="VERB",
        help="Scaffold a canonical vertical (lib.py/api.py/__main__.py) pre-wired "
        "lib->api->cli per FACES.md. Repeatable: --vertical prices --vertical dispatch.",
    )
    return p


def main(argv: list[str]) -> int:
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
    )
    print(f"init_project: scaffolded shape {args.shape!r} into {dest}")
    for path in created:
        print(f"  created {path.relative_to(dest)}")
    print(f"init_project: {len(created)} file(s) created.")
    print(f"Next:")
    print(f"  1. cd {dest}")
    print(f"  2. Edit [tool.importlinter] in the library pyproject — replace the")
    print(f"     placeholder layer with your real package layout (PACKAGING.md §9).")
    print(f"  3. make install-dev")
    print(f"  4. .venv/bin/pre-commit install")
    print(f"  5. make check-full")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
