---
title: "AR-417 acceptance verification record"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, verification, critic, installation]
related:
  - docs/roadmap/issue-AR-417-self-contained-qualified-veto-regression.md
  - docs/roadmap/acceptance/evidence/AR-416-installed-qualified-veto-20260908.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-417
candidate_commit: caab485176d63c3c0062c022e55866d8733f19e7
evidence_cutoff: 2026-09-08
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/790
---

# AR-417 acceptance verification record

## Builder evidence

Installed replay and packaged regression evidence are distinguished from native
host evidence. Refreshed native hooks require operator review at this candidate.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | command-output | Verified extracted source regression changes from one failure to eight passes | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-416-installed-qualified-veto-20260908.md#packaged-regression |
| 1 | test | Self-contained exact native verdict literal | 2026-09-08 | tests/test_qualified_critic_reasons.py:27-41 |
| 2 | test | Same captured verdict and rejection, projection and finalizer assertions | 2026-09-08 | tests/test_qualified_critic_reasons.py:27-78 |
| 2 | command-output | Runtime and archive-policy scope unchanged | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-416-installed-qualified-veto-20260908.md#candidate-and-build |
| 3 | file | Canonical issue state and tracker mapping | 2026-09-08 | docs/roadmap/issue-AR-417-self-contained-qualified-veto-regression.md#current-state |
| 3 | command-output | Exact source archive evidence | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-416-installed-qualified-veto-20260908.md#packaged-regression |
| 3 | command-output | Linked worklog and PR | 2026-09-08 | docs/worklog/2026-09-08-installed-qualified-veto-verification.md#verification |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-417.1-20260908-e3fb880c` | `4febe233695a1d419c11461b7eda2c09594fdddc7bd34598057a83b96228c46c` | 2026-09-08 | Snapshot tests/test_qualified_critic_reasons.py pins the verdict inline with no JSON read (only a comment), MANIFEST.in ships tests/*.py but only docs/*.md so the attachment is excluded, and the AR-416 evidence and worklog both record the extracted verified sdist run returning 8 passed. |
| 2 | satisfied | `AR-417.2-20260908-1f89f38e` | `005a54d4a9c57e5243a42152980952c36bdf39eb378f97b545065df67717a2ac` | 2026-09-08 | tests/test_qualified_critic_reasons.py:27-78 pins the literal verdict matching the captured response in AR-414-native-critic-packet.json:860 and drives the real veto, receipt projection and failed finalizer (0 events); MANIFEST.in allows only docs *.md and no AR-417 change appears in agency_runtime. |
| 3 | satisfied | `AR-417.3-20260908-b6667545` | `75faeca8799567a9e5cb1e25d2e20d982f0d6e6eaf493782c6413766dcc3005c` | 2026-09-08 | Issue AR-417 front matter (in_progress, p2, tracker #790, related links) matches docs/roadmap/README.md mapping and commit table (8629e2ed, 0bc2f895), the worklog README rows, and the worklog plus AR-416 evidence figures (extracted regression 8 passed, focused 124, 1151/3 skips, AR-417 still open). |
