---
title: "Fresh Codex trust and activation verification after resume"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [codex, activation, live-evidence, staffing]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/worklog/2026-09-08-planner-reliability.md
supersedes: []
superseded_by: null
type: worklog
commit: 681b6eab
short: 681b6eab
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/771
related_issues: [docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md]
---

# Fresh Codex activation after resume

PR771 merged as `1101b4eeefb4a711392fa0b0a63e6e004cce224e`. Trust and MCP are verified; activation and ordinary staffing remain unproven. This merge records evidence, not a staffing-policy repair.

Evidence commit `681b6eab11f6333088c7f10f67c453dcd8bc593a` records the directly trusted hook set, working resumed MCP and one failed no-bypass activation attempt.

## Outcome

Owner approval is no longer the blocker. A direct native hook-trust inspection
using the installed package, isolated Python and the actual Codex launcher
reports eight expected, eight observed and eight trusted hooks. Modified,
untrusted, disabled, missing, duplicate, warning and error counts are zero.
The resumed conversation's actual Agency MCP status succeeds: 293 roster
entries and a verified SQLite binding. This does not mean its failed staffing
decision became accepted.

## Approach and observations

Ran exactly one normal owner-profile verification, without reinstalling or
bypassing trust:

```bash
agency install --agent codex --verify-activation --activation-timeout 180 --json
```

The CLI exits 1 with activation_verification_failed, live_attempted true,
canary_passed false, attestation_persisted false and trust_bypass_used false.
Native diagnosis is codex_parent_spawn_missing; exact activation evidence is
preflight_failed. No accepted child execution, final header or finalization is
claimed. Configuration, adapter, trust store, workforce and dashboard unchanged.

Installation identity: bundle
0fe533927f560ef672e1d97147802eced939e890dc5990aebb71f8a02b63700d,
install52e7cc6e-195b-4232-bf17-294a384c7028, Codex CLI0.153.4.

The durable failed canary trace01a08166-c945-7023-8ce2-7ae2c0b3c181 at
14:25:06.340UTC records the following stage evidence:

| Stage | Milliseconds | Result |
|---|---|---|
| Planner first call | 23809 | GLM-5.3-flash response rejected: plan_response_semantic_invalid |
| Planner repair | 34914 | Structured response applied; response model reports the alias |
| Recall embedding | 41911 | 294 inputs, catalog_cache_hit false, qwen3-embedding:latest |
| Recall reranker | 9643 | Structured response applied, qwen3-14b-abliterated:latest |
| Recruiter | 744 | Structured response applied; response model reports the alias |

Final staffing reasons: no_safe_sufficient_team and recruiter_abstained. These
stage durations total111021ms, not a wall-time measurement. The 41.9second cold
embedding call is canary evidence, not proof every ordinary warm turn repeats
that work. No gateway or performance configuration was changed this turn.

The resumed ordinary parent separately records a rejected subject response in
5015ms and a planner timeout in60070ms at14:22:18.578UTC, trace
01a08164-f411-7b11-9de2-cf2c0bc109ab. No HTTP status was returned for that local
timeout; it must not be described as a captured HTTP408.

## Challenges and decisions

The generic status field hook_trust_status is derived from the activation
attestation in installer_inventory.py, not from a fresh trust inspection. The
previous agent interpretation that unverified meant owner approval was absent
was wrong. The direct inspector and actual verification are stronger evidence.
Do not send the owner through the same approval loop again on that field alone.
An initial ad hoc inspector call without isolated Python returned an error; the
isolated invocation with the actual launcher above supplies the usable evidence.

The prior timeboxed backlog goal is complete, not the entire backlog or runtime
reliability objective. Readback confirms AR-173 PR722 merged at20:18:19UTC
September7, before AR-174 and later oldest-first PRs through20:52Eastern.
Windows/owner-held work stays explicitly retained. Main76fab67d is clean, final
PR770 is merged, and worklog/docs gates pass. Existing reconciliation and active
capsule are the durable stopping point; no new backlog wave was started.

## Follow-ups

Delivery checks: metadata, policy availability, exact worklog index, strict
documentation/tracker parity and diff checks pass under the project verification
environment. No production code changed; no unit-suite rerun or additional live
attempt was performed for this evidence-only update.

Inspect the failed canary's exact planner/eligibility/recruiter contract boundary
to explain the abstention without selecting a worker by hand or weakening
validation. Separate expected isolated-canary cold embedding from ordinary
catalog-cache behavior before proposing a cache optimization. No repeated live
run until that inspection produces a concrete hypothesis.
