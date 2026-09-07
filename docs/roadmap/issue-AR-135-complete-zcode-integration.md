---
title: "AR-135: Complete ZCode native integration end to end"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [host-integrations, zcode, installer, hooks, evidence]
related:
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0070-run-child-specific-agency-activation.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - tests/test_zcode_installer.py
  - tests/test_zcode_header_proof.py
  - docs/decisions/0089-zcode-stop-rejections-use-decision-block.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - agency_runtime/core/installer_payloads.py
  - agency_runtime/core/installer_registration.py
  - agency_runtime/adapters/hooks.py
supersedes:
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-135
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-135: Complete ZCode native integration end to end

## Problem

Original July report, not a description of the current implementation:

The CLI documents ZCode as supported, but fresh install produces a Claude
bundle, registration raises `KeyError("zcode")`, control planning falls through
to Claude commands, and its post-tool path cannot consume or attribute the
specialist prompt inserted by its pre-tool path.

## Current state

September 7 reconciliation at ac1ce173: **retain open for current native
evidence, not an installer rewrite**. The dedicated ZCode renderer is reachable;
bundle generation no longer falls through to Claude. Direct config merge,
idempotency, preservation, toggles, rollback, drift detection, host identity,
Agent prompt rewriting and `zcode-agent:*` identity construction all exist.
Current contract checks pass: 16 installer/header cases (4.74s), 13 selected
hook/Stop cases (5.80s), and four ZCode child-adapter/delivery/profile cases
(0.31s). The header test uses stubbed routing, not a live ZCode turn; its
misleading docstring is corrected without changing behavior.

The current-source `agency smoke --agent zcode --json` passes all four checks:
Store, roster, five-host parity and generated ZCode plugin. The generated
plugin check proves all seven event bindings, preserved config, idempotency,
per-handler toggles and an actual isolated SessionStart process invocation.
It does not launch a native ZCode parent/child or prove complete Stop payloads.
No normal user-profile install or configuration was changed by this smoke.

Read-only installed inspection reports discovered/staged/registered/enabled
true, loaded unknown, no canary/attestation and maturity
`enabled-runtime-unverified`. Its executable is null, and `command -v zcode`
finds no CLI. Therefore the next native proof remains **waiting_for_operator**:
an attended installed ZCode Agent call, not an invented headless backend.
The dated August 19 record-zero delivery below remains valid historical
evidence, not certification of today's package. No live matrix cell or
original acceptance criterion changes; no isolated acceptance verdict is
claimed for this incomplete end-to-end package. This is a tracker-exempt
legacy record, so do not create a duplicate tracker.

September 5 successor responsibility (ADR-0223): AR-127's output-shape fix is
implemented, but its retry/unavailable/full-corpus checklist is retired rather
than certified. This issue owns current ZCode Stop integration: actual negative
and malformed-envelope rejections use decision:block; terminal replay is exact;
Agency-unavailable publication follows Rule 8. Current native/full-response
proof remains separate from source tests and historical installed receipts.
The old turn-5 truncated-preview assertion is a hypothesis to test if relevant,
not an established cause. AR-135 remains open; retirement moves no live matrix
cell and does not assert this issue's broader acceptance is complete.

### Historical integration checkpoints

The following preserves the original defect descriptions and dated repairs;
the present renderer/registration state is described above.

The dedicated `zcode_hooks()` renderer is unreachable. ZCode is absent from
activation-consumption host constraints and some canonical tool/worker maps.
Status inspects staged files rather than the active ZCode config-hook
registration. Failure hooks are incomplete.

Local ZCode 3.5.2 contract inspection confirms direct reversible management of
`~/.zcode/cli/config.json`, not an invented marketplace CLI. Hooks use
`hooks.enabled`, `hooks.timeoutMs`, and `hooks.events` with exactly
SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse,
PostToolUseFailure, and Stop. Agent input uses `prompt`; success returns
`agentId`, while failure exposes no agent identity and must close prepared
activation without fabricating lineage.

An attended installed ZCode 3.8.1 call on 2026-08-19 traversed the real
SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, and Stop hooks and
recorded `zcode-agent:agent_526b8a7a-4732-455c-8e93-c0cec510e418` lineage.
Its isolated child judge was actually answered by the `zcode-recruiter` GLM
profile, but the validated selection then failed with
`native_child_prompt_hydration_failed`. ZCode therefore ran a generic child:
provider attribution and lifecycle correlation are now observed, while
specialist-prompt consumption remains unproven.

The local repair identified the exact cross-contract mismatch. Of the 72 cards
eligible in that call's read-only reconstructed universe, 28 use the supported
Store identity form `sha256:<digest>`. Prompt lookup, active-worker state,
version, body hash, and size all passed, but native-child hydration incorrectly
required the catalog identity itself to equal the normalized bare digest. It
now uses the exact stored identity for immutable lookup and body verification,
then binds v6 delivery and evidence to the canonical bare SHA-256 digest. The
same live catalog replays 72/72 hydratable without another provider call.

The installed recheck closes that hydration and delivery gap on ZCode 3.8.1.
Runtime `f24664b87f3b…`, bundle `da04cfbf7847…`, and install
`759efa16-bdce-4fcb-ab3c-b3b3c0bcf3d8` produced applied native-child decision
`native-child-aa6e5296…`. The requested and answering provider was the
canary-only `zcode-recruiter` profile (`GLM-5.2`), which selected
`python-application-engineer`. ZCode's host-written metadata binds Agent call
`call_1f2255f…` to child `agent_07b6377b…`; child transcript record zero already
contains the complete v6 envelope and byte-identical 2,928-character Store
body before any child speech. Fourteen mechanical identity, ordering, hash,
Store-body, and validity-window checks pass. The native lifecycle projection's
`generic-worker` label names the host child, not the delivered specialist card.

## Approach

Use one canonical five-host registry across bundle generation, native command
planning, registration, inventory, controls, activation consumption, tool
identity, pre/post/failure hooks, lineage, status, smoke, and UI presentation.
Merge the exact ZCode config reversibly and prove postconditions.

The remaining bounded proof package is:

1. At an attended checkpoint, bind the installed package and existing ZCode
   profile to an exact candidate; preserve normal provider and user config.
2. Capture a native Agent success and failure, one-use correlation, record-zero
   specialist delivery before speech, and the full parent Stop payload. Check
   actual rejection/block, exact terminal replay and Agency-unavailable
   publication separately. The old truncated-preview explanation remains an
   unconfirmed hypothesis until the native payload demonstrates it.
3. Cite each of the five original criteria and run isolated acceptance before
   closing. Update AR-119's matrix only with evidence that independently meets
   its stricter exact-candidate host-artifact authority, not by inheritance.

Continue oldest-first reconciliation at AR-138 after this disposition merges;
AR-136 and AR-137 are already done. Windows execution remains with the owner.

## Dependencies

AR-134 owns the schema migration. AR-131 owns shared MCP schemas. AR-136 owns
cross-process child correlation.

## Acceptance

- Fresh, idempotent ZCode install writes and merges only canonical ZCode files.
- Registration, enable/disable, rollback, status, and smoke have exact
  postconditions and no Claude fallback.
- PreToolUse through PostToolUse or failure consumes one activation and records
  `zcode-agent:*` lineage.
- Every claimed ZCode hook event has the documented host-native response shape.
- Tests cover fresh home, existing config preservation, rollback, and drift.

## Implementation evidence

The source implementation now owns ZCode independently: it renders the exact
3.5.2 seven-event configuration, merges and restores config.json atomically,
tracks ownership and drift, plans no Claude-native commands, exposes canonical
status/toggle/smoke contracts, and records ZCode pre/post/failure activation
lineage. The interactive configuration wizard now includes ZCode in its
canonical detected-host status and persisted adapter selection; the complete
suite exposed that missing presentation path. Fresh-home, preservation,
rollback, drift, schema, UI, and smoke tests pass, including the 167-test
integrated native-hook/ZCode slice. This item remained open at the prior
checkpoint because a real installed call still needed to hydrate and deliver
the selected specialist prompt after an applied child-judge result. That gap is
now closed by the host-written record-zero artifact above. The repair has 117
core native-child passes, 162 wider hook/proof passes, and all 12 fast local gates;
broader AR-135 acceptance and matrix authority remain separate.
