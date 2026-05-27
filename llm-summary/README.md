# LLM Summary — Shareable Knowledge Package

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

Generator (not a review lens). Produces a Markdown bundle in `docs/$repo/` designed to be **shared as a single file** — drag it into Claude, Gemini, or ChatGPT (mobile or desktop) and have a productive conversation about the system without source access. The intended consumer is **another person using their own LLM** to ask questions about your ideas and products, learn how the system works, and reason about next steps. The author also uses it themselves on mobile to noodle on refactors and direction without uploading the repo.

Distinct from `CLAUDE.md` / `/init` (operational, in-repo, for an agent writing code), `/document-release` (post-ship CHANGELOG for human readers), and the racecar review lenses (compliance, not handoff). It is also **not** a reconstruction-grade specification — earlier iterations of this skill targeted full system rebuild; that use case proved theoretical and was killed. The brief now optimizes for **interview-quality**: a recipient can ask the LLM about the system and get grounded answers about concepts, design intent, and surface.

## When to use

- "I want a single file I can share with a collaborator / partner / investor / customer and let them interview it via their own LLM."
- "I want to brainstorm refactors or next steps from my phone without uploading the repo."
- "Capture a portable system snapshot for someone who won't have source access."

Do not use this skill for code-writing handoff (that's `CLAUDE.md`), formal release docs, or reconstruction-grade specification.

## Conventions

- `$repo` = repo root basename, lowercased, with any character outside `[a-z0-9_-]` replaced by `-`. `$REPO` = `$repo` uppercased.
- `$subsys` / `$SUBSYS` = subsystem dir basename, same rules.
- Placeholders in this spec use `$X` notation; they are not shell variables.
- Main brief: `docs/$repo/$REPO.md`.
- Subsystem brief: `docs/$repo/$subsys/$REPO-$SUBSYS.md`.
- Intra-file references use `§N.M`; cross-file references within a bundle use bare filenames.
- `## Confidence` lives in the main brief only.
- Heading depth **in the brief**:
  - H1: brief title only (`# <System> — Knowledge Package`).
  - H2: top-level output sections (`## §1. Map`, `## §2. Implementation`, `## §3. Live access`) and `## Confidence`.
  - H3: subsections (`### §1.1 Purpose`, `### §2.5 Internal contracts`, etc.).
  - H4+: nested structure inside a subsection.

## Frontmatter (YAML)

The brief opens with a YAML frontmatter block between `---` fences **before the H1**. The frontmatter carries (a) bundle metadata and (b) the **three relational sections** a recipient queries deterministically via their LLM: **entities** (class-level), **relationships** (the inter-entity DAG), **external surface** (endpoints). Everything else — design decisions, weirdness, flows, configuration, internal contracts, narrative — lives in the markdown body.

Schema:

```yaml
---
generator:
  name: racecar-llm-summary
  version: "X.Y.Z"              # from racecar/VERSION
target:
  repo: <$repo>
  sha: <short git SHA>
  date: <ISO date>
bundle:
  - <$REPO>.md                  # main brief; plus any overflow siblings by bare filename

# §2.2 — class-level identity only (no field tables; no per-field detail)
# Use `case: none` for **conceptual/behavioral primitives** the system reasons
# about that aren't stored anywhere (e.g., a Lens, a Verdict, a Finding, a
# severity tier). They have purpose + notes but no path/count/fields.
entities:
  - name: <ClassName>           # required; for content_tree case, use the dimension name
    case: db_backed | on_disk_managed | content_tree | none     # required enum
    lifecycle: realized         # realized (default) | deprecated | planned
    purpose: <one sentence>     # required: what this class represents in the domain
    parent: <string>            # optional
    notes: <string>             # optional class-level note (anything that isn't a field)
    # Optional, content_tree only:
    path_pattern: <string>      # e.g. data/<datatype>/<curriculum>/<programme>/...
    count: <int|string>         # number of files; use 'none on disk' for `lifecycle: planned`
    validator: <string>         # tool that checks it

# §2.3 — the DAG between entities; omit key when no relationships
relationships:
  - from: <Class>
    to: <Class>
    cardinality: "1:1"          # required: "1:1" | "1:N" | "M:N" — must be quoted
    on_delete: CASCADE          # OPTIONAL: CASCADE | PROTECT | SET_NULL | DO_NOTHING | RESTRICT — omit for non-DB / M:N edges
    fk_column: <string>         # optional
    owner_side: <Class>         # optional but recommended
    notes: <string>             # optional

# §2.4 — by surface kind; omit kinds with zero entries
external_surface:
  http_routes:
    - method: GET               # GET | POST | PUT | PATCH | DELETE | HEAD | OPTIONS
      path: "/api/v1/accounts/{slug}/"   # must be quoted when it contains `{` — PyYAML reads bare `{slug}` as a flow mapping
      view: <string>            # handler / view name
      name: <string>            # url name
      auth: <string|list>
      throttle_scopes: [<string>]   # optional
      status_codes: [<int>]     # optional
      side_effects: <string>    # optional
  cli_verbs:
    - verb: <string>            # e.g. 'xeno data status'
      module: <string>          # dotted path
      args: <string>
      behavior: <string>
      exit: <int|string>        # optional — put a single exit code or short pattern here ("0" / "0|1" / "0 clean, 1 dirty"); only defer to body prose when exit semantics are flow-specific and need narrative
  library_exports:
    - name: <string>
      module: <string>
      signature: <string>
      behavior: <string>
  webhooks:                    # incoming HTTP from external systems
    - source: <string>         # who sends it (e.g. 'stripe', 'github')
      path: <string>           # quote if contains `{`
      method: POST
      auth: <string>           # signature / HMAC / token / none
      behavior: <string>
  signals:                     # in-process events (Django signals, blinker, custom dispatch)
    - name: <string>           # required: e.g. 'post_save', 'order_placed'
      sender: <string>         # required: dotted class path that fires it (e.g. 'apps.orders.models.Order'); for app-level dispatch use the AppConfig label
      handler: <string>        # required: the receiver function or class name
      module: <string>         # where the receiver lives (dotted path)
      behavior: <string>
---
```

`X.Y.Z` is the skill version — read from `racecar/VERSION`. The `bundle:` list names every file the consumer must upload together.

**Validation:** `python3 <racecar>/llm-summary/scripts/check_brief.py [<bundle-path>]` parses the frontmatter, validates the schema, and checks required body headings + `## Confidence` markers.

## Discovery procedure

Each row keyed to its output section. Cite paths or commit SHAs in the draft. Parallelize independent reads per [`../shared/OPERATIONAL.md`](../shared/OPERATIONAL.md). Finish discovery before drafting.

Where the repo already ships per-module design docs (`DESIGN.md`, `ARCHITECTURE.md`, `SYSTEM.md`, `PROTOCOL.md`, `PLAYBOOK.md`, per-app READMEs), cite them with `<path> §N` rather than retranscribing — the bundle adds value by structuring what's missing or scattered, not by duplicating a single canonical home.

| → Section | Walk |
| --- | --- |
| §1.1 Purpose | Read root `README.md` in full. Extract problem statement, named user/audience, user-facing primitives. Note absences rather than inventing. |
| §1.2 Modules | Top-level dirs + per-module READMEs. One-line purpose per module. |
| §1.3 Vendors | Dependency manifests filtered to paid SaaS, cloud platforms, and sibling local packages. One paragraph. |
| §2.1 Runtime | Every root config file + every entry point in full. Read **every** settings module (dev, production, test). Name each runtime separately when a system ships more than one. |
| §2.2 Entities | Find every persistent shape: ORM model classes, on-disk artifact types, structured content tree dimensions. Each entry needs a one-sentence purpose; no field tables. Mark `lifecycle: deprecated` for entities still in source but no longer authoritative; `lifecycle: planned` for documented-but-not-realized dimensions. |
| §2.3 Relationships | FKs, M2M, polymorphic, JSON references at the class level. Cardinality (quoted), direction, owner side. `on_delete` only where applicable. |
| §2.4 External surface | Every user-callable: HTTP route, CLI verb, library export, gRPC, webhook, signal. Split by kind in the frontmatter; one sub-key per kind. |
| §2.5 Internal contracts | Cross-module wire shapes: queue/event schemas, IPC formats, plugin/hook contracts. One bullet per contract — name, producer, consumer(s), one-line purpose. |
| §2.6 Configuration | Env vars, feature flags, settings keys, secrets. One bullet or table row per — name + one-line effect. Mark `(prod-only)` / `(dev-only)` when dev and production diverge. |
| §2.7 Flows | Each meaningful operation input→output as numbered prose. Idempotency and failure modes inline. |
| §2.8 Seams | Plugin registries, ABCs, hook points. Bullets; one recent example with file path per seam. |
| §2.9 Design decisions | `git log --oneline -100`, `ADR/`, `docs/decisions/`, `CHANGELOG.md`. Rejected alternatives, incidents, constraints. |
| §2.10 Operational | Install/build steps, system dependencies, scheduled jobs, healthcheck endpoints, observability hooks. State both sides where dev and production differ. |
| §2.11 Weirdness | Looks-wrong-but-correct, looks-right-but-isn't, design-rule reasons. |
| §3.1–3.6 | Pick the case:<br>• **Deployed service** — full §3: deploy manifests, auth + redacted token, OpenAPI/GraphQL/Postman, rate limits, healthchecks, SDKs.<br>• **Pure library** — stub `N/A — no deployed instance` and collapse §3. §3.6 (SDKs) also stubs `N/A — no deployed instance` since there's no public surface to wrap.<br>• **Library with network dependency** — document the upstream's contract: base URL, auth shape, the operations you call, errors you handle. State the case in §3's opening line. Sub-rules:<br>&nbsp;&nbsp;– §3.1 table: include a `local` row with `n/a — library` in the base-URL cell + the local invocation entry-point in the access cell (e.g. `python -m <pkg>`), then the upstream environment rows (UAT / PROD / …).<br>&nbsp;&nbsp;– §3.5 errors: add an `origin: upstream \| library` column **as the last column** when both sides raise — the consumer needs to know which side to handle.<br>&nbsp;&nbsp;– §3.6 SDKs: `none — neither this library nor the upstream publishes one` is a legitimate single-line stub when both sides lack an SDK. |

## Output contract

| §N.M | Form | Stable shape / location |
| --- | --- | --- |
| §1.1 Purpose | paragraph | problem, users, primitives |
| §1.2 Modules | short markdown table | name, one-line purpose |
| §1.3 Vendors | one paragraph | paid SaaS, cloud platforms, sibling locals |
| §2.1 Runtime | prose + entry-point table | CLI / library / service / daemon (one **or more**); entry points; state location |
| §2.2 Entities | **frontmatter `entities`**; body §2.2 has narrative gloss (per-case overview, anything not capturable in YAML) | See [Frontmatter schema](#frontmatter-yaml). Class-level only — no fields. |
| §2.3 Relationships | **frontmatter `relationships`**; body §2.3 has the ERD (ASCII or Mermaid) | See [Frontmatter schema](#frontmatter-yaml). |
| §2.4 External surface | **frontmatter `external_surface.{http_routes, cli_verbs, library_exports, webhooks, signals}`**; body §2.4 has per-call detail for load-bearing routes only | See [Frontmatter schema](#frontmatter-yaml). One sub-key per surface kind. |
| §2.5 Internal contracts | markdown bullets in body | name → producer → consumer(s), one-line purpose |
| §2.6 Configuration | markdown bullets or table in body | name + one-line effect; mark `(prod-only)` / `(dev-only)` if diverges |
| §2.7 Flows | numbered prose | sequence input→output; idempotency and failure modes inline |
| §2.8 Seams | bullets | where new behavior plugs in; one recent example with file path per seam |
| §2.9 Design decisions | bullet per decision | choice, rejected alternative, why (incident / constraint), ADR or commit SHA |
| §2.10 Operational | bullets | install, deps, schedules, healthchecks, observability |
| §2.11 Weirdness | paragraph per item; soft cap 5–8 items | looks-wrong-but-correct OR looks-right-but-isn't + the design-rule reason |
| §3.1 Environments | table | env, base URL, region, access, credentials source |
| §3.2 Auth | prose + redacted example token | flow, lifetime, refresh, scopes |
| §3.3 Operations | per-endpoint subsection for load-bearing routes | method, path, request schema, response schema, status codes, JSON example req + resp |
| §3.4 Rate limits | bullets | per-endpoint limits, retry expectations, idempotency-key behavior |
| §3.5 Errors | table | code or message, meaning, recommended client action |
| §3.6 SDKs | bullets | pointers, not contents |

Voice per [`../shared/VOICE.md`](../shared/VOICE.md): terse, name the claim then support it. No marketing language ("powerful," "robust," "elegant"). Tables for parallel-shape items; bullets and paragraphs only where the row above specifies.

## Query examples

The finished bundle, dragged into a chat with the recipient's LLM, answers questions like:

- What is this system and who is it for?
- How does it work conceptually? What are the core primitives?
- What does entity X represent? What relates to it?
- What endpoints exist? What does endpoint E do? Show me an example request and response.
- Why was approach P chosen over Q? What incident or constraint motivated it?
- What behavior in module M looks wrong but is intentional?
- What's working today? What's documented but not yet built? Where is it going?
- How do I run this locally? How is it deployed?
- What does error code C mean to a client?
- Could it do W? What would need to change?

Every rule in this spec serves at least one of these question classes — or navigation between them (§1.2 modules), classification (§1.3 vendors), or operational handoff (§2.10). Rules with no such purpose are dead weight.

## Bundle lifecycle

**Location.** Default `docs/$repo/`. If `docs/` already houses Sphinx (`conf.py`), MkDocs (`mkdocs.yml`), build outputs (`_build/`, `_static/`), an index (`index.md`), or ADRs (`decisions/`, `adr/`), surface the collision and fall back to `briefs/$repo/`. User override accepted.

**Re-run.** Ask before overwriting an existing `$REPO.md`. Sibling overflow files the new run did not produce are listed as orphans to the user (the user may have edited them); the validator treats orphans as errors so the bundle is internally consistent.

**Subsystem briefs.** Invocation: `one brief per subsystem — <path1>, <path2>, …`. Each subsystem produces a self-contained bundle at `docs/$repo/$subsys/$REPO-$SUBSYS.md`. No top-level meta-brief in subsystem mode. Cross-references between sub-bundles use relative bare filenames.

**Handoff.** Generator's responsibility ends at write. The recipient drags the file (or files) into their chat.

## Structural budget

Bounds are expressed by structure, not token count. The required conditions below are mechanically enforced by `python3 <racecar>/llm-summary/scripts/check_brief.py` — run it before handing the bundle off.

Required at write-time:
- Frontmatter YAML parses and matches the [schema](#frontmatter-yaml).
- Every required body heading is present (`## §1. Map`, `### §1.1`–`§1.3`, `## §2. Implementation`, `### §2.1`–`§2.11`, `## §3. Live access`, `### §3.1`–`§3.6`, `## Confidence`). Stub `N/A — <reason>` permitted where the spec allows (e.g., §3.* for pure library).
- §2.4 frontmatter surface kinds: no single kind exceeds 5 entries without being its own first-class key.
- `## Confidence` present at end of main brief with ≥3 `**Least confident**` bullets and ≥1 `**Not in this brief**` bullet (bolded markers, exact).
- The `bundle:` frontmatter list names exactly the sibling `.md` files in the bundle directory (no orphans, no missing).
- Spine/body agreement: any snapshot SHA restated in the brief's preamble (the text before `## §1`) matches `target.sha` in the frontmatter. Commit SHAs cited in §2.9 design history are out of scope — they are different commits, not the snapshot point.

Target size: 400–800 lines per brief (3–6K tokens). The previous reconstruction-grade format produced 900–1400 lines; the trimmed schema (class-level entities, no field tables, narrative §2.5/§2.6) brings the brief back to single-file mobile-shareable scale.

Overflow files (`$REPO_*.md`) are no longer routine — the trimmed shape rarely needs them. **Subsystem-split heuristic**: signals to consider — ≥25 entities, ≥3 runtimes, or >800 lines after a clean trim. **Crossing any one is a signal, not a verdict.** Split only when the relationship DAG decomposes cleanly along subsystem boundaries (sub-bundles don't redeclare the same anchor entities) **or** the brief still exceeds 800 lines after trimming. A tightly-coupled DAG around a small anchor set (e.g. `Site`/`Artifact`, `Order`/`Customer`) should stay monolithic even at 40+ entities. A multi-runtime repo whose runtimes share entity vocabulary should also stay monolithic. **Library-with-network-dependency** briefs may legitimately run 800–850 lines due to the upstream-contract content in §3; treat that as the soft cap for the case.

## Self-check

End the main brief with `## Confidence`. Two parts, each introduced by a literal bolded marker on its own paragraph: `**Least confident**` and `**Not in this brief**`. The bolding is required — `check_brief.py` matches against the exact markdown.

**Least confident** — at least three claims (the load-bearing doubts), each citing the file or commit that would verify it. Use concrete source-cited identifiers, not `<placeholders>`:

```
- §2.2 (Entities): `PracticeQuestion.practice_engine` choice values (`seeded` / `freeform` / `exambank`) are reconstructed from the `seed_question` and `exambank_question` FK names plus the `taxonomy_*` snapshot field set; the canonical Choices class was not directly sourced. Verify against `apps/activity/ib/models.py`.
- §2.5 (Internal Contracts): the `Catalog.resolve(ref) → Atom(Tfv) | Compound(CompoundId)` dispatcher named in `CLAUDE.md` was not found implemented; the `data/compounds/` directory does not exist on disk. The contract appears documented but unimplemented. Verify against `grep -rn "class Catalog\|Catalog.resolve" djapp/`.
- §2.7 (Flows): the daily-budget enforcement point (per-request middleware? scheduled aggregator?) was not directly sourced. Verify with `git log -S "DAILY_LLM_BUDGET_USD"` and `grep -rn DAILY_LLM_BUDGET_USD djapp/`.
```

**Not in this brief** — bullets for anything a reader might expect that is not derivable from source: revenue model, pricing, customer list, oncall rotation, bus factor, strategic risks, roadmap intent. Mark each `unknown — ask user`. Closes the absence-vs-omission gap.

## Invocation

```
/racecar-llm-summary
/racecar-llm-summary write the bundle to briefs/$repo/ instead of docs/$repo/
/racecar-llm-summary skip §3 — pure library
/racecar-llm-summary one brief per subsystem — apps/ingest, apps/serve, apps/admin
```

Default: discover the current working directory, derive `$repo` / `$REPO` from the root basename, write `docs/$repo/$REPO.md` — or `briefs/$repo/` on `docs/` collision. Ask before overwriting an existing `$REPO.md`.
