---
title: "Close native and workflow trust gaps"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [security, operator-presence, release, ci, dashboard]
related:
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
supersedes: []
superseded_by: null
type: worklog
commit: f64ba1e54b76cf4c05a7a6a290028f316467bd07
short: f64ba1e
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
---

# Worklog detail: Close native and workflow trust gaps

## Purpose

Close the production-readiness defects found by independent native, release,
HMAC-authority, executable-discovery, CI, and UI traces while preserving honest
external gates. The package needed one real operator-presence-controlled
mutation, platform-honest artifacts, fail-closed workflow capability checks,
and truthful dashboard evidence before clean artifact and dogfood evaluation.

## Approach

Implemented exact roster rollback as a prepare, native-presence verify,
transactional revalidate, and commit coordinator. Added the pinned Windows 11
x64 consent helper, source/provenance/notices, portable and `win_amd64` wheel
profiles, structural PE and cross-artifact verification, and an explicit
unsigned-build versus signed-delivery boundary.

Paired isolated CI sessions to remove duplicate hosted job envelopes, collapsed
unavailable CodeQL fanout behind one preflight, and made dependency-review
fallback require an exact authenticated capability response. Strengthened
remediation history with current candidate/audit/active-basis eligibility and a
revision-bound dashboard projection. Centralized repository-ancestor executable
exclusion across every confirmed launch surface. Finished the UI trace by
keeping controls read-only, surfacing safe request IDs, and clarifying runtime
capture disclosure.

## Challenges encountered

The broad review found two late security defects after earlier focused suites
were green: repository-sibling `PATH` poisoning from nested workdirs and stale
signed remediation history suppressing its original queue event. A subsequent
UI trace found stale paged history could survive the server repair, and the CI
trace found ambiguous GitHub 403/404 responses could select non-equivalent
fallback evidence. GitHub Actions billing remained externally blocked, so all
runner savings are projections rather than hosted measurements.

## Decisions and alternatives

The Windows helper remains a reproducible unsigned review input; publisher
signing, legal disposition, and attended Windows Hello canary evidence remain
separate AR-161 gates. Portable wheels exclude every structural PE, while the
Windows wheel admits only the pinned helper. CI reductions preserve every exact
Python, OS, coverage, artifact, and CodeQL-language surface. Ambiguous hosted
capability responses fail instead of being reinterpreted as unavailable.

## Verification

- Combined security/release/integration package: 1,102 passed, 1 platform skip.
- Independent security checkpoint: 406 passed, 1 skip; 265 passed; final
  remediation snapshot 34 passed; no actionable severity finding remained.
- Remediation/dashboard projections: 166 passed; dashboard UI: 102 passed.
- Release/workflow contracts: 115 passed; dependency-review subset: 37 passed.
- Ruff lint and format: 577 files passed.
- Documentation metadata/policy/worklog and 424-document verification passed.
- Zizmor pedantic strict offline: no findings, one documented suppression.
- `git diff --check`: passed.

## Follow-ups

- [AR-160](../roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md):
  build and compare the exact clean Windows/Linux artifact set.
- [AR-161](../roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md):
  obtain publisher, legal, signing, timestamp, and attended-canary authority.
- [AR-156](../roadmap/issue-AR-156-restore-cost-bounded-verification.md) and
  [AR-159](../roadmap/issue-AR-159-enforce-production-branch-protection.md):
  repair Actions billing, measure one PR and one main run, then authorize hosted
  enforcement separately.
- Tracker creation and closure for AR-160 through AR-166 remain pending owner
  authorization; no outward mutation occurred.
