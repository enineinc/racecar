#!/usr/bin/env python3
"""check_doc_graph: validate the documentation node graph.

Every in-scope Markdown doc (see DOC_GRAPH.md) declares its parent once, in a
``pnode`` frontmatter list. Children and peers are derived by scanning, never
stored. This checker assembles the graph from every doc's ``pnode`` and holds
it to three rules:

- **types**    every ``pnode`` (and optional ``see_also``) entry resolves to an
               existing in-scope Markdown file.
- **dag**      the graph assembled from all ``pnode`` edges is acyclic.
- **consistency**  where a doc's body carries an ``Accessed via [X](path)`` link,
               ``path`` is among its declared ``pnode`` (the prose is the human
               echo of the machine edge; the two must agree).

A doc with ``pnode: []`` is a root. Exit 0 when clean, 1 on any finding.

Deterministic, stdlib plus PyYAML (already a dev dependency); no model calls.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Directories whose Markdown is not part of the doc graph: vendored templates,
# generated mirror trees, the deliberately-broken demo, the llm-summary briefs
# (which carry a different frontmatter schema), and the tool trees.
EXCLUDED_DIR_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "templates",
    "examples",
}
EXCLUDED_PATHS = {
    Path("docs/summary"),
    Path("arch-coherence/templates"),
}
ACCESSED_VIA = re.compile(r"Accessed via \[[^\]]*\]\(([^)]+)\)")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_UNVISITED, _ACTIVE, _DONE = 0, 1, 2


def in_scope(path: Path, root: Path) -> bool:
    """A tracked Markdown doc that participates in the graph.

    CLAUDE.md is machine baseline; SKILL.md files are skill definitions with
    their own frontmatter schema. Both are exempt (a SKILL.md may still be a
    pnode *target*, it just does not declare its own edge here).
    """
    if path.name in ("CLAUDE.md", "SKILL.md"):
        return False
    rel = path.relative_to(root)
    if any(part in EXCLUDED_DIR_PARTS for part in rel.parts):
        return False
    return not any(exc in rel.parents for exc in EXCLUDED_PATHS)


def graph_edges(text: str) -> tuple[list[str] | None, list[str]]:
    """Read `pnode` (the parent list) and `see_also` from the frontmatter block.

    Parses only those two values, not the whole block, so a doc whose other
    frontmatter is not strict YAML does not break graph validation. Returns
    (pnode, see_also); pnode is None when the doc has no frontmatter `pnode`.
    """
    match = FRONTMATTER.match(text)
    if not match:
        return None, []
    block = match.group(1)

    def field(key: str) -> list[str] | None:
        line = re.search(rf"^{key}:[ \t]*(\[.*\])[ \t]*$", block, re.MULTILINE)
        if not line:
            return None
        value = yaml.safe_load(line.group(1))
        return [str(v) for v in value] if isinstance(value, list) else None

    return field("pnode"), field("see_also") or []


def resolve(doc: Path, ref: str, root: Path) -> Path | None:
    """Resolve a pnode/link ref (relative to the doc's directory) to a repo path.

    None when the ref escapes the repository root (an invalid edge).
    """
    try:
        return (doc.parent / ref).resolve().relative_to(root.resolve())
    except ValueError:
        return None


def find_root() -> Path:
    """The repository root: the nearest ancestor of cwd holding a `.git`."""
    start = Path.cwd().resolve()
    for cand in (start, *start.parents):
        if (cand / ".git").exists():
            return cand
    return start


def main() -> int:
    """Assemble the doc graph from every in-scope doc's pnode and validate it."""
    root = find_root()
    docs = sorted(p for p in root.rglob("*.md") if in_scope(p, root))
    findings: list[str] = []
    edges: dict[Path, list[Path]] = {}

    for doc in docs:
        rel = doc.relative_to(root)
        text = doc.read_text(encoding="utf-8")
        pnode, see_also = graph_edges(text)
        if pnode is None:
            findings.append(f"{rel}: missing or malformed `pnode` frontmatter")
            continue

        resolved: list[Path] = []
        for ref in pnode:
            target = resolve(doc, ref, root)
            if target is None or not (root / target).is_file():
                findings.append(f"{rel}: pnode target does not exist: {ref}")
                continue
            resolved.append(target)
        edges[rel] = resolved

        for ref in see_also:
            target = resolve(doc, ref, root)
            if target is None or not (root / target).is_file():
                findings.append(f"{rel}: see_also target does not exist: {ref}")

        via = ACCESSED_VIA.search(text)
        if via:
            declared = resolve(doc, via.group(1), root)
            if declared is not None and declared not in resolved:
                findings.append(
                    f"{rel}: 'Accessed via' points at {via.group(1)} "
                    f"but it is not in pnode {pnode}"
                )

    findings.extend(_cycle_findings(edges))

    if findings:
        print(f"check_doc_graph: {len(findings)} finding(s)")
        for line in findings:
            print(f"  {line}")
        return 1
    roots = [str(d) for d, parents in edges.items() if not parents]
    print(f"check_doc_graph: OK ({len(edges)} docs, roots: {', '.join(roots) or 'none'})")
    return 0


def _cycle_findings(edges: dict[Path, list[Path]]) -> list[str]:
    """Report each pnode cycle once, by DFS on the parent relation."""
    findings: list[str] = []
    color: dict[Path, int] = {}

    def visit(node: Path, stack: list[Path]) -> None:
        color[node] = _ACTIVE
        for parent in edges.get(node, []):
            if color.get(parent, _UNVISITED) == _ACTIVE:
                loop = stack[stack.index(parent):] + [parent]
                findings.append("pnode cycle: " + " -> ".join(str(p) for p in loop))
            elif color.get(parent, _UNVISITED) == _UNVISITED:
                visit(parent, stack + [parent])
        color[node] = _DONE

    for node in edges:
        if color.get(node, _UNVISITED) == _UNVISITED:
            visit(node, [node])
    return findings


if __name__ == "__main__":
    sys.exit(main())
