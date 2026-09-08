---
title: "Bind OpenClaw installed-copy provenance"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-09-07
tags: [openclaw, uninstall, provenance, reliability]
related:
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/roadmap/handoffs/issue-AR-270.md
  - docs/roadmap/acceptance/evidence/AR-270-openclaw-copy-provenance-20260907.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/installer_uninstall.py
  - tests/test_installer_registration.py
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-270
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/749
depends_on: []
blocks: []
---

# AR-270: Bind OpenClaw installed-copy provenance

## Problem

OpenClaw `2026.7.1-2` reports a path-installed plugin with a native installed
copy under its extensions directory and a distinct `install.sourcePath` that
points at Agency's owned managed target. Agency's uninstall preflight currently
examines the installed copy alone and rejects the valid two-path receipt as
unbound.

## Current state

2026-09-07 code-first package: implementing. A scoped candidate now validates
the complete installed-copy receipt and carries the current inspect envelope's
sibling install record into the existing native-state digest. The existing
owned-tree, install-ID, bundle-digest, gateway and operator-authority checks
remain prerequisites. Forty-five regression cases are written but deliberately
not executed under the owner's code-first/no-tests instruction. Static Ruff
and diff checks pass; test execution, isolated acceptance and any mutating/live
delivery are still pending. No uninstall, disable or
owner configuration mutation was performed. This is not a completion claim.

Read-only inspection of installed OpenClaw 2026.8.2 confirms a `{plugin, install}`
envelope, `plugin.rootDir`, a copied entry source and the distinct managed
`install.sourcePath`. The historical flat shape remains separately represented.
Versions are optional in the native install schema; exposed versions must
agree with the independently validated ownership manifest.

The first independent source review found a High extraction issue: an earlier
conflicting identity alias could hide the Agency id and be treated as native
absence before binding validation. The candidate now retains records with any
exact Agency identity and refuses conflicting ids at inventory and inspect
admission. Plan-level regressions cover all four identity aliases in inventory,
flat inspect and envelope inspect. The final narrow source-only recheck confirmed
the High resolved and found no additional scoped issue. Neither independent
review executed tests or granted acceptance. Source checkpoint `fc699ff3` is
preserved through normal main integration `a9073fe6`.

Separately authorized tracker [#749](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/749)
was created on 2026-09-07 with `epic:install`. The historical Acceptance wording
and existing proof boxes below are retained; the pending-authorization text is
historical, not the present tracker state. No new acceptance verdict is claimed.

### Preserved historical observations

The write-free uninstall attempt is preserved as
`Native plugin identity is not bound to the managed target`. Native inspection
proved exact plugin id `agency-preflight`, version `0.1.0`, managed source path,
installed-copy path, and the matching Agency install receipt. Recovery used
OpenClaw's native dry-run and uninstall while the gateway was stopped; the
Agency managed target and rollback evidence remain retained.

The current Agency-owned install reproduced the same write-free refusal as
operation `952ff8f6-a660-4309-ac54-191481944440`, plan digest
`a497a256064f2ececd2f27d11993cb681628e4094d2309b398c039d89ec7e2aa`.
The owned stage, install ID, bundle digest, launcher, top-level installed-copy
paths, and nested managed source/install paths all correlated; no mutation was
made and the unchanged plan was not retried. For immediate service recovery,
the stopped gateway used OpenClaw's reversible native disable. Agency remains
registered/staged but inactive; OpenClaw restarted RPC-green with Telegram and
Slack probes green and native model routing unchanged.
The operator then sent exact `reply with pong` through Telegram and received
exact `pong`. Redacted channel status records both inbound and outbound
activity, and the native transcript SHA-256 is `0420d72c...`; role-aware parsing
confirmed the exact request and assistant response without exposing identifiers.

## Approach

Teach the uninstall boundary to validate the documented OpenClaw inspect shape
as one closed provenance receipt: exact plugin identity, managed source path,
installed-copy root, source file within that root, and no conflicting path.
Keep ambiguous or partial records fail-closed.

Accept the historical flat receipt or the exact single-plugin current inspect
envelope. Require native install source `path`, exact managed source, coherent
installed-copy/root aliases (`root` or `rootDir`), and an entry strictly inside
that copy. Reject traversing, substituted, relative or conflicting paths.
Presence of partial install metadata cannot fall through to legacy direct-path
binding. Join only the envelope's own single plugin, never an arbitrary nested
install record. Preserve the joined receipt in the existing plan digest so
provenance changes invalidate application. Native copied files remain retained
by the unchanged `--keep-files` command; they are not Agency-owned tree data.

## Dependencies

- OpenClaw native plugin inspect schema for the audited 2026.7.x line.
- Existing owned-target install-id and bundle-digest checks.
- ADR-0108's closed native provenance and ownership-bound retirement contract.

## Acceptance

- [x] Preserve both exact owned installed-copy refusal receipts.
- [x] Prove the current refusal made no mutation.
- [x] Restore ordinary OpenClaw mode through a reversible native disable.
- [x] Prove an ordinary Telegram request and exact response with Agency disabled.
- [ ] Add an expected-red for the exact installed-copy/native-source shape.
- [ ] Accept only the complete dual-path binding and retain conflicting-shape rejection.
- [ ] Run focused uninstall, registration, and host-boundary tests.
- [ ] Tracker creation remains pending separate authorization.
