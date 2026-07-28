---
title: "Worklog detail: Packaged Codex canary candidate"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, packaging, smoke, production-readiness]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
supersedes: []
superseded_by: null
type: worklog
commit: 55a03e1304d41adcb3eab1c276efaf976fb53896
short: 55a03e1
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
---

# Worklog detail: Packaged Codex canary candidate

## Purpose

Bind the persisted Codex activation correction to one exact locally verified
Windows artifact pair and fresh installed-package evidence without changing the
currently trusted Codex launcher while the operator is remote.

## Approach

Exact ledger head `1a58e5e` was checked out in an owner-private detached
worktree. The canonical builder materialized reviewed Git blobs into an
owner-private build boundary, emitted the host-honest Windows wheel/source pair,
and the independent verifier compared both artifacts to that exact commit. The
wheel was installed into a separate fresh Python 3.13 environment for dependency,
package-option, smoke, and offline routing checks.

## Challenges encountered

The first build attempt used the repository virtual environment and was rejected
because its executable ACL permits cross-account mutation. No artifact was
published from that attempt. An owner-private Python environment passed the
same launcher-identity gate; no ACL rule or release check was relaxed.

## Decisions and alternatives

The existing `194d697` Codex installation and its trusted hook inventory were
left untouched. The package proof is not promoted to live activation evidence:
attended refresh, trust of the changed launcher, and one fresh current-profile
canary remain separate gates. Hosted and exhaustive diagnostics remain outside
this bounded package.

## Verification

- Canonical build passed for exact commit
  `1a58e5e307237e1549c96c03f1200b4531c57cd5` in 67.8 seconds.
- Windows wheel: 7,528,969 bytes,
  SHA-256 `e6a94cd99cd7a7a387144e3e332d4885e12cfc295d86ce4ed052c61e80e43bf5`.
- Source archive: 18,402,728 bytes,
  SHA-256 `7d7d003ed6ec41a1d7cba7cb235038be65914a878e818926cb65288f440a2209`.
- Strict Twine and independent exact-commit distribution verification passed.
- Fresh Python 3.13.14 wheel installation and dependency checks passed.
- Packaged smoke passed all 8 checks with no failures or skips in 43.6 seconds.
- Installed canary-option assertions passed; offline routing evaluation passed
  every gate in 15.1 seconds.
- No live model call, trusted-install change, hosted workflow, exhaustive corpus,
  compatibility matrix, push, tag, or publication occurred.

## Follow-ups

After the operator returns, install exact candidate `1a58e5e` through the
attended refresh, trust the changed eight-hook inventory, and run one bounded
current-profile activation canary. Record the exact attestation or the smallest
truthful failure before changing the candidate again.
