---
name: racecar-cli-docs
description: Project a repository's `python -m <pkg>…` CLI tree into a mirror of README pages under `docs/cli/**` (one page per CLI node) plus the repo README's `## CLI` block. The pages are GENERATED from the audited command tree — reusing `check_cli_commands.py`'s walk, inventing no structure — so a stale page is a build failure, not a silent lie. Offers `--write` / `--check`. Use when asked to "generate the CLI docs", "document the CLI commands", "build the docs/cli tree", "refresh the command reference", or to add per-command reference pages for a package that exposes `python -m <pkg>`.
---

# racecar-cli-docs

Give every CLI node its own reference page, derived from the one source of truth — the `__main__.py` + `commands()` + argparse tree — so the docs cannot drift from the commands. The mechanics are deterministic and live in [`arch-coherence/scripts/gen_cli_docs.py`](../arch-coherence/scripts/gen_cli_docs.py); this skill runs it and reads the result. It is a *projection*, never a second home: the generator reuses `check_cli_commands.py`'s audit ([`arch-coherence/CLI.md`](../arch-coherence/CLI.md)) and writes the tree out as prose.

This applies only to a repo that exposes a CLI surface (`src/<pkg>` with `__main__.py`). It is not a required doc — generate it where a CLI exists ([`../docs-orchestrator/ORCHESTRATION.md`](../docs-orchestrator/ORCHESTRATION.md), stage 2, the CLI-surface spine).

## Run it — from the target repo, not from racecar

The generator is a **delivered** script: it derives the repo root from its own location and writes into *that* repo's `docs/cli/`, so it must run from the adopter's own `scripts/gen_cli_docs.py`, beside the `check_cli_commands.py` it imports.

    python scripts/gen_cli_docs.py --write     # emit / refresh docs/cli/** + the README ## CLI block
    python scripts/gen_cli_docs.py --check      # exit non-zero if any page is stale or orphaned
    python scripts/gen_cli_docs.py              # dry run: print the projected page list
    python scripts/gen_cli_docs.py src/<pkg>    # point at a package (default: auto-discover)

If `scripts/gen_cli_docs.py` is not present, the repo has not synced the current racecar script set — sync it first with [`racecar-normalize`](../normalize/SKILL.md) (or `racecar-upgrade`), which delivers it alongside the checkers, then run the above.

## What it does

1. Audits the live CLI tree once (`audit_cli_tree`), discovering the root package — never hard-coded.
2. Writes one `docs/cli/**/README.md` per node, its path mirroring the module path. A **discovery** node gets its docstring lead paragraph and a linked table of subcommands; a **leaf** gets its description and its argparse **usage + options**, captured from `python -m <pkg> --help` under a pinned `COLUMNS` so the bytes are reproducible.
3. Refreshes the repo README's marker-delimited `## CLI` block from the *same* audit (`render_tree`), so it shows byte-for-byte what `make arch` prints — no second renderer to drift.
4. Removes orphaned pages (a node the tree no longer projects), prunes empty directories, and skips a broken or unregistered (§3 orphan) node rather than emitting a false page.

## After writing

Every page opens with a `pnode:` frontmatter edge, so the subtree is a doc-graph citizen: the root joins the nearest existing parent (`docs/ARCHITECTURE.md`, else `docs/README.md`, else the storefront), each child names its parent page. Close with the coherence gate — `check_doc_graph.py` and `check_docs.py` (or drive [`racecar-docs`](../docs-orchestrator/SKILL.md)) — so links resolve and the graph stays acyclic.

## Boundaries

- **Generated, never hand-edited.** Each page carries a DO-NOT-EDIT banner. Wire `--check` into CI (or a test) so a moved command that left its docs behind fails the build.
- **Content-blind by construction.** Every byte is derived from tracked source (docstrings, argparse help); the pages are exactly as content-blind as the code they mirror ([`../docs-orchestrator/CONTENT_BLINDNESS.md`](../docs-orchestrator/CONTENT_BLINDNESS.md)).
- **Idempotent.** A second `--write` with no source change is a no-op ([`../shared/PRINCIPLES.md`](../shared/PRINCIPLES.md), P-05).
- **One home for structure.** It invents no tree of its own; the command tree is `check_cli_commands.py`'s. Change the CLI, then regenerate — do not edit the pages to match.
