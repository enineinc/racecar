# racecar: manifesto

Why racecar exists, and the theses it is built on. The doctrine docs (`shared/`, `arch-coherence/`)
say *how*; this says *why*. It is the one place that argues the frame; everything else assumes it.

## The want

Build trustworthy systems with AI across unrelated domains, at velocity. Not one polished app: a
portfolio of them, in domains that share no code (energy trading, storage analytics, education and web
SaaS, regulatory data), run by a small team plus AI without the canon drifting out from under it.
racecar is the operating discipline that makes that possible.

## Mechanical over heuristic: the trust thesis

A check you cannot reproduce is not a check. Every gate in racecar is deterministic: a script that
fails a violation by naming `file:line`, never a model asked to judge. The model is the last, deferred
stage, used to *mechanize* judgment (turn a rule into a deterministic check) or for irreducible
judgment fed by deterministic pre-filtering, never as the gate itself. The rule of thumb: the detector
must have lower entropy than the thing it watches. An LLM watching an LLM is not a detector; it is a
second source of the same noise. Most AI-assisted tooling puts the model in the loop as the arbiter;
racecar puts it last.

Corollary: AI multiplies foundations, it does not replace them. On a strong foundation it is leverage;
on weak judgment it amplifies slop faster. So the foundation, the deterministic canon, is the thing
worth building.

## Drift is the enemy: one home per rule

Every rule lives in exactly one canonical place; everything else points to it. Two homes for a rule is
two places it diverges, which is zero places it holds reliably. Drift is fought structurally first
(eliminate the surface: one home), then by automatic per-change checks, then by periodic sweep, in that
order. A local fix to a drift symptom masks the global cause; resolve it at the largest frame that
explains it.

## Agent-grade software is data-plane-dominant: the architecture thesis

The packages worth building for an agent connect to real data: broad in volume, shallow in complexity.
The more useful the package, the more data it moves, and the smaller the ORM-governed *fraction* of the
system becomes. The ORM is a control-plane tool (auth, config, audit, identity: low-volume,
relational), right for that and wrong for a shallow firehose. So the architecture inverts the
conventional Django repo: the **library is the center**, Django-free, holding the data plane; the ORM
is **confined** to a server that touches the data plane never. The `src/` vs `server/` split is that
confinement made physical. The conventional ORM-centric repo governs the part that *shrinks* as the
system gets more useful; racecar governs the part that grows.

From that one thesis the whole shape follows: the library at `src/<pkg>`, surfaces (`cli` / `rest` /
`mcp`) as thin adapters over one `api`, the server database-light, and the Authorization Server the
only stateful piece (it owns exactly the control-plane state the ORM is for).

## One canon, many repos: the portfolio thesis

racecar is not a tool you run on a repo; it is the operating system of a portfolio. One canon governs N
unrelated codebases so a small team plus AI can run all of them without each drifting into its own
dialect. The cost of the canon amortizes across the fleet; the leverage is at fleet scale, not
single-repo scale. The proof, therefore, is not that it works on one repo (it does) but that one canon
change propagates across the fleet cheaply, and that racecar can normalize itself. Until the fleet runs
on it, the portfolio thesis is intent, not fact.

## Judgment over execution

The scarce, irreducible thing is knowing what to build and where; the doing is increasingly cheap.
racecar exists to make the cheap part trustworthy and reproducible so the scarce part, judgment, is
where the human time goes. Tooling confirms; the owner authorizes. The checks catch error
mechanically; they never decide. Responsibility stays with the owner and is not delegable to a gate.

## What would prove it wrong

Held to its own standard, racecar must be falsifiable:

- If the fleet migration grinds into bespoke per-repo patching, the portfolio thesis fails: it is N
  copies of a dialect, not one canon.
- If a deterministic gate cannot express a rule and an LLM has to judge it, the trust thesis has a hole
  at that rule.
- If the library-centric shape forces the data plane through the ORM anyway, the architecture thesis is
  wrong for that class of package.

The theses earn their place by surviving the fleet, not by being well-argued here.
