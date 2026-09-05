---
title: "AR-285 stopped-gateway backlog verification evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, evidence, openclaw, backlog]
related:
  - docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
supersedes: []
superseded_by: null
type: evidence
---

# AR-285 stopped-gateway backlog verification evidence

## Source and scope

Observed 2026-09-05 against source 6edfa6d8, identical to installed runtime code
1de05aea. Documentation-only reconciliation changes no product or test bytes.
The earlier repair is 85ad8d885ca8f29be938ba8c0078cf208e5d9e31; its parent is
4a3267738bb20519500513ea1498fc68f8ea9443. The issue was subsequently renumbered
to AR-285. Replaying a classifier is offline diagnostic evidence, not a live
gateway lifecycle or proof of installation on the current release line.

## Regression and negative-case replay

Read-only extraction of the exact named production classifier from that parent
and from current source, with the native probe replaced by a fixed receipt,
returned the following. No native executable was launched. None means unknown;
True means live/blocking; False means proven stopped.

| Input | Parent classifier | Current classifier |
|---|---|---|
| Complete exit-1 stopped/inactive/dead, RPC unavailable | None | False |
| Same triple with exit 2 | not replayed | None |
| stdout or stderr truncated | not replayed | None |
| Malformed JSON or non-object JSON | not replayed | None |
| Partial stopped triple | not replayed | None |
| Triple plus contradictory running=true | not replayed | True |
| Nested running/active/running | not replayed | True |
| Empty object | not replayed | None |
| Legacy top-level running=false, exit 0 | not replayed | False |
| Legacy top-level running=false, exit 1 | not replayed | None |

The existing regression test
tests/test_installer_registration.py:test_openclaw_gateway_gate_accepts_explicit_nested_stopped_status
uses the same native command and exact stopped triple. Tests immediately above
it prove that unknown/live state stops the registration path before mutation.
tests/test_native_installer.py:test_openclaw_refuses_install_that_would_silently_restart_live_gateway
checks the full installer and asserts that no target or plugin-install command
is created. The runtime implementation remains
agency_runtime/core/installer_registration.py:123-178.

Reproduction method for the parent comparison: git show
85ad8d88^:agency_runtime/core/installer_registration.py, parse the
openclaw_gateway_live function with ast, compile that function only with postponed
annotations and the current pure JSON helpers, replace _run_native with a
NativeCommandResult for the table input, and invoke with home_dir=None and
command_runner=None. Repeat with the current file. This comparison exercises
the changed classifier, not historical host executable preparation.

## Focused checks

Run the issue's current focused suite in an isolated Python environment with
the repository dev dependencies:

```bash
python -m pytest tests/test_installer_registration.py tests/test_native_installer.py -q -W error
```

Result: 181 passed in 4.49 seconds, exit 0 (Linux, Python 3.12).

The wider seven-file triage run is not green: 443 passed, two skipped and two
Windows-attribute fixture failures in tests/test_build_distributions.py
(11.73 seconds). These are recorded separately as AR-405. Missing build-tool
dependencies in the initial environments were corrected using the existing
build-system pins; no runtime configuration or host trust was changed.

## Historical changed-precondition installation

AR-285's original Current state records the rejected writable executable and
parent namespace, followed by the stopped-receipt failure and the regression
repair. Its original Acceptance records a changed-precondition dry run and real
install with the gateway left stopped. Independent detailed installation
records remain in AR-119-openclaw-hermes-verification-packet.md, section 7:
clean a70131d63c511e418edcda2ccae1f8e45866a95a, OpenClaw 2026.7.1-2,
install 479c1a47-7e89-4091-a0f4-548f6913db58, complete without installer restart
or contractor changes; exact bundle, launcher, runtime and manifest digests.
Another retained bundle at 4fab954b0224883439b978adccf95d515f753b3b records
install 87b518e8-dfee-4759-af7d-565705d09afa complete with the gateway still
stopped. These historical receipts are not relabeled as fresh September proof.

## Current host limits

No OpenClaw stop, restart, installation or uninstall was performed for this
backlog review. Current gateway-interruption permission remains outstanding.
AR-271's separate uninstall classifier still rejects nonzero status and is not
fixed or closed by AR-285. Current all-host live proof remains under AR-119.
