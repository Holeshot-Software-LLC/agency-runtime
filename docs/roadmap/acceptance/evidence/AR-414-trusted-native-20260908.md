---
title: "AR-414 and AR-415 trusted native evidence"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, native, staffing, headers]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/worklog/2026-09-08-trusted-native-acceptance.md
supersedes: []
superseded_by: null
---

# Trusted native evidence

## Installed identity and trust

Baseline main cba230199550e01d2620ec739cb0795325e9185b was clean and synchronized.
The existing verified wheel from source8629e2ed remains installed; wheelSHA256
`a36fa23834dcf1010f23e99e8ce787a0760e9247f50560228ded1d6ce6506bfa`.
The installed-qualified-veto worklog records the independent build check and
614 matching installed files. No runtime, provider, owner configuration, model,
trust store or artifact changed during this native verification.

After the owner reported `trusted`, actual inspection returned eight expected,
observed, enabled and trusted hooks; zero modified, missing, disabled, duplicate,
unexpected or untrusted entries. Plugin0.1.0+codex.823aab6fbe85 remains installed.
All eight hashes are retained in the repository evidence JSON.
The parent long-lived process still reports projectionf72f24a788ca versus the
published6e7dc299c23e. The new process transcript contains no stale-runtime
notice; it does not emit its projection identity, so equality is not inferred
from that absence. Native execution evidence below is independent of the parent.

## Ordinary native invocation

One fresh `codex exec --json --output-last-message ... -C <repository>` invocation,
using persisted owner configuration and normal trust. Inherited thread and
originator environment values were removed. No resume, model override, manual
specialist choice, injected provider failure, instrumentation or native retry.
The prompt asked to review supplied `average(values)` using
`sum(values) // len(values)`, preserve fractions, raise ValueError for empty
input, and explain `[2, 7]` and `[]`. It explicitly said
`This is not a request to change the repository` and prohibited file inspection
and mutation. The exact prompt and response are in
[the native evidence JSON](../../evidence/AR-414-trusted-native-turn.json).

Session `01a08279-181d-78c2-8991-d9a1c89503b4`;
trace `01a08279-187c-7bd2-9796-188987e5e660`.
Store start2026-09-08T19:22:52.256086Z; end19:23:44.215323Z.
Process exit0, wall56.656seconds; routing39.866seconds. This sample is not a
performance improvement or population reliability claim.

## Staffing and scope

Stored routing and staffing are accepted, cache_hit=false, session_reused=false.
Inference selected only code-reviewer; no specialist identity was requested.
One verified unit, artifact_kind=analysis, mutation_scope=read_only,
authority=advise; delegate=false. No implementation, assurance or release unit
was invented from the explicitly negated change clause. Native transcript has
zero function calls and the main checkout remained clean.

Planner, embedding, recruiter and independent critic applied. The reranker
returned provider_response_contract_invalid; the unchanged pipeline still
accepted the verified nomination and critic decision. This nonfatal diagnostic
is retained, not omitted to present an all-green provider chain. The stored
receipt does not provide per-stage timing; none is reconstructed.

AR-415 deterministic regression in tests/test_workforce_intent.py:75-99 covers
both nominal exclusions and six punctuation/contrast boundaries preserving
positive mutation requirements. The negated-request worklog records the original
2failed/6passed result and installed isolated-import verification. This new
native invocation supplies the previously missing native scope evidence.

## Injection and headers

The actual native developer message contains the complete governed code-reviewer
contract and the current-turn initial header with exact session/trace correlation.
The specialist-load row starts19:23:33.337Z and expires on finalization.
All five initial header lines match the delivered response byte-for-byte:

```text
Agency/Agencies loaded: agency-steward, code-reviewer
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: workforce inference: task-agency-critic-v2 -> agency-recruiter-critic/task-agency-critic-v2 (wrapper)
Recruited via: inference
```

The model field identifies the observed workforce wrapper; it does not claim an
unobserved executor/provider base model. Injection capsuleSHA256
`c84afc053a31d2062e1fedd4a11e6ef3f5083b071f023d0f6adfadf30598e164`.

## Finalization

Store run is completed, preflight_state=ready, with zero preflight failures.
Stop-hook finalization `e7fefc6e-85d0-4ff3-b59b-4ae85a6f65a5` has action=accept,
terminal_status=completed, missing=null. Its ID equals the run's terminal ID.
SHA256 of the actual delivered response equals the finalization response_hash:
`f0575a3cc6111caa3d2c0e7b3e4791042a0705fa0968954c3277534e412c9b02`.
The output-file text also matches after its trailing newline is stripped.
The answer correctly reports4versus4.5 and ZeroDivisionError versus ValueError.
No explicit MCP-finalizer invocation occurred in this child; acceptance came
from the normal native Stop hook, and that is the exact claim.

## Failure boundaries and limitations

AR-414 failure-header tests cover bounded cause rendering, missing/malformed
receipts, wrong session/trace/host, revision mismatch and other terminal states.
The installed captured-veto replay preserves preflight_failed, emits the exact
qualified cause plus omission marker, and creates zero accepted finalization
events. See the installed-qualified-veto evidence; replay is not native evidence.
The historical handoff veto remains supported by experiment-tracker assigned to
a non-experiment handoff review. No forced acceptance or changed critic policy.

The separate owner-confirmation trace01a08274-5dbc-7af3-90d9-283fb1bfc5ea has
receiptbb227c4e-25f4-4fba-adc1-a761dfa6508b: subject and reranker contract-invalid,
planner and recruiter applied, recruiter_abstained/no_safe_sufficient_team,
no critic attempt. Hiring diagnostics include provider_http_status_error without
a numeric status. This is not evidence of the historical recruiter404 or critic
veto recurring. No successful staffing is claimed for that parent turn.

One accepted ordinary turn proves the bounded native outcome; it cannot promise
all prompts will staff successfully. All selection, validation, critic and repair
limits remain unchanged. No Windows, other-host, exhaustive matrix, publication,
or clean Bandit scan claim; the existing B202 finding remains recorded in the
installed verification worklog.
