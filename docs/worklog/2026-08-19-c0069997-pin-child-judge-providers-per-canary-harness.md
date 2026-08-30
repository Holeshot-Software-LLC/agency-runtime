---
title: "Worklog detail: pin child-judge providers per canary harness"
status: active
category: worklog
created: 2026-08-19
updated: 2026-08-19
tags: [canary, inference, providers, hosts, credentials, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - agency_runtime/core/canary_judge_provider.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/native_child_staffing.py
supersedes: []
superseded_by: null
type: worklog
commit: c0069997dfcb4e0a570c28f7f75414bd5968d475
short: c0069997
date: 2026-08-19
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
---

# Worklog detail: pin child-judge providers per canary harness

## Purpose

The same digest-verified 71-agent universe and 138-character child unit staffed
on `codex-subscription` but declined twice on `claude-subscription`. The live
Claude canary had silently changed judges because its disposable environment
could not reach the first provider in the owner's ordered chain. The owner
chose a persistent per-harness, canary-only mitigation so harness changes do
not require global re-pinning and real child turns do not change.

## Approach

A typed `canary.child_judge_provider_by_host` map resolves one exact named CLI
provider. Agency-mode canary preparation requires the active host's entry,
projects that provider identity into the host environment, and narrows both the
initial child judge and abstention repair to a one-entry provider tuple. A
missing, unsupported, or mismatched pin fails before inference; there is no
fallback.

The safe backend uses the host's isolated auth home for a same-transport pin.
For Claude-to-Codex judging it copies only Codex `auth.json` into a second
private directory under the same disposable profile and sets `CODEX_HOME`.
Ordinary staffing never reads the canary map. Routing evidence records the
requested provider separately from the provider that actually answered, and a
successful native-child route validates that they match.

ADR-0160 keeps all five harness keys in the policy shape while naming the
current execution boundary: only Codex and Claude have structured CLI judge
transports. ZCode/GLM remains an explicit AR-253 target, not a claim that a
ZCode subscription is already callable by Agency.

## Challenges encountered

The first proof projection read `provider` from the canary parent route. Review
caught that the child judge owns a different routing decision and query hash.
The implementation now derives the actual answering provider from the sealed
native-child provider attempts and uses the backend result only for the
requested pin.

Adding `requested_provider` also changed the exact successful child-route
shape. The validator now accepts either the historical unpinned shape or the
pinned shape and, for the latter, requires the requested name to equal the one
applied provider receipt. This preserves old evidence without weakening new
evidence.

## Decisions and alternatives

ADR-0160 owns the durable choice. A global pin, automatic same-brand pairing,
ambient ordered fallback, and changing general child staffing were rejected.
The measured Claude provider remains the falsification path because it is
currently expected to decline this exact unit.

## Verification

- Focused Option A regression slice: 43 passed.
- Broader affected slice: 169 passed, 1 skipped, with one unrelated pre-existing
  failure where a test expects workforce mode `fast` but bundled defaults are
  `strict`; a separate earlier slice also exposed the corresponding pre-existing
  hiring-budget mismatch (`4` expected, `6` configured).
- Ruff lint and format checks passed for every modified Python file.
- Documentation metadata, policy availability, worklog precheck,
  `verify_docs.py`, and `git diff --check` passed.

## Follow-ups

- Obtain renewed authorization before changing the installed owner profile,
  installing, or running a live canary.
- Choose the installed per-host values. Current AR-119 evidence supports
  `claude -> codex-subscription`; `claude -> claude-subscription` is the
  falsification run.
- Implement and prove a structured ZCode/GLM judge transport and a safe
  noninteractive ZCode canary backend under AR-253 before claiming that pairing.
- A fresh host-authored Rule-4 artifact remains required; this source checkpoint
  moves no AR-119 matrix cell.
