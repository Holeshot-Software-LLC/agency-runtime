---
title: "AR-271 bounded stopped-gateway uninstall evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, uninstall, openclaw, regression, safety]
related:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/acceptance/issue-AR-271.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-271 bounded stopped-gateway uninstall evidence

## Observable outcome and red baseline

Starting main: 78e501b7b17b6c270b5c2c7122b61bf454190749. Linux/Python 3.12
with an isolated dev/release environment. The same complete bounded native
receipt contains service.runtime status=stopped, state=inactive, subState=dead,
rpc.ok=false and exit 1. A process-local replay through the existing production
functions returns install=False (stopped), uninstall=None (unknown), with no
native command executed. New tests were added before production changed:

```text
python -m pytest tests/test_host_uninstall.py -k \
  'stopped_exit_one or unproven_or_live_status or stopped_openclaw_is_rechecked or share_the_bounded_gateway_classifier' \
  -q -W error
7 failed, 15 passed, 31 deselected in 0.94s
```

All seven failures are at the expected stopped-receipt refusal: two positive
retirement cases, four stopped-then-drift scenarios before they can reach the
drift, and the install/uninstall parity assertion. Existing negative cases pass.
This is not a live gateway or real installed-host uninstall receipt.

## Implementation and focused demo

The install classifier is extracted without changing its interpretation into
installer_registration.openclaw_gateway_state. Installation still invokes its
existing native runner and returns the classification plus original receipt.
Uninstall imports the same function and still obtains its receipt through
_run_bound_native_command. No authority, command, retention, locking, native
postcondition or executable trust implementation is replaced.

After the shared classifier, the focused installer/uninstall/CLI files returned
244 passed, two Windows skips in 7.11s. Three more execution-identity drift
cases and an OpenClaw owner-denial case were then added. Final focused command:

```text
python -m pytest tests/test_host_uninstall.py tests/test_installer_registration.py \
  tests/test_native_installer.py tests/test_cli_uninstall.py -q -W error
248 passed, 2 skipped in 7.38s
```

The disposable-home demo plans without writes, observes the exact stopped
receipt, runs the prepared transaction with a test owner-verification callback,
and compares the retained bundle bytes to the original for both registered and
already-detached plugin cases. It performs at least four gateway status probes,
only the required plugin mutation, and no gateway start/stop/restart command.
Separate cases change the gateway to live/unknown after approval and after the
locked replan immediately before commit; no plugin mutation or bundle movement
occurs. Native-bound launcher/environment/revalidation drift is rejected before
the process launcher is called. These are deterministic contract tests using
injected native responses, not a bypass used on a real host.

## Scope and remaining delivery

The original empty Acceptance section now spells out the existing issue's
bounded outcome and retained safety requirements; it does not drop an old
criterion. AR-285 retains its distinct historical dry-run/install evidence gap.
This package does not stop, restart or uninstall the owner's real gateway.
The named fast spine, isolated acceptance, PR merge and exact installed-source
smoke checkpoint are recorded as they complete. Native Windows and exhaustive
integration workflows are not claimed; AR-119/160 keep those evidence owners.

Pre-candidate fast verification: the named Python production spine returned
1030 passed, three skipped in 63.79s; UI returned 138 passed. Ruff check and
format pass. These are distinct from a live installed-host acceptance claim.

## Post-candidate final verification

Candidate 4fdcd6a7 has three satisfied isolated Codex verdicts, retained at
8421e5f7. Protected umask 077 decision conformance passed its baseline (99.682s),
killed 182/182 mutations with zero invalid/survived, and returned
source_unchanged=true. Routing gates passed in the deterministic recall-only
scope. Documentation/acceptance/tracker unit tests returned 104 passed (0.71s),
and strict tracker parity passed (396 mapped records, two PR-history skips).
PR #679 carries this bounded code fix; installed-source smoke follows merge.
