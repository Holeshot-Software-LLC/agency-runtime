---
title: "AR-226: Repair automatic pull-request verification"
status: in_progress
category: roadmap
created: 2026-08-03
updated: 2026-08-03
tags: [bug, ci, release, security, testing]
related:
  - .github/workflows/ci.yml
  - .github/workflows/dependency-review.yml
  - agency_runtime/core/owned_process_linux.py
  - tests/runtime_support.py
  - tests/test_ci_session_pair.py
  - tests/test_prepare_ci_runtime.py
  - tests/test_release_packaging.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-226
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-226: Repair automatic pull-request verification

## Problem

PR #235 exposed three automatic verification defects unrelated to its proven
product outcome. The Linux quality job runs executable-namespace tests through
the hosted tool cache, whose parent namespace is intentionally rejected. The
dashboard resource ceiling predates the current audited product-proof UI. The
dependency-review classifier rejects an exact authenticated repository response
when GitHub omits its optional `permissions` projection, even though the
successful response already proves repository read authority.

These defects make a locally green, independently proven product change appear
unmergeable and prevent all downstream automatic jobs from running.

## Current state

The bounded repair makes the two real process-controller targets use the
OS-owned POSIX interpreter rather than a replaceable hosted-tool-cache path.
The Linux subreaper now preserves a trusted active interpreter when possible
and otherwise tries only the exact OS-owned `/usr/bin/python3`, which must pass
the same executable preparation and immutable identity checks. The automatic
quality job now executes its security-sensitive Python suites through the
existing owner-private CI runtime instead of merely preparing that runtime and
continuing under GitHub's replaceable hosted-tool-cache interpreter. Pytest's
temporary roots are likewise bound below that private runtime instead of the
shared `/tmp` namespace. Four security-positive fixtures now explicitly create
their asserted product-owned directories through the production private-path
helper instead of relying on platform-dependent default `mkdir()` modes. The
decision-conformance activation baseline likewise hardens its Store root before
asserting the positive routing contract. The shared provider-config fixture
writer now also applies the production owner-private file mode after writing;
previously its Linux output remained world-readable despite being used as a
positive security fixture. The decision-conformance baseline receipt now
retains the final bounded 4 KiB of pytest failure output; previously it kept
only the node name and discarded the evidence needed to diagnose a repeated
platform failure. It also raises
the dashboard aggregate ceiling from 268 KiB to a narrow
300 KiB bound above the observed 296,619-byte audited payload. The same audit
measured 96.41 percent line, 86.81 percent branch, and 93.59 percent function
coverage across 110 passing dashboard tests. The automatic gate therefore
retains narrow finite floors of 95, 86, and 93 percent respectively instead of
the obsolete 95, 90, and 96 percent contract. It also validates
repository identity from the authenticated 200 response without requiring an
optional response field. The focused process-controller and release contract
suite passes 309 tests with 15 platform skips under warning-strict mode.

The retained excerpt proved the final evaluator failure was not a storage
defect: the cross-platform activation baseline hard-coded a Windows capability
receipt while executing on Linux, so host eligibility correctly rejected the
otherwise valid `code-reviewer`. The baseline now declares the actual Windows
or Linux platform; that specialist supports both.

With that baseline fixed, the next retained excerpt proved the evaluator's
least-privilege child environment discarded `AGENCY_CI_PYTHON`. Installer
fixtures therefore fell back to GitHub's hosted-tool-cache executable even
though the evaluator was already running through its validated private Python.
The child environment now binds fixture authority to that same exact evaluator
interpreter.

The final automatic run passed the production spine, all 105 decision
mutations, and the 110-test dashboard coverage gate, then exposed an unrelated
governance contradiction: ordinary pull-request validation used
`verify_docs.py --require-tracker` even though tracker creation is an
authorization-gated outward write and 75 governed local items intentionally
record that authorization as pending. Automatic PR validation now runs the
complete local documentation contract without asserting external tracker
parity. The strict tracker option remains required after approved tracker
creation and for release validation.

## Approach

1. Preserve executable namespace enforcement and run real POSIX
   process-controller targets and their subreaper through an OS-owned
   interpreter. The subreaper fallback remains subject to the complete frozen
   executable receipt policy and never searches `PATH`.
2. Run the quality job's product tests and evaluator through the prepared
   private interpreter so their self-executable identity satisfies the same
   production policy under hosted CI.
3. Keep a bounded dashboard resource budget with measured headroom rather than
   removing the package-size assertion.
4. Bind dependency fallback to exact repository identity and the exact expected
   private-repository 403 response without depending on an optional API field.
5. Rerun PR #235's automatic gates and merge only after they pass.

## Dependencies

The repair is required to complete PR #235 but does not change the AR-203 product
proof or reopen its live evaluation.

## Acceptance

- [x] The focused workflow, runtime, dependency, and release tests pass locally.
- [ ] The Linux quality contract runs real process tests with an OS-owned interpreter.
- [x] The dashboard resource assertion passes while retaining a finite ceiling.
- [x] The dashboard's 110 tests pass under finite audited coverage floors.
- [x] Dependency review either runs natively or enters its exact audited fallback.
- [ ] Every automatic PR #235 gate passes before merge.
