---
title: "AR-404 live Codex header and injection diagnostic"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, codex, activation, runtime, backlog]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/roadmap/handoffs/issue-AR-383.md
supersedes: []
superseded_by: null
---

# Live Codex header and injection diagnostic

## Scope

September 7, approximately 21:01–21:07 UTC. The owner requested live output,
headers and injection checks without routine attendance. These observations
are separate from AR-175's passing private installed-dashboard browser checks.
They do not count registration, generated smoke, readiness or a unit test as
native activation. No credentials or trust hashes were copied or changed.

## Current runtime observations

Both connected Agency status tools returned `Transport closed`. The installed
CLI remains callable. Its bounded status reports Codex 0.153.4 registered,
enabled and with current launcher artifacts, but loaded=null, hook trust
unverified and maturity=activation-required. Inference state is degraded; its
latest persisted failure at 2026-09-07T20:14:22.897000+00:00 records subject and
planner stages failing `provider_credential_env_unset`, with
`workforce_provider_unavailable`, `inference_unavailable` and
`workforce_credential_env_unset`. No actual model resolution is claimed.

A fresh explicit stale-runtime directive prompted exactly one
`agency install --agent codex`. It exited 1: Codex files registered but
activation unverified. The CLI runs from an AR-348 immutable package while
the diagnostic published pointer still names an AR-271 package. This is
installation/projection evidence, not proof that another host should be
reinstalled. OpenClaw was not replaced or stopped.

`agency evidence wiring --host codex --json` exits 1 with
`measurement_status=not_measured`, `reason_code=host_not_measured`.
The default wiring command measures Claude, not all five hosts. An unavailable
wiring measurement cannot be interpreted as healthy Codex wiring.

## Fresh current-profile canary

Readiness said ready=true, no unmet prerequisites, but canary_passed=false and
hook_trust_status=unverified. The verification-only command was therefore
attempted once to test what actually happened, without changing installation,
configuration, trust or governance. Immediately preceding telemetry reported
57.5 percent remaining.

```bash
agency install --agent codex --verify-activation --activation-timeout 60 --json
```

Actual bounded activation result, exit 1:
```json
{
  "attestation_persisted": false,
  "canary_passed": false,
  "host": "codex",
  "invocation": {
    "failure_reason": "codex_parent_spawn_missing"
  },
  "live_attempted": true,
  "mode": "agency",
  "profile_scope": "current-profile",
  "schema_version": "agency.host_canary.v1",
  "unmet_prerequisites": [
    "host invocation did not complete successfully",
    "host invocation did not return a nonempty response",
    "final response header was not proven",
    "exact Codex activation evidence was not proven (preflight_failed)"
  ]
}
```

The command records live_attempted=true, not a pre-invocation trust refusal.
It reports `codex_parent_spawn_missing`, no nonempty response, no proven final
header and `preflight_failed`. The general trust action in installer output
does not itself explain that observed failure. Neither child injection nor a
valid header was proven; no activation attestation was persisted.

## Constraints and next diagnostic

Official [Codex hook documentation](https://learn.chatgpt.com/docs/hooks)
requires review of exact non-managed hook definitions; installing a plugin
does not establish trust. No trust bypass, manual hash change or managed-policy
conversion was used. Preserve this live failure, inspect source-labelled
invocation/Store evidence and available harness readiness without claiming an
unverified session is working. An actual credential or human trust requirement
remains distinct from code that can be repaired unattended.

## Claude namespace correction and fresh all-host readiness

The owner installation's Linux ELF Claude launcher was refused because the
package parent directory allowed group writes (mode 0775). Only that exact
directory was changed to 0755; no recursive chmod, ownership, file contents,
credentials or hook trust changed:
```bash
chmod g-w /home/holeshot/.npm-global/lib/node_modules/@anthropic-ai/claude-code
```
The first immediate status still returned the old refusal. A later fresh CLI
and direct source inspection both report Claude 2.1.263, registered/enabled,
inventory_error=null, maturity=enabled-runtime-unverified. The complete
launcher symlink and resolved namespace were inspected with `namei -l`;
all executable parents are owner-controlled and non-group-writable.

Read-only native readiness:
- Claude: ready=true for the existing isolated native-child canary; no pass
  claimed yet. Exact confirmation is `RUN LIVE claude CANARY`.
- OpenClaw and Hermes: ready=false; the implementation has no proven bounded
  read-only native-child noninteractive canary for either host.
- ZCode: ready=false; additionally no executable or native version discovered.
- All five fresh installation inventory rows had loaded=null and no current
  canary attestation. Installed/enabled is not proof of injected instructions.

The lack of a supported canary is a tooling coverage gap, not evidence that
these hosts are inherently impossible to test unattended. The existing
AR-199/309 activation and AR-119/125 cross-host proof records remain open.
