---
title: "Hermes planning distinguishes proposed tests from observed results"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [hermes, planner, reliability]
related:
  - docs/roadmap/issue-AR-428-avoid-test-results-units-without-test-results.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
supersedes: []
superseded_by: null
type: worklog
commit: 0ac9d78e2b632343dc6785f6a13e65c76af5e91c
short: 0ac9d78e
date: 2026-09-09
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/831
related_issues:
  - docs/roadmap/issue-AR-428-avoid-test-results-units-without-test-results.md
---

# Hermes planning distinguishes proposed tests from observed results

## Purpose

After the OpenClaw priority diagnostic, Hermes is the next active host. Its
captured AR-428 plan requests static test-evidence for unexecuted tests, then
recruits a role whose contract requires supplied complete test results. The
independent critic veto is retained and is not assumed erroneous.

## Approach

Clarify the active compact intent prompt and bounded repair prompt together.
Static review of proposed tests produces a review report; test-evidence needs
supplied observed results or permitted execution. Keep independent correctness
review and mandatory execution gates. Recipe 20 prevents older planning contexts
from serving as new policy evidence; older receipts remain supported and immutable.

## Challenges encountered

The legacy full planner prompt already partly described this boundary but the
production compact planner did not. The fix targets the actual active contract.
The real native packet also contains other nominations, so it does not prove
this was the sole reason for the critic veto.

## Decisions and alternatives

No worker names, local staffing rules, parser exemptions, validator changes,
critic overrides, token limits or retries are added. This repairs the intent
contract under ADR-0200; it does not redefine test results or grant execution.

## Verification

Final recipe20 focused checks: 164 passed / 1 skipped in 33.93s. Named fast
production spine: 1151 passed / 3 skipped in 68.89s. UI224, routing, Ruff788,
metadata, policy, documentation1379 and strict tracker419 pass. Frozen conformance,
installed native evidence and isolated acceptance remain pending. Canonical artifact
`ecf8a584` passes strict Twine, independent verification, portable installed smoke
and all616 installed file comparisons; Hermes refreshed on recipe20.
No exhaustive or Windows workflow ran. The exact original packet remains in
AR-428-captured-native-critic-packet-20260909.json.

## Follow-ups

Run final focused and required fast checks, canonical installed verification and
one bounded fresh Hermes native case. Verify the inferred plan and actual cards,
headers and first authoritative receipt. Isolated acceptance governs closure.
Then proceed Codex and Claude; Zcode remains owner-deferred.
