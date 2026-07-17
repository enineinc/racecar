---
summary: The hardware-sizing method — two evidence inputs (telemetry profile + four-surface review), the reasoning chain (bound-class, RAM floor, burstable call, EBS), the EC2 proposal output contract, and the worked gfem reference.
pnode: [README.md]
---

# Hardware sizing from evidence

Accessed via [`README.md`](README.md). If you arrived here directly, read that first.

This lens proposes an EC2 instance type for a governed repo, and defends the
proposal from evidence. It refuses to assert. Every claim traces to either a
measured number (the telemetry profile) or a named line of code (the surface
review). The output is a primary pick, priced alternatives, an explicit peak
command the box is sized for, a burstable-vs-sustained call, EBS sizing, and the
one measurement that would let you step down a tier with confidence.

The method is two evidence inputs feeding one reasoning chain. Read the telemetry
first: it tells you what the commands cost. Read the surfaces second: they tell
you why, and whether the cost will hold as data grows.

## Input A: the telemetry profile (what it costs)

Run [`scripts/telemetry_profile.py`](scripts/telemetry_profile.py) over a
telemetry log that holds a representative period of real runs (see
[`TELEMETRY.md`](TELEMETRY.md) for switching the probe on). It prints one row per
command with count, worker count, and the p50 / p95 / max of cores-actually-used,
wall-clock, peak RSS, and CPU time, sorted so the memory-binding command leads.

Read four things off it:

1. **The peak command.** The top row: the highest p95 peak RSS. This is the
   command the box must survive. Size for it, not for the average.
2. **Cores actually used vs workers.** `cores_used` is mean parallelism. A
   command launched with 16 workers that shows `cores_used` p95 near 3 is not a
   16-vCPU workload; it is a 3-to-4-vCPU workload with a memory cost paid 16 ways.
3. **The bound class per command.** High `cores_used` and high CPU with modest
   RSS is CPU-bound. High wall with low `cores_used` and low RSS is IO-bound.
   High RSS that scales with workers is memory-bound. Short and infrequent is
   burstable-friendly.
4. **Failures.** A non-zero `exit_status` count on the peak command is a signal
   that it already hits a limit (often OOM); an OOM is a failed run, not a slow
   one, and it moves RAM from "nice to have" to "binding."

## Input B: the four-surface review (why, and whether it holds)

Telemetry measures today's data. Code review tells you the shape and how it
scales. Read the `api` / CLI / REST / MCP surfaces (the shape is in
[`../arch-coherence/SURFACES.md`](../arch-coherence/SURFACES.md)) and the library
under them for six things:

1. **Concurrency model.** Thread pool or process pool? What is the worker
   default, and is there a floor? A hardcoded floor (e.g. `max(8, cpu_count)`)
   means concurrency, and therefore per-worker memory, is N-way regardless of how
   few cores the box has. Find the exact line.
2. **Compute engine.** polars / numpy / sklearn / pandas / pure Python / GPU? Do
   the hot loops release the GIL (polars, numpy, sklearn kernels do; pure-Python
   loops do not)? GIL-releasing kernels scale across cores and justify vCPUs;
   pure-Python parallelism over threads does not.
3. **Memory pattern.** Full-frame loads or streaming? Per-worker allocation
   (memory scales with concurrency) or a shared read-only frame (it does not)?
   Re-loaded per task or loaded once?
4. **Data footprint and growth.** Current size of the data dir, and its growth
   rate. What dominates it, and does the working set for the peak command load
   all of it or a slice? This sizes EBS and flags whether next year's data breaks
   this year's box.
5. **GPU.** Present anywhere? If not, do not pay for it.
6. **Bound class, confirmed.** Does the code corroborate the telemetry's
   bound-class read? If they disagree, the code wins for scaling and the
   telemetry wins for the current absolute numbers; reconcile explicitly.

## The reasoning chain

From the two inputs, reason in this order. Each step narrows the box.

1. **Latency sensitivity gates everything.** If the workload is background or
   batch (a nightly refresh, an offline recompute), speed stops constraining and
   burstable (T-series) becomes correct: you buy baseline plus credits, not
   sustained cores. If it is interactive or latency-bound, sustained (M general,
   C compute, R memory) is the floor.
2. **Find the binding constraint.** Cores or RAM, not both. If concurrency is
   floored in code, per-worker memory is paid N ways whatever the core count, so
   **RAM to survive peak concurrency is usually the binding constraint** and
   cores are secondary. OOM is a failed run; a slow run is not. Size the binding
   constraint to the peak command's p95 (with headroom), then take whatever cores
   come with that memory tier.
3. **Reconcile cores-used against the tier.** If `cores_used` p95 is well under
   the tier's vCPUs, note that the extra cores are slack, and that `--workers`
   lets the operator trade the unwanted speed for memory safety on a smaller box.
4. **Architecture family.** No GPU in the code means no GPU instance. GIL-
   releasing kernels mean cores are usable (favor compute or general). Pure-
   Python hot loops mean cores are not, and you size for memory and IO.
5. **Storage.** EBS sized to the data dir plus its growth over the planning
   horizon, gp3 unless the IO profile shows sustained throughput that needs
   provisioned IOPS. State the current size, the growth rate, and the horizon.
6. **The de-risking measurement.** Name the single measurement that would let you
   step down a tier. Usually: the peak command's p95 RSS at a reduced
   `--workers`, or the same command on the full production data slice rather than
   a sample. State it so the owner can take it and decide.

## The output contract

The proposal is a recommendation, not a pass/fail verdict; it does not use the
review lenses' Blocker/Ship vocabulary. It carries, in order:

1. **The peak command,** named, with its p95 peak RSS, `cores_used`, and worker
   count, and the sentence "size for this."
2. **The bound class** (CPU / IO / memory / burstable-friendly) and the binding
   constraint, each tied to its evidence (a profile number or a code line).
3. **A primary pick,** one instance type, with the reason it wins.
4. **An alternatives table:** instance, vCPU, RAM, on-demand price, verdict. At
   least the burstable option and the sustained right-size, plus a step-down and
   a step-up so the owner sees the ladder.
5. **The burstable-vs-sustained call,** stated as a decision with its condition
   (latency sensitivity), not left implicit.
6. **EBS sizing:** volume type and size, from the current data footprint plus
   growth over a stated horizon.
7. **The de-risking measurement,** one concrete probe that would justify stepping
   down.

The alternatives table:

| Instance | vCPU | RAM | On-demand | Verdict |
|---|---|---|---|---|
| `<step-down>` | | | | why it is risky and what would justify it |
| `<primary>` | | | | why it wins |
| `<alt same tier>` | | | | when to prefer it |
| `<step-up>` | | | | what it buys and why it is likely slack |

Prices are region- and date-sensitive; cite the region and pull current
on-demand numbers rather than asserting them from memory.

## Worked reference: gfem

This is the quality bar. The lens should walk any repo to a conclusion of this
shape and rigor.

**Evidence gathered.**

- Telemetry peak command: `python -m gfem.radiant run --all` over 49 spec YAMLs.
- Surface review, concurrency: `radiant run` uses a `ThreadPoolExecutor` with
  `workers = min(max(8, cpu_count), n_specs)`, a hardcoded **8-worker floor** even
  on a 4-vCPU box (`src/gfem/radiant/run.py`).
- Surface review, compute: hot loops are polars, a numpy Monte Carlo, and a
  sklearn KDTree. **All release the GIL**, so the work genuinely scales across
  cores. **No GPU** anywhere. `sync` is network/IO-bound; `derive` is moderate
  CPU plus IO.
- Data footprint: `.data/` is about 4.5 GB, growing 1 to 3 GB/month, dominated by
  per-fordate `radiant.csv` outputs (about 30 MB/day, about 10 GB/yr).

**Reasoning applied.**

1. Background, latency-insensitive batch. Speed stops constraining, so burstable
   (T-series) is admissible once speed is deprioritized.
2. The 8-worker floor makes memory pressure N-way regardless of core count.
   **RAM to survive peak concurrency is the binding constraint, not cores.** OOM
   is a failed run.
3. `--workers` lets the operator trade unwanted speed for memory safety, so a
   smaller box is safe if RAM covers the peak.
4. GIL-releasing kernels and no GPU: cores are usable when wanted, but not the
   constraint here; no GPU instance.
5. Storage: 4.5 GB now, plus about 10 GB/yr; an EBS gp3 volume with room for a
   couple of years of growth.

**Conclusion reached.**

- Primary once speed is deprioritized: `t4g.xlarge` / `t4g.2xlarge` (burstable,
  16 / 32 GB) sized so peak concurrency does not OOM, with `--workers` capping
  memory.
- Non-burstable right-size: `m7g.2xlarge` when the run must not depend on CPU
  credits.
- De-risking measurement: the peak `run --all` p95 RSS at a reduced `--workers`,
  to confirm the 16 GB tier survives peak concurrency before committing to it.

## The procedure, mechanized

1. Confirm the probe is adopted and switched on (see [`TELEMETRY.md`](TELEMETRY.md)),
   and that the log holds a representative period. If not, say so and stop: a
   proposal without measured peak-command data is a guess.
2. Run the profiler. Identify the peak command, its p95 RSS, `cores_used`, and
   worker count.
3. Review the four surfaces for the six structural signals. Find the concurrency
   line, the compute engine, the memory pattern, the data footprint and growth,
   the GPU answer, and confirm the bound class.
4. Walk the reasoning chain. Latency gate, binding constraint, cores reconcile,
   architecture family, storage, de-risking measurement.
5. Emit the proposal in the output contract's order. Cite region and pull current
   prices. Tie every claim to a profile number or a code line.
