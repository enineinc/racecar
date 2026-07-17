---
name: racecar-sysadmin-hardware
description: Hardware-sizing lens — propose EC2 instance types for a governed repo from evidence, not assertion. Combines empirical telemetry (measured peak RSS, CPU time, wall-clock, cores actually used, worker count per command, from the `_telemetry` probe) with a structural review of the four surfaces (concurrency model, compute engine, memory patterns, data footprint, and whether the workload is CPU-, IO-, memory-bound, or burstable-friendly). Emits a reasoned proposal: a primary pick plus alternatives with vCPU/RAM/price/verdict, an explicit size-for-the-peak-command call, a burstable-vs-sustained decision, EBS sizing, and the single measurement that would de-risk stepping down a tier. Use when asked to size a box, pick an EC2 instance, right-size infrastructure, decide burstable vs sustained, or turn command telemetry into a hardware recommendation.
---

# racecar-sysadmin-hardware

Load [`HARDWARE.md`](HARDWARE.md) in full. It holds the sizing method (the two
evidence inputs, the reasoning chain, the EC2 proposal output contract) and the
worked gfem reference that fixes the quality bar.

The telemetry mechanism that produces the empirical half is specified in
[`TELEMETRY.md`](TELEMETRY.md): the probe [`lib/_telemetry.py`](lib/_telemetry.py)
records one resource line per CLI invocation, and the aggregator
[`scripts/telemetry_profile.py`](scripts/telemetry_profile.py) reduces the log
to a per-command profile.

Operational reminder: run the profiler first, over real telemetry, before any
prose reasoning. A proposal with no measured peak command is a guess.

```
# From the governed repo, after RACECAR_TELEMETRY=1 has been set for a
# representative period so the log holds real runs:
python3 ~/.claude/skills/racecar-sysadmin-hardware/scripts/telemetry_profile.py
```

The peak command (top row, sorted by p95 peak RSS) sets the RAM floor; size for
it. Reason from the numbers the profiler prints; state every step from evidence.
