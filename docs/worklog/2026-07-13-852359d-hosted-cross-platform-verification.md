---
title: "Hosted cross-platform verification hardening"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [worklog, ci, windows, linux, security, portability]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
type: worklog
commit: 852359d4dd688651ca13c1d2ef9bc3bc6b93359e
short: 852359d
date: 2026-07-13
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
---

# Worklog detail: Harden hosted cross-platform verification

## Purpose

Repair defects that appeared only when the reviewed branch ran on GitHub's
Ubuntu and Windows fleets, while preserving the strict security and portability
claims enforced by the release gate.

## Approach

- Recognize drive-qualified and UNC Windows executables independently of the
  current operating system so Linux-generated Windows payloads remain inert and
  valid.
- Replace tests that mutated the shared process-wide `os.name` module value
  with module-owned platform seams, eliminating failure-report corruption.
- Close socket-backed `HTTPError` responses centrally before re-raising them,
  covering every no-redirect caller and repeated dashboard authentication
  probes.
- Verify leading-user expansion against an exact expected path instead of
  rejecting legitimate tildes in Windows 8.3 runner directory names.
- Give only the real Windows PowerShell and Job Object integration test a
  bounded cold-start allowance; production timeouts and the strict timeout
  regression remain unchanged.
- Run CodeQL locally on every supported repository, uploading results natively
  when GitHub Code Security is available and retaining SARIF artifacts when it
  is not.

## Challenges encountered

The local Windows suite did not reproduce hosted antivirus startup latency or
the `RUNNER~1` path used by GitHub's runner image. Linux exposed a second
cross-compilation defect because POSIX path resolution treated a synthetic
drive-qualified Windows command as relative. CodeQL completed both language analyses but
failed only when the private repository rejected SARIF upload.

## Decisions and alternatives

- **Raise every delegation timeout.** Rejected; only the native PowerShell
  integration fixture needs a hosted cold-start budget.
- **Ban every tilde in a resolved path.** Rejected because a tilde is ordinary
  data after the leading user-expansion token.
- **Disable CodeQL for private repositories.** Rejected because local analysis
  and retained SARIF remain valuable without a licensed upload endpoint.
- **Enable GitHub Code Security automatically.** Rejected because licensing and
  billing are repository-owner decisions.

## Follow-ups

- Confirm Ubuntu Python 3.10-3.14, Windows Python 3.10 and 3.14, CodeQL,
  dependency review fallback, security, and artifact smoke jobs on the pushed
  commit.
- Record the hosted evidence in AR-07, AR-16, AR-17, and the release checklist
  only after the reviewed branch is green.
