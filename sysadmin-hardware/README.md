---
pnode: [SKILL.md]
---

# Sysadmin: Hardware Sizing

The lens that turns a repo's measured command behavior into a hardware
recommendation. It pairs a cheap, always-available telemetry probe (one
resource-usage line per CLI run) with a structural read of the four surfaces,
and proposes an EC2 instance type from that evidence: a primary pick, priced
alternatives, an explicit "size for the peak command," a burstable-vs-sustained
call, and EBS sizing.

Run it with `/racecar-sysadmin-hardware`. It reads the telemetry log the
`_telemetry` probe writes and reviews the code that produced it, then reasons to
a box. It states its reasoning from the numbers; it does not assert.

**When to reach for it:** sizing a box for a governed repo, picking an EC2
instance, deciding burstable (T-series) vs sustained (M/C/R), right-sizing an
over-provisioned instance, or converting command telemetry into a defensible
hardware choice.

**What a finding looks like:** the peak command is `python -m gfem.radiant run`
at p95 6.2 GB RSS over an 8-worker floor, but cores-actually-used is 3.1 of 16.
*Memory, not cores, is the binding constraint; size RAM to survive peak
concurrency and let `--workers` trade unwanted speed for headroom.*

## What's here

| Doc | Covers |
|---|---|
| [`HARDWARE.md`](HARDWARE.md) | **Start here.** The sizing method: the two evidence inputs (telemetry + surface review), the reasoning chain (bound-class, RAM floor, burstable call), the EC2 proposal output contract, and the worked gfem reference. |
| [`TELEMETRY.md`](TELEMETRY.md) | The telemetry mechanism: the record schema, the hook point, the storage path, the enable switch, and the one-line adoption a governed repo adds. |

The runtime probe is [`lib/_telemetry.py`](lib/_telemetry.py) (copied into a
governed repo as `<pkg>/_telemetry.py`, like the optional
[`../arch-coherence/lib/_cli.py`](../arch-coherence/lib/_cli.py) renderer). The
aggregator is [`scripts/telemetry_profile.py`](scripts/telemetry_profile.py).

Pair with [`../arch-coherence/README.md`](../arch-coherence/README.md) for the
surfaces shape this lens reviews, and [`../eng-review/README.md`](../eng-review/README.md)
for code-level hygiene. The human storefront is the repo [`../README.md`](../README.md).
