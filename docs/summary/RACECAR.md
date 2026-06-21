---
generator:
  name: racecar-llm-summary
  version: "0.8.0"
target:
  repo: racecar
  sha: 6b2038b
  date: 2026-06-21
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
    purpose: A stdlib-only Python script that catches deterministic drift the model is not asked to think about. Most gate (exit 1 on violation); check_face_orchestration and check_config_drift are ADVISORY (exit 0 by default) — gate defects, surface choices.
    notes: "Twelve: check_docs, check_subsystem_docs, check_todo_format, check_claude_shape, check_file_placement (doc-coherence); check_upward_imports, check_cli_commands, check_dj_model_ref_as_string, check_packaging (arch-coherence, gating); check_face_orchestration (arch-coherence, advisory faces detector); check_brief (llm-summary). All synced to adopters via sync_scripts/init_project EXCEPT check_config_drift (scripts/, racecar-run-only: diffs an adopter's Makefile/pre-commit against templates/classic, needs the racecar checkout)."

  - name: Finding
    case: none
    lifecycle: realized
    purpose: A single review observation tagged with severity (`Blocker`/`Major`/`Minor`/`Nit`) that contributes to a verdict (`Ship`/`Revise`/`Rework`).
    notes: "Not stored on disk. Carried in model context and reproduced in model output per each lens README's Feedback format section. check_packaging reuses a two-tier Blocker/Finding variant in its own output."

  - name: ProjectShape
    case: none
    lifecycle: realized
    purpose: A consumer project's packaging layout — one of `src`, `pypkg`, `pypkg+djapp`, `djapp` — that the packaging canon parameterizes over.
    notes: "Defined in arch-coherence/PACKAGING.md §Scope; detected mechanically by check_packaging.detect_shape(). All four share the same infrastructure (PEP 621/735 pyproject, make check gate, dev tool set); only the source layout and pyproject location differ. racecar itself is NOT one of these shapes — it is a standards framework, not a deployable package."

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
    purpose: A `hooks.*` entry in `~/.claude/settings.json` that wires a racecar hook into the Claude Code permission and event pipeline.
    notes: "Seven managed: PreToolUse Bash (compound-command-allow.sh), PostToolUse Read (claude_racecar_hook.sh), PreCompact (precompact_history.py) + SessionStart/compact (session_compact_history.py) [the decision-log pair], and three SessionStart startup/resume/clear/compact hooks — session_load_standards.py (force-load baseline), session_discover_cli.py (CLI-surface snapshot), and session_check_sync.py (warns when this repo's synced check scripts are behind racecar canon). Identified by command basename so a moved checkout self-heals."

  - name: DecisionLog
    case: on_disk_managed
    lifecycle: realized
    purpose: A per-project append-only `<repo>/.claude/HISTORY.md` capturing where context was compacted and the reconciled why; mirrored to `~/.claude/history/<repo-kebab>.md`.
    notes: "Opt-in: the decision-log hooks no-op unless the project already has a `.claude/HISTORY.md`. PreCompact appends a deterministic compaction marker (branch@HEAD, trigger); SessionStart(compact) prompts the agent to mine the pre-compaction transcript and append the rationale. Tiered: deterministic spine + judgment-only why."

  - name: VersionFile
    case: on_disk_managed
    lifecycle: realized
    purpose: A plain `major.minor.patch` text file at the repo root that tracks the framework's release line.
    notes: "Manually edited per shared/COMMITS.md; current 0.7.0. The packaging canon deprecates VERSION only where a `[project].version` exists to replace it; racecar, having no `[project]` table, is exempt and keeps VERSION as its legitimate version home (commit 745cef1)."

  - name: SkillManifest
    case: content_tree
    lifecycle: realized
    purpose: A short YAML-fronted Markdown file (`SKILL.md`) that registers a slash command and points at its sibling README as the loader.
    path_pattern: "<skill>/SKILL.md (root router + arch-coherence, doc-coherence, eng-review, llm-summary, commit, commit-decompose, commit-preflight, doctor, normalize, upgrade, expert)"
    count: 12
    validator: "Claude Code at skill registration time"

  - name: StandardDoc
    case: content_tree
    lifecycle: realized
    purpose: A living Markdown standard — lens README, language overlay, or shared convention — read into the agent's context on demand.
    path_pattern: "<skill>/README.md, arch-coherence/{PYTHON,DJANGO,CLI,PACKAGING,FACES}.md, eng-review/{PYTHON,DJANGO}.md, shared/*.md (incl. DRIFT.md), expert/EXPERT.md, root CLAUDE.md (machine baseline + resolver), root README.md (human storefront)"
    count: "~24"
    validator: "doc-coherence/scripts/check_docs.py (+ check_subsystem_docs.py)"

  - name: ProjectTemplate
    case: content_tree
    lifecycle: realized
    purpose: A copy-into-consumer-project baseline that illustrates the framework's packaging canon. Example artifact, NOT racecar's own operational truth — canon lives in PACKAGING.md + the check scripts.
    path_pattern: "templates/classic/{library-pyproject.toml, djapp-pyproject.toml, Makefile, pre-commit-config.yaml, gitignore, README.md}"
    count: 6
    validator: "arch-coherence/scripts/check_packaging.py (in the consumer project)"
    notes: "Single canonical set (black + isort + pylint; djhtml added to the Django dev group as the canonical template-tag formatter, PACKAGING.md §6). The earlier ruff variant was dropped (commit 9ad5c27) under the PACKAGING.md governance rule excluding VC-backed tooling. The Makefile is parameterized over the four ProjectShapes via SRC/PKG/DJAPP/LIB_PYPROJECT/DJAPP_PYPROJECT; its fmt/fmt-check targets run djhtml gated on $(DJAPP)."

relationships:
  - from: Router
    to: Lens
    cardinality: "1:N"
    notes: "Root CLAUDE.md (the force-loaded machine baseline) lists topic rows pointing at each lens README; /racecar loads it as the resolver."

  - from: Router
    to: Generator
    cardinality: "1:1"
    notes: "Root CLAUDE.md also routes to llm-summary even though it is not a lens."

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

  - from: SettingsHook
    to: DecisionLog
    cardinality: "1:N"
    notes: "The PreCompact hook appends the compaction marker to the project's HISTORY.md; the SessionStart(compact) hook prompts reconciliation of the same file. Both no-op unless the project opted in with a `.claude/HISTORY.md`."

  - from: SettingsHook
    to: StandardDoc
    cardinality: "1:N"
    notes: "The SessionStart standards-loader (session_load_standards.py) inlines CLAUDE.md + every shared/*.md as additionalContext on startup/resume/clear/compact, so the machine baseline is present, not merely pointed at. README.md is the human storefront and is not loaded."

  - from: SettingsHook
    to: MechanicalCheck
    cardinality: "1:1"
    notes: "The SessionStart CLI-discovery hook (session_discover_cli.py) runs check_cli_commands.py --json and injects a summarized CLI-surface tree into context."

  - from: ProjectTemplate
    to: MechanicalCheck
    cardinality: "1:N"
    notes: "The classic template wires the checks for a consumer project. Pre-commit (templates/classic/pre-commit-config.yaml): check_upward_imports.py, validate-pyproject, import-linter (and check_dj_model_ref_as_string.py / check_docs.py when copied in). Makefile `arch` target: lint-imports + check_upward_imports + check_cli_commands + check_packaging (+ check_dj_model_ref_as_string under a DJAPP/manage.py guard); `docs` target: check_docs. check_brief validates briefs in docs/, not source."

  - from: Overlay
    to: PointerBlock
    cardinality: "1:1"
    notes: "racecar-expert-mode installs its own twin BEGIN/END markers as a second managed block in CLAUDE.md."

external_surface:
  cli_verbs:
    - verb: /racecar
      module: SKILL.md
      args: none
      behavior: "Load the root resolver (CLAUDE.md); route from topic to lens or generator."
    - verb: /racecar-arch-coherence
      module: arch-coherence/SKILL.md
      args: freeform prompt
      behavior: "Apply the four architectural checks (acyclicity, direction, layer integrity, depth-plus-one) plus a red-flag scan; emit findings + verdict. Loads PYTHON.md / DJANGO.md / CLI.md / PACKAGING.md on demand."
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
      behavior: "Discovery walk + bundle write to docs/summary/$REPO.md, validated by check_brief.py."
    - verb: /racecar-upgrade
      module: upgrade/SKILL.md
      args: freeform prompt (the repo to upgrade)
      behavior: "Detect divergence from current racecar mechanically, classify each Conform/Declare/Escalate (burden of proof on Conform), owner-authorized, idempotent, no clobber. Optional lib/api/faces uplift from existing structure."
    - verb: /racecar-expert-mode
      module: expert/SKILL.md
      args: none
      behavior: "Adopt the expert output discipline (terse, lead with result, no preamble) for the rest of the session."
    - verb: ./install
      module: install
      args: "none; env: CLAUDE_SKILLS_PATH, CLAUDE_MD_PATH, CLAUDE_SETTINGS_PATH"
      behavior: "python3 precheck → symlink five skills under ~/.claude/skills/ → invoke sync_claude_md.py to manage the pointer block and seven hooks. Idempotent; refuses to clobber foreign state."
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
      behavior: "Run check-docs + check-subsystem-docs + test + check-brief (racecar's own self-verification gate)."
    - verb: make check-docs
      module: Makefile
      args: none
      behavior: "Run doc-coherence/scripts/check_docs.py against this repo."
    - verb: make check-subsystem-docs
      module: Makefile
      args: none
      behavior: "Run doc-coherence/scripts/check_subsystem_docs.py — every import-linter subsystem owns README + CLAUDE (no-op here: racecar declares no contracts)."
    - verb: make check-brief
      module: Makefile
      args: none
      behavior: "Validate docs/<repo>/<REPO>.md against the llm-summary schema."
    - verb: make test
      module: Makefile
      args: none
      behavior: "pytest across arch-coherence/tests, doc-coherence/tests, llm-summary/tests, scripts/tests (eight modules: check_cli_commands, check_packaging, check_dj_model_ref_as_string, check_upward_imports, check_docs, check_subsystem_docs, check_brief, sync_claude_md)."
    - verb: make clean
      module: Makefile
      args: none
      behavior: "Remove __pycache__, *.pyc, .DS_Store, and build artifacts; prunes .git and the venv so neither is touched."
    - verb: make distclean
      module: Makefile
      args: none
      behavior: "clean + remove the virtualenv."
    - verb: make obsidian
      module: Makefile
      args: none
      behavior: "List the two obsidian sync modes (obsidian-data / obsidian-docs); syncs nothing itself. (racecar's own Makefile only — the consumer template Makefile dropped these targets.)"
    - verb: make obsidian-data
      module: Makefile
      args: "vars: OBSIDIAN_DEST, DATA_DIR, OBSIDIAN_SLUG"
      behavior: "Mirror DATA_DIR/ into OBSIDIAN_DEST/<org>-<repo>/data/ via rsync --delete (slug from git remote). No-op if DATA_DIR absent."
    - verb: make obsidian-docs
      module: Makefile
      args: "vars: OBSIDIAN_DEST, OBSIDIAN_SLUG"
      behavior: "Mirror every all-uppercase *.md ([A-Z]+.md) found anywhere in the repo into OBSIDIAN_DEST/<org>-<repo>/docs/, preserving tree structure (wipe + recopy). No-op if none found."

  library_exports:
    - name: check_docs
      module: doc-coherence/scripts/check_docs.py
      signature: "python3 check_docs.py"
      behavior: "Walk up to .git; (1) check intra-repo Markdown links/anchors; (2) check `FILENAME.md §N` citations across .py/.yaml/.toml/Makefile; (3) check vocabulary identity — every `<Class> values are literal: **<literal>**` line agrees across all markdown. Honors [tool.pylint.MASTER].ignore-paths from the consumer's pyproject.toml. Exit 0/1."
    - name: check_subsystem_docs
      module: doc-coherence/scripts/check_subsystem_docs.py
      signature: "python3 check_subsystem_docs.py"
      behavior: "Resolve every dotted package in [tool.importlinter].contracts to a directory; walk for 'major' subsystems (has a subdirectory OR direct-child source >= loc_threshold, default 1000 lines); assert each owns a non-empty README.md and CLAUDE.md with >= 1 `## ` heading. Config under [tool.racecar.subsystem-docs]. No-op when no contracts. Exit 0/1."
    - name: check_brief
      module: llm-summary/scripts/check_brief.py
      signature: "python3 check_brief.py [<bundle-path>]"
      behavior: "Validate frontmatter schema, required §N.M headings, ## Confidence markers, bundle membership, and spine/body SHA agreement for a racecar-llm-summary brief. Exit 0/1."
    - name: check_upward_imports
      module: arch-coherence/scripts/check_upward_imports.py
      signature: "python3 check_upward_imports.py <file> [<file>...]"
      behavior: "Reject `from <root> import …` in files that are neither __init__.py nor __main__.py, where <root> is the root package that OWNS the file. Roots read from the library pyproject's [tool.importlinter].root_packages (list) or root_package (string); the library pyproject is located by detect_shape (imported from check_packaging). Each file is checked only against its owning root — a `from <other-root> import …` is a cross-root dependency (import-linter's concern) and is NOT flagged. Exit 0/1; 2 on missing config."
    - name: check_cli_commands
      module: arch-coherence/scripts/check_cli_commands.py
      signature: "python3 check_cli_commands.py <root.pkg|path> [...] [--json] [--workers N]"
      behavior: "Walk a Python CLI tree; verify the commands()/subcommands()/parser() contracts; classify each node Pattern 1/2/3; fan subprocess probes (--help, no-args listing, subcommand --help) across a thread pool (default min(32, cpus*4); --workers 1 = sequential); capture __main__.py import errors as structural violations; scan for orphan __main__.py / main-guard modules. --json emits the enriched node tree (raw audit fields + resolved command/role/description) that the SessionStart CLI-discovery hook consumes."
    - name: check_packaging
      module: arch-coherence/scripts/check_packaging.py
      signature: "python3 check_packaging.py [--root <path>] [--strict]"
      behavior: "Detect the ProjectShape via detect_shape(); validate the library pyproject ([project] PEP 621 keys, [dependency-groups].dev against the canon tool set, [build-system], no [tool.uv|ruff|poetry|pdm] blocks), the djapp pyproject, the Makefile target surface, .gitignore, .pre-commit-config.yaml, requirements.txt, and CHANGELOG. Two severities (Blocker / Finding); --strict promotes Findings to Blockers. Exit 0 if no Blockers / 1. Pure stdlib. Exports detect_shape(), imported by check_upward_imports."
    - name: check_dj_model_ref_as_string
      module: arch-coherence/scripts/check_dj_model_ref_as_string.py
      signature: "python3 check_dj_model_ref_as_string.py"
      behavior: "AST-walk every .py under each [tool.importlinter].root_packages dir; flag ORM string-target FKs/O2O/M2M; classify LIVE vs NOOP against INSTALLED_APPS; annotate UPWARD DAG cross by layer."
---

# Racecar — Knowledge Package

A Claude Code skills bundle that ships an opinionated Python/Django code-review framework as five installable slash commands plus an optional output-mode overlay. Cloning this repo and running `./install` symlinks its directories into `~/.claude/skills/`, writes a managed pointer block into `~/.claude/CLAUDE.md`, and registers six Claude Code hooks in `~/.claude/settings.json`. After that, the slash commands resolve, the cross-cutting baseline is force-loaded into every session, and the agent reads the lens standards from this checkout on demand.

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
- **MechanicalCheck** — deterministic Python scripts the lenses delegate to: `check_docs.py`, `check_subsystem_docs.py`, `check_upward_imports.py`, `check_cli_commands.py`, `check_dj_model_ref_as_string.py`, `check_packaging.py`, `check_brief.py`.
- **ProjectShape** — the packaging vocabulary (`src` / `pypkg` / `pypkg+djapp` / `djapp`) the packaging canon (`arch-coherence/PACKAGING.md`) parameterizes a consumer project over.

### §1.2 Modules

| Module | Purpose |
| --- | --- |
| `arch-coherence/` | Architectural-coherence lens: four checks (acyclicity, direction, layer integrity, depth-plus-one) + Python/Django specifics (`PYTHON.md`, `DJANGO.md`) + the CLI contract (`CLI.md`) + the packaging canon (`PACKAGING.md`) + the faces doctrine (`FACES.md`: `lib → api → faces`, a face is a wrapper on `api`, named-file autodiscovery convention, the single gated `layers` contract, advisory detector) + five enforcement scripts (`check_upward_imports`, `check_cli_commands`, `check_dj_model_ref_as_string`, `check_packaging` gating; `check_face_orchestration` advisory), each with its own test module. |
| `doc-coherence/` | Documentation-coherence lens: update protocol + review lens + two mechanical pre-passes — `check_docs` (link / anchor / §N / vocabulary drift) and `check_subsystem_docs` (every import-linter subsystem owns README + CLAUDE). |
| `eng-review/` | Engineering-review wrapper: racecar pre-pass → gstack `/plan-eng-review` → racecar post-pass. |
| `llm-summary/` | This generator's spec + the `check_brief.py` validator. |
| `expert/` | Optional output-mode overlay: terse, high-density expert delivery. |
| `shared/` | Cross-cutting docs loaded on demand: `OPERATIONAL`, `OWNERSHIP`, `VOICE`, `PERSONA`, `GLOSSARY`, `VOCABULARY` (severity/verdict literals), `DRIFT`, `COMMITS`, `TODO_FORMAT`. |
| `scripts/` | racecar-internal tooling (not synced as checks): `sync_claude_md.py` (pointer + hooks), `init_project.py` (scaffolder, incl. `--vertical` and the README skeleton), `sync_scripts.py` (sync canonical checks into an adopter), `check_config_drift.py` (advisory Makefile/pre-commit drift vs templates/classic), `doctor.py`, `expert_mode.py`, `sync_md_to_obsidian.py`. |
| `hooks/` | Claude Code hooks wired into `~/.claude/settings.json`: two bash (`compound-command-allow.sh`, `claude_racecar_hook.sh`) and five Python (`precompact_history.py`, `session_compact_history.py`, `session_load_standards.py`, `session_discover_cli.py`, `session_check_sync.py` — synced-script staleness warning). |
| `templates/` | Copy-into-project starter files under `classic/` (a single canonical set). Example artifacts illustrating the packaging canon — not racecar's own operational truth. |
| `docs/` | Generated briefs from this skill at `docs/summary/<REPO>.md`, including `docs/summary/RACECAR.md` (this file). |
| (root) | `CLAUDE.md` (machine baseline + resolver, force-loaded), `README.md` (human storefront), `SKILL.md` (router), `install`, `Makefile`, `pyproject.toml`, `VERSION`, `LICENSE`. |

### §1.3 Vendors

Pure stdlib at runtime in the shipped scripts. Dev-only dependencies declared in `pyproject.toml` under `[dependency-groups].dev`: `pytest` (test runner), `pyyaml>=6.0` (hard requirement of `check_brief.py`), `black` / `isort` / `pylint` (the canonical consumer toolchain wired into the templates; unused by racecar's own check surface). System dependencies: `python3 ≥ 3.11` for `tomllib` (hard, stdlib only), `jq` (hard for the Bash hook; the Read hook falls back to `sed` if absent), `make` (human surface). Consumer projects additionally need `pip ≥ 25.1` for PEP 735 dependency groups (a template requirement, not racecar's own).

No paid SaaS, no cloud platforms. One sibling skill bundle is referenced by name: **gstack**, a separate Claude Code skill bundle whose `/plan-eng-review` skill `eng-review/README.md` delegates phase 2 to. If gstack is absent the wrapper degrades to pre-pass plus post-pass; the README states the degradation explicitly.

## §2. Implementation

### §2.1 Runtime

Two runtimes share this repo, plus a quasi-runtime that executes in target projects.

1. **Skill bundle (primary).** A set of Markdown documents loaded into a Claude Code agent's context window when the corresponding slash command fires. Entry points are eleven `SKILL.md` files — Claude Code reads YAML frontmatter (`name`, `description`) to register `/racecar` (router) plus `-arch-coherence`, `-doc-coherence`, `-eng-review`, `-llm-summary`, `-commit`, `-commit-decompose`, `-commit-preflight`, `-doctor`, `-normalize`, and (after `make expert`) `-expert-mode`. The skill body is a one-screen pointer at the relevant `README.md`. The model — not the bundle — does the work. The SessionStart standards-loader hook additionally force-loads the `CLAUDE.md` + `shared/*.md` machine baseline so it is present, not merely routable; `README.md` is the human storefront and is not loaded.

2. **CLI bootstrap (secondary).** A bash entry point (`install`) plus three stdlib Python scripts under `scripts/` (`sync_claude_md.py`, `expert_mode.py`, `sync_md_to_obsidian.py`) that mutate `~/.claude/` state. `make` is the human surface; `./install` is the bash surface. Both end in `scripts/sync_claude_md.py`.

3. **Mechanical pre-pass (quasi-runtime).** The seven scripts under `doc-coherence/scripts/`, `arch-coherence/scripts/`, and `llm-summary/scripts/` run inside the *target* project being reviewed (or, for `check_brief.py`, against any repo with a brief at `docs/<repo>/<REPO>.md`), not inside racecar's own tree. They discover the target via `.git` walk-up and read its `pyproject.toml`.

| Runtime | Entry point | Invocation | State location |
| --- | --- | --- | --- |
| Skill: router | `SKILL.md` (root) | `/racecar` | none |
| Skill: arch lens | `arch-coherence/SKILL.md` | `/racecar-arch-coherence` | none |
| Skill: doc lens | `doc-coherence/SKILL.md` | `/racecar-doc-coherence` | none |
| Skill: eng wrapper | `eng-review/SKILL.md` | `/racecar-eng-review` | delegates to gstack |
| Skill: generator | `llm-summary/SKILL.md` | `/racecar-llm-summary` | writes `docs/summary/$REPO.md` in target repo |
| Skill: expert overlay | `expert/SKILL.md` | `/racecar-expert-mode` | session-scoped output behavior |
| Installer | `install` (bash) | `./install` | `~/.claude/skills/`, `~/.claude/CLAUDE.md`, `~/.claude/settings.json` |
| Mechanical pre-pass | `*/scripts/check_*.py` | `make check*` here, or pre-commit / Makefile in target | reads target repo |
| Hook: PreToolUse Bash | `hooks/compound-command-allow.sh` | Claude Code, on every Bash | reads three settings files |
| Hook: PostToolUse Read | `hooks/claude_racecar_hook.sh` | Claude Code, on every Read | re-fires `sync_claude_md.py` on match |
| Hook: PreCompact | `hooks/precompact_history.py` | Claude Code, on compaction | appends marker to project HISTORY.md (opt-in) |
| Hook: SessionStart(compact) | `hooks/session_compact_history.py` | Claude Code, post-compaction | prompts HISTORY.md reconciliation (opt-in) |
| Hook: SessionStart(start/resume/clear/compact) | `hooks/session_load_standards.py` | Claude Code | injects CLAUDE.md + shared/*.md as context |
| Hook: SessionStart(start/resume/clear/compact) | `hooks/session_discover_cli.py` | Claude Code | injects summarized CLI-surface tree |

### §2.2 Entities

See frontmatter `entities` for the class-level enumeration. This section is the narrative gloss.

The system has **no database, no ORM, no `INSTALLED_APPS`** in its own source. The classes split into three flavors.

- **Behavioral primitives** (`case: none`). `Lens`, `Generator`, `Router`, `Overlay`, `MechanicalCheck`, `Finding`, and `ProjectShape` are not stored as files; they are the conceptual vocabulary the framework asserts. A `Lens` is a particular shape of skill (load README, apply checks, emit findings); `Generator` is a contrasting shape (produce an artifact); `Finding` is the unit of lens output; `ProjectShape` is the packaging-layout vocabulary the canon parameterizes a consumer over. The on-disk artifacts realize these classes — each lens skill *is a* `Lens`.

- **Managed on-disk state** (`case: on_disk_managed`). `PointerBlock`, `SkillSymlink`, `SettingsHook`, `DecisionLog`, `VersionFile`. Everything `./install` and `make expert` write or rewrite. The `PointerBlock` and `SettingsHook` are unusual because they live *inside* files the racecar installer does not own — `~/.claude/CLAUDE.md` and `~/.claude/settings.json` — and must coexist with arbitrary other content. The byte-exact BEGIN/END HTML-comment markers and the basename-identity rule on hooks are what make that coexistence safe.

- **Content trees** (`case: content_tree`). `SkillManifest` (six `SKILL.md` files), `StandardDoc` (the Markdown standards corpus: lens READMEs + PYTHON/DJANGO/CLI/PACKAGING overlays + shared/* + expert/EXPERT.md + root README.md), `ProjectTemplate` (five files under `templates/classic/`). The first two are the framework's content; agents read them as standards. `ProjectTemplate` is different in kind: it is an *example* a consumer copies, not a statement of how racecar itself operates — racecar's packaging canon lives in `PACKAGING.md` and the scripts, never in the template files.

### §2.3 Relationships

There are no foreign keys — there is no relational store. The DAG above the frontmatter is logical: skill-manifest → CLAUDE.md (resolver); router → lens (and → generator); lens → mechanical-check (with bidirectional `§N` and docstring citations); installer-script → managed-state; project-template → mechanical-check (via the consumer's `.pre-commit-config.yaml` and `Makefile`); settings-hook → standard-doc and → mechanical-check (the two SessionStart loaders).

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
 racecar-eng-review,            (seven hook entries)            (expert pointer block)
 racecar-llm-summary}                  ^
                                       |  PostToolUse Read self-heal
                                       |  + SessionStart load/discover
                       hooks/{claude_racecar_hook.sh,
                              session_load_standards.py,
                              session_discover_cli.py, ...}
```

Inside the markdown corpus, root `README.md` fans 1→N to each lens README plus 1→1 to `llm-summary/README.md`; each `SKILL.md` points 1→1 to its sibling `README.md`; `arch-coherence/{PYTHON,CLI,PACKAGING}.md`, `doc-coherence/README.md`, and `llm-summary/README.md` each pair bidirectionally with their respective scripts via `§N` backrefs and `__doc__` citations.

### §2.4 External surface

See frontmatter `external_surface` for the full enumeration. Three surface entries warrant body detail because they encode load-bearing behavior the frontmatter cannot convey in one line.

#### §2.4.1 `./install`

Bash, idempotent. Reads three env vars (`CLAUDE_SKILLS_PATH`, `CLAUDE_MD_PATH`, `CLAUDE_SETTINGS_PATH`) with `~/.claude/` defaults. On a fresh clone, the sequence is: `python3` precheck (prints an OS-specific install hint and exits 1 if missing) → for each of five `(skill-name, dir)` pairs, link `~/.claude/skills/<name>` → `<dir>` (refuse on conflict) → invoke `scripts/sync_claude_md.py` to write the pointer block and upsert the seven hooks. A symlink already at the right target is left alone; one pointing elsewhere or a regular file at the path is refused and counted as a conflict (`exit 1`). See `install` and `scripts/sync_claude_md.py` for the symmetry between the bash phase (filesystem primitives) and the Python phase (structured rewriting of CLAUDE.md and settings.json).

#### §2.4.2 PostToolUse Read self-heal

`hooks/claude_racecar_hook.sh` receives PostToolUse JSON on stdin and case-globs `*/racecar/README.md` against `.tool_input.file_path`. On match, it re-fires `sync_claude_md.py` with output silenced. The hook **always exits 0** so a malformed payload never blocks the Read. This is the mechanism by which the pointer block and the absolute paths inside the seven hook entries self-heal whenever the checkout moves.

#### §2.4.3 SessionStart loaders

Two SessionStart hooks, both wired on four matchers (startup, resume, clear, compact) so they re-fire after `/clear` and auto-compaction. `session_load_standards.py` inlines `CLAUDE.md` (racecar's machine baseline, which carries the resolver) and every `shared/*.md` as `additionalContext`, framed so the agent treats the baseline as already present rather than as a routing table to consult later; `README.md` is the human storefront and stays unloaded, and the lens files stay load-on-demand by design. `session_discover_cli.py` finds CLI roots by scanning the filesystem (every direct-child dir of `<repo>/` and `<repo>/src/` with both `__init__.py` and `__main__.py` — deliberately ignoring `[project].name` since dist and import names differ), runs `check_cli_commands.py --json`, then summarizes the enriched tree (dropping kind / pattern codes / audit noise) into context.

Short slash commands, `make` targets, and mechanical pre-pass scripts are fully captured in frontmatter and need no body gloss.

### §2.5 Internal contracts

Cross-module contracts that are not user-callable:

- **Severity vocabulary `Blocker / Major / Minor / Nit`** → canonical home `shared/VOCABULARY.md`; repeated inline in each lens README's `Feedback format` section so a reviewer never has to follow a link. Drift between sibling READMEs is mechanically caught by the vocabulary-identity check in `doc-coherence/scripts/check_docs.py`.
- **Verdict vocabulary `Ship / Revise / Rework`** → same shape as severity; same mechanical identity check.
- **The CLI contract — `commands()` / `subcommands()` / `parser()`** → defined in `arch-coherence/CLI.md`; consumed by every `__main__.py` in a consumer project and by `check_cli_commands.py`. `commands() -> list[tuple[str,str]]` lists direct-child `(name, description)` pairs (Pattern 1/2). `subcommands() -> list[tuple[str,str]]` mirrors each `add_parser(...)` call (required on Pattern 2/3 nodes using `add_subparsers()`, forbidden on Pattern 1). `parser() -> argparse.ArgumentParser` returns the parser without calling `parse_args()` so the audit can walk `parser._actions`. All three are pure data functions; printing is confined to `_print_commands()` (Patterns 1/2) or argparse (Pattern 3).
- **CLI audit JSON (enriched node tree)** → produced by `check_cli_commands.py --json` (schema in `CLI.md §"Audit JSON schema"`); consumed by the `session_discover_cli.py` SessionStart hook, doc generators, and CI. The script enriches (raw audit + resolved `command`/`role`/`description`); each consumer summarizes.
- **Packaging canon (library + djapp pyproject)** → defined in `arch-coherence/PACKAGING.md`; enforced by `check_packaging.py`. The library pyproject carries `[project]` (PEP 621), `[build-system]`, `[dependency-groups].dev` (PEP 735, = the canon tool set), and all `[tool.*]`; the djapp pyproject (Shape `pypkg+djapp` only) carries `[dependency-groups].runtime` and no `[project]`. No VC-backed tool blocks (`[tool.uv|ruff|poetry|pdm]`) are permitted.
- **`[tool.importlinter].root_packages` / `.root_package`** → produced by the consumer's library pyproject; consumed by `check_upward_imports.py` (per owning root) and `check_dj_model_ref_as_string.py`. `check_packaging.detect_shape()` locates the library pyproject for both. Missing → exit 2.
- **`[tool.importlinter].contracts`** (`type='layers'`) → produced by consumer; consumed by `import-linter` (external), `check_dj_model_ref_as_string.py` (UPWARD-DAG-cross annotation), and `check_subsystem_docs.py` (subsystem resolution). Each layer row may be `"A | B"` for independent peers.
- **`[tool.racecar.subsystem-docs]`** → produced by consumer; consumed by `check_subsystem_docs.py`. Keys `loc_threshold` (int, default 1000) and `exclude` (list, added to defaults).
- **`[tool.pylint.MASTER].ignore-paths`** → produced by consumer; consumed by `check_docs.py`. `list[regex]`. Absent → empty tuple.
- **Pointer-block markers / Claude Code hook JSON** → as before: byte-exact BEGIN/END partition of `~/.claude/CLAUDE.md` by `sync_claude_md.py` / `expert_mode.py`; hook stdin `{"tool_input": {...}, "cwd": ...}`, PreToolUse may emit `permissionDecision: allow`. Both bash hooks always exit 0 — racecar never denies, only auto-allows or falls through.
- **`racecar-llm-summary` output contract** → produced by `llm-summary/README.md`; consumed by this brief, downstream LLMs, and `check_brief.py` (which now also enforces spine/body SHA agreement). Schema drift → `check_brief.py` exit 1.

### §2.6 Configuration

Racecar has no production / dev split — there is no deployed instance. Every knob is evaluated on the consumer machine.

- `CLAUDE_SKILLS_PATH` / `CLAUDE_MD_PATH` / `CLAUDE_SETTINGS_PATH` — where `./install` writes skill symlinks / the pointer block / the seven hook entries. Defaults `~/.claude/skills`, `~/.claude/CLAUDE.md`, `~/.claude/settings.json`.
- `STRING_RELATIONS_INSTALLED_APPS` — comma-separated app labels; overrides Django app discovery in `check_dj_model_ref_as_string.py` (test / CI mode; bypasses `manage.py shell`).
- `OBSIDIAN_SYNC_ROOT` — destination root for `scripts/sync_md_to_obsidian.py`. Not wired into the Makefile. CLI flag `--dest` > env var > `dest_root` in `~/.config/obsidian-sync.toml`. No default.
- `--claude-md` / `--target`, `--settings`, `--dry-run` — `sync_claude_md.py` CLI flags. CLI flag > env var > default.
- `VENV` — `Makefile` auto-detect (`.venv`, `venv`, `../venv`); first that exists is prepended to `PATH`.
- **Consumer-template Makefile shape variables** (`templates/classic/Makefile`): `SRC` (source root), `PKG` (audited package path), `DJAPP` (Django app dir, empty when not Django), `LIB_PYPROJECT` (library pyproject path), `DJAPP_PYPROJECT` (djapp pyproject path, Shape `pypkg+djapp` only). Set together per the chosen ProjectShape; `PYTEST_ARGS` appends to `make test`.
- `OBSIDIAN_DEST` / `DATA_DIR` / `OBSIDIAN_SLUG` — racecar's **own** Makefile variables (the consumer template dropped the obsidian targets); defaults `$(HOME)/Obsidian` / `.data`, slug `<org>-<repo>` from `git remote get-url origin`.
- `[tool.importlinter].root_package(s)` / `.contracts`, `[tool.racecar.subsystem-docs]`, `[tool.pylint.MASTER].ignore-paths` — consumer-project TOML; see §2.5.

No secrets. No environment-variant rows because there is no environment split.

### §2.7 Flows

1. **Fresh install (`./install`).** python3 precheck; for each of five `(skill-name, dir)` pairs, link `~/.claude/skills/<name>` → `<dir>` (refuse on conflict); invoke `scripts/sync_claude_md.py`, which renders the pointer block, partitions `~/.claude/CLAUDE.md` on BEGIN/END markers, and upserts the seven hooks into `~/.claude/settings.json` by command basename. Idempotent. Exit 0 if no conflicts; 1 otherwise.

2. **Baseline force-load (SessionStart hook).** On startup / resume / clear / compact, `session_load_standards.py` inlines `CLAUDE.md` + every `shared/*.md` as `additionalContext`, framed as already-loaded; `README.md` (human storefront) stays unloaded and lenses stay load-on-demand. Always non-blocking.

3. **CLI-surface discovery (SessionStart hook).** `session_discover_cli.py` walks up to `.git`, scans for CLI roots (dirs with `__init__.py` + `__main__.py`), runs `check_cli_commands.py --json` under the in-tree `.venv` (or `sys.executable`), summarizes the enriched tree, and injects it.

4. **Pointer self-heal (PostToolUse Read hook).** Reading any `racecar/README.md` re-fires `sync_claude_md.py` silently; hook always exits 0.

5. **Compound-bash autoallow (PreToolUse hook).** `compound-command-allow.sh` reads three settings files, splits the compound on unquoted `&&`/`||`/`;`/`|` via an embedded quote-respecting Python parser, and emits `permissionDecision: allow` only if every subcommand matches an allow prefix and none matches a disallow. Otherwise no output, exit 0 (falls through to the normal prompt — never a deny).

6. **Doc pre-pass (`check_docs.py`).** Walk up to `.git`; check intra-repo links + `#anchor` slugs; check `FILENAME.md §N` citations against the target's heading set. Exit 0/1.

7. **Subsystem-docs pre-pass (`check_subsystem_docs.py`).** Resolve `[tool.importlinter].contracts` packages to dirs; walk for "major" subsystems; assert each owns a non-empty `README.md` + `CLAUDE.md` with a heading. No-op when no contracts. Exit 0/1.

8. **Upward-import check (`check_upward_imports.py`).** Pre-commit feeds file args; the script resolves the owning root for each file (from the shape-located library pyproject's `root_packages`/`root_package`) and rejects `from <owning-root> import …` outside `__init__`/`__main__`. Cross-root imports are left for import-linter. Exit 0/1; 2 on missing config.

9. **CLI-tree audit (`check_cli_commands.py`).** Walk the package tree; verify `commands()`/`subcommands()`/`parser()`; classify Pattern 1/2/3; fan `--help` / no-args / `<sub> --help` probes across a thread pool; capture `__main__` import errors as violations; scan orphans. `--json` emits the enriched tree.

10. **Packaging audit (`check_packaging.py`).** Detect the ProjectShape; validate the library + djapp pyprojects, Makefile targets, `.gitignore`, `.pre-commit-config.yaml`, `requirements.txt`, `CHANGELOG`. Blockers fail; Findings fail only under `--strict`. The VERSION-deprecation Finding fires only where `[project].version` exists. Exit 0/1.

11. **Cross-module string-relation check (`check_dj_model_ref_as_string.py`).** Read `root_packages`; obtain `INSTALLED_APPS`; AST-walk each root; flag string-target ORM relations; classify LIVE/NOOP; annotate UPWARD DAG cross. Self-references and `settings.AUTH_USER_MODEL` exempt.

12. **Brief generation (`/racecar-llm-summary`).** Read `llm-summary/README.md` in full → discovery walk → draft body → derive frontmatter → write `docs/summary/$REPO.md` → end with `## Confidence` → validate with `check_brief.py`. This brief is the literal artifact of Flow 12 against this repo.

### §2.8 Seams

Plugin / extension surfaces:

- **Skill registration.** Add `<name>/SKILL.md` with `name:`/`description:` frontmatter, add a row to `install`'s symlink loop, add a row to the root resolver `CLAUDE.md`. The pointer block rendered by `sync_claude_md.py:render_block` is intentionally generic and does not enumerate skills.
- **Hook contract.** Append another `upsert_hook(settings, event, matcher, command, basename)` call in `scripts/sync_claude_md.py:sync_settings`. Hooks are identified by command basename so a moved checkout self-heals. Recent examples: the SessionStart baseline-loader (commit `ff21b54`) and the SessionStart CLI-discovery hook (commit `3bb2ec9`).
- **Mechanical check.** A new stdlib script under a lens's `scripts/`; a row in the template `pre-commit-config.yaml` under `repo: local` (or a Makefile `arch`/`docs` target for full-tree audits); and a doc section the docstring backrefs by `§N`. Recent examples: the packaging canon `check_packaging.py` wired into `make arch` + `validate-pyproject` pre-commit (commit `39fb900`), and `check_subsystem_docs.py` (commit `4b67ef5`).
- **Output overlay.** A directory with `SKILL.md` + content `.md`, a manage-block script under `scripts/` using twin BEGIN/END markers, and a `make` install/uninstall target pair. Recent example: `racecar-expert-mode` (commit `6ce3338`).

### §2.9 Design decisions

- **No CI gate; local enforcement only.** `shared/OWNERSHIP.md`: enforcement is `pre-commit` / `lint-imports` / `make check`, not required-status-check workflows. Tooling confirms; the owner ratifies.
- **One packaging opinion, four shapes.** `arch-coherence/PACKAGING.md` (commit `39fb900`). PEP 621/735 pyproject as the sole config source, `Makefile` contract, `.venv` discipline, optional `requirements.txt` via `pip-compile`, the black + isort + pylint dev set. Parameterized over `src` / `pypkg` / `pypkg+djapp` / `djapp`; the canon explicitly does not accommodate uv-shops, Bazel, or other layouts.
- **PSF/PyPA + community OSS governance — no VC-backed tooling.** PACKAGING.md §1–2. `uv`, `ruff`, `poetry`, `pdm` are rejected on governance/lock-in grounds, not technical ones. This is why the ruff template variant was dropped (commit `9ad5c27`) and `check_packaging` blocks `[tool.uv|ruff|poetry|pdm]`.
- **VERSION-deprecation carve-out for non-package repos.** Commit `745cef1`. The canon says `[project].version` is the sole version source — but only where a `[project]` table exists. A docs/scripts/standards-framework repo (racecar itself) has no `[project]`, so VERSION is its legitimate version home and `check_packaging` no longer misfires on it.
- **The §3 CLI surface is a three-contract / three-pattern model.** `arch-coherence/CLI.md` (commit `3bb2ec9`). `commands()`/`subcommands()`/`parser()` are pure data functions; `check_cli_commands.py --json` emits one enriched tree that every consumer (SessionStart hook, doc gen, CI) summarizes — single source of CLI truth.
- **Parallelize the CLI audit.** Commit `98f7738`. Cold `python -m` probes dominated wall time; a structural walk drops `_Probe` sentinels that a thread pool resolves, preserving per-node ordering (so exact-equality tests pass). `__main__` import errors are captured as structural violations rather than killing the audit.
- **Force-load the baseline every SessionStart.** Commit `ff21b54`. The pointer block is only an instruction; inlining the machine baseline (`CLAUDE.md` + `shared/*.md`) as `additionalContext` makes it present, not merely routable. README is the human storefront and is not loaded; lenses stay on-demand by design.
- **Decision log as a tiered hook pair.** Commit `86aee48`. A deterministic `PreCompact` marker (spine) + a `SessionStart(compact)` reconciliation prompt (judgment). Opt-in per project via `.claude/HISTORY.md`.
- **Completion-claim guardrails.** `shared/OPERATIONAL.md` rules 7–12 (commit `9ced60c`): never claim done without the production-path command + exit code; agent-workaround keywords are stop signals; cross-agent equal numbers must be checked; doc invariants need test code; tests routing around production are bugs; banned completion vocabulary.
- **Subsystem-docs presence check.** Commit `4b67ef5`. Every import-linter subsystem must own a README (developer) + CLAUDE (agent); "major" is structural (a subdir) or size (`loc_threshold`).
- **YAML frontmatter as the brief's relational store; class-level entities only.** `llm-summary/README.md`. A downstream LLM queries frontmatter deterministically; field tables blew the line budget and were rarely the interesting query. `check_brief.py` now also enforces spine/body SHA agreement (commit `938d27c`).
- **Drift doctrine.** `shared/DRIFT.md`. Defense must be structural or automatic; resolve drift at the largest frame that explains the symptom; "duplication is drift" is Tier 1.
- **Faces as named convention, not a wall.** `arch-coherence/FACES.md`. One library exposed through N thin faces (`lib → api → {cli, mcp, web/django}`); a **face is a wrapper on `api`**. The first pass made face→worker routing a hard `forbidden` import-linter contract; that was racecar breaking its own OWNERSHIP ("tooling confirms, the owner authorizes") and DRIFT ("detect and surface") doctrine. Recast (built on the `lib → api → faces` proving ground): **gate genuine defects** (acyclicity + direction stay one gated `layers` contract), **surface choices** (face reaching past `api` is advisory, not walled). The canonical file names (`lib.py`/`api.py`/`mcp.py`/`__main__.py`) are an **autodiscovery contract** — the Django `admin.py` model, fixed because the framework looks them up — not dogma. Role identification is declare-then-verify in three tiers (canonical name → `[tool.racecar.faces]` manifest → structural cut-vertex inference), LLM-last; non-classifiability is itself the drift finding.
- **Advisory faces detector + scaffolder replace the wall.** `check_face_orchestration.py` is advisory (exit 0; `--strict` opts in) and identifies each vertical's `lib`/`api`/faces, flagging non-classifiable verticals and orchestration restated across faces. `scripts/init_project.py --vertical` scaffolds the canonical vertical pre-wired `lib → api → cli` (the `startapp` equivalent): the good shape is the default you receive (FACES.md §10). Scaffold + advisory detector + docs-that-teach is how convention spreads where enforcement does not.
- **djhtml is the canonical Django-template formatter.** `arch-coherence/PACKAGING.md §6`. Idempotent by construction (it only reindents `{% %}` tags), permissively licensed, community OSS — chosen over the heavier, GPL, empirically-idempotent `djlint`. Lives in the Django dev group; `make fmt`/`fmt-check` run it gated on `$(DJAPP)`; `check_packaging` requires it in the django group for any repo with a `manage.py` (the propagation lever to existing Django adopters).
- **README is for humans, CLAUDE.md for machines.** README is the readable storefront and is NOT force-loaded into agent context; `CLAUDE.md` is the machine baseline + resolver the SessionStart hook inlines, and the consuming-project pointer references. Modeled on gstack's README/AGENTS/CLAUDE split.
- **Brief home is `docs/summary/<REPO>.md`.** Dropped the redundant `docs/<repo>/` segment (the repo name is already the host repo) and the Sphinx/MkDocs collision heuristic (an implicit detector racecar otherwise avoids). One fixed location; user override for the rare exception.
- **Nuanced upgrade, not naive clobber.** The `racecar-upgrade` skill (`upgrade/README.md`) never assumes the existing repo is wrong. Every divergence from current racecar gets one of three verdicts: Conform (drift; bring to base), Declare (intentional; preserve and record in `[tool.racecar.overrides]`), Escalate (racecar's default is wrong; change the standard, repo untouched). Burden of proof on Conform; owner-authorized; idempotent. Mechanical floor: `scripts/check_config_drift.py` (portable stdlib Python — deliberately NOT a bash `declare -A` map, which breaks on macOS bash 3.2 — normalizing the per-project shape variables so they are not reported as drift).
- **Adopter self-sufficiency for synced checks.** `check_subsystem_docs` and `check_brief` were racecar-only, so an adopter could not validate artifacts (its own subsystem docs, its own `docs/summary/` brief) without the racecar checkout. Both are now synced; `check_brief` needs `pyyaml`, which was promoted to a canonical dev tool (PACKAGING.md §6) to make the adopter's gate self-contained. The template `docs:` target runs `check_brief` guarded so a repo with no brief pays only the inert dependency.
- **Standard README shape as a received template, not a gate.** Human READMEs follow who-what -> Getting Started -> Using -> when/where/why (`templates/classic/README.md`, scaffolded by `init_project`). No checker enforces the section names: forcing headings would be theater. The structure is the easy default you receive, per the FACES.md "make the right thing easy" principle.

### §2.10 Operational

- **Install (fresh clone).** Requires `python3 ≥ 3.11` on `PATH` (stdlib only) and a writable `~/.claude/`. Run `./install`. Idempotent. Override targets via the three env vars.
- **Bootstrap check.** Verify `~/.claude/settings.json` `hooks.PostToolUse` contains an entry whose command ends with `hooks/claude_racecar_hook.sh`. Root `README.md` documents this.
- **Move the checkout.** Re-run `./install`; the PostToolUse Read hook also self-heals the pointer block and the seven hook absolute paths whenever any `racecar/README.md` is read.
- **System dependencies.** `python3 ≥ 3.11` (`tomllib`). Optional `jq` for the Read hook (sed fallback); required `jq` for the Bash hook. `make` for the human surface. Consumer projects additionally need `pip ≥ 25.1` (PEP 735) — a template requirement, not racecar's own.
- **Dev dependencies.** `pip install --group dev` (via `make install-deps`) pulls `black`/`isort`/`pylint`/`pytest`/`pyyaml>=6.0`. Only `pytest` and `pyyaml` exercise racecar's own surface; the formatters/linter are consumer-side defaults.
- **Self-test.** Owner-driven, no `.github/workflows/`. `make check` = `check-docs` + `check-subsystem-docs` + `pytest` (eight modules) + `check-brief`. racecar itself is **not** one of the four ProjectShapes, so `check_packaging` is not run against racecar's own tree.
- **Healthcheck / observability.** None — no service. Hook scripts never block; `sync_claude_md.py` prints `created` / `updated` / `already up to date`.
- **Uninstall.** Not provided for the main install (symlinks + pointer survive a `git rm`). `make expert-uninstall` reverses the overlay.
- **Tests.** Fifteen modules across `arch-coherence/tests`, `doc-coherence/tests`, `llm-summary/tests`, and `scripts/tests` — covering every check script plus `check_face_orchestration`, `init_project`, `doctor`, `sync_claude_md`, and `session_check_sync`. Still untested: `expert_mode.py`, `sync_md_to_obsidian.py`, the two bash hooks, four of the five Python hooks (`session_check_sync.py` is the tested one), and `./install`.

### §2.11 Weirdness

- **The skill spec is the executable artifact.** `llm-summary/README.md` is a Markdown contract a model reads and then *executes by drafting Markdown*. The generator is the model; the spec is the program; `check_brief.py` can only check, never generate. Looks wrong (no source-to-output transformer); is correct (the model is the runtime; Markdown is the source language).
- **The skill describes itself.** This document is `racecar-llm-summary` applied to the repo that contains `racecar-llm-summary`. Not a paradox: the spec changes with the rules; the brief changes with the source.
- **`./install` is bash but ends in a Python script.** Bash does filesystem primitives; Python does structured rewriting (JSON, ordered HTML-comment markers). Each is the right tool for its phase.
- **`compound-command-allow.sh` embeds an inline Python parser.** Splitting `cmd && cmd2 ; cmd3 | cmd4` while respecting quotes is not cleanly expressible in sed/awk. The hook is bash because Claude Code hands it a bash command; the parsing is Python because bash cannot parse bash safely.
- **Mechanical pre-pass scripts run against the *consumer's* repo, not racecar's.** Each walks up to the CWD's `.git`. They ship as skill content and operate on whichever repo the agent is reviewing.
- **racecar is exempt from its own packaging canon.** It has no `[project]` table, no `[tool.importlinter]` block, and is not one of the four ProjectShapes — there is no DAG or wheel to enforce when the artifacts are standalone scripts and Markdown. The framework imposes import-linter and packaging discipline on consumers without claiming to be a deployable package itself; the VERSION carve-out (commit `745cef1`) makes that exemption mechanical rather than asserted.
- **`templates/` is example, not canon.** The template files illustrate the packaging canon for a consumer to copy; they are not authoritative statements about how racecar operates. The truth lives in `PACKAGING.md` + the check scripts. Reading a template as racecar's own config would invert the source of truth.

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

N/A — no deployed instance. Script exit codes are inlined in frontmatter `external_surface.cli_verbs[].exit` and in §2.7 Flows.

### §3.6 SDKs

N/A — no deployed instance. The install surface is `./install`, `make`, and the slash-command names.

## Confidence

**Least confident**

- §2.2 (Entities): the `ProjectShape` entry treats the four shapes (`src` / `pypkg` / `pypkg+djapp` / `djapp`) as a closed set; if PACKAGING.md grows a fifth shape this brief will lag. Verify against `arch-coherence/PACKAGING.md §Scope` and the `detect_shape` branches in `arch-coherence/scripts/check_packaging.py`.
- §2.1 / §2.4.3 (SessionStart hooks): the claim that both SessionStart loaders fire on exactly the four matchers (startup / resume / clear / compact) is taken from the `upsert_hook` calls in `scripts/sync_claude_md.py`; verify against the `SESSION_*` matcher constants and the `sync_settings` body there.
- §2.5 (Internal contracts): the `subcommands()` / `parser()` "required on Pattern 2/3, forbidden on Pattern 1" rule is transcribed from `arch-coherence/CLI.md §"The three contracts"`; if `_classify` in `check_cli_commands.py` enforces it differently, the script is authoritative. Verify against the current `_classify` / contract-checking code.
- §2.10 (Operational): the test-module count and the `make check` chain are read from the root `Makefile`; the working tree is ahead of committed `6b2038b` (this session added the faces recast, djhtml, docs/summary, and the README/CLAUDE split uncommitted). Verify with `make test` and `grep -n 'check:' Makefile`.
- §2.9 / §2.2 (Faces): `check_face_orchestration.py`'s Tier-3 structural inference (api = cut vertex between faces and lib) is summarized from the rebuilt script; the exact articulation-point algorithm and the single-face `api==lib` collapse edge are authoritative in `arch-coherence/scripts/check_face_orchestration.py` (`_cut_vertices` / `_infer_api`). Verify there and in `arch-coherence/FACES.md §5`.

**Not in this brief**

- Owner identity beyond `shared/PERSONA.md`'s persona JSON — unknown — ask user.
- Adoption — which consumer repos use the templates, which ProjectShape each picked — unknown — ask user.
- Roadmap intent: no `TODO.md` despite `shared/TODO_FORMAT.md` prescribing one — unknown — ask user whether work is tracked elsewhere.
- Purpose and intended invocation of `scripts/sync_md_to_obsidian.py` (not wired into the Makefile; not referenced from any README) — unknown — ask user.
- Whether `gstack` is publicly available or owner-private — unknown — ask user.
