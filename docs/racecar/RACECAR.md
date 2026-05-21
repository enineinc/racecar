---
generator:
  name: racecar-llm-summary
  version: "0.2.0"
target:
  repo: racecar
  sha: 9c70eef
  date: 2026-05-20
bundle:
  - RACECAR.md

entities:
  - name: Lens
    case: none
    lifecycle: realized
    purpose: A review skill that loads one README in full, applies a numbered check list, and emits findings with a verdict.
    notes: "Three ship: racecar-arch-coherence, racecar-doc-coherence, racecar-eng-review."

  - name: Generator
    case: none
    lifecycle: realized
    purpose: A skill that produces an artifact (a Markdown bundle) rather than findings; structurally distinct from a Lens.
    notes: "One ships: racecar-llm-summary. This brief is its output."

  - name: Router
    case: none
    lifecycle: realized
    purpose: The umbrella resolver skill that maps a topic to the component file the agent should load.
    notes: "Loaded only when the user says 'racecar' generically or is unsure which lens applies."

  - name: Overlay
    case: none
    lifecycle: realized
    purpose: A behavioral skill that adjusts agent output discipline without adding any review checks.
    notes: "One ships: racecar-expert-mode. Installed separately via `make expert`, not by `./install`."

  - name: MechanicalCheck
    case: none
    lifecycle: realized
    purpose: A stdlib-only Python script that catches deterministic drift the model is not asked to think about.
    notes: "Five ship: check_docs, check_brief, check_upward_imports, check_cli_commands, check_string_relations."

  - name: Finding
    case: none
    lifecycle: realized
    purpose: A single review observation tagged with severity (`Blocker`/`Major`/`Minor`/`Nit`) that contributes to a verdict (`Ship`/`Revise`/`Rework`).
    notes: "Not stored on disk. Carried in model context and reproduced in model output per each lens README's Feedback format section."

  - name: PointerBlock
    case: on_disk_managed
    lifecycle: realized
    purpose: A managed region inside the user's `~/.claude/CLAUDE.md` between BEGIN/END HTML-comment markers that points an agent at this checkout.
    notes: "Two flavors: main pointer (always, by `./install`) and expert pointer (only after `make expert`). Content outside the markers is preserved verbatim on every re-write."

  - name: SkillSymlink
    case: on_disk_managed
    lifecycle: realized
    purpose: A symlink under `~/.claude/skills/` that lets Claude Code resolve a `/racecar*` slash command to a directory inside this checkout.
    notes: "Five created by `./install` (racecar, -arch-coherence, -doc-coherence, -eng-review, -llm-summary); a sixth (racecar-expert-mode) by `make expert`. Refused if a regular file or foreign symlink already occupies the target — never clobbered."

  - name: SettingsHook
    case: on_disk_managed
    lifecycle: realized
    purpose: A `hooks.*ToolUse` entry in `~/.claude/settings.json` that wires a racecar bash hook into the Claude Code permission and event pipeline.
    notes: "Two managed: PreToolUse Bash (`compound-command-allow.sh`) and PostToolUse Read (`claude_racecar_hook.sh`). Identified by command basename so a moved checkout self-heals."

  - name: VersionFile
    case: on_disk_managed
    lifecycle: realized
    purpose: A plain `major.minor.patch` text file at the repo root that tracks the framework's release line.
    notes: "Manually edited per shared/COMMITS.md; current 0.2.0."

  - name: SkillManifest
    case: content_tree
    lifecycle: realized
    purpose: A short YAML-fronted Markdown file (`SKILL.md`) that registers a slash command and points at its sibling README as the loader.
    path_pattern: "<skill>/SKILL.md"
    count: 6
    validator: "Claude Code at skill registration time"

  - name: StandardDoc
    case: content_tree
    lifecycle: realized
    purpose: A living Markdown standard — lens README, language overlay, or shared convention — read into the agent's context on demand.
    path_pattern: "<skill>/README.md, arch-coherence/{PYTHON,DJANGO}.md, eng-review/{PYTHON,DJANGO}.md, shared/*.md, expert/EXPERT.md, root README.md"
    count: "~20"
    validator: "doc-coherence/scripts/check_docs.py"

  - name: ProjectTemplate
    case: content_tree
    lifecycle: realized
    purpose: A copy-into-consumer-project baseline (`pyproject.toml`, `pre-commit-config.yaml`, `Makefile`) that ships the framework's chosen toolchain.
    path_pattern: "templates/{ruff,classic}/{pyproject.toml,pre-commit-config.yaml,Makefile}"
    count: 6
    validator: "manual diff against consumer projects"
    notes: "Two variants: ruff (recommended) and classic (black + isort + pylint)."

relationships:
  - from: Router
    to: Lens
    cardinality: "1:N"
    notes: "Root README.md (loaded by /racecar) lists topic rows pointing at each lens README."

  - from: Router
    to: Generator
    cardinality: "1:1"
    notes: "Root README.md also routes to llm-summary even though it is not a lens."

  - from: SkillManifest
    to: StandardDoc
    cardinality: "1:1"
    notes: "Each <skill>/SKILL.md points at its sibling README.md as a one-screen loader."

  - from: Lens
    to: MechanicalCheck
    cardinality: "1:N"
    notes: "arch-coherence and doc-coherence READMEs back-reference their scripts by §N; the scripts' docstrings cite the README in return."

  - from: Generator
    to: MechanicalCheck
    cardinality: "1:1"
    notes: "llm-summary/README.md owns the schema; llm-summary/scripts/check_brief.py mechanizes it."

  - from: Lens
    to: Finding
    cardinality: "1:N"
    notes: "Each lens emits zero or more findings per review; verdict is a function of the worst severity."

  - from: SkillSymlink
    to: StandardDoc
    cardinality: "1:N"
    notes: "Each symlink exposes one skill directory's docs into ~/.claude/skills/ so Claude Code can load them."

  - from: SettingsHook
    to: PointerBlock
    cardinality: "1:1"
    notes: "PostToolUse Read hook re-fires sync_claude_md.py whenever `*/racecar/README.md` is read; the pointer block then self-heals if the checkout moved."

  - from: ProjectTemplate
    to: MechanicalCheck
    cardinality: "1:N"
    notes: "Each template variant wires four of the five mechanical checks. Pre-commit hooks: check_upward_imports.py, check_docs.py, and check_string_relations.py (the last guarded by `[ -f manage.py ]` so non-Django consumers skip it). Makefile targets: check_cli_commands.py via `make arch`; check_docs.py via `make docs`; check_string_relations.py via `make arch` with the same Django guard. Only check_brief.py is not wired — it validates briefs in the consumer's docs/ tree, not source code."

  - from: Overlay
    to: PointerBlock
    cardinality: "1:1"
    notes: "racecar-expert-mode installs its own twin BEGIN/END markers as a second managed block in CLAUDE.md."

external_surface:
  cli_verbs:
    - verb: /racecar
      module: SKILL.md
      args: none
      behavior: "Load the root resolver README; route from topic to lens or generator."
    - verb: /racecar-arch-coherence
      module: arch-coherence/SKILL.md
      args: freeform prompt
      behavior: "Apply the four architectural checks (acyclicity, direction, layer integrity, depth-plus-one) plus a red-flag scan; emit findings + verdict."
    - verb: /racecar-doc-coherence
      module: doc-coherence/SKILL.md
      args: freeform prompt
      behavior: "Run check_docs.py mechanical pre-pass, then apply five prose checks (cogency, scope honesty, file naming, rule testability, one-home-per-rule)."
    - verb: /racecar-eng-review
      module: eng-review/SKILL.md
      args: freeform prompt
      behavior: "Racecar pre-pass → gstack /plan-eng-review → racecar post-pass (PYTHON.md, DJANGO.md). Findings tagged [pre]/[gstack]/[post]."
    - verb: /racecar-llm-summary
      module: llm-summary/SKILL.md
      args: "optional: subsystem list, target dir override, 'skip §3'"
      behavior: "Discovery walk + bundle write to docs/$repo/$REPO.md, validated by check_brief.py."
    - verb: /racecar-expert-mode
      module: expert/SKILL.md
      args: none
      behavior: "Adopt the expert output discipline (terse, lead with result, no preamble) for the rest of the session."
    - verb: ./install
      module: install
      args: "none; env: CLAUDE_SKILLS_PATH, CLAUDE_MD_PATH, CLAUDE_SETTINGS_PATH"
      behavior: "python3 precheck → symlink five skills under ~/.claude/skills/ → invoke sync_claude_md.py to manage the pointer block and two hooks. Idempotent; refuses to clobber foreign state."
      exit: "0 ok / 1 on conflicts or missing python3"
    - verb: make install
      module: Makefile
      args: none
      behavior: "make install-deps then ./install."
    - verb: make install-deps
      module: Makefile
      args: none
      behavior: "pip install --group dev (pulls pytest, pyyaml, black, isort, pylint)."
    - verb: make expert
      module: Makefile
      args: none
      behavior: "scripts/expert_mode.py install — symlink + CLAUDE.md pointer block for the overlay."
    - verb: make expert-uninstall
      module: Makefile
      args: none
      behavior: "Reverse make expert."
    - verb: make check
      module: Makefile
      args: none
      behavior: "Run check-docs + test + check-brief."
    - verb: make check-docs
      module: Makefile
      args: none
      behavior: "Run doc-coherence/scripts/check_docs.py against this repo."
    - verb: make check-brief
      module: Makefile
      args: none
      behavior: "Validate docs/<repo>/<REPO>.md against the llm-summary schema."
    - verb: make test
      module: Makefile
      args: none
      behavior: "pytest across arch-coherence/tests, doc-coherence/tests, llm-summary/tests, scripts/tests (currently six test modules covering check_cli_commands, check_string_relations, check_upward_imports, check_docs, check_brief, sync_claude_md)."

  library_exports:
    - name: check_docs
      module: doc-coherence/scripts/check_docs.py
      signature: "python3 check_docs.py"
      behavior: "Walk up to .git; (1) check intra-repo Markdown links/anchors; (2) check `FILENAME.md §N` citations across .py/.yaml/.toml/Makefile; (3) check vocabulary identity — every `<Class> values are literal: **<literal>**` line agrees across all markdown. Honors [tool.pylint.MASTER].ignore-paths from the consumer's pyproject.toml."
    - name: check_brief
      module: llm-summary/scripts/check_brief.py
      signature: "python3 check_brief.py [<bundle-path>]"
      behavior: "Validate frontmatter schema, required §N.M headings, ## Confidence markers, and bundle membership for a racecar-llm-summary brief."
    - name: check_upward_imports
      module: arch-coherence/scripts/check_upward_imports.py
      signature: "python3 check_upward_imports.py <file> [<file>...]"
      behavior: "Reject `from <root> import …` in non-__init__/__main__ files. <root> from [tool.importlinter].root_package."
    - name: check_cli_commands
      module: arch-coherence/scripts/check_cli_commands.py
      signature: "python3 check_cli_commands.py <root.pkg> [...] [--json]"
      behavior: "Walk a Python CLI tree; verify the `commands() -> list[tuple[str,str]]` contract, classify as Pattern 1/2/3, subprocess each node to check listing + --help, scan for orphan __main__.py / main-guard modules."
    - name: check_string_relations
      module: arch-coherence/scripts/check_string_relations.py
      signature: "python3 check_string_relations.py"
      behavior: "AST-walk every .py under each [tool.importlinter].root_packages dir; flag ORM string-target FKs/O2O/M2M; classify LIVE vs NOOP against INSTALLED_APPS; annotate UPWARD DAG cross by layer."
---

# Racecar — Knowledge Package

A Claude Code skills bundle that ships an opinionated Python/Django code-review framework as five installable slash commands plus an optional output-mode overlay. Cloning this repo and running `./install` symlinks its directories into `~/.claude/skills/`, writes a managed pointer block into `~/.claude/CLAUDE.md`, and registers two Claude Code hooks in `~/.claude/settings.json`. After that, the slash commands resolve and the agent reads the standards from this checkout on demand.

There is no service, no database, no daemon. Every primitive is a Markdown document loaded into a model's context plus a small set of stdlib Python scripts that mechanize the deterministic checks. The relational sections of this brief — entities, relationships, surface — live in the frontmatter above; the narrative lives below.

## §1. Map

### §1.1 Purpose

Racecar enforces — by review, not by gate — a consistent architectural and engineering discipline for a single owner's Python/Django projects. The framework asserts that **tooling enables design and confirms correctness; responsibility stays with the owner** (`shared/OWNERSHIP.md`). Local checks (`pre-commit`, `lint-imports`, `make check`) replace CI gating because gates decide without the owner in the loop.

Audience is the repo owner. Consumers are Claude Code agents acting under that owner's authority via slash commands. The agent's reading style is set by `shared/PERSONA.md` (precise, no preamble, lead with counterargument) and tightened further by the optional `racecar-expert-mode` overlay.

User-facing primitives:

- **Lens** — a review skill: load one README in full, apply a numbered check list, emit `Finding`s tagged `Blocker / Major / Minor / Nit` with a `Ship / Revise / Rework` verdict. Three lenses ship: `racecar-arch-coherence`, `racecar-doc-coherence`, `racecar-eng-review`.
- **Generator** — a skill that produces an artifact, not a review. One ships: `racecar-llm-summary` (this document is its output).
- **Router** — the umbrella `racecar` skill: a topic-to-component-file resolver. Loaded only when the user says "racecar" generically or is unsure which lens applies.
- **Overlay** — a behavioral skill that adjusts output style without adding checks. One ships: `racecar-expert-mode` (terse, lead-with-result delivery), installed separately via `make expert`.
- **MechanicalCheck** — deterministic Python scripts the lenses delegate to: `check_docs.py`, `check_brief.py`, `check_upward_imports.py`, `check_cli_commands.py`, `check_string_relations.py`.

### §1.2 Modules

| Module | Purpose |
| --- | --- |
| `arch-coherence/` | Architectural-coherence lens: four checks (acyclicity, direction, layer integrity, depth-plus-one) + Python/Django specifics + three enforcement scripts (`check_upward_imports`, `check_cli_commands`, `check_string_relations`), each with its own test module. |
| `doc-coherence/` | Documentation-coherence lens: update protocol + review lens + mechanical pre-pass for link / anchor / §N drift. |
| `eng-review/` | Engineering-review wrapper: racecar pre-pass → gstack `/plan-eng-review` → racecar post-pass. |
| `llm-summary/` | This generator's spec + the `check_brief.py` validator. |
| `expert/` | Optional output-mode overlay: terse, high-density expert delivery. |
| `shared/` | Cross-cutting docs loaded on demand: `OPERATIONAL`, `OWNERSHIP`, `VOICE`, `PERSONA`, `GLOSSARY`, `VOCABULARY` (severity/verdict literals), `COMMITS`, `TODO_FORMAT`. |
| `scripts/` | Installer-internal tools: `sync_claude_md.py`, `expert_mode.py`, `sync_md_to_obsidian.py`. |
| `hooks/` | Bash hooks wired into `~/.claude/settings.json`: `compound-command-allow.sh` (PreToolUse Bash), `claude_racecar_hook.sh` (PostToolUse Read). |
| `templates/` | Copy-into-project starter files in `ruff/` and `classic/` variants. |
| `docs/` | Generated briefs from this skill, including `docs/racecar/RACECAR.md` (this file). |
| (root) | `README.md` (resolver), `SKILL.md` (router), `install`, `Makefile`, `pyproject.toml`, `VERSION`, `LICENSE`. |

### §1.3 Vendors

Pure stdlib at runtime in the shipped scripts. Dev-only dependencies declared in `pyproject.toml` under `[dependency-groups].dev`: `pytest` (test runner), `pyyaml>=6.0` (hard requirement of `check_brief.py`), `black` / `isort` / `pylint` (classic-template tooling; unused by racecar's own check surface). System dependencies: `python3 ≥ 3.11` for `tomllib` (hard, stdlib only), `jq` (hard for the Bash hook; the Read hook falls back to `sed` if absent), `make` (human surface).

No paid SaaS, no cloud platforms. One sibling skill bundle is referenced by name: **gstack**, a separate Claude Code skill bundle whose `/plan-eng-review` skill `eng-review/README.md` delegates phase 2 to. If gstack is absent the wrapper degrades to pre-pass plus post-pass; the README states the degradation explicitly.

## §2. Implementation

### §2.1 Runtime

Two runtimes share this repo, plus a quasi-runtime that executes in target projects.

1. **Skill bundle (primary).** A set of Markdown documents loaded into a Claude Code agent's context window when the corresponding slash command fires. Entry points are six `SKILL.md` files — Claude Code reads YAML frontmatter (`name`, `description`) to register `/racecar`, `/racecar-arch-coherence`, `/racecar-doc-coherence`, `/racecar-eng-review`, `/racecar-llm-summary`, and (after `make expert`) `/racecar-expert-mode`. The skill body is a one-screen pointer at the relevant `README.md`. The model — not the bundle — does the work.

2. **CLI bootstrap (secondary).** A bash entry point (`install`) plus three stdlib Python scripts under `scripts/` (`sync_claude_md.py`, `expert_mode.py`, `sync_md_to_obsidian.py`) that mutate `~/.claude/` state. `make` is the human surface; `./install` is the bash surface. Both end in `scripts/sync_claude_md.py`.

3. **Mechanical pre-pass (quasi-runtime).** The five scripts under `doc-coherence/scripts/`, `arch-coherence/scripts/`, and `llm-summary/scripts/` run inside the *target* project being reviewed (or, for `check_brief.py`, against any repo with a brief at `docs/<repo>/<REPO>.md`), not inside racecar's own tree. They discover the target via `.git` walk-up and read its `pyproject.toml`.

| Runtime | Entry point | Invocation | State location |
| --- | --- | --- | --- |
| Skill: router | `SKILL.md` (root) | `/racecar` | none |
| Skill: arch lens | `arch-coherence/SKILL.md` | `/racecar-arch-coherence` | none |
| Skill: doc lens | `doc-coherence/SKILL.md` | `/racecar-doc-coherence` | none |
| Skill: eng wrapper | `eng-review/SKILL.md` | `/racecar-eng-review` | delegates to gstack |
| Skill: generator | `llm-summary/SKILL.md` | `/racecar-llm-summary` | writes `docs/$repo/$REPO.md` in target repo |
| Skill: expert overlay | `expert/SKILL.md` | `/racecar-expert-mode` | session-scoped output behavior |
| Installer | `install` (bash) | `./install` | `~/.claude/skills/`, `~/.claude/CLAUDE.md`, `~/.claude/settings.json` |
| Mechanical pre-pass | `*/scripts/check_*.py` | `make check*` here, or pre-commit / Makefile in target | reads target repo |
| Hook: PreToolUse Bash | `hooks/compound-command-allow.sh` | Claude Code, on every Bash | reads three settings files |
| Hook: PostToolUse Read | `hooks/claude_racecar_hook.sh` | Claude Code, on every Read | re-fires `sync_claude_md.py` on match |

### §2.2 Entities

See frontmatter `entities` for the class-level enumeration. This section is the narrative gloss.

The system has **no database, no ORM, no `INSTALLED_APPS`** in its own source. The classes split into three flavors.

- **Behavioral primitives** (`case: none`). `Lens`, `Generator`, `Router`, `Overlay`, `MechanicalCheck`, and `Finding` are not stored as files; they are the conceptual vocabulary the framework asserts. A `Lens` is a particular shape of skill (load README, apply checks, emit findings); `Generator` is a contrasting shape (produce an artifact); `Finding` is the unit of lens output. The on-disk artifacts realize these classes — each lens skill *is a* `Lens`.

- **Managed on-disk state** (`case: on_disk_managed`). `PointerBlock`, `SkillSymlink`, `SettingsHook`, `VersionFile`. Everything `./install` and `make expert` write or rewrite. The `PointerBlock` and `SettingsHook` are unusual because they live *inside* files the racecar installer does not own — `~/.claude/CLAUDE.md` and `~/.claude/settings.json` — and must coexist with arbitrary other content. The byte-exact BEGIN/END HTML-comment markers and the basename-identity rule on hooks are what make that coexistence safe.

- **Content trees** (`case: content_tree`). `SkillManifest` (six `SKILL.md` files), `StandardDoc` (the Markdown standards corpus: lens READMEs + PYTHON.md/DJANGO.md overlays + shared/* + expert/EXPERT.md + root README.md), `ProjectTemplate` (six files under `templates/{ruff,classic}/`). These are the framework's content; agents read them as standards.

### §2.3 Relationships

There are no foreign keys — there is no relational store. The DAG above the frontmatter is logical: skill-manifest → README; router → lens (and → generator); lens → mechanical-check (with bidirectional `§N` and docstring citations); installer-script → managed-state; project-template → mechanical-check (via the consumer's `.pre-commit-config.yaml` and `Makefile`).

The implicit graph between installer scripts, hooks, and consumer artifacts is a star centered on `RACECAR_ROOT`:

```
                            RACECAR_ROOT (git checkout)
                                    |
        +---------------------------+-----------------------------+
        |                           |                             |
    install (bash)         scripts/sync_claude_md.py      scripts/expert_mode.py
        |                           |                             |
        v                           v                             v
~/.claude/skills/{racecar,    ~/.claude/CLAUDE.md          ~/.claude/skills/
 racecar-arch-coherence,        (main pointer block)        racecar-expert-mode
 racecar-doc-coherence,       ~/.claude/settings.json       ~/.claude/CLAUDE.md
 racecar-eng-review,            (two hook entries)           (expert pointer block)
 racecar-llm-summary}                  ^
                                       |
                                       |  re-fires on PostToolUse Read
                                       |
                       hooks/claude_racecar_hook.sh
```

Inside the markdown corpus, root `README.md` fans 1→N to each lens README plus 1→1 to `llm-summary/README.md`; each `SKILL.md` points 1→1 to its sibling `README.md`; `arch-coherence/PYTHON.md`, `doc-coherence/README.md`, and `llm-summary/README.md` each pair bidirectionally with their respective scripts via `§N` backrefs and `__doc__` citations.

### §2.4 External surface

See frontmatter `external_surface` for the full enumeration. Two surface entries warrant body detail because they encode load-bearing behavior the frontmatter cannot convey in one line.

#### §2.4.1 `./install`

Bash, idempotent. Reads three env vars (`CLAUDE_SKILLS_PATH`, `CLAUDE_MD_PATH`, `CLAUDE_SETTINGS_PATH`) with `~/.claude/` defaults. On a fresh clone, the sequence is: `python3` precheck (`install:19-33` prints an OS-specific install hint and exits 1 if missing) → for each of five `(skill-name, dir)` pairs, link `~/.claude/skills/<name>` → `<dir>` (refuse on conflict) → invoke `scripts/sync_claude_md.py` to write the pointer block and upsert the two hooks. A symlink already at the right target is left alone; one pointing elsewhere or a regular file at the path is refused and counted as a conflict (`exit 1`). See `install` and `scripts/sync_claude_md.py` for the symmetry between the bash phase (filesystem primitives) and the Python phase (structured rewriting of CLAUDE.md and settings.json).

#### §2.4.2 PostToolUse Read self-heal

`hooks/claude_racecar_hook.sh` receives PostToolUse JSON on stdin and case-globs `*/racecar/README.md` against `.tool_input.file_path`. On match, it re-fires `sync_claude_md.py` with output silenced. The hook **always exits 0** so a malformed payload never blocks the Read. This is the mechanism by which the pointer block and the absolute paths inside the two hook entries self-heal whenever the checkout moves. See `hooks/claude_racecar_hook.sh:13-32`.

Short slash commands, `make` targets, and mechanical pre-pass scripts are fully captured in frontmatter and need no body gloss.

### §2.5 Internal contracts

Cross-module contracts that are not user-callable:

- **Severity vocabulary `Blocker / Major / Minor / Nit`** → canonical home `shared/VOCABULARY.md`; repeated inline in each lens README's `Feedback format` section so a reviewer never has to follow a link. Drift between sibling READMEs is mechanically caught by the vocabulary-identity check in `doc-coherence/scripts/check_docs.py`, which scans for `<Class> values are literal: **<literal>**` lines and asserts a single literal per class across all markdown.
- **Verdict vocabulary `Ship / Revise / Rework`** → same shape as severity; same mechanical identity check.
- **`commands() -> list[tuple[str, str]]`** → produced by `arch-coherence/PYTHON.md §3`; consumed by every `__main__.py` in a consumer project and by `arch-coherence/scripts/check_cli_commands.py`. Direct-child `(name, description)` pairs, no dots in names. Three patterns (1 pure discovery, 2 discovery + own CLI, 3 leaf) are mechanized in `_classify` and `_make_node`.
- **Pointer-block markers** → produced by `scripts/sync_claude_md.py` (main) and `scripts/expert_mode.py` (overlay); consumed by the same scripts' `replace_or_append` and `install_block` / `uninstall_block`. Byte-exact partition of `~/.claude/CLAUDE.md` on `<!-- BEGIN racecar pointer (managed) -->` / `<!-- END racecar pointer (managed) -->` and the parallel `racecar-expert-mode` pair.
- **Claude Code hook JSON** → produced by the Claude Code harness; consumed by both racecar bash hooks. Stdin carries `{"tool_input": {...}, "cwd": ...}`; PreToolUse may write `{"hookSpecificOutput": {"hookEventName":"PreToolUse","permissionDecision":"allow",…}}` on stdout. Both hooks always exit 0 — racecar never denies, only auto-allows or falls through.
- **`[tool.importlinter].root_package`** → produced by the consumer's `pyproject.toml`; consumed by `arch-coherence/scripts/check_upward_imports.py`. Single string. Missing → script exits 2.
- **`[tool.importlinter].root_packages`** → produced by the consumer's `pyproject.toml`; consumed by `arch-coherence/scripts/check_string_relations.py`. `list[str]`. Missing → exit 2.
- **`[tool.importlinter].contracts`** (`type='layers'`) → produced by consumer; consumed by `import-linter` (external) and by `check_string_relations.py` for UPWARD-DAG-cross annotation. Each layer row may be `"A | B"` for independent peers.
- **`[tool.pylint.MASTER].ignore-paths`** → produced by consumer; consumed by `doc-coherence/scripts/check_docs.py`. `list[regex]`. Absent → empty tuple (no exclusions).
- **`STRING_RELATIONS_INSTALLED_APPS`** → produced by CI/test environment; consumed by `check_string_relations.py` as an override for the otherwise-mandatory `python manage.py shell` boot.
- **`racecar-llm-summary` output contract** → produced by `llm-summary/README.md` (`## Frontmatter (YAML)` + `## Output contract`); consumed by this brief, by downstream LLMs reading the bundle, and by `llm-summary/scripts/check_brief.py`. Schema drift surfaces as `check_brief.py` exit 1.

### §2.6 Configuration

Racecar has no production / dev split — there is no deployed instance. Every knob is evaluated on the consumer machine.

- `CLAUDE_SKILLS_PATH` — where `./install` writes skill symlinks. Default `~/.claude/skills`.
- `CLAUDE_MD_PATH` — which `CLAUDE.md` the pointer block is written into. Default `~/.claude/CLAUDE.md`.
- `CLAUDE_SETTINGS_PATH` — which `settings.json` receives the two hook entries. Default `~/.claude/settings.json`.
- `STRING_RELATIONS_INSTALLED_APPS` — comma-separated app labels; overrides Django app discovery in `check_string_relations.py`. Test / CI mode; bypasses the `manage.py shell` invocation.
- `OBSIDIAN_SYNC_ROOT` — destination root for `scripts/sync_md_to_obsidian.py`. Not wired into the Makefile. CLI flag `--dest` > env var > `dest_root` in `~/.config/obsidian-sync.toml`. No default — the script refuses to guess.
- `--claude-md` / `--target`, `--settings`, `--dry-run` — `sync_claude_md.py` CLI flags. CLI flag > env var > default.
- `VENV` — `Makefile` auto-detect (`.venv`, `venv`, `../venv`); first that exists is prepended to `PATH`.
- `PKG` — consumer-project Makefile variable (default `src`); scope for the `make arch` target in the templates.
- `[tool.importlinter].root_package` / `.root_packages` / `.contracts` — consumer-project TOML; see §2.5.
- `[tool.pylint.MASTER].ignore-paths` — consumer-project TOML; see §2.5.

No secrets. No environment-variant rows because there is no environment split.

### §2.7 Flows

1. **Fresh install (`./install`).** python3 precheck; for each of five `(skill-name, dir)` pairs, link `~/.claude/skills/<name>` → `<dir>` (refuse on conflict); invoke `scripts/sync_claude_md.py`, which renders the pointer block, partitions `~/.claude/CLAUDE.md` on BEGIN/END markers, and upserts the two hooks into `~/.claude/settings.json` by command basename. Idempotent. Exit 0 if no conflicts; 1 otherwise. Implementation: `install` and `scripts/sync_claude_md.py` (`render_block`, `replace_or_append`, `upsert_hook`, `sync_settings`).

2. **Pointer self-heal (PostToolUse Read hook).** Claude Code reads any file ending in `racecar/README.md` → `hooks/claude_racecar_hook.sh` extracts `.tool_input.file_path` (`jq` if present, else `sed`) → case-globs the path → re-fires `sync_claude_md.py` silently. Hook always exits 0. Implementation: `hooks/claude_racecar_hook.sh`.

3. **Compound-bash autoallow (PreToolUse hook).** Claude Code is about to run a Bash tool call. `hooks/compound-command-allow.sh` reads three settings files (`~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`), pulls `Bash(<prefix>:*)` allow/disallow patterns, splits the compound on unquoted `&&`, `||`, `;`, `|` using an embedded Python quote-respecting parser, then emits a JSON `permissionDecision: allow` only if every subcommand matches an allow prefix and none matches a disallow. Otherwise no output, exit 0 (falls through to the normal permission prompt — never a deny). Implementation: `hooks/compound-command-allow.sh`.

4. **Doc pre-pass (`check_docs.py`).** Walk up from CWD to `.git`; read `[tool.pylint.MASTER].ignore-paths` from the consumer's `pyproject.toml`; for each `*.md` check intra-repo links and `#anchor` targets (GitHub-style slugs); for each `.py`/`.yaml`/`.toml`/`Makefile` check `FILENAME.md §N` citations against the target's `## N.` heading set. Exit 0 clean / 1 drift. Implementation: `doc-coherence/scripts/check_docs.py`.

5. **Upward-import check (`check_upward_imports.py`).** Pre-commit feeds file args; the script reads `[tool.importlinter].root_package` and rejects `from <root> import …` in any file whose basename is not `__init__.py` or `__main__.py`. Exit 0/1; 2 on missing TOML key. Implementation: `arch-coherence/scripts/check_upward_imports.py`.

6. **CLI-tree audit (`check_cli_commands.py`).** Walk a package tree from argv-supplied dotted root or filesystem path; at each node, import `<pkg>.__main__`, verify the `commands()` contract, classify as Pattern 1 / 2 / 3, shell out `python -m <pkg>` and `python -m <pkg> --help` and parse the listing back, recurse into registered children, scan the filesystem for orphans (unregistered direct-child `__main__.py` or `.py` with a main guard). `--json` emits the per-node dict. Implementation: `arch-coherence/scripts/check_cli_commands.py` (`audit_cli_tree`, `_audit_package`, `_classify`).

7. **Cross-module string-relation check (`check_string_relations.py`).** Read `[tool.importlinter].root_packages`; obtain `INSTALLED_APPS` via `python manage.py shell` (or `STRING_RELATIONS_INSTALLED_APPS` env override); AST-walk every `.py` under each root (skipping `migrations`); flag `ForeignKey`/`OneToOneField`/`ManyToManyField` calls whose first positional or `to=` is a `Constant[str]`. Classify LIVE (target file's app in `INSTALLED_APPS`) vs NOOP (dead code, file's app absent). Annotate by DAG layer from `[tool.importlinter].contracts` and flag `UPWARD DAG cross` where applicable. Self-references and same-file forward strings are exempt; `settings.AUTH_USER_MODEL` is exempt because it is an attribute access, not a string. Implementation: `arch-coherence/scripts/check_string_relations.py`.

8. **Brief generation (`/racecar-llm-summary`).** Read `llm-summary/README.md` in full → run the discovery walk keyed to each output section → draft the markdown body → derive the YAML frontmatter from the body → write `docs/$repo/$REPO.md` → end with `## Confidence`. Validate with `python3 llm-summary/scripts/check_brief.py`. This brief is the literal artifact of Flow 8 against this repo.

### §2.8 Seams

Plugin / extension surfaces:

- **Skill registration.** Add `<name>/SKILL.md` with `name:` and `description:` frontmatter, add a row to `install`'s symlink loop so `./install` creates the link, add a row to the root resolver `README.md`. The pointer block rendered by `scripts/sync_claude_md.py:render_block` is intentionally generic (points at `README.md` + `shared/OPERATIONAL.md`) and does not enumerate skills, so adding one does not require editing `render_block`. Recent example: the `racecar-llm-summary` skill (commit `eac2a8c` and follow-ups; see `install:77-88` for the symlink loop).
- **Hook contract.** Append another `upsert_hook(settings, event, matcher, command, basename)` call in `scripts/sync_claude_md.py:sync_settings`. Hooks are identified by command basename so a moved checkout self-heals. Recent example: the PreToolUse Bash hook added alongside the PostToolUse Read hook (commit `3368339`).
- **Mechanical check.** A new Python script in `arch-coherence/scripts/`, `doc-coherence/scripts/`, or `llm-summary/scripts/`; a row in the relevant template `pre-commit-config.yaml` under `repo: local` (or, for full-tree audits, a Makefile target); and a doc section that the script's docstring backrefs by `§N`. Recent example: the scope-honesty close-out (`9c70eef`) wired `check_string_relations.py` and `check_docs.py` into both ruff and classic templates, with the Django-only check guarded by `[ -f manage.py ]` so non-Django consumers fall through silently.
- **Output overlay.** A directory with `SKILL.md` + content `.md`, a manage-block script under `scripts/` using twin `<!-- BEGIN ... (managed) -->` / `<!-- END ... (managed) -->` markers, and a `make` target pair (install / uninstall). Recent example: `racecar-expert-mode` (commit `6ce3338`; manage script `scripts/expert_mode.py`).

### §2.9 Design decisions

- **No CI gate; local enforcement only.** `shared/OWNERSHIP.md`: enforcement is `pre-commit` / `lint-imports` / `make check`, not required-status-check workflows. Tooling confirms; the owner ratifies.
- **The generator ships alongside the lenses.** Root `README.md` lists `llm-summary` as a topic row even though its `SKILL.md` says "Not a review lens; a generator." Rejected alternative: separate repo. Motivation: shared voice (`shared/VOICE.md`), shared operational discipline (`shared/OPERATIONAL.md`), shared installer.
- **Identify hooks by command basename, not exact path.** `scripts/sync_claude_md.py:upsert_hook` matches via `cmd.rstrip().rstrip('"').rstrip("'").endswith(basename)`. Motivation: when the checkout moves, the absolute path changes; basename match lets the re-run rewrite the stale path without duplicating the hook.
- **Idempotent install that refuses to clobber.** Both `install` and `scripts/expert_mode.py` refuse to overwrite a foreign symlink or a regular file at a target path. Rejected: a `--force` flag. Motivation: a foreign symlink is evidence of another tool's state — racecar should not silently win the conflict.
- **`make expert` separate from `./install`.** Commit `6ce3338`. The overlay changes output discipline session-wide; opt-in is the safe default.
- **`shared/OPERATIONAL.md` rule ordering: independent → dependent.** Earlier rules apply before later rules can; matches how the reviewer reads top-down.
- **`doc-coherence/scripts/check_docs.py` is repo-agnostic.** Discovers via `.git` walk-up; honors consumer-side `[tool.pylint.MASTER].ignore-paths` (commit `aed81bc`). The script ships as skill content and runs against whichever repo the agent is reviewing.
- **Conventional Commits + tabular VERSION rule.** `shared/COMMITS.md`. Fixed grammar means commits can be filtered; VERSION delta is `+0.0.1` / `+0.1.0` / `+1.0.0` and any other delta is invalid.
- **YAML frontmatter as the relational store for the brief.** `llm-summary/README.md ## Frontmatter (YAML)`. Rejected: everything in body tables. Motivation: a downstream LLM can query frontmatter deterministically (parse once, ask many) where parsing tables-from-Markdown is fragile.
- **Class-level entities only, no field tables.** Recent pivot in `llm-summary/README.md`. The brief is a single-file mobile-shareable knowledge package, not a reconstruction-grade specification. Field tables blew the line budget and were rarely the interesting query.

### §2.10 Operational

- **Install (fresh clone).** Requires `python3 ≥ 3.11` on `PATH` (stdlib only) and a writable `~/.claude/`. Run `./install`. Idempotent. Override targets via `CLAUDE_SKILLS_PATH` / `CLAUDE_MD_PATH` / `CLAUDE_SETTINGS_PATH`.
- **Bootstrap check.** Verify `~/.claude/settings.json` `hooks.PostToolUse` contains an entry whose command ends with `hooks/claude_racecar_hook.sh`. Root `README.md` documents this as the "Bootstrap check."
- **Move the checkout.** Re-run `./install`. The PostToolUse Read hook also self-heals the pointer block and the two hook absolute paths whenever any `racecar/README.md` file is read.
- **System dependencies.** `python3 ≥ 3.11` (`tomllib` stdlib). Optional `jq` for the Read hook (sed fallback); required `jq` for the Bash hook. `make` for the human surface.
- **Dev dependencies.** `pip install --group dev` (via `make install-deps`) pulls `black` / `isort` / `pylint` / `pytest` / `pyyaml>=6.0`. Only `pytest` and `pyyaml` are exercised by `make check` against this repo's own surface; `black` / `isort` / `pylint` are consumer-side defaults wired into the templates.
- **Scheduled jobs.** None. No `.github/workflows/`. Self-test cadence is owner-driven: `make check` runs `check-docs` + `pytest arch-coherence/tests` + `check-brief`.
- **Healthcheck / observability.** None — no service. Hook scripts redirect their failures (`>/dev/null 2>&1 || true`) so PostToolUse never blocks a Read. `sync_claude_md.py` prints `created` / `updated` / `already up to date` at every run.
- **Uninstall.** Not provided for the main install — symlinks and the pointer block survive a `git rm` of the checkout. `make expert-uninstall` does reverse the overlay block + symlink.
- **Tests.** Six modules: `arch-coherence/tests/{test_check_cli_commands,test_check_string_relations,test_check_upward_imports}.py`, `doc-coherence/tests/test_check_docs.py`, `llm-summary/tests/test_check_brief.py`, `scripts/tests/test_sync_claude_md.py`. Still untested: `expert_mode.py`, `sync_md_to_obsidian.py`, the two bash hooks, and `./install` itself.

### §2.11 Weirdness

- **The skill spec is the executable artifact.** `llm-summary/README.md` is not a generator program — it is a Markdown contract that a model reads into its context and then *executes by drafting Markdown*. The generator is the model; the spec is the program. The companion `check_brief.py` cannot generate a brief, only check one. Looks wrong (no source-to-output transformer); is correct (Claude Code's model is the runtime; Markdown is the source language for behavior).
- **The skill describes itself.** This document is the `racecar-llm-summary` generator applied to the racecar repo — which contains the `racecar-llm-summary` skill. The spec lives at `llm-summary/README.md`; this brief sits at `docs/racecar/RACECAR.md`. Self-application is not a paradox because the artifacts are not interchangeable — the spec changes when the framework rules change; the brief changes when the racecar source changes.
- **`./install` is bash but ends in a Python script.** Bash handles the filesystem primitives (`ln -s`, `realpath`-via-python3 because macOS lacks `realpath`); Python handles structured rewriting (JSON, ordered HTML-comment markers). Each is the right tool for its phase.
- **`hooks/compound-command-allow.sh` embeds an inline Python parser.** Splitting `cmd && cmd2 ; cmd3 | cmd4` while respecting quotes is not expressible in `sed` / `awk` cleanly. The hook is bash because Claude Code wants a bash command on stdin; the parsing is Python because bash cannot parse bash safely.
- **Mechanical pre-pass scripts run against the *consumer's* repo, not racecar's.** Each script walks up to `.git` at the CWD's ancestor — the consumer's repo, not racecar's. The scripts ship as skill content under `~/.claude/skills/racecar-doc-coherence/scripts/` (etc.) and operate on whichever repo the agent is reviewing. Looks wrong (a script that doesn't know which repo it's for); is correct (the repo it's for is wherever the model is running).
- **No `[tool.importlinter]` block in this repo's own `pyproject.toml`.** Racecar imposes import-linter discipline on its consumers but does not run import-linter on itself — there are no business-logic packages here, just standalone scripts. The framework does not dodge its own rules; there is no DAG to enforce when the artifacts are stand-alone scripts.

## §3. Live access

N/A — racecar is a Claude Code skills bundle distributed as a git checkout. There is no deployed instance; the consumer's machine is the only execution environment.

### §3.1 Environments

N/A — no deployed instance.

### §3.2 Auth

N/A — no deployed instance. Filesystem permissions on `~/.claude/` are the only access control.

### §3.3 Operations

N/A — no deployed instance. The CLI surface is enumerated in frontmatter `external_surface.cli_verbs`.

### §3.4 Rate limits

N/A — no deployed instance.

### §3.5 Errors

N/A — no deployed instance. Script exit codes are inlined in frontmatter `external_surface.cli_verbs[].exit` and in the body of §2.7 Flows.

### §3.6 SDKs

N/A — no deployed instance. The install surface is `./install`, `make`, and the slash-command names.

## Confidence

**Least confident**

- §2.5 (Internal contracts): the claim that the vocabulary-identity regex `(\b[A-Z][a-z]+)\s+values\s+are\s+literal:\s*\*\*([^*]+)\*\*` catches *every* drift case between sibling READMEs assumes reviewers do not phrase the same vocabulary differently (e.g. "Severities are: …"). Verify against the regex at `doc-coherence/scripts/check_docs.py:200` and the inlined copies in each lens README.
- §2.3 (Relationships) `ProjectTemplate → MechanicalCheck`: the post-`9c70eef` wiring note rests on the assumption that both `templates/ruff/` and `templates/classic/` are kept in lockstep. Drift between the two variants would be invisible to the framework's own `make check`. Verify with `diff <(sort templates/ruff/pre-commit-config.yaml) <(sort templates/classic/pre-commit-config.yaml)` and `diff templates/ruff/Makefile templates/classic/Makefile`.
- §2.7 Flow 6 (CLI-tree audit) pattern classification: Patterns 1 / 2 / 3 and the "must also have `_print_commands`" rule are taken from `_classify` in `arch-coherence/scripts/check_cli_commands.py`; if the script is refactored to add a fourth pattern or to drop the `_print_commands` requirement, this brief will lag. Verify against the current `_classify` and `_make_node` definitions.
- §2.9 (Design decisions): attribution of "identify hooks by command basename" to the moved-checkout motivation is inferred from the surrounding commit messages and the `upsert_hook` implementation; the precise commit where the basename rule was introduced was not isolated. Verify with `git log -p scripts/sync_claude_md.py`.

**Not in this brief**

- Owner identity beyond `shared/PERSONA.md`'s persona JSON — unknown — ask user.
- Adoption — which consumer repos use the templates, how many — unknown — ask user.
- Roadmap intent: no `TODO.md` despite `shared/TODO_FORMAT.md` prescribing one — unknown — ask user whether work is tracked elsewhere.
- Purpose and intended invocation of `scripts/sync_md_to_obsidian.py` (not wired into Makefile; not referenced from any README) — unknown — ask user.
- Whether `gstack` is publicly available or owner-private — unknown — ask user.
- Whether `check_string_relations.py` and `check_docs.py` are deliberately omitted from the consumer templates or just not wired yet — unknown — ask user.
