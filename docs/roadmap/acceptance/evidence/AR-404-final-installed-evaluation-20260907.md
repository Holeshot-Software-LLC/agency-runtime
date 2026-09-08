---
title: "AR-404 final exact-main installed evaluation"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [evidence, installation, verification, native]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/roadmap/acceptance/evidence/AR-409-installed-live-delivery-20260907.md
  - docs/worklog/2026-09-08-final-installed-evaluation.md
supersedes: []
superseded_by: null
---

# AR-404 final exact-main installed evaluation

## Outcome and scope

Owner requested a stopping point, all completed work on main, all-harness
installation and live evaluation. New backlog work stopped. Source candidate
`4cbebf73df18545120348628afd6848b8e67e3ff` is PR762 merged at02:06:31Z.
Earlier wrap-up PR757/759/760/761 carry fallback accounting, static timeout
routes, retention-safe resident recovery and process-drift guidance.
The all-harness outcome is not a pass: installed payload identity and native
staffing/injection are separate gates. No unfinished acceptance is promoted.

## Executed source verification

- Named fast Python spine:1151 passed,3 skipped in69.91s. Dashboard224 pass.
- Fallback accounting/Store/inference:161 pass2.58s; installer/lease:186 pass,
  one skip29.28s; resident recovery/header:46 pass11.90s; explicit-file/parser:
  48 pass0.65s; runtime-staleness:39 pass0.17s; cache/Hermes:56 pass0.76s.
- Combined extra focused run:1 failed,371 passed,1 skipped39.47s. The failure
  counted UTF-8 decoration against an invented whole-card limit. Test-only
  correction proves the4096-byte content/line bound;61 card tests then pass
  in0.42s. Runtime source unchanged after the named production spine.
- Routing evaluation passed all checked-in gates, explicitly deterministic
  candidate recall only, not inference staffing or real task quality.
- Decision conformance: initial ambient umask0002 caused baseline private-path
  fixture setup failure before mutations. Corrected invocation umask0077 ran
  02:03:56.740969–02:06:56.763858Z and reached its180-second outer bound with
  no report. No success or mutation score is inferred; source unchanged and
  process inspection found no remaining owned evaluator.
- Metadata, policy, worklog, strict docs/tracker, Ruff and diff passed on the
  combined branch:1309 documents,403 roadmap items,776 Python files formatted.
  No exhaustive corpus, coverage shards, compatibility matrix or native Windows.

## Exact artifact and installation

Portable wheel SHA256:
`a02c3cb34d3fff080d674d1de14107c3342322fa0eeb7c6c16247ef0c38113dd`.
Source archive SHA256:
`c96f0a519ebc5aa5fe96ce45cf236a5d0509255ad08c58d2b9650ad7054bc9c2`.
Canonical build, independent verifier and strict Twine checks passed. Initial
build from main refused its locally ignored Claude settings file under strict
Git isolation; a fresh exact-commit detached tree passed. No user file removed.

Fresh portable wheel install:Agency0.1.0/PyYAML6.0.3, pip check clean.
Installed smoke proves10 dashboard assets, loopback health,8 MCP tools/status,
265 approved bundled roster cards and safe offline abstention. Aggregate smoke
passed8/8 with all five generated adapters, OpenClaw syntax and real generated
ZCode hook execution. These are not native host or provider results.

Owner CLI upgrade02:08:13.279188–02:08:18.707150Z exited0. Its immutable VCS
metadata names exact4cbebf73 and all614 package payload files match the wheel;
pip check is clean. Owner config SHA4913dacc8a46 and wrapper SHA c31ca4d10508
remain unchanged. No credentials or provider/profile settings were modified.

| Host | Normal installer UTC interval | Result |
|---|---|---|
| Codex | 02:09:01.715641–02:09:06.624515 | exit0; registered/enabled; activation required |
| Claude | 02:09:46.021879–02:09:48.981195 | exit0; registered/enabled; loaded unknown |
| Hermes | 02:09:49.002479–02:09:51.260723 | exit0; registered/enabled; loaded unknown |
| ZCode | 02:09:51.284265–02:09:52.587645 | exit0; registered/enabled; loaded unknown |
| OpenClaw | 02:09:52.609053–02:09:55.283488 | exit1; host_restart_consent_required; live gateway |

All staged host pointers name projection
`4d2934ddb59e70a94cab668077a84422a08cd1beb662adc2db578e39dd96e86b`.
OpenClaw's pointer changed during staging despite refused native installation;
do not equate the advisory pointer with successful native publication. Its
running gateway was not stopped. Restart consent was requested asynchronously.
Dashboard service was untouched throughout.

The later stale-process notice prompted one normal Codex refresh at
02:22:56.617095–02:22:58.372870Z. It returned `already_current`, exit0,
transaction complete but activation still required. Disk refresh cannot replace
the already-running parent process or grant native hook trust.

Actual installed CLI demonstrations also passed: explicit card output for
`config get profile --card`, and `config validate --config <absolute-file>`
against a neutral file naming an absent Store. Validation reported that Store,
host and provider health were not checked; no Store was created and the input
file's mode remained0664. An earlier guessed fixture path failed namespace
validation; that was a demonstration setup error, not a schema regression.

## Actual native results

### Codex: attended trust boundary, no model invocation

Current-profile activation ran02:17:20.518106–02:17:23.338322Z against
codex-cli0.153.4. All eight hooks appeared exactly once and enabled, but all
eight were modified/untrusted: zero trusted, missing, duplicate, disabled or
unexpected hooks. Verification returned `codex_hook_trust_not_ready`, exit1,
`model_invocation_attempted:false`, with no trust bypass. There is no new
response, injection proof or accepted finalization to report. Normal terminal
Codex hook trust is an operator prerequisite; it was not retried unattended.

An initial invocation incorrectly combined verification-only mode with
`--no-dashboard` and was rejected before inspection; the corrected command
above is the native result, not that CLI shape error. Installed bundle digest:
`f838a7676e42ac9b336da1335f3b26ca73e32cdc4c4126ace68c5d2c28f6aa7f`.

### Claude: real response, unstaffed and injection unproven

One installed native isolated canary ran02:17:21.714577–02:18:24.396010Z.
The native command completed exit0 with1896 response characters and all five
header fields; the actual canary correctly exited1. Observed header values:

| Field | Actual output value |
|---|---|
| Agency/Agencies loaded | agency-steward |
| Agency/Agencies delegated | none |
| Skills loaded | none |
| Actual Model selected | claude-opus-5[1m] |
| Recruited via | unstaffed (workforce_provider_unavailable) |

Those are observed output values, not an independent model or specialist
attestation. The Store delta contains one run and one preflight failure,
zero routing, specialists, delegations, model receipts or finalizations.
No expected specialist was selected or loaded, no accepted trace exists,
and native child-card evidence failed with `delivery_marker_absent`.
The isolated plugin was registered/enabled, but invoked/loaded remained
unknown; the final report did not prove canary-profile plugin activation.
No attestation was persisted and no verifier policy was changed.

Response SHA256:
`f34bf566bedda0ff85fedd0a4284b95d08c28469e7d2a931558a182eb6465bdd`.
The63-second interval is a failed end-to-end canary, not successful staffing
latency or a quality benchmark. Native header observation returned the original
production canary classification unchanged.

### Hermes: staffing failed, native command timed out

One ordinary production battery command ran02:25:08.845223–02:32:12.929546Z.
It hit the420-second owned-process bound, returned no captured stdout/stderr
or header and failed the battery. Its own session contains one run and one
preflight failure, with no routing, loaded specialist or finalization. The
failure is `workforce_inference_failed` / `inference_invalid`, not an inferred
credential failure. Recorded provider stages distinguish the costs:

| Stage | Recorded result | Duration |
|---|---|---|
| Planner | structured response applied | 67,230ms |
| Dense recall | 295 inputs, cold catalog, one embedding call | 79,833ms |
| Reranker | provider_response_contract_invalid | 27,679ms |
| Recruiter | provider_call_timed_out | 120,180ms |

The own trace is
`20260907_222518_b16009:35d0c827-dced-427d-85d4-37cd1ba14ca1:441a1e03`.
The bounded native process ended; older unrelated Hermes processes were not
touched. There was no repeat trial or false success inferred from OpenClaw's
concurrent Store activity.

### OpenClaw: existing gateway staffed, finalization still unproved

One ordinary production battery command ran02:25:10.052868–02:31:10.828556Z.
It completed exit0 and passed the battery's limited staffing criterion: its
own turn has one run, one accepted routing decision, one loaded
`silent-failure-hunter`, five model receipts and zero preflight failures.
Hermes's concurrent failure was counted as foreign and did not affect this
verdict. This is existing-gateway evidence, not the refused candidate update.

Actual payload text starts with all five fields: loaded
`agency-steward, silent-failure-hunter`; delegated `none`; skills `none`;
model `workforce inference: [router] task-agency-router ->
linux-task-agency-router/task-agency-router (wrapper)`; recruited `inference`.
The same fields appear in native final-visible/raw metadata. Independently,
native terminal metadata reports answer provider/model `litellm/task-general`.
The header identifies workforce evidence, not an answer-model attestation.

Native prompt accounting reports130 caller characters plus7050 model-only
characters, or7180 current-turn characters. This proves additional prompt
material was delivered, but does not identify exact specialist-card bytes or
prove child execution. No child-card attestation is inferred from that count.
There are zero accepted finalizations; the Agency run remains `active` even
though native status is `ok`, summary `completed`, with `aborted:false`.
Thus the staffing-only battery pass is not a full finalized-roundtrip pass.

Own native run/Agency trace:
`f0f7bf5c-23e7-4f95-a83f-d08c5b091f4c`.
Routing latency is288,389ms; native duration is355,506ms. This was an existing
106-message session while the Hermes check ran concurrently; it is not an
isolated performance benchmark. The result does not establish a speedup.
Raw stdout SHA256:
`a2ee73e5b97678f0dce05530877c8f4cf490472d95bc839a3c967323fd20bad7`.

### ZCode: native executable unavailable

Readiness reports no executable or proven native version and no supported
native-child mode. Its normal integration install and real generated hook
smoke passed, but no native ZCode session or injection was proved.

## Operator boundaries and continuation

Current parent is old projection5059543ccea4 with LITELLM_API_KEY unset. The
pre-install doctor names that cause for eight configured inference profiles.
An install cannot retroactively staff this process. Do not reuse past headers.
Do not generalize that parent diagnosis to Hermes/OpenClaw: their actual
provider receipts prove successful authenticated stages in their native paths.
Credentials, native trust and shared-service lifecycle were not bypassed.
OpenClaw restart permission was requested once and has not been received.
All scheduled local checks and workers are terminal. Stop after normal evidence
publication; no further backlog implementation, trial, service restart or
acceptance closure is authorized by this stopping-point package.

On an explicit continuation, first make one fresh native turn prove staffing,
exact injection and accepted finalization. Use the existing AR119/409/410 and
AR353 work for these failures, with separate Codex trust/OpenClaw restart/ZCode
availability prerequisites. Do not begin another wide backlog or benchmark run.
Raw captures remain owner-private; no prompt bodies, credential values or private
transcripts are included here. No source or configuration was changed by the
native checks; main remained clean.
