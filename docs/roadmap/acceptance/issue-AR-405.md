---
title: "AR-405 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, testing, portability]
related:
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/acceptance/evidence/AR-405-portable-directory-identity-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-405
candidate_commit: pending
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/675
---

# AR-405 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Synthetic volatile Windows bit is ignored; file/link/reparse/missing-inode/device/inode changes are rejected` | 2026-09-05 | `tests/test_build_distributions.py:543-591` |
| 1 | test | `Real directory use and same-path object/kind replacement stay covered on every platform` | 2026-09-05 | `tests/test_build_distributions.py:612-638` |
| 1 | file | `Production identity rejects wrong kinds and reparse points, requires stable inode and seals device/inode/mode/masked attributes` | 2026-09-05 | `scripts/build_distributions.py:148-195` |
| 2 | command-output | `Exact before/after full-file Linux command: 91 pass/two fail before, 100 pass/one native-only skip after` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-405-portable-directory-identity-20260905.md:20-42` |
| 2 | test | `Portable ordinary I/O assertions remain active` | 2026-09-05 | `tests/test_build_distributions.py:530-540` |
| 2 | test | `Only the native Windows observation has a platform guard; real kind/object assertions remain unguarded` | 2026-09-05 | `tests/test_build_distributions.py:594-638` |
| 3 | file | `Current Windows execution is explicitly unavailable; historical 71833c5c evidence and native observation remain scoped, with no artifact-parity claim` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-405-portable-directory-identity-20260905.md:44-61` |
| 3 | test | `Native Windows filesystem premise and observation are retained separately from synthetic coverage` | 2026-09-05 | `tests/test_build_distributions.py:594-609` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
