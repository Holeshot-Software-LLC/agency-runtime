---
title: "AR-404 Codex launch repair and native roundtrip"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [codex, credentials, native, verification]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/worklog/2026-09-08-codex-launch-roundtrip.md
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
supersedes: []
superseded_by: null
---

# AR-404 Codex launch repair and native roundtrip

## Scope and outcome

The owner confirmed native trust and authorized a bounded Codex package:
restore launch connectivity/credentials, prove a fresh native staffed turn with
exact injection and accepted finalization, then measure a small cold/warm sample.
No OpenClaw restart, new credential, changed provider route, weaker staffing or
broad backlog wave is in scope. Main floor is c5516afe; installed runtime remains
4cbebf73. No product code or generated hook changed. First activation passes;
ordinary MCP connectivity passes, but both ordinary staffing attempts fail.

## Fresh diagnosis, September 8 UTC

At 11:12:06 the installed inspector proved all eight Codex hooks enabled,
exactly once and trusted; missing/modified/untrusted/duplicate/error counts zero.
The previous handoff's untrusted result is now historical.

The current conversation's MCP status returns Transport closed. A separate
fresh process from the actual installed plugin MCP manifest initialized,
listed all eight tools and served agency.status: exit0, no stderr or parse
error. This distinguishes a dead current connection from an unlaunchable server;
it does not reconnect this conversation or prove its finalizer.

All eight LiteLLM profiles reference LITELLM_API_KEY, absent in this process.
The existing owner-private environment file declares that variable beside
native-API and gateway-base variables; its values were not printed or copied.
The Codex wrapper already unsets OPENAI_API_KEY for subscription-login policy,
but never provisioned LiteLLM. Parent ancestry is terminal/bash/node/Codex;
environment inspection stops at the OS permission boundary, not elevated access.

## Owner launch repair

The existing wrapper now provisions the configured LiteLLM variable from the
owner's existing environment file when absent. Function-local bindings prevent
that file's native API key and gateway base from changing the launch policy or
inherited routing override. Existing API-key unset and native exec are preserved;
an inherited LiteLLM key still wins. This is explicit owner launch configuration
under ADR-0204, not a runtime secret-file fallback or global CLI allowlist change.

Wrapper SHA256 changed from
d87f1d17a1dfbc14421d303f173bb9f4cce862490569fc145e24848f5416d276
to f23714086e26ba5b02ecd88522da18fe66372d84cc48a926190133bc49e27673.
Mode remains0755 in an owner-private executable directory. The original wrapper
is retained privately for recovery; no secret file was copied. Agency config and
provider/profile values are unchanged.

## Executed checks

- Bash syntax passes; native version remains codex-cli0.153.4.
- Two metadata-only probes exercised the actual wrapper prefix, replacing only
  final exec with assertions. An absent LiteLLM key becomes present; an inherited
  sentinel remains unchanged. Both preserve the gateway override and remove the
  native API key. No real credential values enter output or evidence.
- Fresh MCP handshake/status passes as above, without a model call.

## First fresh trusted native activation

Normal `agency install --agent codex --verify-activation` ran September8
11:22:17–11:24:27UTC, about129.6seconds. Native CLI and activation exit0,
current-profile, trust_bypass_used=false, ready/complete, persisted attestation.
The launching Agency process lacked LITELLM_API_KEY: the repaired native wrapper
provisioned it. No alternative model route or trust bypass was supplied.

Native session01a080c1-30c6-7380-bdc4-6067e0c5433a, own trace
01a080c1-3108-79f1-a099-a0ebbc2e96c1. Store evidence shows accepted inference
selecting code-reviewer, native child01a080c2-d0ab-7002-a5c2-db869a5a0512
completed through spawn_agent, and finalization accept/completed with no missing
fields at11:24:24.640416UTC. All five output labels parse; loaded steward and
code-reviewer, delegated code-reviewer via generic-worker/spawn_agent, skillsnone,
inference critic provenance and recruited inference. Those are this canary's
headers, not the old parent conversation's headers.

The canary proof contract agency.codex-activation-canary.v4 passed, proof digest
7d808bc795bf4b11df2a1432d820f775e34fa394076d7f94969476410ee2920e,
bundle f838a7676e42ac9b336da1335f3b26ca73e32cdc4c4126ace68c5d2c28f6aa7f.
Native final output762characters SHA256
b9d6d8716d09c81210631886d7073dd0e828295c3d61df5ce8f152e525166e19.
Raw captures stay private. The normal CLI's concise verification projection omits
detailed evidence; these details are joined to its exact stored trace, not
inferred from absent projection fields.

Staffing latency97454ms; child inference2900ms. One recruiter response failed
candidate validation, then its retry succeeded. No cold/warm claim is made from
this single sample. Successful activation is not proof of a public MCP tool call:
the activation harness deliberately reduces tools.

The subsequent requested `agency install --agent codex --json` refresh exits0:
Codex files unchanged, eight-hook trust retained, activation ready, no attestation
invalidation or persistent-profile change, runtime_drift=null. Its default
optional dashboard integration ran daemon-reload and restarted that dashboard;
OpenClaw and other host installations were untouched. Refresh cannot replace
the hooks or closed MCP connection already loaded into this running parent.

## Ordinary native execution: connectivity passes, staffing fails

Two normal `codex exec --json --sandbox read-only` invocations used the existing
owner profile, native subscription login and repaired launcher. No model, MCP
configuration or trust override was supplied. The second explicitly requested
Agency MCP status and finalization, so these are not identical-task timing
samples. A private opt-in hook log was enabled only on the second launch.

| Observation | Ordinary1 | Ordinary2 |
|---|---|---|
| UTC interval | 11:32:19–11:33:21 | 11:36:29–11:38:02 |
| Native wall seconds | 61.718 | 92.215 |
| Planner milliseconds / deadline | 45774 / 60000 | 45791 / 60000 |
| Native exit / timeout | 0 / false | 0 / false |
| Staffing | preflight_failed | preflight_failed |
| Delegations / accepted finalizations | 0 / 0 | 0 / 0 |

Ordinary1 session01a080ca-55f2-7030-a984-aa52c8f2826e, trace
01a080ca-564e-7d41-81c9-b0e13b958a30. Ordinary2 session
01a080ce-2753-7a63-9224-a778f6da9eb6, trace
01a080ce-27ba-7871-96ec-0ac3eb662014. Each has one attempted planner call,
provider_http_status_error, workforce_provider_unavailable, inference_unavailable.
There are no credential-unset failures. No new hiring occurred.

Both correctly identify the supplied helper's floor-division and empty-input
defects and show a minimal arithmetic-mean replacement plus two example checks.
The native answers explicitly say those checks were not executed. This is useful
answer evidence, not an Agency staffing/finalization success.

Ordinary2 actually calls public agency.status and agency.host_status successfully:
verified Store, current launcher artifacts, trusted hooks, and the earlier
activation attestation. Its public agency.finalize attempt fails in the native
host with “MCP tool call requires approval, but approval policy is never.”
This read-only test therefore does not prove an accepted MCP write. It also
submitted empty identifiers because its failed-preflight instructions lacked a
current finalization binding. No approval was bypassed or identifier invented;
no finalization row exists. Do not attribute this approval restriction to the
repaired MCP transport or generalize it to all owner launch modes.

Final output hashes: Ordinary1
e9dd56e1ee2b03c8232c4e93e5d90c30aa48a22454246360a51d8a396ea64347;
Ordinary2 bd57f2a8bc688eeccc468053117955db45145ffcaae3c8e8e376e37f79737f92.
Both outputs have five parseable labels but disclose unavailable staffing;
header syntax alone is not correctness. Native raw captures remain private.

## Root-cause boundary and next package

Read-only gateway journal metadata at11:33:08.27UTC shows an upstream
APITimeoutError and HTTP408, coincident with Ordinary1's planner failure. This
supports an upstream timeout, not a missing credential or our60second deadline;
there is no request-ID join, so retain that correlation limitation. No service
configuration, route, timeout, credentials or gateway process was changed.

The transport captures HTTP status but WorkforceInferenceAttempt drops it before
durable failure projection. AR-413 tracks that concrete downstream gap under
ADR-0209; no status is guessed from latency. Separately, the four-hour MCP idle
expiry can end a paused live host; its role in the old parent's disconnect is
unproven. Do not remove the AR-372 process-leak bound based on this hypothesis.

Stop repeated model calls after these two ordinary failures. The next bounded
package is source-preserving planner/gateway diagnosis, then an explicitly
authorized provider change only if required; carry AR-413 status metadata through
the full receipt path. A successful ordinary staffed turn must precede any
cold/warm performance or reliability claim. Re-run public finalization with valid
current-turn binding and an approved native MCP-write mode, not a trust bypass.

## Verdict

Owner launch provisioning repaired; fresh trusted activation and ordinary MCP
reads pass. Ordinary staffed/finalized reliability is NO-GO; no latency speedup,
warm-cache benefit, general hiring quality or all-harness success is claimed.
The current parent remains unstaffed with a closed connection.
