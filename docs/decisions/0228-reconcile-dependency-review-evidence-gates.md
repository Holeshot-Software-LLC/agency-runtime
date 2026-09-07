---
title: "Reconcile dependency-review measurement and legacy tracker gates"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [ci, security, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0228
type: decision
deciders: [maintainers]
---

# ADR-0228: Reconcile dependency-review measurement and legacy tracker gates

## Context

AR-165's actual malformed-JSON boundary still needed repair: duplicate keys
could overwrite an ambiguous error or repository identity, while object and
non-finite success payloads were accepted. Strict bounded parsing repairs that
behavior without changing either permitted workflow path.

The record also retains a private-repository snapshot, a historical 0.43 raw
runner-minute observation, and a presumed current billing block. September 7
read-only identity instead reports public/non-fork; the exact comparison
endpoint returns an empty array for the calling identity. This is not proof of
workflow-token authority, a current hosted job, or the cause of old cancellations.
No savings claim is made. The owner requested relevance-led backlog cleanup,
and AR-347 already provides this legacy record's self-shrinking tracker exemption.

## Decision

Explicitly reconcile only criteria 8 and 9:

- Current repository capability and hosted-check limits are reported accurately;
  any speed or billing-savings claim requires a matched hosted pull-request run
  recording the selected path, stable check name and raw duration.
- AR-165 follows the governed pre-tracker exemption while unmapped; both strict
  documentation/tracker checks pass, and any later authorized tracker mapping
  has exact URL/state parity with the local record.

Preserve both original wordings and historical telemetry. Criteria 1–7 remain
unchanged. Do not claim an unperformed benchmark passed or create a redundant
tracker. Require all nine current criteria to receive isolated candidate-bound
verdicts before completion.

Keep the single job, authenticated bounded requests, exact identity/scoped
unavailable classification, pinned native action and moderate threshold,
non-equivalent installed-runtime audit, and fail-closed aggregate. ADR-0037 and
ADR-0097 remain accepted; no hosted setting, licensing or workflow dispatch is
authorized. AR-159 still owns current hosted check/enforcement proof.

## Consequences

Implementation completion cannot be presented as current hosted success or cost
savings. Future claims retain their matched-run requirement. Tracker mapping
must remove the legacy exemption and satisfy both strict parity gates.
Current malformed input is repaired; historical missing evidence is not invented.

Implementation and builder evidence are committed at 9effff3f; b038cdb9 is the
immediate worklog checkpoint. Candidate-bound review, not this decision, assigns
the nine acceptance verdicts.

## Alternatives

- Require a new hosted run despite no current savings claim: rejected as an
  unnecessary external gate for this bounded implementation record.
- Infer savings from fewer jobs or old timing: rejected as unsupported.
- Delete the fallback or native action: rejected; both permitted paths remain.
- Create a duplicate tracker or silently call old parity satisfied: rejected in
  favor of explicitly applying AR-347's existing governance.
