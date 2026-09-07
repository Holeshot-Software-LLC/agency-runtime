---
title: "Separate implemented ZCode contracts from current native proof"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, zcode, contracts, evidence]
related:
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - tests/test_zcode_header_proof.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: cca759ab098607cd069454f02ada8173a53e1d8e
short: cca759ab
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
---

# Worklog: reconcile ZCode implementation and proof

## Approach and decision

After AR-131 merged in PR #698/ac1ce173, inspect the next unfinished record.
The old ZCode renderer/registration/identity failures are already repaired.
Retain the relevant native evidence obligation under ADR-0028 and ADR-0223;
do not restore old code, retries or unavailable-verifier blocking. Preserve
the five original criteria and August 19 artifacts as historical evidence.

Correct only the header fixture docstring/comment that called stubbed routing
live proof. No production behavior, user profile, provider, credential, matrix
or acceptance state changes. Reciprocal governing ADR links are repaired.

## Verification

- Installer/header: 16 pass (4.74s); after wording-only edit, 16 pass (3.85s).
- Selected ZCode hook/Stop cases: 13 pass, 96 deselected (5.80s).
- Selected child-adapter/delivery/profile cases: four pass, 104 deselected
  (0.31s).
- Current-source generated ZCode smoke: 4/4 pass, no skips, including exact
  seven-event argv binding, config preservation/idempotency/toggles and a real
  isolated SessionStart process. No native ZCode parent or child is launched.
- Read-only installed inspection: registered/enabled, loaded unknown, no
  canary/attestation, enabled-runtime-unverified; executable null and no CLI on
  PATH. No runtime probe or trust normalization was requested.
- Ruff check/format, metadata, policy, exact worklog, strict docs/tracker and
  diff checks pass. The unchanged production base retains AR-131's 1085-test
  spine/three skips, 138 UI passes, routing and 184/184 conformance receipts;
  they are not claimed as newly rerun for this documentation-only disposition.

## Remaining package

Waiting for an attended installed ZCode call: pin the exact package/profile,
capture Agent success/failure and one-use identities, record-zero specialist
delivery, full Stop payload, actual rejection/replay and unavailable behavior.
Then build evidence and run isolated acceptance. No invented headless backend,
new tracker, new live claim or count change: 40 mapped plus 98 legacy remain.
Publish/merge this disposition and continue to AR-138 (AR-136/137 are done).
