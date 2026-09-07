---
title: "Verify existing public HTTP disconnect handling"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [http, observability, verification, backlog]
related:
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: a35657e14e0d0bd669a542f02abda2b64a5374ca
short: a35657e1
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
---

# Worklog detail: HTTP disconnect evidence

## Approach

Confirm the existing shared classifier and nested response boundary; no runtime
repair is needed. Strengthen primary GET/POST tests to enter actual observation
emission, match their surface/operation and reject private query/body/error text.
Preserve quiet primary/defensive completion, unrelated-error propagation and
one sanitized response for genuine faults.

## Challenges and decisions

The four-module HTTP gate exposed two stale fixtures, both reproduced on
unchanged main 6b4650b3 (two failed, 3.01s). Compare roster cardinality to the
actual enabled Store catalog, not another fixed size. Seed a real correlated
suggestion for the resident-worker admission test and assert its exact rows
remain unchanged after rejection; do not rely on a mocked hiring lifecycle.
AR-176 records these as repaired here, not additional unresolved work.

Only the sixth verification criterion is explicitly reconciled under ADR-0105;
the original wording and first five criteria remain. No coverage floor or
security policy changes. Native Windows stays with the owner.

## Verification

Initial disconnect pair: 26 pass (0.52s); pair plus repaired HTTP cases:
28 pass (1.83s). Final complete HTTP/disconnect/runtime-observation package:
104 pass, three existing inference skips (22.25s); shared classifier coverage
100 percent, 11 statements/four branches, no misses or partial branches.
Ruff check/format pass over 766 files. Exact-byte reuse binds the unchanged
29-module spine (1085/three skips), UI 188/current floors and 21-case wheel
receipt from AR-156. No new install, aggregate coverage or exhaustive claim.

## Follow-ups

Freeze six builder rowsets at a35657e1 and run isolated acceptance before closure.
Publish one normal PR, read back the merge and continue at AR-158. Counts
remain 40 actual open trackers plus 91 unfinished legacy records until accepted.
