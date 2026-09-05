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
candidate_commit: 593f074fc2e9e302efc9a20cdc2c82ce98637bb0
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
| 1 | satisfied | `AR-405.1-20260905-124a4504` | `5c23ff3f2472e3c80a2101f1d36a14a007b782d3b3b3f521dc7246319cbbcce0` | 2026-09-05 | tests/test_build_distributions.py:543-591 asserts identity survives clearing only 0x10000000 and rejects kind, inode, and device changes; lines 612-638 additionally cover same-path directory and file replacement. |
| 2 | satisfied | `AR-405.2-20260905-c63ec485` | `137cfdbbb45505167ca58031c13382b77ebf7bd917b41fabb2d96a4e172cfc60` | 2026-09-05 | The cited evidence document records the complete Linux pytest run with 100 passed and one skip; test excerpts retain portable I/O and object identity assertions and explicitly scope the native Windows observation. |
| 3 | satisfied | `AR-405.3-20260905-346df944` | `32944a0324ea4e834019befc929a49aed5e4af160ae3f6272623615109589905` | 2026-09-05 | The evidence document explicitly disclaims current native Windows execution and labels prior observations historical; the Windows-only test retains the filesystem observation with an explicit premise-based skip. |
