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
    python scripts/init_project.py --shape pypkg+djapp --name athena --package athena --dest ./athena \\
        --description "Weather model" --author "Jane Doe" --email jane@example.com --version 0.1.0

Exit codes: 0 ok; 2 bad arguments / clobber refusal (argparse uses 2 for
arg errors, so we reuse it for the destination-conflict refusal too).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "classic"

SHAPES = ("src", "pypkg", "pypkg+djapp", "djapp")

# Check scripts the scaffolded project's Makefile `arch:` / `docs:` targets
# invoke as `scripts/<name>.py`. Copied verbatim from their canonical homes —
# these scripts ARE the canon (PYTHON.md §4 "to adopt on a new project" and
# the templates/classic/Makefile arch:/docs: targets). Source path is relative
# to the racecar repo root; destination is always scripts/<basename>.
#
# All eight are copied for every shape. The set is exactly the scripts/check_*.py
# the template Makefile and pre-commit config invoke between them; a scaffold must
# contain every script its own gate calls.
#   - check_upward_imports.py imports check_packaging (detect_shape), so they
#     must travel together regardless of shape.
#   - check_string_relations.py is Django-only at runtime, but the Makefile
#     guards its invocation (runs only when DJAPP is set and djapp/manage.py
#     exists), so a non-Django scaffold simply never calls it. Copying it for
#     all shapes matches the adoption list in PYTHON.md §4 (which presents it
#     unconditionally with a runtime skip) and lets any shape grow a djapp
#     later without re-running adoption. The cost is one inert stdlib file.
#   - check_todo_format.py, check_claude_shape.py, check_file_placement.py back
#     the todo-format / claude-md-shape / file-placement pre-commit hooks the
#     template ships; without them those hooks have no script to run.
CHECK_SCRIPTS = (
    "arch-coherence/scripts/check_upward_imports.py",
    "arch-coherence/scripts/check_cli_commands.py",
    "arch-coherence/scripts/check_packaging.py",
    "arch-coherence/scripts/check_string_relations.py",
    "doc-coherence/scripts/check_docs.py",
    "doc-coherence/scripts/check_todo_format.py",
    "doc-coherence/scripts/check_claude_shape.py",
    "doc-coherence/scripts/check_file_placement.py",
)


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

    # Source package skeleton so `make check` has something to point at.
    pkg_dir = dest / layout["SRC"] / package
    init_doc = f'"""Top-level package for {name}."""\n'
    _write(pkg_dir / "__init__.py", init_doc, created)

    # Check scripts the Makefile arch:/docs: targets invoke as scripts/<name>.py.
    # Without these, `make arch` / `make docs` / `make check-full` fail with
    # file-not-found in every scaffolded project. Copy verbatim (canonical
    # source) into the project's scripts/ directory.
    copy_check_scripts(dest, created)

    return created


def copy_check_scripts(dest: Path, created: list[Path]) -> None:
    """Copy each canonical check script into the scaffold's scripts/ directory.

    The scripts are copied byte-for-byte from their racecar homes (CHECK_SCRIPTS)
    to dest/scripts/<basename>.py. They are the canonical source; the scaffold
    must not diverge from them.
    """
    for rel_source in CHECK_SCRIPTS:
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
    )
    print(f"init_project: scaffolded shape {args.shape!r} into {dest}")
    for path in created:
        print(f"  created {path.relative_to(dest)}")
    print(f"init_project: {len(created)} file(s) created. Next: cd {dest} && make install-dev && make check-full")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
