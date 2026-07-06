---
pnode: [SKILL.md]
---

# racecar-deploy-server: the procedure (TODO)

Accessed via [`SKILL.md`](SKILL.md). **This skill is not yet built**: it is named so the cascade is
complete and the edit-vs-ship boundary is explicit.

Doctrine home: [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md) and
[`../arch-coherence/AUTH.md`](../arch-coherence/AUTH.md).

## What this skill will be for

The **ship** step of the cascade. `racecar-create-package`, `racecar-create-server`, and
`racecar-secure-server` *edit code*, idempotent, writing the library once and the `server/` tree
thereafter, never a running host. `racecar-deploy-server` takes that generated `server/` and *stands it
up*: it touches no code.

Intended scope, when built:

- Install the generated Apache vhosts (`server/apache/{api,mcp,auth}.vhost.conf`) and reload Apache.
- Run the per-surface ASGI processes (REST + MCP via `server/run.sh`, the Authorization Server via
  `server/run-auth.sh`) under a process manager.
- Provision TLS for `api.*`, `mcp.*`, `auth.*`.
- Bring the Authorization Server online (migrations applied, introspection client provisioned), per
  [`../arch-coherence/AUTH.md`](../arch-coherence/AUTH.md).

Until it exists, deployment is manual: see a project's `docs/PILOT.md` for the by-hand runbook.

## Voice

Common voice: [../shared/VOICE.md](../shared/VOICE.md).
