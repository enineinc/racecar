---
pnode: [../README.md]
---

# AI-native is not AI-replacing-deterministic

*Match the tool to the entropy of the problem.*

Ask ten teams what "AI-native" means and most describe the same thing: putting a model where code used to be. A function becomes a prompt. A pipeline becomes retrieval over a lake. A rule becomes a judgment call. That is not imagination. It is substitution, and it is often the worst trade on the table.

The mistake is easy because it looks like progress. You delete a hundred lines of brittle logic and replace them with a model that "just figures it out." But ask what you traded. Some code earns its keep precisely by being boring: it returns the same answer every time and you can prove it. Trade that for a model and you have put variance in the one place you needed none.

Three words do the work here. Entropy is how much a result is allowed to vary. Determinism is zero entropy across identical inputs: same input, same output. Idempotence is zero entropy across repeated application: run it again and nothing changes after the first time. Deterministic, idempotent code is low-entropy by construction. AI is high-entropy by design. That is its gift for generation and its disqualification as a mechanism.

## Three tiers of variance

Most "AI-native" talk skips a distinction that decides the whole argument: not everything that varies varies the same way. There are three tiers.

The first is pure deterministic: output depends only on the inputs you pass in. The second is controllable volatility: a clock read, a random number, an ordering, an environment variable. It varies, but the variance is liftable. Seed the generator, inject the clock, pass the timestamp as an argument, and it reproduces exactly. This is what a real CS foundation is for. A pseudo-random generator with a fixed seed is perfectly reproducible. The third tier is irreducible fuzziness, where AI lives: variance you cannot lift into a parameter and pin. Temperature zero narrows it; it does not turn the model into a function you can specify and replay.

So the question is not whether a function varies. It is whether you can make it stop. A seed is not a prompt. Treating tier two as if it were tier three (a clock as unmanageable as a model) is a failure of nerve. Treating tier three as if it were tier one (a model as a stable function) is a failure of judgment. "AI-native" keeps drawing the line in the wrong place.

## Where AI belongs, and where it does not

None of this is anti-AI. AI is genuinely excellent at writing and reading deterministic code, because that code is specifiable. Let it. It is also excellent at replacing code that was deterministic only out of necessity. A brittle regex over messy human text, a hand-tuned heuristic for intent, a fuzzy match you never trusted: these were approximations of judgment you could not afford at runtime. Replacing them with a model is correct, and it is genuinely AI-native.

The test is simple. If a different answer on a re-run is a bug, the thing must stay deterministic. If a different, better answer on a re-run is an improvement, AI may belong. Auth gates, money arithmetic, migrations, parsers of specified formats, the checks that pass or fail: a different answer there is a bug. Keep them deterministic. Do not hand them to a model because the model is new.

The disaster is letting the model become the mechanical part: the checker that gains an opinion. The clearest version is everywhere right now, an LLM reviewing an LLM's output. The one thing a checker cannot have is an opinion. If your reviewer holds a different view on different runs, it cannot tell a real regression from a bad day.

## The verifier must be quieter than the author

Here is the part the substitution crowd has backwards. As the author of your code becomes probabilistic, the verifier has to become more deterministic, not less. The detector must have lower entropy than the thing it watches. You do not catch a machine's mistake by asking a second machine for an impression. You catch it with a check that cannot have a bad day.

Which means AI does not retire deterministic infrastructure. It makes it cheap. Writing a rigorous parser, a real validator, a proper check used to cost engineering time, so we skimped and shipped the lake instead. The model writes that code well now. The honest prediction for an AI-native world is an explosion of deterministic infrastructure, written by AI and guarding AI, not its disappearance. The conflation gets the direction exactly backwards: it retires determinism at the moment AI made it affordable and a probabilistic author made it necessary.

## Structure beats the lake

I have built systems both ways, and the structured way wins. Take a market-data pipeline. It has two steps that look alike and are nothing alike. The first, sync, pulls raw data from an external source into local storage: the network fails, the upstream is late, the payload shifts. It is high-entropy by nature, so you quarantine it in its own step. The second, derive, computes everything downstream from the local raw data. It touches no network, and it takes the clock as an explicit argument rather than reading it. Given the same inputs it returns the same outputs, and running it again is a no-op. Deterministic and idempotent by construction.

A model answering questions over that pipeline does better than the same model turned loose on an undifferentiated lake, and the reason is mechanical: the structure already did the entropy reduction the model would otherwise have to do, unreliably, on every call. Structure shrinks the surface the model has to be right about. A lake is the right tool when the domain is genuinely unstructured: open-ended prose, exploratory retrieval. It is the wrong tool when you reached for it to avoid modeling a domain that had structure all along. "My domain is hard" is not "my domain is unstructured."

It is the same move at every scale. Do not make a check an LLM. Do not make a structurable domain a lake. Do not review deterministic output with a probabilistic reviewer. Match the tool to the entropy of the problem.

## The worldview, executable

I build racecar on exactly this line. It is a set of deterministic, idempotent checks an AI agent loads and runs against the code it just wrote: the import graph stays acyclic, dependencies point the right way, layers do not leak, the packaging holds its shape. Plain scripts, no model in the loop. The agent writes fast. The rules decide whether the design survived it. You can run the demo in one command and watch it catch a real violation.

So here is the stance, and I will not soften it. An LLM anywhere in your verification path is a mistake. Put the model where the entropy is: the generation, the judgment, the fuzzy human text it was built for. Keep it out of the place whose entire job was to never change its mind. That is what AI-native should have meant all along.

*racecar.dev*
