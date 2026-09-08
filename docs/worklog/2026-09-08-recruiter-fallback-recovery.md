---
title: "AR-414: Repair and fund the recruiter fallback"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [recruiter, fallback, live-evidence]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/handoffs/issue-AR-414.md
  - docs/decisions/0192-route-content-invalid-completions-to-a-content-fallback-profile.md
  - tests/test_workforce_inference.py
supersedes: []
superseded_by: null
type: worklog
commit: 6d9c91fc481602df148ae61364dba47e833b6626
short: 6d9c91fc
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/782
related_issues:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
---

# AR-414: Repair and fund the recruiter fallback

## Purpose

Resolve recruiter transport and malformed-content failures without treating a
successful repeat as a fix, changing nominations, or relaxing verification.
This is an owner configuration recovery plus regression coverage: the existing
ADR-0192 provider loop already implements bounded content fallback correctly.
No Python production behavior or packaged defaults changed.

## Diagnosis

Two installed stock calls failed recruiter HTTP404 in792ms and730ms. A captured
53,782-character recruiter packet contains the real three-unit synthetic clamp
review plan, governed detail cards, schema and system instructions. Replaying
it against the existing MiniMax deployment returned200 in7.268s. The exact
GPT-5.5 fallback deployment returned404/model_not_found in0.699s.

The owner configuration also had an empty content_fallback_routes mapping.
Gateway transport fallback cannot see HTTP200 contract-invalid replies. Even
adding that mapping would not suffice: strict_call_budget5 cannot fund subject,
planner repair, recruiter repair, content fallback and the reserved critic.

Existing GPT-5.6-sol was tested, timed out at60s, and was not adopted. The
existing planner GLM deployment returned the same packet in18.568s; a cached
replay passed the real nomination accumulator and staffing verifier. This is
candidate qualification, not an independent critic or native-host proof.

## Exact operational change

Only these two existing gateway deployment IDs were changed:

| Deployment | Stable alias | Change |
|---|---|---|
| fc07bd43-a77b-5227-9e8c-d6dcce576525 | task-agency-recruiter-v2 | order2 fallback: ChatGPT GPT-5.5 to OpenAI-compatible GLM-5-turbo |
| 03d783b3-032c-5e05-88c5-107fdea5692a | task-agency-recruiter-v2-content-fallback | same backend replacement, single-deployment alias |

The model parameter is openai/glm-5-turbo, API base is the existing ZAI coding
endpoint, extra_body.reasoning_effort is low, and api_key references the
gateway's existing ZAI_API_KEY environment variable. No secret was printed or
copied into repository records. The stored model_info mode is chat and its
base_model is glm-5-turbo. Order, timeouts and other deployment parameters
remain unchanged; all unrelated deployments were compared before and after.
The original MiniMax primary and independent critic routes remain intact.

Owner Agency configuration adds a named agency-recruiter-content-fallback
profile pointing to that stable content-fallback alias with the same loopback
gateway, LITELLM_API_KEY reference and60s timeout. It maps only
workforce.recruiter in inference.content_fallback_routes. strict_call_budget
is8: subject1 + planner2 + primary recruiter2 + fallback2 + critic1.
Healthy turns do not consume unused calls. Per-provider repair bounds, strict
critic reservation, nomination constraints and all other configuration remain
unchanged. The previous owner file was privately backed up before editing.

## Challenges encountered

Changing a deployment's model alone leaves its stored API mode behind. The
first replacement attempt reached ZAI's unsupported /v4/responses endpoint
and returned404. Changing model_info.mode from responses to chat and base_model
from gpt-5.5 to glm-5-turbo fixed that mismatch. A resulting gateway cooldown
temporarily returned429; it was allowed to expire, not disabled. The corrected
content-fallback alias then returned200 in5.914s and passed staffing verification;
its gateway response header identified deployment03d783b3 at the ZAI endpoint.

The real fallback is not assumed infallible: the fault-path demonstration below
received non-JSON content on its first answer and needed its funded repair.
After correction, the exact order-2 transport deployment returned HTTP 200 in
11.375 s with its ID and ZAI base in response headers, but omitted unit IDs and
failed nomination validation. That proves repaired transport, not staffing.

## Verification

Focused inference, configuration and installer checks:336passed, including12
new cases for shape/non-JSON/HTTP404, valid/invalid fallback, and budgets5/8.
They retain failure for invalid fallback, preserve the critic reservation, and
require a valid staffing proposal before the critic is called.

Installed fault-path demonstration: reuse the captured real plan and roster;
explicitly inject two empty-object primary responses, then call the actual
configured fallback and critic. Reserve three already-spent upstream calls.
The first live fallback reply was provider_model_text_not_json in15.282s; its
bounded repair passed in18.783s; the live critic approved in3.171s. Result:
accepted,37.282s,8budget units including the three simulated upstream calls.
Both injected faults retain recruiter_response_shape_invalid. This proves
recovery with real fallback/critic inference, not natural reproduction of the
earlier primary malformed response, nor an end-to-end native session.

Fresh unmodified installed stock staffing naturally reproduced both primary
shape failures: first {}, then units as a string. The content fallback passed
in12.509s and the critic approved in2.396s. Overall accepted96.503s: subject
2.963s, planner6.413s, embedding38.258s, reranker8.880s, primary3.639s then
21.166s, fallback12.509s, critic2.396s. This proves recovery on the original
failure class with the normal configured pipeline, not just fault injection.
It does not establish latency improvement: embeddings dominated this sample.

Named production spine1151passed/3skipped in94.39s; dashboard224passed;
metadata/docs validation1325documents; Ruff check/format778files passed.
Routing gates and strict tracker parity406items pass. Policy availability,
worklog, metadata, strict docs and diff checks pass. The first conformance run
was invalidated (source_unchanged=false) by correcting the new test's HTTP reason
constant during evaluation. This was an operator sequencing error, not a passed
gate. A repeat on frozen source is required. Corrected focused336pass also
asserts the exact provider_http_status_error/404 receipt.
The frozen-source repeat now passes: baseline99.989s,188mutations killed,
0survived/invalid, source_unchanged=true. No source edits followed that run.
Installed package identity was rechecked: all614files still match the existing
c1ef8566wheel, and the six positive/negative scope boundaries still pass.
The current long-lived hook process reports stale projection
14852134f0aa versus publishedf72f24a788ca; direct installed-provider checks do
not establish fresh native integration. No host restart or trust bypass occurs.
Old/new generated hook timeouts are595seconds on Codex, Claude, Hermes and
OpenClaw. No hook or package rewrite is needed for this owner-config recovery.

The fresh stock probe is reproducible without external project content: ask for
a read-only review of `def average(values): return sum(values) // len(values)`,
requiring fractional means for nonempty numeric sequences and ValueError for
empty input, with examples `[2, 7]` and `[]`. No file inspection or modification
is requested. The capture replay used the analogous clamp review described
above; all candidate selection remained inference-owned.

## Decisions and alternatives

Reuse ADR-0192 and stable gateway aliases. Do not replace the recruiter with
deterministic selection, silently normalize malformed content, remove the
critic, copy candidate rows across providers, or add unbounded retries.
Changing an advertised model name without an actual request was rejected as
insufficient evidence. No unrelated planner, reranker or hiring work is bundled.

## Recovery and follow-ups

Owner-file reversal removes only the added fallback mapping/profile and the
explicit strict_call_budget8 override, after checking for concurrent edits.
Do not blindly restore an old entire owner file. Gateway reversal restores the
two exact deployments to chatgpt/gpt-5.5, model_info responses/gpt-5.5, clears
the ZAI-specific base/key/extra_body, and preserves their original order and
timeouts. The gateway PATCH endpoint ignores null for ordinary fields; a null
PATCH is not a verified clear. Restoring this known-broken backend is not advised.

AR-414 remains open for current-process native evidence and isolated acceptance
verification. Reconnect/restart the stale Agency host by the normal operator
workflow, then test a fresh session. Reinstall alone cannot refresh this process.

Delivered on main through PR782, merge `7420ed57`; substantive checkpoints
`6d9c91fc`, `9e6d05c0` and `369427db` have their exact ledger rows. No new package
installation, host restart, acceptance closure or unrelated backlog change.
