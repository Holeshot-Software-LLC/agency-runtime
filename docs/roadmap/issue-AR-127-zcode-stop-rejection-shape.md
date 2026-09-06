---
title: "AR-127: Make ZCode Stop rejections actually block"
status: wont_do
category: roadmap
created: 2026-07-25
updated: 2026-09-05
tags: [governance, host-integrations, zcode, observability, reliability]
related:
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - AGENTS.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/header/contract.py
  - tests/test_host_hooks.py
  - docs/decisions/0089-zcode-stop-rejections-use-decision-block.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/roadmap/issue-AR-118-reconcile-native-child-activation-evidence.md
supersedes: []
superseded_by: docs/roadmap/issue-AR-135-complete-zcode-integration.md
type: issue
epic: host-integrations
issue_id: AR-127
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/151
depends_on: []
blocks: []
---

# AR-127: Make ZCode Stop rejections actually block

## Problem

Historical report below, not a fresh diagnosis of current hooks. In particular,
its truncated-preview explanation was a hypothesis, not a proven root cause.

The Agency evidence header is enforced at the `Stop` hook via
`validate_completion_policy`, which correctly classifies a response as
accept-or-reject every turn. The rejection is then translated to a host-native
JSON shape by `HookBridge._reject_completion`
(`agency_runtime/adapters/hooks.py`). That translation special-cases `codex`
(forces the shared lifecycle shape) but has **no `zcode` branch**, so zcode
inherits whatever `retry` value the caller passes.

`_completion_rejection` (hooks.py:146-151) emits two different shapes:

- `retry=True`  -> `{"continue": False, "stopReason": ...}`  (Claude's shape)
- `retry=False` -> `{"decision": "block", "reason": ...}`     (the only shape
  ZCode recognizes as a block)

Per the ZCode hooks contract, `continue`/`stopReason` are unknown fields that
ZCode silently ignores, so a rejection emitted in the lifecycle shape
collapses into a pass-through accept. Whether a given rejection blocks
therefore depends on the retry state in the SQLite store (the
`claim_continuation` outcome), not on the response content, producing
intermittent enforcement.

Observed in a live ZCode session over five consecutive turns: a missing
header was accepted on turns 1-2 (retry-exhausted path, lifecycle shape),
correctly rejected on turn 3 (first-rejection claimed path, decision:block),
and a correct header was rejected on turn 5 (a separate, second defect - see
Dependencies).

## Current state

Retired as superseded under ADR-0223, not accepted against its old checklist.
The narrow output-shape fix is already present at reviewed main 79930464 in
both rejection sites and was originally delivered in d9ce781a / PR #150.
ADR-0089 remains accepted. ADR-0120 now requires terminal rejection and exact
replay, not continuation claims; Rule 8 publishes when Agency cannot verify or
persist its own evidence; malformed Stop envelopes still block. ADR-0105 also
supersedes the old mandatory full-corpus gate cited in the reopening note.

AR-135 explicitly owns the surviving current ZCode Stop/native/full-response
outcome. Its status remains open. No code, original acceptance item, founding
rule or matrix cell changes, and no new live session is claimed. PR #694 merged
at 66282312; tracker #151 closed NOT_PLANNED at 2026-09-06T00:23:39Z, read back.

Focused current-contract checks pass **37 tests in 3.37s**: real-Store first
terminal rejection/replay on all three hook hosts, ZCode unpersistable-pass
behavior, malformed/oversized Stop shape, no legacy retry consultation and
completion-policy boundaries. This is source/test evidence, not a live canary.

The broader host-hook/policy/turn-evidence check is **133 passed, three failed**
in 41.91s. All three failures are already-documented legacy public-delegate and
Codex/Claude retry expectations, now explicitly owned by AR-176. They are not
hidden, skipped or repaired by this retirement, and the run is not called green.

### Historical pre-reconciliation diagnosis

The detection layer (`validate_completion_policy`,
`evaluate_completion_policy`) is correct and consistent; the defect is solely
in the host output-translation branch. No prior roadmap item or ADR covers
the ZCode Stop output-shape mismatch. AR-27 owns Stop enforcement authority
and AR-118 owns a different family of Stop false-rejects (native-child
activation evidence); neither addresses the output shape.

## Approach

Current disposition: retain the implemented decision:block shape, retire the
obsolete retry/unavailable/full-suite checklist, and keep current integration
evidence under AR-135. The implementation proposal below remains provenance.

Two rejection-emission sites needed the same zcode correction:

1. `HookBridge._reject_completion` (hooks.py:2028) — the in-bridge path hit by
   every Stop rejection (first rejection, retry-exhausted, and
   verifier-unavailable). Add a `zcode` branch mirroring the `codex` branch
   but inverted: zcode always emits `{"decision": "block", "reason": ...}`
   regardless of the caller's `retry` state.

2. `_boundary_failure_result` (hooks.py:154) — the module-level fallback hit by
   `run_hook_stdio`'s `except` blocks when the Stop envelope is oversized,
   malformed, or raises during adapter/storage handling. It called
   `_completion_rejection(..., retry=True)` directly, emitting the ignored
   lifecycle shape. Pass `host` through and emit `decision:block` for zcode so
   a malformed-Stop block can no longer collapse into a pass-through accept.

Lock the contract by parametrizing the existing Stop-rejection test over
`zcode`, adding a dedicated regression test asserting both the first-rejection
and retry-exhausted paths emit `decision:block` with no `continue`/
`stopReason` keys, and adding a boundary test asserting the oversized-Stop
fallback also emits `decision:block` for zcode.

## Dependencies

Current responsibility: AR-135 retains native Stop and full-response proof,
including investigation of the historical turn-5 symptom if it recurs. The
following original cause assertion is not accepted as present evidence.

- The turn-5 "present header reported as missing" symptom is a **separate
  defect**. Its rejection message is emitted uniquely at
  `agency_runtime/core/header/contract.py:1026-1035` after `validate_header`
  fails, and `validate_header` requires the header at offset 0 of the validated
  string. Since the header was present in the model output, the
  `last_assistant_message` the Stop hook received must have been a truncated
  preview. That requires either ZCode to deliver the full response or the
  contract to validate against the authoritative finalized text. Track as a
  follow-up; do not bundle.
- AR-122 ("contractor-hiring-and-lifecycle") confirms contractor hiring is an
  implemented feature, resolving the unrelated `software-test-engineer`
  question raised in the originating session.

## Acceptance

Historical checklist, unchanged. Retirement does not mark these criteria
satisfied or turn prior/live claims into current exact-candidate proof.

- `_reject_completion` emits `{"decision": "block", "reason": ...}` for the
  `zcode` host on every in-bridge rejection path (first rejection,
  retry-exhausted, and verifier-unavailable), with no `continue`/
  `stopReason` keys.
- `_boundary_failure_result` emits `{"decision": "block", ...}` for the `zcode`
  host on the oversized/malformed-Stop fallback path.
- `tests/test_host_hooks.py` parametrizes the blank-stop-response test over
  `zcode`, includes a dedicated regression test asserting the shape on both
  the claimed and exhausted continuation paths, and includes a boundary test
  for the oversized-Stop fallback.
- `ruff check`, `ruff format --check`, and `python -m pytest tests/ -q -W error`
  pass.
- A live ZCode session no longer accepts responses missing the Agency header.

## AR-256 status correction (2026-08-12)

Reopened because no durable receipt proves the exact historical full-suite
command named above. The implementation, focused checks, and live ZCode result
remain valid evidence for the other criteria.
