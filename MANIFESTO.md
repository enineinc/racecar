---
pnode: [README.md]
summary: >-
  racecar lets every builder stand on the shoulders of the giants and ship more
  rigorous work without giving up much velocity. The principles are old and
  borrowed, and the model has already read the giants; racecar's value is not the
  reading, it is the binding: enforcement at generation time, at file:line,
  force-loaded into every session. What used to be a large-team luxury, rigor
  gated on team scale, on human discipline, and on the assumption that rigor makes
  QA harder, is now affordable to every builder across many unrelated repos, and
  the enforced structure inverts that last gate: with one home and a DAG, bugs get
  fewer and more local and QA gets easier, not harder.
---

# racecar: manifesto

Why racecar exists, and the theses it is built on. The doctrine docs (`shared/`,
`arch-coherence/`) say *how*; this says *why*. It is the one home for the frame; everything
else assumes it. A public essay, if one is ever posted, is a projection of this file, not a
rival to it. The axioms are homed in [`shared/PRINCIPLES.md`](shared/PRINCIPLES.md), grouped as
known principles (P-nn) and racecar principles (R-nn) and enumerated below.

## What racecar really is

racecar is a call to arms, and the call is this: every builder gets to soar.

The trade was always ambition for safety. Reach, and the architecture rots into a mess no one can
hold. Play safe, and you build small, one careful app inside the lines, never the portfolio of
unrelated ambitions you actually wanted. Having both took a large team: architects to hold the
shape, a review priesthood to enforce it. That was the luxury, and it priced everyone else out.
So the solo builder and the small team were told the same thing a model tells itself, that to
think big and fail is worse than to think small and never fail. Keep it simple. Pick one domain.
Do not reach.

That trade is dead. The principles that hold a system's shape under ambition are fifty years old,
DRY, the Acyclic Dependencies Principle, Parnas, Lakos, Dijkstra, Deming, Lehman, Cunningham, and
the model has already read every one. Ask it and it recites Parnas. Reading was never the
problem: a model trained to produce plausible code regresses to the mean of the corpus, which is
mediocre, not to the peak of the theory, which is rare. Knowing the canon and holding to it under
a deadline are different acts. racecar is the second act, the **binding**: the canon force-loaded
into every session and enforced at `file:line`, so the right shape is what you receive, not what
you are trusted to remember. The giants wrote rules for a human who had to be persuaded and then
relied on to comply. racecar makes the rule a check that passes or names the violation.

That is the net, and once the fall is caught you are free to reach. Build big, across many
domains, at velocity, because drift and the bug are caught the moment they appear, not in the
wreckage a year on. It reduces to one sentence: racecar lets every builder stand on the shoulders
of the giants and reach further than a large team could, without the fall. The belief that you
must think small to never fail is the shackle. racecar cuts it.

## The axioms

racecar's axioms are the known principles and the racecar principles below. A known principle
rests on a theorem or a tautology; a racecar principle is a stance racecar takes. Each is defined
in full at [`shared/PRINCIPLES.md`](shared/PRINCIPLES.md), where each is enumerated and homed. The
thematic sections below argue the theses that draw on them.

**Known principles**

- **P-01** dependencies form a directed acyclic graph — [in full](shared/PRINCIPLES.md#p-01-dependencies-form-a-directed-acyclic-graph)
- **P-02** one home per artifact — [in full](shared/PRINCIPLES.md#p-02-one-home-per-artifact)
- **P-03** reconcile to source; do not re-derive from memory — [in full](shared/PRINCIPLES.md#p-03-reconcile-to-source-do-not-re-derive-from-memory)
- **P-04** resolve drift at the largest frame — [in full](shared/PRINCIPLES.md#p-04-resolve-drift-at-the-largest-frame-that-explains-the-symptom)
- **P-05** idempotent by default — [in full](shared/PRINCIPLES.md#p-05-idempotent-by-default-re-running-changes-nothing)

**Racecar principles**

- **R-01** a detector must have lower entropy than what it watches — [in full](shared/PRINCIPLES.md#r-01-a-detector-must-have-lower-entropy-than-what-it-watches)
- **R-02** enforced, not professed; the enforced contract is truth — [in full](shared/PRINCIPLES.md#r-02-enforced-not-professed-the-enforced-contract-is-truth)
- **R-03** determinism; the model is last, never the gate — [in full](shared/PRINCIPLES.md#r-03-determinism-over-heuristic-the-model-is-last-never-the-gate)
- **R-04** scope honesty — [in full](shared/PRINCIPLES.md#r-04-scope-honesty)
- **R-05** ownership is not delegable — [in full](shared/PRINCIPLES.md#r-05-ownership-is-not-delegable)
- **R-06** make the right thing easy; help, not law — [in full](shared/PRINCIPLES.md#r-06-make-the-right-thing-easy-help-not-law)
- **R-07** agent-grade software is data-plane-dominant — [in full](shared/PRINCIPLES.md#r-07-agent-grade-software-is-data-plane-dominant)

## The three gates: why this was a large-team luxury, and no longer is

Rigor at this level used to be affordable only to a large organization, because it was gated
three times.

The first gate is **team scale**. Holding a canon in force needs dedicated architects,
reviewers, a style council: people whose job is to keep the shape from rotting. Only a large
org can staff that, so the discipline was priced out of the small team and the solo builder.

The second gate is **human discipline**. Even fully staffed, the canon depended on each person
having read it, remembered it, and chosen to comply on the day. Humans drift. The review
catches some of it, late, and the rest ships.

LLMs remove the first two gates at once. The canon force-loads into every session, so no one
need have read it. It is enforced at `file:line`, so no one need remember it. The architect and
the style council are replaced by a script the agent cannot rationalize around, and the reading
and remembering are replaced by the load. What was a large-team luxury becomes affordable to
every builder across N repos.

Building the canon is real work: mechanizing a rule into a check with lower entropy than the
thing it watches costs once. What that buys is a marginal cost of applying the canon to the next
repo that approaches zero. Pay once, collect across the fleet.

The third gate is **the cost of the rigor itself**, and it is not removed by the substrate, it
is dissolved by the structure. The received wisdom is that discipline is a tax: more process,
harder QA, slower shipping, paid for maintainability you may never collect. That is true of
rigor that is professed and partial. It is false of rigor that is enforced and total, because
the axioms do not merely organize the code, they change the bug distribution. When every fact
has one home, the divergence bug, the same thing fixed in four places and missed in the fifth,
cannot exist. When the graph is a DAG, a change has a bounded blast radius and you can reason
locally, so the non-local bug, spooky action at a distance, has nowhere to live. When names do
not lie and output is reconciled to source, the misunderstanding bug and the phantom-second-model
bug drop out. What remains is a smaller, more local, more testable class of defect. QA gets
easier, not harder: you are testing a system whose structure bounds where a bug can hide. The
rigor is not a cost paid down later, under enforcement it is a net reduction in the bug surface,
paid forward. **This is the genuinely new thing, and the third gate is the one that inverts the
usual trade.** The principles are old; what is new is the substrate that makes universal enforced
adherence cheap, and the enforced structure that turns rigor into a QA dividend instead of a QA
tax.

The velocity is sustained. Drift is caught at the moment it is introduced, so it is never paid
down in the expensive refactor that unmanaged drift forces. You go fast because the shape holds a
year in.

## Binding over reading: the trust thesis (R-01, R-03)

A check you cannot reproduce is not a check. Every gate in racecar is deterministic: a script
that fails a violation by naming `file:line`, never a model asked to judge. The model is the
last, deferred stage, used to *mechanize* judgment (turn a rule into a deterministic check) or
for irreducible judgment fed by deterministic pre-filtering, never as the gate itself. The rule
of thumb, and the keystone the rest rests on: the detector must have lower entropy than the thing
it watches (R-01). An LLM watching an LLM is not a detector; it is a second source of the same
noise. Most AI-assisted tooling puts the model in the loop as the arbiter; racecar puts it last (R-03).

Corollary: AI multiplies foundations, it does not replace them. On a strong foundation it is
leverage; on weak judgment it amplifies slop faster. So the foundation, the deterministic
canon, is the thing worth building.

## A generator cannot gate itself: why the deterministic check is permanent (R-01)

There is an obvious objection: if the model keeps improving, isn't racecar scaffolding a better
model makes obsolete? No, and the reason is R-01 turned on the model watching itself.

Two things hide inside "the model should just do this." The first is knowledge: has it read the
giants. That half decays toward the model; a stronger model does close it, and largely has. The
second is enforcement, and it does not decay, ever. A generator samples tokens, and a sampler
has a nonzero probability of emitting a cycle, a second home, a scope-dishonest name, however
strong it gets. Its floor rises; it never reaches zero. A deterministic check has probability
zero of missing the class it decides, at negligible cost, today. So a better model raises the
*floor* of the output and the cheap script still guarantees the *ceiling*. You also cannot
audit a generator's judgment about its own output, because the audit runs at the same entropy
as the thing audited: the second-source-of-noise problem again.

racecar is therefore not a bridge to a smarter model. The knowledge half is a bridge; the
enforcement half is permanent, orthogonal to model quality. That permanence is the durable core.

## Drift is the enemy: one home per rule (P-02)

Every rule lives in exactly one canonical place; everything else points to it. Two homes for a
rule is two places it diverges, which is zero places it holds reliably. Drift is fought
structurally first (eliminate the surface: one home, P-02), then by automatic per-change
checks, then by periodic sweep, in that order. A local fix to a drift symptom masks the global
cause; resolve it at the largest frame that explains it (P-04).

## Agent-grade software is data-plane-dominant: the architecture thesis (R-07)

The packages worth building for an agent connect to real data: broad in volume, shallow in
complexity. The more useful the package, the more data it moves, and the smaller the
ORM-governed *fraction* of the system becomes. The ORM is a control-plane tool (auth, config,
audit, identity: low-volume, relational), right for that and wrong for a shallow firehose. So
the architecture inverts the conventional Django repo: the **library is the center**,
Django-free, holding the data plane; the ORM is **confined** to a server that touches the data
plane never. The `src/` vs `server/` split is that confinement made physical. The conventional
ORM-centric repo governs the part that *shrinks* as the system gets more useful; racecar governs
the part that grows.

From that one thesis the whole shape follows: the library at `src/<pkg>`, surfaces (`cli` /
`rest` / `mcp`) as thin adapters over one `api`, the server database-light, and the
Authorization Server the only stateful piece (it owns exactly the control-plane state the ORM is
for).

## Partitions, not contradictions

This looks like it contradicts the conventional Django canon (fat models, the ORM at the
center, the O'Reilly and Two Scoops tradition). It does not. It bounds where that canon applies.
This is scope honesty (R-04) turned on the books: their advice is right, their implicit
claim to *universality* is the bug.

The mechanism is shape detection, read off disk, not imposed. An app genuinely tied to the ORM
lands in the `server` shape (Django, no library), and there the conventional canon holds in
full, unchanged; racecar never tells a relational CRUD app to split into `src` plus `server`,
because that shape does not match on disk and the advice never fires. A data-plane-dominant
package lands in the library-centric shape the books never addressed, because they were written
for request-response over a relational core, not a broad shallow firehose. racecar routes each
workload to the regime that fits rather than imposing one. It corrects the false universality,
not the content. It is not neutral about which regime is worth being in for agent work (the
data-plane thesis says the valuable packages are the data-plane ones), but that is a claim about
*what to build*, not about how to build a given ORM-tied app; on the latter it agrees with the
books.

## One canon, many repos: the portfolio thesis

racecar is not a tool you run on a repo; it is the operating system of a portfolio. One canon
governs N unrelated codebases so a builder plus AI can run all of them without each drifting
into its own dialect. The cost of the canon amortizes across the fleet; the leverage is at fleet
scale, not single-repo scale. The proof, therefore, is not that it works on one repo (it does)
but that one canon change propagates across the fleet cheaply, and that racecar can normalize
itself. Until the fleet runs on it, the portfolio thesis is intent, not fact.

## Principle, judgment, execution, noop

That is the order of the work, highest to lowest. A principle is proven. A judgment is chosen and
yours, the discernment only you can supply. Execution is the doing, increasingly
cheap, and the model does it well. Noop is the safe nothing: the small thing you ship to be
certain you never fail. The two at the top are scarce and irreducible; the one at the bottom is
the enemy. To think small and never fail is to rank noop above execution, and it is the worst move
on the board.

racecar makes execution, the cheap layer, trustworthy and reproducible, so the human time goes to
the two scarce layers above it and fear never drives you down to the noop. The gate makes bold
execution safe, and safe boldness is what keeps you reaching instead of retreating. Tooling
confirms; the owner authorizes. The checks catch error mechanically; they never decide.
Responsibility stays with the owner, never delegable to a gate.

## Prior art: borrowed, not invented

racecar invents none of its axioms and claims none. Each restates something older. One home per
rule is DRY and single source of truth. The acyclic import graph is the Acyclic Dependencies
Principle, Parnas's information hiding, and Lakos's levelization. Reconcile-to-source rests on
Dijkstra: testing shows the presence, not the absence, of bugs. Scope honesty is
naming-as-a-promise and least astonishment. Make-the-right-thing-easy is the paved road and the
pit of success. Ownership-is-not-delegable restates "you build it, you run it" and Deming's
refusal to inspect quality in after the fact. The drift doctrine is Lehman's laws of software
evolution and Cunningham's technical debt. This is fifty years of software engineering,
borrowed. Where a principle has a clear origin the credit is theirs, not racecar's; where it is
folk wisdom, no one owns it and racecar least of all.

What racecar does with them is the work. It sees which of these ideas cohere, that they
reinforce each other, and that the LLM substrate finally makes enforcing them together
affordable. Seeing a true structure and naming it so others can use it is not lesser than
inventing one: it is what Parnas did with information hiding, and Dijkstra with a sentence about
tests. racecar enforces the borrowed canon together, mechanically, at `file:line`, on the
owner's machine, bound at generation time, as one canon that governs a portfolio, and it holds
two positions that cut against current practice: no model in the trusted loop, and no CI-gate
that decides without the owner. It earns its keep by holding borrowed wisdom in force without
drift.

## What would prove it wrong

Held to its own standard, racecar must be falsifiable:

- If the fleet migration grinds into bespoke per-repo patching, the portfolio thesis fails: it
  is N copies of a dialect, not one canon.
- If a deterministic gate cannot express a rule and an LLM has to judge it, the trust thesis
  (R-03) has a hole at that rule.
- If the library-centric shape (R-07) forces the data plane through the ORM anyway, the
  architecture principle is wrong for that class of package.
- If the marginal cost of applying the canon to the next repo does not approach zero, the
  affordability claim (the first two gates) was fixed cost dressed as leverage.
- If enforcing the axioms does not shrink and localize the bug surface, and QA stays as hard,
  the third gate was never real: the rigor was a tax after all.
- If a model gets strong enough that a deterministic gate never fires on its output across a
  real fleet, the permanence-of-enforcement claim was wrong and the binding was only ever a
  bridge.

The theses earn their place by surviving the fleet, not by being well-argued here.
