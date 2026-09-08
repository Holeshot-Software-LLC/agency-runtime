---
title: "Retire the obsolete Codex V2 activation-grant checklist"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [codex, native-child, backlog, governance, evidence]
related:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/roadmap/acceptance/evidence/AR-191-v2-checklist-retirement-20260907.md
  - agency_runtime/adapters/hooks.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0236
type: decision
deciders: [maintainers]
---

# ADR-0236: Retire the obsolete Codex V2 activation-grant checklist

## Context

AR-191 repaired July Codex V2 hook-name compatibility and diagnostic defects.
Its checklist also requires the former one-use activation-grant chain and
replacement of a distinct supplied child turn with an active parent trace.
Those requirements no longer describe the product: `b222414b` deleted the
grant API and `7e1b3603` deliberately rejects invalid explicit parent turns.
AR-255 already owns the inference-owned, host-proven successor contract under
ADR-0118, ADR-0156 and ADR-0159.

The exact aliases, argument preservation, truthful process exit codes and
existing-Store requirement still exist. A September 7 live receipt proves one
restricted current-profile exec canary under ADR-0179/ADR-0193, not restoration
of the July grant graph or completion of AR-180's broader host matrix.

## Decision

Retire AR-191 as `wont_do`, superseded by AR-255. Preserve its original nine
criteria and checked/unchecked states verbatim as history. Do not mark them all
satisfied, issue acceptance verdicts, or label the record `done`.

Keep both exact native-spawn spellings, explicit current follow-up spellings,
non-message tool arguments, process exit-code fidelity and current-profile
existing-Store checks intact. Do not restore the deleted grant APIs or allow an
invalid explicit turn to borrow another live trace. Legacy read/attachment
support for existing rows is not new grant-issuance authority.

AR-255 remains the successor for current native-child staffing and host delivery.
AR-180 retains broader live gates; AR-185 and AR-192 retain exact verification
and trust requirements. The restricted one-card exec receipt does not prove
ordinary encrypted assignments, TUI/Desktop, multi-card or child-only delivery.

This is a records-only application of existing policy, not a new runtime
authority or formal supersession of those governing ADRs. It authorizes no
provider call, hook trust change, profile mutation or Windows work.

## Consequences

The backlog loses an obsolete grant-era checklist without disguising missing
current evidence as success. Its useful implementation stays in production,
and its historical failed attempts and original criteria remain discoverable.
Current staffing and delivery work continues through the explicit successor
instead of reconstructing removed machinery solely to close a stale issue.

## Alternatives

- Accept all nine original criteria: rejected; the grant graph was removed and
  the new live receipt has a narrower, different contract.
- Restore grants or invalid-turn fallback: rejected; that would contradict the
  existing implementation and authority boundary.
- Leave AR-191 as a mandatory duplicate blocker: rejected; AR-255 and AR-180
  already retain the current staffing and live-evidence obligations.
- Remove aliases or diagnostic safeguards along with the record: rejected;
  those are implemented behavior, not obsolete checklist machinery.

## Verification basis

At `c64ce3ce`, 23 fresh focused offline checks pass in 3.47 seconds. The receipt
preserves their exact command/output, separately labels the earlier retained
64-check summary, identifies removed history, and maps every original
criterion. Existing AR-180 live evidence is reused with its exact limitations.
No production bytes change and no new native or model turn is run.
