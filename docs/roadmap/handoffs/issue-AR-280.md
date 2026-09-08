---
title: "AR-280 authenticated Hermes internal invocation checkpoint"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, hermes, lifecycle, security]
related:
  - docs/roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md
  - docs/roadmap/acceptance/evidence/AR-280-native-purpose-boundary-20260908.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-280
branch: codex/ar280-authenticated-internal-purpose
evidence_commit: 7c0c1221226cdf388f886e4ce18e9554d3d56204
minimum_ledger_commit: 51a84b9cdadc486ff14f5b251912900de1b6caf9
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-280 authenticated Hermes internal invocation checkpoint

## Checkpoint

In progress; no bypass implementation or acceptance verdict. Metadata names
the inherited clean source/ledger floor. Current substantive receipt and exact
following ledger are indexed in the worklog. Owner deferred tests, CI and
native/model calls while prioritizing code-ready bounded work.

## Completed evidence

Clean installed Hermes 0.21.0 source 7cd91114 exposes no authenticated purpose
in pre_llm_call. Title generation already uses the separate auxiliary client.
Background-review forks reuse the user session and ordinary conversation loop;
their private memory-write origin is not a purpose authority. Agency already
skips exact durable internal retries. The portable receipt retains native
file hashes/schema, rejected shortcuts and 21 written/unrun boundary cases.

## Exact blocker

No supported invocation-purpose contract bound to session/turn with
stale/replay rejection. Native Hermes edits were outside this package.
Tracker creation remains pending explicit authorization. Original acceptance
requirements remain unchanged and unchecked; performance savings unmeasured.

## Same-task continuity

Exclusive branch is codex/ar280-authenticated-internal-purpose. Parent owns
publication and all owner installation/provider operations. Preserve other
workers' edits and historical Aug24 live evidence.

## Next bounded work package

Obtain and review a native purpose contract before implementing a skip.
Do not rerun live staffing to rediscover the missing discriminator. Once that
contract exists, bind and consume it before preflight and verify real user
status/skill/substantive turns plus malformed/replayed/cross-session inputs.

## Verification

Source inspection, targeted Ruff and diff checks only. New regressions are
not run by owner direction. No pytest, acceptance review, model/native run,
installed change or all-harness result is claimed.

## Constraints

No prompt-text heuristics, serialized internal flags, private native-agent
introspection or session-only bypass. No native configuration/provider/profile
edits, native monkeypatching, deterministic staffing or weakened finalization.
