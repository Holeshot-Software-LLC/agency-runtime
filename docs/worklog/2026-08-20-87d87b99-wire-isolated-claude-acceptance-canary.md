---
title: "Worklog detail: Wire isolated Claude acceptance canary"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [outcomes, canary, native-child, evidence, promotion, claude]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
supersedes: []
superseded_by: null
type: worklog
commit: 87d87b99b4e8acf10f383281ea9a69a2144d0f81
short: 87d87b99
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
---

# Worklog detail: Wire isolated Claude acceptance canary

## Purpose

Give the private exactly-two collector one explicit installed-host proof path
without widening verified-delivery capabilities into ordinary turns or a
general caller-controlled outcome API.

## Approach

The new Claude mode is selected only by `host-canary --accepted-outcome` and
requires the exact phrase `RUN LIVE claude ACCEPTED-OUTCOME CANARY`. One fixed
prompt asks Claude to start a TypeScript producer and then an independent
verifier serially in the same isolated invocation. A random 128-bit identity
binds both child launch markers and the verifier's exact semantic JSON line.

The backend retains both host artifacts only until the private home is cleaned
up, then invokes the sealed pair collector directly. It accepts no callback or
caller-supplied envelope. Before either capability can reach the atomic Store
call, both immutable routes must name exactly one applied provider equal to the
configured per-host child-judge pin. A mismatch fails as
`provider_pin_mismatch` and records no accepted outcome.

The result projection is content-free: it reports the requested pin, both
providers that actually answered, exact card revisions, host-artifact digests,
pair and decision identities, fresh Store result, and promotion status. Model,
parent, producer, and verifier prose are deliberately omitted; replay cannot
pass as a fresh live outcome.

## Challenges encountered

The complete local harness found one regression already present on exact main:
the ZCode parent-header repair parametrized and renamed its first-pass header
test, while the curated decision-conformance manifest still named the deleted
Codex-only function. The manifest now names the real three-host test. Its full
baseline passed and all 151 curated mutations were killed.

The global Python installation exposes pytest only through user site-packages,
which the mutation evaluator intentionally removes. Running through the
repository's existing virtual environment made the baseline authoritative; no
package was installed. The restricted source-CLI smoke could not attest the
real host inventory, so it counts only as confirmation-gate proof.

## Decisions and alternatives

The ordinary one-child canary remains unchanged at two turns. Only the explicit
outcome mode receives four bounded turns for two serial child calls and a final
response. Provider verification happens before outcome recording rather than
being inferred from the parent host or checked only after a row exists. The
mode targets one exact known contractor and refuses plural producer cards,
replay, missing output, ambiguous semantics, extra children, and cross-parent
or cross-provider results.

## Verification

- Focused accepted-outcome collector, backend, runner, parser, and CLI tests:
  46 passed with warnings treated as errors.
- Widened canary/outcome/CLI regression surface: 273 passed warning-strict.
- Complete local harness: 14/14 gates in 14.4 minutes, including 796 production-
  spine passes with 20 skips, 695 AR-119 matrix-evidence passes, and 134
  dashboard tests at the required coverage thresholds.
- Full decision-conformance evaluation: green baseline, 151/151 mutations
  killed, zero survived or invalid, and source unchanged.
- Ruff lint/format, `git diff --check`, metadata, policy, worklog, and 710-file
  documentation validation passed.
- Read-only source CLI reached the new exact confirmation gate without
  `--execute`; no host CLI, provider, Store outcome, or promotion was invoked.

## Follow-ups

- Obtain fresh owner approval before push, PR, merge, exact-main installation,
  or the first live Claude accepted-outcome draw.
- Use live results to decide acceptance and promotion evidence without moving a
  matrix cell beyond its named authority or claiming optional R8 credit.
- Retain Codex's upstream child-artifact blocker and continue ZCode plural-card
  proof under AR-253 after the Claude package closes.
