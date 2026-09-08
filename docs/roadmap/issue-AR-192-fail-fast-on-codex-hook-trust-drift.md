---
title: "AR-192: Fail fast on Codex hook trust drift"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-09-08
tags: [codex, hooks, trust, activation, performance]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/handoffs/issue-AR-192.md
  - docs/roadmap/acceptance/evidence/AR-192-hook-trust-reconciliation-20260908.md
  - README.md
  - CHANGELOG.md
  - docs/TROUBLESHOOTING.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/codex_hook_trust.py
  - tests/test_codex_hook_trust.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-192
priority: p0
tracker_url: null
depends_on: [AR-182, AR-193]
blocks: [AR-180]
---

# AR-192: Fail fast on Codex hook trust drift

## Problem

An attended Codex refresh can replace Agency's hook commands while an older
Codex TUI still holds the pre-refresh hook snapshot. Approving that stale view
writes valid trust hashes for the prior definitions, but the settled plugin is
correctly reported as `modified` and none of its hooks execute. Activation
verification nevertheless spent a full model-backed canary before discovering
that the Store had received no hook evidence.

This failure has recurred during rapid upgrade testing. Codex's refusal to run a
modified command is the intended security boundary; the Agency verifier's
failure to inspect that boundary before a model call is the bug.

## Current state

The existing implementation at `d6611ca` remains relevant: ordinary attended
current-profile exact-activation verification inspects the selected Codex
executable's exact working-directory inventory before launching the model.
This is not a blanket rule for every generic canary or for the separately
explicit autonomous-bypass and managed-policy modes governed by ADR-0173.
The September 8 reconciliation changes records, not product trust authority.

Fresh Linux focused tests at `f0e38863` pass **180 tests in 11.34 seconds**;
six targeted files pass Ruff lint and formatting. All product, script, test and
packaging paths are unchanged from installed-source candidate `4db6be16`.
The portable receipt records exact file hashes and the scope of each probe.
An earlier actual installed read-only inspection found 8/8 trusted hooks in
0.569 seconds. That inspection occurred after the earlier live canary and is
not represented as its preceding preflight. After the parent's exact
`4db6be16` reinstall, the 00:30:44 UTC native inspection found **8 enabled,
8 modified, 0 trusted** in 0.542472 seconds. The subsequent actual installed
verification exited 1 in 3.488429 seconds with
`codex_hook_trust_not_ready` and `model_invocation_attempted=false`.
This is a live proof of the fail-fast boundary, not successful activation.
Criterion 6 remains open for supported owner approval of the settled hashes
and then a successful no-bypass canary. No acceptance run was spent on that
known missing evidence. The named source-equivalent production spine passed
1085 cases with three skips in 69.50 seconds; its exact provenance is linked
in the receipt.

Retained evidence publication:
[PR #742](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/742).

### Historical July implementation evidence

Codex 0.145's read-only app-server `hooks/list` method is the authoritative
inspection surface. A fresh inspection of installed plugin
`0.1.0+codex.9e970ea1b470` found all eight expected Agency hooks enabled but
`modified`. Their current hashes differed from the hashes persisted by the
stale TUI. The same result held for the repository and private canary working
directories, ruling out project trust and canary CWD as the cause. Tracker
creation remains pending explicit authorization for the outward-facing write.

The implementation now binds an isolated worker and the selected Codex
executable to frozen, revalidated artifact identities, bounds the interactive
protocol and JSON structure, and projects only allowlisted trust evidence. Two
independent read-only reviews found no remaining scoped Critical, High, or
Medium issue. Seventy focused trust, activation, CLI-projection, and
fail-before-model tests pass; the 536-test named production spine, 109 dashboard
tests, documentation checks, lint/format, and routing evaluation also pass.

## Approach

Before an attended current-profile exact-activation canary invokes a model,
ask the selected Codex executable for `hooks/list` in the exact canary working
directory. Select
only the `agency-preflight@agency-runtime` plugin, require the canonical AR-182
event inventory exactly once, and require every entry to be enabled and
`trusted`. Bound process time and output, return only sanitized event, status,
and hash evidence, and never write Codex configuration or reproduce its private
hash algorithm. Fail closed with a precise remediation when inspection is
unavailable, incomplete, disabled, untrusted, or modified.

An exact refresh requires inspecting the settled definitions, not manufacturing
a second approval when those exact definitions are already natively trusted.
If they are not trusted, stop and use the supported owner approval path; never
write private trust state. Explicit managed-policy and autonomous-bypass
invocations remain distinct and must not be mislabeled as attended trust.

## Dependencies

AR-182 owns the canonical eight-event inventory. AR-180 owns final native
activation proof; AR-255 owns inference-selected, host-proven native-child
staffing. AR-191's older activation-grant mechanism is historical context, not
a dependency to restore. AR-193's separate native Windows evidence remains
outside this Linux trust-inspection package. ADR-0173 supersedes ADR-0119 and
ADR-0077's blanket attended-only policy while preserving explicit modes and
real activation proof. No new authority is introduced here.

## Acceptance

- [x] Attended current-profile exact-activation verification performs
  `hooks/list` in the exact working directory before its model-backed Codex
  execution; explicit managed-policy and autonomous-bypass modes remain
  separately identified under ADR-0173.
- [x] That attended preflight requires the exact canonical Agency event inventory and
  rejects missing, duplicate, disabled, untrusted, or modified entries.
- [x] The inspection is read-only, bounded, fail-closed, and omits hook command
  strings from returned evidence.
- [x] A trust failure returns actionable structured evidence in seconds and
  does not start the expensive canary.
- [x] Focused trust and canary tests plus the named fast production spine pass.
- [ ] After an exact reinstall, an authoritative inspection of the settled
  definitions confirms 8/8 enabled, natively trusted Agency hooks before an
  attended no-bypass current-profile live canary. A fresh supported owner
  approval is required only if those exact definitions are not already trusted;
  neither persistent trust writes nor an invocation bypass can substitute.

The original criteria 1, 2 and 6 are retained verbatim in the portable receipt.
This is an explicit application of the accepted trust-mode policy, not a
claim that native trust equals activation or that a new TUI approval occurred.
