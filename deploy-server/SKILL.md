---
name: racecar-deploy-server
description: Ship a generated `server/` to a running deployment — the sysadmin step (Apache vhosts, the uvicorn processes per surface, TLS, the AS process). This is the only cascade step that does NOT edit code: `create-package` / `create-server` / `secure-server` write the tree; `deploy-server` stands it up on a host. STATUS — TODO, not yet built; named so the cascade is complete and the boundary (edit vs ship) is explicit. Use when asked to "deploy the server", "stand up the service", "put it behind Apache", or "go live".
---

# racecar-deploy-server — stand up the running service (TODO)

This skill is a routing pointer, not content. Load [`README.md`](README.md).

**Status: TODO — named, not built.** It completes the cascade
`create-package → create-server → secure-server → deploy-server` and marks the **edit/ship boundary**:
the first three skills edit code (idempotent, writing `src/` once and `server/` thereafter);
`deploy-server` ships that code to a host and touches no code at all.

Intended scope: install the generated `server/apache/{api,mcp,auth}.vhost.conf`, run the per-surface
uvicorn processes (`run.sh`, `run-auth.sh`), provision TLS, and bring the Authorization Server online —
the operational concerns deliberately kept out of the code-editing skills.

Doctrine home: [`../arch-coherence/GENERATION.md`](../arch-coherence/GENERATION.md) (the generated
`server/` tree it ships) and [`../arch-coherence/AUTH.md`](../arch-coherence/AUTH.md) (the AS process).
