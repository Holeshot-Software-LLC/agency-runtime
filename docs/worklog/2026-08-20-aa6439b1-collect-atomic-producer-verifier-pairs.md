---
title: "Worklog detail: Collect atomic producer verifier pairs"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [outcomes, native-child, evidence, promotion, claude]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
supersedes: []
superseded_by: null
type: worklog
commit: aa6439b1c84c4ef4c7b95d17c530a586bf4c08b4
short: aa6439b1
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
---

# Worklog detail: Collect atomic producer verifier pairs

## Purpose

Turn the accepted-outcome v2 rule into a private collector path without making
verified host-child delivery generally reusable. The owner authorized exactly
two consumptions inside one atomic producer/verifier transaction and no wider
authority.

## Approach

The Claude collector accepts exactly two artifacts from one fresh isolated
invocation. Both must independently verify against their immutable Store routing
decisions. Exact launch markers give them one shared 128-bit pair identity and
distinct producer/verifier roles. The producer must carry one contractor card
and host-written output; the verifier must write one exact semantic JSON line in
its own artifact. The collector supplies only the named binding half that the
verifier cannot compute: producer artifact digest and verifier child identity.

Pair-scoped sealed capabilities are registered together, refused by the
ordinary single consumer, and removed together only after the locked Store call
returns a bounded result that rebinds to the locally evaluated envelope, worker,
replay key, and producer digest. All failure paths discard both identities.

## Challenges encountered

Packaged contractor revisions retain the `sha256:` identity form in the Store,
while v6 host delivery canonically carries the equivalent bare digest. The
first end-to-end test exposed a false revision mismatch. Store attribution now
compares the canonical digest identity while preserving exact version and slug
checks; every affected fixture uses the same host-delivery form.

The repository's pytest harness requires an ACL-private scratch boundary, so
the focused tests ran through its trusted local environment rather than the
restricted command sandbox. No hosted runner or live provider was used.

## Decisions and alternatives

The capability did not become a public two-use token, a generic collection, or
an ordinary-turn recorder. A single-capability redesign was not selected after
the owner's exactly-two ruling. Completion alone is still not acceptance: a
producer transcript needs output and a distinct verifier artifact must author
the semantic decision. Extra artifacts, cards, role markers, semantic markers,
or pair identities fail closed under named reasons.

## Verification

- The dedicated synthetic-host collector suite passed 11 tests.
- The affected acceptance, delivery, Rule-4, promotion, lifecycle, and dashboard
  surface passed 339 tests with warnings treated as errors.
- Ruff lint and format checks passed on all changed Python files.
- `git diff --check` and documentation validation passed for 709 Markdown files.

## Follow-ups

- Wire the isolated Claude canary to one bounded producer/verifier invocation,
  verify it locally, then request fresh install/live authorization under AR-252.
- Keep Codex live outcome proof blocked on the upstream readable child surface.
- Prove ZCode, OpenClaw, and Hermes behavior under AR-253; no matrix cell moved
  in this source-only checkpoint.
