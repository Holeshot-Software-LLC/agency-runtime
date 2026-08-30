---
title: "AR-332: Pin a private umask for host-canary child launches"
status: in_progress
category: roadmap
created: 2026-08-29
updated: 2026-08-30
tags: [bug, reliability, canary, security-posture, claude]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/security.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-332
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/346
depends_on: []
blocks: []
---

# AR-332: Pin a private umask for host-canary child launches

## Problem

`agency host-canary` launches the host child with the ambient umask. Under
this machine's default umask 002 the Claude child creates its project
directory inside the private collection lease at mode 775, and the strict
artifact guard, which requires an owner-only final parent, refuses the child
card artifact with `artifact_not_trusted`. An otherwise fully passing live
canary then fails on an environmental default the runtime never pinned.

## Current state

- 2026-08-29 receipts in
  `~/.agency-runtime/evidence/ar297-live-harness-20260829/`:
  `claude-canary-execute.json` ran under the ambient umask and reports a
  complete live turn (run, delegation, finalization, `code-reviewer` selected
  and loaded, zero preflight failures) with delivery refused as
  `artifact_not_trusted`; `claude-canary-execute-2.json` ran identically under
  a `umask 077` wrapper and reports `canary_passed=true` with the delivery
  `collected`.
- The runtime creates the lease root itself at mode 0700; only the child's own
  directories inherit the ambient umask.
- The real profile `~/.claude/projects` tree is also mode 775 under
  claude-code 2.1.251, so any future real-profile artifact trust check faces
  the same posture.
- The claude-code 2.1.251 npm tree shipped group-writable directories that
  blocked the executable posture probe (`native-inventory:error`,
  "cross-account substitution") until tightened manually with `chmod -R g-w`
  on 2026-08-29.
- Code landed 2026-08-30: the safe canary backends wrap every host child
  launch (both codex `exec` sites and the claude `-p` site) in a restored
  POSIX `os.umask(0o077)` scope, a focused regression proves the wrapper
  applies and restores the mask, and troubleshooting documentation names the
  umask precondition for releases without the pin. The ambient-umask live
  Claude canary re-run rides the next production install.

## Approach

Set a private umask (or equivalent explicit mode remediation) for the canary
child launch inside the safe canary backends so artifact trust does not depend
on the invoking shell's umask. Consider normalizing or asserting the
collection-root subtree modes before scanning, and add a regression that runs
the collection under an 002 umask.

## Dependencies

None. Keep the strict guard semantics in
`agency_runtime/core/store/security.py` unchanged; the launch environment,
not the guard, is the defect.

## Acceptance

- [ ] The Claude live canary passes from a shell with umask 002 without a
      wrapper.
- [x] A focused regression covers the child-launch umask pin (applied and
      restored around the launch sites artifact collection depends on).
- [x] Troubleshooting documentation names the umask precondition for older
      releases.
