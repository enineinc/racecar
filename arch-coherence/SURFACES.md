# Surfaces: lib → api → surfaces

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

One core library exposed through N thin surfaces. This file is the home for the
`lib → api → {cli, mcp, web/django}` doctrine: where orchestration lives, how the
surfaces stay thin, the canonical file names that make surfaces autodiscoverable, and
the one gated import contract that keeps the graph coherent. It is the **surfaces
axis**; the orthogonal **shapes axis** (`src` / `src+server` / `server`)
lives in [`PACKAGING.md`](PACKAGING.md) §"Scope".

For module roles (`__init__.py` / `__main__.py`) see [`PYTHON.md`](PYTHON.md) §1.
For the cli surface's own contract (`commands()` / `subcommands()` / `parser()`)
see [`CLI.md`](CLI.md). For the django surface's layering see [`DJANGO.md`](DJANGO.md).

Sections are ordered as a DAG: most independent first, most dependent last.

## North star (governs everything below)

Two aims, in order: **(1) help write good code; (2) help others who want to write
good code do so.** Dogma is the enemy of both. **Every rule here is HELP, not LAW.**
A rule that imposes a belief by force fails aim (2) — it produces compliance, not
understanding — and is therefore suspect under aim (1) as well. When a rule below
reads as a wall, that is a defect in the rule. The test applied throughout: *gate
genuine defects, surface choices.* A cycle is a defect; a surface reaching past `api`
is a choice. The first earns a gate, the second earns a finding.

Surface→worker routing is a **named convention with an advisory detector**, not a hard
`forbidden` `import-linter` contract. Walling it would break racecar's own
[`OWNERSHIP.md`](../shared/OWNERSHIP.md) doctrine ("tooling confirms, the owner
authorizes; a green ledger is confirmation, not a merge gate") and
[`DRIFT.md`](../shared/DRIFT.md) ("detect and surface"). The names are fixed (an
autodiscovery contract); the import shape is not.

## 1. The shape

```
                   ┌──> cli  (__main__)
   lib ──> api ────┼──> mcp
                   └──> web/django
```

The arrow reads **"provides for"**: `lib` provides for `api`, `api` provides for
each surface. **Import edges run the reverse**: a surface imports `api`, `api` imports
`lib`. The graph is a DAG; [check 1 Acyclicity](AXIOMS.md#1-acyclicity-root-axiom)
is non-negotiable here as everywhere.

Three roles:

- **lib (worker).** The engine. Pure capability: compute, fetch, transform,
  persist. No knowledge of who calls it, no input resolution, no credential
  acquisition, no defaulting policy.
- **api.** The engine **plus the orchestration policy**: resolve inputs, seed
  credentials, apply defaults, dispatch to the right worker. `api` is a
  **superset of `lib` in reach**: everything `lib` can do, plus the policy that
  makes it callable without ceremony. It is **not** a peer surface and **not** a 1:1
  re-export; the exposed surface is curated.
- **surfaces.** **A surface is a wrapper on `api`** — whether `cli`, `mcp`, `web/django`,
  or anything else. That is the definition: a thin **presentation adapter** that
  translates input from its transport, calls `api`, renders output in its
  transport's idiom, and does nothing else. It holds no orchestration of its own;
  strip the transport and the surface vanishes, leaving `api`. The shipped surfaces are
  `cli` (a `__main__` per [CLI.md](CLI.md)), `mcp` (an MCP tool server), and
  `web/django` (views/services per [DJANGO.md](DJANGO.md)); a cron entry, a webhook
  receiver, or a gRPC servicer is equally a surface if it wraps `api`. **If it does not
  wrap `api`, it is not a surface** — it is either part of `api` (orchestration) or part
  of `lib` (capability), and belongs there.

### Correction to racecar's prior packaging model

Racecar's earlier model conflated `api` with `lib`: "the installable package **is**
the api." That holds **only when surfaces = 1**: a single `__main__` over a library is
its own de-facto api, and the conflation costs nothing. At **N surfaces it breaks**.
With no `api` vertex, the orchestration (resolve inputs, seed credentials, default,
dispatch) has nowhere to live but **inside each surface**, so it triplicates across
`cli`, `mcp`, and `django`. Three homes for one policy is three places it drifts,
Tier 1 drift per [`DRIFT.md`](../shared/DRIFT.md). `api` is the **one home** for
orchestration; the surfaces hold none of it.

## 2. Named convention, not a wall

The roles above map to **canonical per-vertical file names**:

| File | Role | Rule |
|---|---|---|
| `__init__.py` | namespace only | empty or docstring; never code or re-exports (§6) |
| `lib.py` | the lib's outward surface | may point to descriptively-named internals |
| `api.py` | orchestration policy | the one home for resolve/seed/default/dispatch |
| `__main__.py` | the cli surface | thin adapter per [CLI.md](CLI.md) |
| `mcp.py` | the mcp surface | present only when an MCP surface exists |

**The name is an autodiscovery contract, fixed; the shape is not walled.** This is
the Django model, and it is the resolution of the "is fixing names dogma?" question.

Django fixes a name **exactly** for the roles its framework must **autodiscover**,
no exceptions, because the framework *looks the name up*:

- `admin.py` — `AdminConfig.ready()` calls `autodiscover_modules('admin')`.
- `templatetags/` — `{% load x %}` resolves `<app>/templatetags/x.py`.
- `templates/` — `APP_DIRS=True` looks in `<app>/templates/`.
- `models` — the app registry imports `<app>.models` during `populate()`.
- `migrations/` — the migration loader reads `<app>/migrations/`.

Django leaves a name **free** for roles you wire **by hand** — `views.py`,
`urls.py` — because Django never looks for them; you reference them explicitly.

**The discriminator is: who does the lookup.** Framework looks it up → fix the
name. You wire it → free name. racecar must **autodiscover surfaces to apply its
lenses** (which module is the api? which is the worker?), so by Django's own logic
the surface names should be fixed. `mcp.py`-mandatory-**if you have an mcp surface** is
exactly `admin.py`-mandatory-**if you have admin**. That is a contract, not dogma.

The fixed thing is the names, not the import shape: there is no import wall (§3). A
project that names its files differently is not in violation — it declares the mapping in a manifest (§4 Tier 2). The canonical
name is the **default you receive** (§5), not a cage.

## 3. Per-vertical co-location

A project has verbs (features): `catalog`, `fetch`, `report`; `prices`,
`dispatch`. For **each verb**, its roles live in the **same submodule**, canonically
named:

```
src/<pkg>/
  <verb>/
    __init__.py   ← namespace only
    lib.py        ← lib role   (the engine for this verb)
    api.py        ← api role   (orchestration policy for this verb)
    __main__.py   ← cli surface   (thin adapter; calls <verb>.api)
    mcp.py        ← mcp surface   (when present)
  shared/         ← shared primitives BELOW all verticals
    <primitive>.py
  config.py       ← environment layer (see PYTHON.md §1)
```

Co-location keeps a vertical's roles readable as a unit and lets verticals move
independently. **Shared primitives sit in a deeper layer below all verticals**: a
vertical reaches *down* into `shared`, never *sideways* into a sibling vertical.

The `mcp` and `web/django` surfaces are often **cross-vertical** (one MCP server
exposes all verbs' tools; one Django app routes all verbs' views). They live in
their own surface module (`mcp.py` / a server tree) and import each vertical's `api`.
They stay thin: a tool/view per verb that translates and delegates.

## 4. Enforcement: gate defects, surface choices

Two kinds of rule, and they get different machinery.

**Gate genuine defects.** A cycle or an upward import is *incoherent* — like a type
error, catching it is unambiguous help. **Acyclicity + direction stay a hard gate**,
via a single `import-linter` `layers` contract (the [layer-integrity](AXIOMS.md#3-layer-integrity)
axiom applied to the tiers). This is the **only gated import contract** the surfaces
axis adds.

**Gate the open surface.** A generated surface exposes `api` to the untrusted outside, so it is
**closed by default**: auth and per-tool scope are a hard gate, not a deployer's afterthought. The
doctrine and its mechanical check are [`AUTH.md`](AUTH.md).

**Surface choices.** A surface reaching past `api` into a worker is *coherent* — it
imports a real module and the graph stays acyclic — just **dispreferred** (a surface
that imports the worker directly tends to grow its own orchestration). Walling it
produces compliance, not understanding, and contradicts OWNERSHIP and DRIFT. So it
is **detected and surfaced**, not gated: [`check_surface_orchestration.py`](scripts/check_surface_orchestration.py)
reports it as a **Finding** (exit 0 by default; `--strict` opts into exit 1 for a
project that wants its own harder line). The old `forbidden` contract is removed.

**The test for any check:** does the forbidden state ever have a legitimate
instance? If yes → detect and surface. If never (it is always a defect) → gate.
Hold even this as judgment, not a new law.

### The one gated contract (copy-pasteable)

Parameterized by package name `<pkg>` and verb names `<verb_a>`, `<verb_b>`. Add to
the library pyproject's `[tool.importlinter]` alongside the layered-DAG contract
from [`PACKAGING.md`](PACKAGING.md) §3. `lint-imports` then reports
`Contracts: N kept, 0 broken.`

```toml
[tool.importlinter]
root_package = "<pkg>"

# Tier order: surfaces > api > lib > shared, downward only. The ONE gated contract.
# Pipe-separated siblings in a tier cannot cross-import (verticals stay independent).
[[tool.importlinter.contracts]]
name = "<pkg>: surface/api/lib tiers"
type = "layers"
layers = [
    "<pkg>.<verb_a>.__main__ | <pkg>.<verb_b>.__main__ | <pkg>.mcp",  # surfaces
    "<pkg>.<verb_a>.api | <pkg>.<verb_b>.api",                        # api (independent siblings)
    "<pkg>.<verb_a>.lib | <pkg>.<verb_b>.lib",                        # lib (independent siblings)
    "<pkg>.shared",                                                   # primitives below all verticals
]
# The environment layer (<pkg>.config) is intentionally NOT a layer row:
# any tier may read it (environment-layer exception, README.md).
```

There is **no second `forbidden` contract.** Surface→worker is the advisory detector's
concern (§7), not a wall. A project with a single surface still benefits from the
`layers` contract with one surface row — the verticals' independence (pipe-separated
siblings) is worth gating from the first vertical.

## 5. Role identification: declare, then verify

To apply its lenses racecar must know which module is the `api`, which is the `lib`,
which are surfaces. It identifies roles by **structural signature, not filename alone**,
so a project can rename. This reuses racecar's existing **declare-then-verify**
pattern (`import-linter` already works this way: you declare the layer order, the
tool verifies the graph obeys it).

Three tiers, ordered by explicitness:

1. **Canonical name** (`lib.py` / `api.py` / `mcp.py` / `__main__.py`). The name
   *is* the declaration — the Django autodiscovery model (§2). Primary. Treat these
   as architecture's **type hints**: optional, but when present the checker is
   exact.
2. **Explicit manifest** (`[tool.racecar.roles]`). For projects that name files
   differently — declare role → module per vertical:

   ```toml
   [[tool.racecar.roles.vertical]]
   name  = "prices"
   lib   = "athena.prices.engine"
   api   = "athena.prices.orchestrate"
   surfaces = ["athena.prices.__main__", "athena.mcp"]
   ```

3. **Structural inference** (fallback; reports its own uncertainty):
   - **cli** = a `__main__.py`, or `if __name__ == "__main__"` + an argparse parser.
   - **mcp / web** = a transport signature: imports an MCP SDK / JSON-RPC stdio
     loop; or `flask` / `fastapi` / `django`.
   - **api** = the **articulation point**: the single in-vertical module every surface
     routes through to reach the lib (the cut vertex between the surface set and the
     lib, computed on the business-logic subgraph — the env layer and stdlib, which
     surfaces may import directly, are excluded).
   - **lib** = the transport-less **sink** below `api`: the node `api` imports that
     fans out to internals and imports nothing further in-vertical.

**Declare, then verify.** The name or manifest *declares*; the structure *verifies*.
A declared-`api` that is **not** the cut vertex is a Finding. When inference cannot
find a clean cut vertex (the surfaces touch the lib directly, with no module mediating
them), **the non-classifiability is itself the drift finding** — identifiability and
good structure are the same property. A vertical you cannot cleanly classify is a
vertical whose orchestration has no single home.

**Edge: single-surface `api == lib` collapse.** At exactly one surface there is no
separate cut vertex — the surface imports the lib directly and `api` legitimately
collapses into `lib` (§1: at surfaces=1 the conflation costs nothing). Read the surface
count **before** expecting a distinct `api`, or single-surface verticals false-positive.

**LLM-last.** All three tiers are deterministic. Genuine ambiguity is resolved by
the owner adding **one manifest line**, never by a model. An LLM asked to guess the
api would be a detector with **higher entropy than the thing it watches**, which
[`DRIFT.md`](../shared/DRIFT.md) forbids ("the detector must have lower entropy than
the thing it watches").

## 6. Supporting rules

- **`__init__.py` is namespace-only.** Empty or a docstring — never code, never
  re-exports. Re-exporting a vertical's symbol up to a parent `__init__` makes a
  **second home** for it (Tier 1 drift) and, when the symbol is named after a
  submodule, **shadows** that submodule — a real import breakage (verified on the
  `lib → api → surfaces` proving ground). Environment-layer config goes in a `config`
  module, not `__init__` (PYTHON.md §1 permits either; this narrows to `config`).
- **Cardinality vs mechanism.** `api` models `n` accounts/tenants as the **general
  case** with `n = 1` as the default — a key into existing storage and a loop that
  happens to run once (`accounts["default"]`, `for account in accounts:`). That is
  concrete cardinality; build it. An injected **resolver** abstracting *where*
  accounts live (filesystem vs DB vs vault) is a **second mechanism**; defer it
  until a second backend actually exists. One implementor is a function, not a
  protocol. (YAGNI; the boundary stated mechanically: model cardinality when
  multi-account is plausible, introduce the mechanism when the second implementor
  lands.)
- **`mcp` is a first-class surface with no prior art.** You are defining it; keep
  `mcp_tools` in the surface taxonomy (§8). Reserve `mcp.py`; **materialize it when
  the surface is built — no empty stubs.** **Amendment (transport-dependent home):**
  `mcp.py` is the home for a **stdio** tool server. When the mcp surface is delivered
  over **HTTP** (Streamable HTTP, behind a web server), it is a **route family in
  the web/django surface, not a standalone `mcp.py`** — one Django project, launched
  as two processes (one per surface): `api.*` → REST, `mcp.*` → the MCP endpoint,
  each vhost selecting its surface's settings module at boot. See
  [`GENERATION.md`](GENERATION.md) §4. The discriminator is transport: stdio →
  `mcp.py`; HTTP → surface.
- **Borrow Django's good, leave its bad.** Good: convention with overridable
  defaults, scaffolding, explicit-not-magic, app = vertical, name-as-autodiscovery
  contract. Bad: the global mutable settings singleton, active-record leakage,
  implicit magic. "Take all the good" only works paired with "leave the bad," else
  the borrowing becomes its own dogma.

## 7. The advisory detector

`check_surface_orchestration.py` is the **surface, not the gate**. The `layers`
contract (§4) proves the import *topology* is clean; it cannot see a surface that
satisfies the topology and still **restates orchestration in its own body**
(re-resolve inputs, re-default, re-seed credentials) calling only `api` primitives.
That restatement is the drift this doctrine prevents, and a green topology hides it.

The detector does two deterministic things, both **advisory** (exit 0 by default;
`--strict` for a project that wants exit 1):

1. **Role identification** (§5): classify each vertical's `lib` / `api` / surfaces via
   name → manifest → structure, and report any vertical that is **non-classifiable**
   (no clean cut vertex) or whose **declared `api` is not the cut vertex**.
2. **Restated orchestration**: extract each surface's `api`-call sequence as a
   normalized token stream and flag a sequence that appears in **two or more**
   surfaces — one orchestration policy with two homes, the signal it belongs in `api`.

Every output is a Finding ("should this live in `api`?"), not a Blocker. This is a
duplication/structure detector in the [PYTHON.md §4](PYTHON.md#4-enforcement) checker
family: lower entropy than the policy it watches, deterministic, LLM-free.

## 8. Surfaces are orthogonal to shapes

The **shapes axis** ([`PACKAGING.md`](PACKAGING.md) §"Scope") answers *how the
project is packaged*: `src`, `src+server`, `server`. The **surfaces axis**
answers *how the one library is exposed*: `cli`, `api`, `mcp`, `web/django`. They
are independent: a `src`-shape, no-Django project can be `lib + cli + mcp`; a
`src+server` project is `lib + cli + django` and may add `mcp`.

| Surface | Status before this doctrine | Recognized as |
|---|---|---|
| `cli` | first-class ([CLI.md](CLI.md), `check_cli_commands.py`) | `__main__` / `commands()` surface |
| `api` | **absent**, conflated with `lib` (§1) | first-class: the public function surface, the one home for orchestration |
| `mcp` | **absent from all of racecar** | first-class: an MCP tool server surface, `mcp.py`, `mcp_tools` surface kind |
| `web/django` | a packaging *shape* only | reframed as a **surface** over the shared lib ([DJANGO.md](DJANGO.md)) |

The `django` shape and the `django` surface are two views of one thing: the shape says
*the repo ships a Django app*; the surface says *that app is a thin adapter over `api`,
holding no orchestration of its own*.

**Reconcile with llm-summary.** The brief's `external_surface` kinds
([llm-summary/README.md](../llm-summary/SPEC.md#frontmatter-yaml)) enumerate surfaces
from the outside: `http_routes` (django), `cli_verbs` (cli), `library_exports`
(api), plus `webhooks` and `signals`. The `mcp` surface adds the `mcp_tools` kind.

## 9. Placement principle

A concern lives at the **most central layer that CAN handle it**. It moves outward
only on **genuine inability**, never because a surface is "more user-facing." Central
placement is the default; outward movement carries the burden of proof.

**Worked example: credential prompting.** `getpass` works from any layer, so
credential prompting **lives in `api`** (the most central layer that can do it). The
no-tty surfaces (`mcp`, `django`, a cron entry) do **not** relocate the concern outward:
they cannot prompt either, so moving it buys nothing. They **fail loudly** when a
credential is absent and require it to be **provisioned out of band** (env var,
secret store, state dir). The concern's home stays `api`; the no-tty surfaces narrow
*how* it is satisfied, they do not own it.

The anti-pattern this rules out: "prompting is user-facing, so put it in the cli
surface." That pushes the concern outward for a *category* reason, not an *inability*
reason, and now the `mcp` and `django` surfaces each reinvent credential handling —
the same triplication as §1.

## 10. Make the right thing easy

This is the half racecar was missing, and it is why convention spreads where
enforcement does not. Django and Rails won because scaffolding paid back on **day
one**: `startapp` hands you the good shape. ArchUnit, JPMS, and `import-linter` stay
niche because enforcement has **no day-one carrot** — it only ever tells you what
you did wrong.

So the good shape is the **default you receive**, not what you are forced into.
`scripts/init_project.py` scaffolds the canonical vertical pre-wired (the `startapp`
equivalent): `<verb>/{__init__.py, lib.py, api.py, __main__.py}`, the `layers`
contract stub, the co-location already correct. **Scaffold + advisory detector +
docs-that-teach replaces the wall.** That is how the doctrine serves aim (2) of the
north star: you help others write good code by making the good code the easy code,
not by gating the bad code.

## 11. How to apply to a project

Mechanical checklist. Copy, run top to bottom.

1. **Identify the verticals.** List the verbs/features. Each becomes a submodule
   `<pkg>/<verb>/`. (Scaffolding a new one: `python scripts/init_project.py` — §10.)
2. **Co-locate with canonical names.** Per vertical: engine in `lib.py`,
   orchestration in `api.py`, cli adapter in `__main__.py`, mcp adapter in `mcp.py`
   when present (§2, §3). Shared primitives down into `<pkg>/shared/`. Rename freely
   if you prefer other names — then declare them in `[tool.racecar.roles]` (§5).
3. **Move orchestration into `api`.** Pull input resolution, credential seeding,
   defaulting, and dispatch **out of every surface** into `<verb>/api.py`. After this a
   surface holds zero policy.
4. **Thin the surfaces.** Each adapter only translates transport input, calls `api`,
   renders. Apply the placement principle (§9): a concern moves to a surface only on
   genuine inability.
5. **Write the one gated contract.** Add the `layers` contract (§4) to
   `[tool.importlinter]`. There is no second `forbidden` contract.
6. **Verify the gate.** `lint-imports` → `Contracts: N kept, 0 broken.` A broken
   `layers` contract names a sibling-vertical cross-import or an upward import: fix
   the structure.
7. **Run the advisory detector.** `python scripts/check_surface_orchestration.py`. For
   each Finding — a non-classifiable vertical, a declared-`api` that is not the cut
   vertex, or orchestration restated across surfaces — decide whether to move policy
   into `api`. It is advisory; the topology being green does not close this (§7).

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).

## Invocation

> Load `arch-coherence/SURFACES.md`. This project has N surfaces over one library;
> verify orchestration lives in `api`, the surfaces are thin, the canonical file names
> (or a `[tool.racecar.roles]` manifest) identify the roles, and the single `layers`
> contract is present and kept. The surface→worker rule is advisory, not a gate.

> Using `arch-coherence/SURFACES.md` §11, restructure this project to `lib → api →
> surfaces`: identify verticals, co-locate under canonical names, move orchestration
> into `api`, thin the surfaces, write the `layers` contract, verify with
> `lint-imports`, then run the advisory detector.
