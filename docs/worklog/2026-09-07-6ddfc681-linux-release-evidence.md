---
title: "Retain paired release proof with current Linux evidence"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [release, packaging, linux, backlog]
related:
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/acceptance/evidence/AR-160-linux-artifacts-20260907.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 6ddfc681ac0140f5910c102d0d13fe21f3327b5b
short: 6ddfc681
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/712
related_issues:
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
---

# Worklog detail: Current Linux release evidence

## Approach and decisions

Retain ADR-0219's current two-profile/no-helper contract. Explicitly distinguish
historical implementation prose from current state; no old checked box becomes
current evidence. No code/test/workflow change, new architecture decision or
acceptance rewrite. All five current criteria remain unchanged and unchecked.

## Verification

258 focused warning-strict release/build/verifier/isolation tests pass in 35.56s,
one actual Windows case deselected, no failures/skips. Clean f1c7d0b0 produces a
canonical Linux wheel/source pair; independent portable verification and strict
Twine pass. The receipt retains exact artifact hashes and candidate identity.
Separate fresh Python 3.12.3 installs each pass packaged MCP/dashboard/config/
roster/offline-selection, CLI help/version, pip check and eight deterministic
smoke checks, including all five generated host bundles, without skips.
Metadata/policy, exact worklog, strict docs/tracker, Ruff and diff checks pass.
AR-156 unchanged-input spine/UI/browser receipts are explicitly reused.

## Challenges and follow-ups

No local test/build/install failure. Windows producer, two-source equality,
shared payload and assembled release proof remain absent for this candidate;
the owner retains Windows. Generated smoke is not attended native loading,
quality staffing or a live canary. No release publication or hosted setting
change is authorized by this package. Keep AR-160 in_progress, counts unchanged
at 40 actual trackers plus 89 unfinished legacy records. Publish one normal PR,
then AR-162; AR-161 is already retired. Artifact hashes apply only to f1c7d0b0,
not subsequent documentation commits.

PR #712 carries this retention. Final docs validation covers 1169 Markdown
files; tracker parity covers 397 mapped items/two historical PR exceptions.
End telemetry is 49.9 percent at 09:06:27Z; 6ddfc681 and immediate ledger
42202ef7 form the clean substantive checkpoint before normal publication.
