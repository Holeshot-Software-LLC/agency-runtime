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

## Actual Claude invocation

After the namespace correction, one native isolated-profile canary ran:
```bash
agency host-canary claude --execute --confirm 'RUN LIVE claude CANARY' --timeout 180
```
It completed without a timeout and its output passed the header parser. It
still failed overall: no routed/loaded specialist or accepted finalization,
two preflight failures, and multiple child artifacts instead of the one exact
verified delivery. A syntactically valid header is not an injected-card proof.
The source-labelled command result, with duplicated inventory and non-content
IDs omitted from this projection, was:
```json
{
  "sampled_at": "2026-09-07T21:17:39.580977+00:00",
  "host": "claude",
  "profile_scope": "isolated-profile",
  "live_attempted": true,
  "canary_passed": false,
  "attestation_persisted": false,
  "trust_bypass_used": false,
  "invocation": {
    "backend": "claude",
    "child_judge_provider_requested": "agency-default",
    "collaboration": null,
    "exit_code": 0,
    "header_missing": [],
    "header_valid": true,
    "host_child_collection_reason": "multiple_child_artifacts",
    "isolated_plugin": {
      "enabled": true,
      "invoked": null,
      "load_requested": true,
      "loaded": null,
      "registered": true
    },
    "profile_scope": "isolated-profile",
    "status": "completed",
    "stderr_truncated": false,
    "stdout_truncated": false,
    "timed_out": false
  },
  "counts": {
    "delegations": 0,
    "finalizations": 0,
    "preflight_failures": 2,
    "receipts": 0,
    "routing": 0,
    "runs": 2,
    "specialists": 0
  },
  "unmet_prerequisites": [
    "canary profile plugin registration and enablement were not proven",
    "verified host-authored Claude child card delivery was not proven (multiple_child_artifacts)"
  ]
}
```
No trust bypass or current-profile attestation. Do not repeat unchanged
preconditions; inspect the two captured failure records and the canary's exact
child collection before claiming any live staffing success.

## Fresh native checks after the documented credential was found

The owner-private client environment documented by AR-388 still exists and
contains the configured LITELLM_API_KEY. Its parent directories are 0700 and
the file 0600, owned by the current user. The diagnostic reads only that named
assignment, rejects shell interpolation, and passes it only to its child
environment. No value is printed, no new credential is provisioned, no gateway
master key is substituted and no persistent setting is changed.

One diagnostic initially inherited PYTHONPATH pointing at this checkout.
The installed CLI then inspected source code whose private worker projection
was not published; the result was worker_projection_unavailable, not observed
untrusted hooks. That diagnostic mistake is retained separately. Removing the
checkout overlay from the actual installed CLI invocation corrects the source
boundary. Its verified interpreter imports the AR-348 installed package under
isolated import inspection.

## Codex current-profile activation now passes

At 22:04:41Z September 7, the actual installed CLI passes the current-profile
activation canary with the documented client variable supplied. The command is
verification-only: installation_attempted=false; no hook definition/trust hash
is changed and trust_bypass_used=false. A bound v4 attestation is persisted for
Codex 0.153.4 and exact trace 01a07de5-15c3-7350-86c4-b38e886caa61.

This proves that bounded native activation, not that the already-running
parent conversation inherited a newly supplied environment or repaired its
closed MCP connection. The generic child-launch audit over the default sessions
root returns zero launches in this window. That negative scan is retained
separately; no additional child-card claim is derived from it.

## OpenClaw actual output and prompt readback

One existing ordinary battery passes with its own run, routing, five model
receipts, one loaded specialist and no own preflight failure. Native run
445adc05-4050-4277-b45e-4ab86ae48c64 equals the persisted Agency trace. The host
returns a 1,270-character final body whose five fields name agency-steward and
silent-failure-hunter, no delegated agent, and inference recruitment. No raw
private response body is published here.

The host reports 274,984 ms for the ordinary review. Its system-prompt report
names 31,884 characters/hash
a1b7312c365b1380b8e1ce569f128c0b4424531d21951c568cd94a343e51a95f.
Its current turn reports 7,180 prompt characters, 7,050 model-only prompt
characters and zero separately labeled runtimeContextChars; the visible task is
130 characters. Model-only injection is observed, but this report does not
expose those bytes or prove every byte belongs to Agency. The exact Store run
is preflight_state=ready but still status=active on readback; no accepted
finalization or native child-card proof is claimed by this ordinary battery.

The final header's workforce model field is a wrapper alias, not proof of the
underlying provider model. The host execution trace names a successful
litellm/task-general assistant attempt. Keep those provenance levels separate.

### Positive source-labelled readback

```json
{
  "openclaw": {
    "observed": {
      "openclaw": "OpenClaw 2026.8.2 (0965053)"
    },
    "result": {
      "mode": "ordinary",
      "outcome": "passed",
      "grading": {
        "mode": "pass_any_k",
        "trials_requested": 1,
        "trials_run": 1,
        "passed_trials": [
          1
        ],
        "failed_trials": []
      },
      "trials": [
        {
          "mode": "ordinary",
          "outcome": "passed",
          "reason": "",
          "timed_out": false,
          "exit_code": 0,
          "own_sessions": [
            "agent:openclaw:main"
          ],
          "own_session_row_counts": {
            "runs": 1,
            "receipts": 5,
            "specialists": 1,
            "routing": 1
          },
          "foreign_session_activity": {},
          "foreign_session_hosts": {},
          "new_row_counts": {
            "runs": 1,
            "receipts": 5,
            "specialists": 1,
            "routing": 1
          },
          "trial": 1,
          "ran_at": "2026-09-07T21:55:38.836622+00:00"
        }
      ],
      "observed_version": "OpenClaw 2026.8.2 (0965053)"
    },
    "captures": [
      {
        "host": "openclaw",
        "started_at": "2026-09-07T21:50:56.759207+00:00",
        "finished_at": "2026-09-07T21:55:35.463076+00:00",
        "command_kind": "shipped ordinary read-only review task",
        "exit_code": 0,
        "stdout_characters": 41899,
        "stdout_sha256": "0d0f3ef0aa1e3829fa489119839ff97942d057b8f5e44428543b23946f373d9d",
        "stderr_characters": 0,
        "channels": [
          {
            "source": "$.result.payloads[0].text",
            "characters": 1270,
            "sha256": "c8a0e1b6c892f89e4dd1e3f96295f8f872f45c868b56d6b705a32408d919d3c8",
            "parsed_header": {
              "agencies_loaded": "agency-steward, silent-failure-hunter",
              "agencies_delegated": "none",
              "skills_loaded": "none",
              "actual_model_selected": "workforce inference: [router] task-agency-router -> linux-task-agency-router/task-agency-router (wrapper)",
              "recruited_via": "inference"
            },
            "header_field_count": 5
          }
        ]
      }
    ]
  },
  "codex": {
    "ok": true,
    "complete": true,
    "installation_attempted": false,
    "hosts": [
      {
        "host": "codex",
        "ok": true,
        "status": "runtime_verified",
        "maturity": "runtime-verified",
        "activation": {
          "complete": true,
          "fresh_attestation": {
            "bundle_digest": "0734429d1ba57907910723b4faaf7ec50f981513dccd0502b4518399034436b2",
            "host": "codex",
            "host_version": "codex-cli 0.153.4",
            "install_id": "c482c4e2-186e-4dce-9692-98bbf22f2696",
            "passed_at": "2026-09-07T22:04:41.025371+00:00",
            "platform_machine": "x86_64",
            "platform_release": "7.0.0-29-generic",
            "platform_system": "Linux",
            "plugin_version": "0.1.0",
            "profile_scope": "current-profile",
            "proof_contract": "agency.codex-activation-canary.v4",
            "proof_digest": "0bf5239c2caa6ca6b98f1346d697b07ae0009c46dcebacc50dc3f867fb55c7d6",
            "trace_id": "01a07de5-15c3-7350-86c4-b38e886caa61"
          },
          "profile_scope": "current-profile",
          "state": "ready",
          "trust_bypass_used": false,
          "verification": {
            "attestation_persisted": true,
            "canary_passed": true,
            "host": "codex",
            "live_attempted": true,
            "mode": "agency",
            "profile_scope": "current-profile",
            "schema_version": "agency.host_canary.v1",
            "unmet_prerequisites": []
          }
        }
      }
    ]
  }
}
```

## Hermes actual slow failure

The shipped 420-second ordinary battery times out. Its own session
20260907_173918_2c7738 contains one run and one preflight failure, no routing or
specialist load. A read-only native-session query finds 27 messages, 15 tool
calls and 11 API calls but no final assistant response/header; the stored
system prompt is empty, so its absence cannot prove injection did not happen.
No current-profile activation is claimed.

Exact failure receipt 5135dd9b-da9a-4c57-b687-07cbcc7f7ee5, recorded 21:43:49Z,
shows real provider attempts: planner 66,421 ms; cold dense recall 50,467 ms
with 296 inputs; reranker 30,952 ms rejected for provider_response_contract_invalid;
recruiter 120,206 ms with provider_call_timed_out. The resulting reason is
workforce_inference_failed/inference_invalid. Its native environment already
reached authenticated providers: the launching shell's missing variable is
not an explanation for this particular Hermes failure.

## Claude configured-client failure

The subsequent source-controller isolated-profile canary receives the existing
client variable but times out at its 180-second boundary: no final header,
delivery_marker_absent and no attestation. It is not mislabeled as a successful
installed-profile test or a remaining missing-credential failure.

Exact receipts 3615c4fb-1c2f-4a9c-b76f-bd8638f59385 and
1a237672-499b-435f-bf5e-6ea227b9e655 show subject/recruiter contract rejection,
staffing_critic_rejected, and a later recruiter provider_http_status_error.
They also expose actual latency: planning 23–31 seconds, a cached embedding
read 343 ms, and one reranker invocation 35,865 ms. Counts over the canary
window include unrelated activity and are not substituted for its empty
correlated accepted/loaded evidence.

## Remaining outcome and next bounded diagnostic

Codex's exact bounded activation and OpenClaw's ordinary staffing/header checks
pass. Claude and Hermes do not; ZCode has no local executable. None of this is
a five-host quality/latency acceptance. Existing AR-119/125/383 and performance
records retain that work. Investigate the actual contract/HTTP timeout receipts
and profile/cache costs before rerunning unchanged long canaries. No Windows
work, gateway restart, credential provisioning or trust bypass was performed.
