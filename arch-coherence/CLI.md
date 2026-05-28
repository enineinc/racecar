# CLI — the §3 contract

Accessed via [`README.md`](README.md). For module structure and import rules see [`PYTHON.md`](PYTHON.md) §1–§2.

A racecar Python package's CLI surface is composed of `python -m <pkg>` invocations across three patterns. Each `__main__.py` declares its surface via three contracts — `commands()`, `subcommands()`, `parser()` — that the audit script `scripts/check_cli_commands.py` enforces. The audit emits a canonical *enriched* JSON tree; downstream consumers (SessionStart hooks, doc generators, CI) summarize from that single source.

## Core principles

**Packages are the preferred CLI entries; runnable modules are also valid.** A package CLI entry is a directory with a `__main__.py`. A `.py` module with an `if __name__ == "__main__":` block is also a valid entry (`python -m fubar.foo.alpha.data`). Prefer a package once the CLI grows past one file or needs its own sub-commands; keep a module for simple single-file tools.

**Unidirectional relationship.** The dependency graph is parent → child only. Parents know about their children (by registering their names). Children never reference parents. This is the CLI-layer expression of the direction axiom in [check 2 Direction](README.md#2-direction).

**Knowledge isolation.** Each `__main__.py` only declares what it directly contains — names of its immediate sub-packages (depth + 1). It does not enumerate grandchildren.

**Side-effect isolation.** `commands()`, `subcommands()`, and `parser()` are pure data functions. No I/O, no network, no heavy processing. Printing the listing is confined to the `_print_commands()` helper (Patterns 1 and 2). Leaf CLIs (Pattern 3) delegate all output to `argparse`. No other CLI functions should call `print()` directly.

## The three contracts

Every `__main__.py` declares some subset of three module-level functions. The audit verifies them; absence-when-required is a violation.

### `commands()` — sub-package composition

```python
def commands() -> list[tuple[str, str]]:
    ...
```

A list of `(sub_package_name, description)` pairs naming the immediate `python -m <pkg>.<name>` children this node composes. Leaves return `[]`. Names are relative (no dots); the print layer constructs full paths using `__package__`. **Required on every `__main__.py`.**

### `subcommands()` — argparse subparser declarations

```python
def subcommands() -> list[tuple[str, str]]:
    ...
```

A list of `(argparse_subparser_name, description)` pairs with one entry per `add_parser(<name>, ...)` call in `main()`. Names must match the `add_parser` argument exactly. **Required on Pattern 2 + Pattern 3 nodes whose `main()` calls `argparse.add_subparsers()`.** Forbidden on Pattern 1. The audit asserts each declared entry exits 0 on `python -m <pkg> <name> --help`. Pure flag-based leaves (no subparsers) declare nothing.

### `parser()` — argparse parser factory

```python
def parser() -> argparse.ArgumentParser:
    ...
```

Constructs and returns the argparse parser **without** calling `parse_args()`. The audit imports this and walks `parser._actions` to extract the full argument surface (flags, types, defaults, choices, required-ness, mutex groups) and emit it as structured data in the audit JSON. **Required on Pattern 2 + Pattern 3 nodes that use `argparse.ArgumentParser`.** Forbidden on Pattern 1.

`main()` then becomes a thin dispatcher:

```python
def main() -> None:
    args = parser().parse_args()
    ...  # dispatch based on args
```

This factoring is the only way the audit can introspect the parser; without it, the agent reading the CLI surface gets `commands` and `subcommands` but is blind to flag-level detail.

## The three patterns

Sample tree used throughout. Directories with `__main__.py` are CLI entry points.

```
src/fubar/
  __init__.py
  __main__.py          ← CLI entry: python -m fubar   (root aggregator)
  foo/
    __init__.py
    __main__.py        ← CLI entry: python -m fubar.foo   (intermediate with own CLI)
    alpha/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.foo.alpha   (leaf CLI)
      data.py          ← utility module (imported by alpha's __main__; NOT a CLI entry)
  baz/
    __init__.py
    __main__.py        ← CLI entry: python -m fubar.baz   (intermediate, discovery only)
    alpha/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.baz.alpha
      data.py          ← utility module
    bravo/
      __init__.py
      __main__.py      ← CLI entry: python -m fubar.baz.bravo
      calculator.py    ← utility module
```

Each `__main__.py` matches exactly one pattern.

---

### Pattern 1 — Pure discovery (root or intermediate without own CLI)

Lists sub-packages. No CLI of its own. Always prints the listing and exits.

Used by `fubar/__main__.py` (root) and `fubar/baz/__main__.py` (intermediate with no own CLI).

```python
"""CLI entry: python -m fubar"""

import sys


def commands() -> list[tuple[str, str]]:
    return [
        ("foo", "Foo sub-package: [one-line description]"),
        ("baz", "Baz sub-package: [one-line description]"),
    ]


def _print_commands() -> None:
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\nAppend --help to any command for its options.")


if __name__ == "__main__":
    _print_commands()
    sys.exit(0)
```

---

### Pattern 2 — Discovery plus own CLI (intermediate that both aggregates and runs)

Lists sub-packages. Has its own argparse CLI. No-args prints the listing; args runs the CLI. Exposes `parser()`; declares `subcommands()` when the parser uses `add_subparsers()`.

Used by `fubar/foo/__main__.py`.

```python
"""CLI entry: python -m fubar.foo"""

import argparse
import sys


def commands() -> list[tuple[str, str]]:
    return [
        ("alpha", "Alpha sub-package: [one-line description]"),
    ]


def _print_commands() -> None:
    entries = [(f"python -m {__package__}.{n}", d) for n, d in commands()]
    width = max(len(p) for p, _ in entries)
    print(f"python -m {__package__}\n")
    for path, desc in entries:
        print(f"  {path.ljust(width)}   {desc}")
    print("\nAppend --help to any command for its options.")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="foo CLI")
    # argument definitions
    return p


def main() -> None:
    if not sys.argv[1:]:
        _print_commands()
        return
    args = parser().parse_args()
    run(args)


def run(args: argparse.Namespace) -> None:
    raise NotImplementedError("replace with project-specific dispatch")


if __name__ == "__main__":
    main()
```

Note: `_print_commands()` must exist in every Pattern 1 and Pattern 2 `__main__.py`. The outward-downward rule ([check 2 Direction](README.md#2-direction)) forbids inheriting it from above; there is no guaranteed leaf below to reuse it from. The function is therefore explicit at every node — a direct expression of the architecture, not a duplication to be reconciled.

---

### Pattern 3 — Leaf CLI (package with no sub-packages)

No sub-packages to discover. `commands()` returns `[]`. The `__main__.py` IS the CLI — argparse handles everything including `--help`. Exposes `parser()`; declares `subcommands()` when the parser uses `add_subparsers()`.

Used by `fubar/foo/alpha/__main__.py`, `fubar/baz/alpha/__main__.py`, `fubar/baz/bravo/__main__.py`.

```python
"""CLI entry: python -m fubar.foo.alpha"""

import argparse


def commands() -> list[tuple[str, str]]:
    return []  # leaf — no sub-packages


def subcommands() -> list[tuple[str, str]]:
    return [
        ("sync",   "fetch latest data from upstream"),
        ("status", "report local cache status"),
        ("list",   "list available datasets"),
    ]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="alpha CLI")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("sync",   help="fetch latest data from upstream")
    sub.add_parser("status", help="report local cache status")
    sub.add_parser("list",   help="list available datasets")
    return p


def main() -> None:
    args = parser().parse_args()
    run(args)


def run(args: argparse.Namespace) -> None:
    raise NotImplementedError("replace with project-specific dispatch")


if __name__ == "__main__":
    main()
```

---

## Expected CLI behaviour

```
python -m fubar
  python -m fubar.foo   Foo sub-package: [one-line description]
  python -m fubar.baz   Baz sub-package: [one-line description]

python -m fubar.foo
  python -m fubar.foo.alpha   Alpha sub-package: [one-line description]

python -m fubar.baz
  python -m fubar.baz.alpha   Alpha sub-package: [one-line description]
  python -m fubar.baz.bravo   Bravo sub-package: [one-line description]

python -m fubar.foo.alpha           # runs alpha's argparse CLI (shows help if needed)
python -m fubar.foo --flag value    # runs foo's own CLI
python -m fubar.foo.alpha.data      # runs data.py if it has `if __name__ == "__main__":`; no-op if not
```

## Audit JSON schema

`scripts/check_cli_commands.py --json <pkg>` emits the **enriched audit tree**. Every node is shaped as follows. The schema is exhaustive — every field present on every node, with `null` rather than absence for missing values (downstream summarizers strip what they don't need).

### Enriched node

```
EnrichedNode = {
  # --- audit affordances (§3 enforcement) ---
  "pkg":         str,                           # dotted package name
  "kind":        "package" | "module" | "missing",
  "pattern":     "pattern-1" | "pattern-2" | "pattern-3" | "unknown",
  "commands":    list[ [str, str] ] | null,     # raw commands() entries
  "subcommands": list[EnrichedSubcommand] | null,  # enriched per below
  "orphan":      bool,                          # registered by parent?
  "violations":  list[str],                     # messages at this node
  "children":    list[EnrichedNode],            # registered + orphan kids

  # --- agent-facing resolutions (computed once, here) ---
  "command":     str,                           # "python -m <pkg>"
  "role":        "pure-discovery"               # composes children only
               | "discovery+cli"                # composes AND own argparse
               | "leaf",                        # own argparse, no children
  "description": str | null,                    # parent's commands() blurb
                                                # (null on top-level root)
  "args":        list[Arg] | null,              # top-level parser args
                                                # (null if parser() not exposed)
}
```

| Field | Type | Notes |
|------|------|-------|
| `pkg` | str | Dotted Python package name, e.g. `fubar.foo.alpha`. |
| `kind` | enum | `"package"` for an imported package, `"module"` for a runnable `.py` file with main guard, `"missing"` when the path is in `commands()` but doesn't resolve. |
| `pattern` | enum | Raw audit code: `pattern-1` (Pattern 1 — pure discovery), `pattern-2` (Pattern 2 — discovery + own CLI), `pattern-3` (Pattern 3 — leaf), `unknown` (broken / can't classify). |
| `commands` | list of `[str, str]` | Raw output of the node's `commands()` function. `null` when the function couldn't be read. |
| `subcommands` | list of `EnrichedSubcommand` | Argparse subparsers from `subcommands()`, enriched per-entry. `null` when the function isn't declared. |
| `orphan` | bool | True when this node has a `__main__.py` but its parent's `commands()` did not register it. A §3 violation in itself. |
| `violations` | list of str | Audit messages at this node only (children carry their own). Empty list when clean. |
| `children` | list of `EnrichedNode` | Registered §3-composed children plus any orphan sub-packages discovered on disk. |
| `command` | str | The literal `python -m <pkg>` invocation. Resolved once during enrichment. |
| `role` | enum | Short label: `pure-discovery`, `discovery+cli`, `leaf`. The agent-facing translation of the raw `pattern` field. |
| `description` | str or `null` | The blurb from the parent's `commands()` entry for this child. `null` on the top-level root (no parent). |
| `args` | list of `Arg` | The top-level parser's args, extracted by walking `parser()._actions`. `null` when `parser()` isn't declared. |

### Enriched subcommand

```
EnrichedSubcommand = {
  "name":        str,            # argparse subparser name (matches add_parser arg)
  "command":     str,            # "python -m <pkg> <name>"
  "description": str,            # from subcommands() blurb
  "args":        list[Arg] | null,  # subparser-level args
                                    # (null if parser() not exposed)
}
```

### Arg

A single argparse argument. Two shapes — regular and mutex group:

```
Arg = RegularArg | OneOfGroup

RegularArg = {
  "dest":       str,                # Python variable name (action.dest)
  "flags":      list[str],          # ["--from", "-f"]; empty list for positionals
  "help":       str | null,         # action.help (omitted if SUPPRESS or None)
  "required":   bool,               # only present when True
  "choices":    list[str] | null,   # action.choices, stringified
  "default":    JSONScalar | null,  # action.default, stringified for non-scalars
  "type":       str | null,         # callable __name__ (e.g. "str", "int", "DataSource")
  "action":     str | null,         # "store_true", "store_false", "count", "append"
                                    # (omitted for default store action)
  "nargs":      str | null,         # action.nargs (when not None/0)
}

OneOfGroup = {
  "oneOf":      list[RegularArg],   # the mutex-group members
  "required":   bool,               # True iff argparse group required=True
                                    # (omit when False)
}
```

| Field | Type | Notes |
|------|------|-------|
| `dest` | str | The Python variable name argparse stores into (`action.dest`). Internal; the slim downstream form drops it. |
| `flags` | list of str | All flag spellings the user can type, e.g. `["--yes", "-y"]`. Empty list for positionals (use `dest` as the name). |
| `help` | str | The help text the author wrote. Stripped if `argparse.SUPPRESS`. |
| `required` | bool | Present-and-true when this arg is required. Omitted otherwise (false is the default). |
| `choices` | list of str | Allowed values when `add_argument(choices=...)` is set. Enum members are stringified via `str(member)`. |
| `default` | scalar | The default value when not passed. Suppressed for `None` and for `False` on store_true actions (both implicit). |
| `type` | str | Best-effort name for the type callable (`__name__` of `int`, `str`, `Path`, custom callable, or enum class). |
| `action` | str | Non-default argparse action name. `store_true` and `store_false` collapse with `type: "bool"`; `count` collapses with `type: "int"`. |
| `nargs` | str | Stringified `action.nargs` when not the default. |
| `oneOf` | list of `RegularArg` | Members of a `parser.add_mutually_exclusive_group()`. Emitted at the position of the group's first member in argparse declaration order. |
| `required` (on `oneOf`) | bool | `True` iff the group was constructed with `required=True` (exactly one must be passed). Omitted when the group is optional (at most one). |

Group-level `default` on `oneOf` is intentionally not supported — argparse mutex groups don't have a member-level default, and "if nothing is passed, treat as X" is better expressed by making the group non-required and setting the relevant member's `default`.

### Convention: mutex groups borrow JSON-Schema `oneOf`

The `oneOf` key is borrowed directly from JSON Schema (and OpenAPI by extension): "value matches exactly one of these schemas." Paired with `required`, it covers both argparse cases:

- `{"oneOf": [...], "required": true}` — exactly one (matches JSON Schema's `oneOf` exactly).
- `{"oneOf": [...]}` — at most one (a benign extension; argparse `required=False` mutex).

The wrapper appears inline in `args` at the position of the group's first member — the agent reads it as a structural sibling of other args, in declaration order, with no separate registry to cross-reference.

### Slim downstream form

The SessionStart hook (`hooks/session_discover_cli.py`) consumes the enriched tree and emits a *slim* form into the agent's context. The slim form drops audit affordances, suppresses empty/false/default fields, collapses single-flag lists, and merges `children` + enriched `subcommands` into one unified `subcommands` list (the agent doesn't distinguish `python -m` composition from argparse subparsers at the surface):

```
SlimNode = {
  "command":     str,                       # always
  "pattern":     "pure-discovery"           # always (from enriched `role`)
               | "discovery+cli"
               | "leaf",
  "description": str,                       # when present (omitted on root)
  "orphan":      true,                      # only when true
  "violations":  list[str],                 # only when non-empty
  "args":        list[SlimArg],             # only when non-empty
  "subcommands": list[SlimSubEntry],        # only when non-empty
}

SlimSubEntry = {
  "command":     str,                       # the python -m invocation
  "description": str,                       # the curated blurb
  "args":        list[SlimArg],             # subparser args, only when non-empty
}
# (§3 children recurse as SlimNode entries in the same list.)

SlimArg = SlimRegular | SlimOneOf

SlimRegular = {
  "flag":        str,                       # when exactly one flag
  "flags":       list[str],                 # when multiple flags (--yes/-y)
  "positional":  str,                       # when no flags (use dest name)
  "help":        str,                       # when present
  "required":    true,                      # only when true
  "choices":     list[str],                 # only when present
  "default":     JSONScalar,                # only when non-trivial
                                            # (false for store_true dropped)
  "type":        str,                       # only when not "str" / "bool"
  "action":      str,                       # only for non-default actions
                                            # (store_true collapsed entirely)
  "nargs":       str,                       # only when present
}

SlimOneOf = {
  "oneOf":       list[SlimRegular],
  "required":    true,                      # only when true
}
```

### Example

Smallest representative tree: root `fubar` (Pattern 1) composing one leaf `fubar.alpha` (Pattern 3 with a mutex group `--data`/`--derived` + a required `--from`).

Enriched (`scripts/check_cli_commands.py --json fubar`):

```json
{
  "pkg": "fubar",
  "kind": "package",
  "pattern": "pattern-1",
  "commands": [["alpha", "Alpha sub-package: [one-line description]"]],
  "subcommands": null,
  "orphan": false,
  "violations": [],
  "args": null,
  "command": "python -m fubar",
  "role": "pure-discovery",
  "description": null,
  "children": [
    {
      "pkg": "fubar.alpha",
      "kind": "package",
      "pattern": "pattern-3",
      "commands": [],
      "subcommands": [
        {
          "name": "report",
          "command": "python -m fubar.alpha report",
          "description": "produce the canonical report",
          "args": [
            {
              "oneOf": [
                {"dest": "data",    "flags": ["--data"],    "help": "sourced data view"},
                {"dest": "derived", "flags": ["--derived"], "help": "derived data view"}
              ]
            },
            {
              "dest": "date_from", "flags": ["--from"],
              "help": "start date (YYYY-MM-DD)", "required": true, "type": "str"
            }
          ]
        }
      ],
      "orphan": false,
      "violations": [],
      "args": [],
      "command": "python -m fubar.alpha",
      "role": "leaf",
      "description": "Alpha sub-package: [one-line description]",
      "children": []
    }
  ]
}
```

Slim (what the SessionStart hook injects):

```json
{
  "command": "python -m fubar",
  "pattern": "pure-discovery",
  "subcommands": [
    {
      "command": "python -m fubar.alpha",
      "pattern": "leaf",
      "description": "Alpha sub-package: [one-line description]",
      "subcommands": [
        {
          "command": "python -m fubar.alpha report",
          "description": "produce the canonical report",
          "args": [
            {"oneOf": [
              {"flag": "--data",    "help": "sourced data view"},
              {"flag": "--derived", "help": "derived data view"}
            ]},
            {"flag": "--from", "help": "start date (YYYY-MM-DD)", "required": true}
          ]
        }
      ]
    }
  ]
}
```

## Rules

| Rule | Rationale |
|------|-----------|
| Packages are the preferred CLI entry; runnable `.py` modules with `if __name__ == "__main__":` are also valid | Packages scale to sub-commands; modules stay simple for single-file tools |
| No inward references in `__main__.py` — no `from ..` | Prevents upward references that would couple children to parents (see [check 2 Direction](README.md#2-direction)) and mask circular deps (see [check 1 Acyclicity](README.md#1-acyclicity-root-axiom)) |
| `commands()` returns relative names, not full paths | `__package__` constructs the path; names stay readable |
| `commands()` lists immediate children — sub-packages or runnable modules | Either is a valid invocation target via `python -m {parent}.{child}` |
| Parents register child names explicitly — no dynamic discovery | Explicit registration; no invisible capabilities |
| Depth + 1 only — never enumerate grandchildren | Each layer owns its own listing |
| Leaves return `commands() == []` | Keeps the contract uniform across all `__main__.py` files |
| Packages with their own CLI run it when args are given | No-args = listing; args = action |
| Printing confined to `_print_commands()` (Patterns 1 & 2) or `argparse` (Pattern 3) | Side-effect isolation; keeps listing logic testable without capturing stdout from arbitrary call sites |
| Nodes using `add_subparsers()` MUST declare `subcommands()`; pure flag-based leaves declare nothing | Argparse subparsers are a structural surface the agent navigates; making them implicit leaves the surface impoverished |
| `subcommands()` is Pattern 2 + Pattern 3 only | Argparse subparsers exist only on nodes that own a parser; Pattern 1 has none to declare |
| `subcommands()` names match `add_parser(<name>, ...)` exactly; each must be invocable via `python -m <pkg> <name> --help` (exit 0) | Same audit rigor as `commands()` — no orphans, no phantoms, no name drift |
| Nodes that construct `argparse.ArgumentParser(...)` MUST expose `parser()` returning the parser without calling `parse_args()` | Without the factory the audit can't introspect the argument surface; the agent reads only command/description and is blind to flags/types/defaults |
| `parser()` is Pattern 2 + Pattern 3 only | Pattern 1 has no `main()` and constructs no parser |
| Mutex groups MUST use `parser.add_mutually_exclusive_group(required=...)` rather than runtime checks | Argparse enforces the constraint at parse time and exposes it via `_mutually_exclusive_groups`; the audit surfaces it as JSON-Schema `oneOf` |
| Machine-enforced via AST: `argparse.ArgumentParser(...)` without `parser()`, and `add_subparsers(...)` without matching `subcommands()`, are both silent-omission violations | The audit walks the source AST in addition to running the contracts; gaps caught at audit time, not by hoping authors remember |

## Registration

New sub-packages must be manually added to the parent's `commands()` list. This is intentional. Dynamic discovery hides what the system can do. Explicit registration makes capabilities visible and auditable.

When a new `__main__.py` is added, update the parent's `commands()` before merging. When a new argparse subparser is added, update `subcommands()` in the same change. The registration contract is mechanized by `scripts/check_cli_commands.py`; see [PYTHON.md §4 Enforcement](PYTHON.md#4-enforcement).
