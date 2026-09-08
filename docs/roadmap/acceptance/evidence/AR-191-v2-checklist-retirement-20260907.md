---
title: "AR-191 obsolete V2 checklist retirement evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [codex, native-child, backlog, evidence, governance]
related:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/handoffs/issue-AR-191.md
  - docs/decisions/0236-retire-obsolete-codex-v2-grant-checklist.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/installer_contracts.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/store/delegation_activation.py
  - tests/test_codex_plaintext_hook.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
---

# AR-191 obsolete V2 checklist retirement evidence

## Outcome and source boundary

Retire AR-191 as `wont_do`, superseded by AR-255 under ADR-0236. This is not an
acceptance-verification record and contains no isolated verdicts. Its original
eight checked criteria and one unchecked criterion remain unchanged; historical
checkboxes are not newly validated claims. The remaining current native-child
and live-evidence obligations stay with AR-255 and AR-180.

Source inspection and the fresh focused run use
`c64ce3ce54c6e51280292298b5e3600611cb72fc`, before these records-only edits.
All line anchors below refer to that source. No production file, native
configuration, trust setting or owner Store was changed. No model or native
canary was run for this reconciliation.

## Historical changes that prevent literal checklist completion

- `b222414b3921597957ec8dd16dba2f480de7258d`, August 9,
  `feat(store): delete the one-use activation grant organ`, deleted the grant
  preparation, consumption and pending-verification APIs and retired their
  tests. The commit deliberately retained historical tables and live
  read/attachment consumers. Its historical test report included five
  pre-existing failures; it is not represented here as a fully green suite.
- `7e1b3603e69d04531d9d606fa8f5501946e89fb1`, August 12,
  `fix(native-child): require host-proven inference delivery`, replaced
  deterministic child staffing and removed recovery from an invalid explicit
  parent turn. The exact diff changes invalid-turn handling to an empty scope;
  only an omitted turn may fall back to one unambiguous live parent.
- The faithful subjects remain indexed in `docs/worklog/README.md:717` and
  `docs/worklog/README.md:823`. No historical subject or result is rewritten.

Current `core/store/delegation_activation.py:54` only attaches an existing
consumed legacy receipt to a delegation; its legacy SQL table names are not
evidence that the removed grant issuer still exists. The newer sealed,
immutable host-delivery receipts and their replay protections under ADR-0156,
ADR-0159 and ADR-0179 remain required. Retiring the old grant checklist does
not retire those receipts.

## All original criteria and their present disposition

The wording below is reproduced without changing its original checked state.
Disposition is a source/evidence map, not a `satisfied` verdict.

| # | Original criterion and state | Current source / disposition |
|---|---|---|
| 1 | [x] Generated Codex hooks match only the exact V1 and V2 native-spawn names. | `core/installer_contracts.py:59` enumerates both spawn names; `:77` anchors the matcher. Current matching also deliberately includes the two exact follow-up names. `tests/test_native_installer.py:499` asserts that full current matcher. Keep explicit aliases; do not restore a spawn-only matcher. |
| 2 | [x] Runtime canonicalization accepts both identities and rejects lookalikes. | `adapters/hooks.py:586` maps only explicit allowlisted identities. `tests/test_security_turn_boundaries.py:93`, `:108`, `:169` cover accepted names, cross-host rejection and lookalikes. This implemented compatibility safeguard stays. |
| 3 | [x] A live-shape V2 regression preserves all non-message tool arguments and proves the complete activation/finalization chain. | `adapters/hooks.py:206` copies all arguments and changes only the task field. `tests/test_codex_plaintext_hook.py:395` asserts the exact argument map, including `fork_turns`, for each explicit alias. The old `_finish_v2_chain_through_hooks` at `tests/test_codex_activation_canary.py:659` is now a definition without callers, not a collected passing chain. Preserve argument behavior, retire the removed grant-chain requirement. |
| 4 | [x] Child lifecycle events bind to the active parent trace when Codex supplies a distinct child `turn_id`. | `adapters/hooks.py:811` and `:939` now reject an invalid explicit parent turn. Only an omitted turn may use the unique-live-trace fallback. `7e1b3603` deliberately replaced the broader historical behavior; it must not be restored to satisfy this checkbox. The restricted current canary has its separate exact child-UUID/digest binding under ADR-0179. |
| 5 | [x] A flattened V2 result cannot consume an activation without a preceding, atomically unclaimed Codex native-child start on the parent trace. | The one-use activation-grant consume API was deleted by `b222414b`. Current host-origin delivery proof and exact live-parent checks replace this grant-era criterion. Neither a flattened name nor a Store row alone proves delivered cards. |
| 6 | [x] Every installed Codex spawn spelling requires lifecycle proof; supplied child identities match exactly and replay is token/tool-use bound. | Exact identity and replay safeguards remain in the current host-artifact contracts, but the original activation-token lifecycle is removed. ADR-0159 binds the exact authenticated call and arguments; ADR-0179 binds only the restricted canary's child, install, decision, hashes and invocation. Do not equate the newer immutable delivery receipt with the deleted activation token. |
| 7 | [x] Projection failures preserve the actual process exit code and identify the unavailable proof surface. | `core/canary_backends.py:3277` keeps the actual return code except real timeout; `:3344` distinguishes missing result/output/collaboration projection. `tests/test_codex_activation_canary.py:1810` proves failed collaboration projection with actual process exit zero. This diagnostic behavior stays. |
| 8 | [x] Executed Agency/current-profile CLI canaries require the existing Store. | `cli/install_commands.py:1439` passes `require_existing_store=True` for exact activation verification; `core/canary_proof.py:388` translates it to `Store(require_existing_current=True)`. `tests/test_codex_activation_verification.py:579` covers the process-boundary requirement. This existing-Store safeguard stays. |
| 9 | [ ] One fresh installed current-profile canary proves the exact activation graph. | The linked AR-180 receipt proves a different, restricted current v6 delivery/finalization graph, not the removed July grant chain. Keep this original criterion unchecked. AR-180 retains the broader still-unproven live shapes. |

Source paths in this table are relative to `agency_runtime/` unless they begin
with `tests/` or `docs/`. The canonical issue retains the original multiline
checkbox block verbatim as well as the July implementation narrative, clearly
labelled historical.

## Fresh focused command and raw result

Executed on Linux from the source worktree at the commit above:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_security_turn_boundaries.py::test_authoritative_tool_names_require_exact_allowlisted_identity tests/test_security_turn_boundaries.py::test_flattened_codex_spawn_identity_is_not_trusted_by_other_hosts tests/test_security_turn_boundaries.py::test_unrelated_tool_names_cannot_fabricate_agency_evidence tests/test_codex_plaintext_hook.py::test_real_attestor_and_hook_integration_rewrites_exact_marked_spawn tests/test_codex_plaintext_hook.py::test_authenticated_codex_spawn_alias_routes_through_plaintext_staffing tests/test_native_installer.py::test_generated_hook_timeouts_exceed_the_configured_sequential_judge_budget tests/test_host_hooks.py::test_missing_turn_id_uses_only_the_unambiguous_open_routing_trace tests/test_host_hooks.py::test_missing_turn_id_stays_uncorrelated_when_open_turns_are_ambiguous tests/test_codex_activation_canary.py::test_codex_v2_rollout_projection_fails_closed_on_ambiguous_parent -q -W error -k 'not windows'
```

Combined stdout from the initial command and completion poll, exit zero:

```text
.......................                                                  [100%]
23 passed in 3.47s
```

These are offline fixtures: the plaintext test exercises the real attestor
against its private test transcript, while staffing is a controlled test double.
The alias test also doubles attestation to test adapter wiring. Neither is a
new native host or provider proof. The interpreter path records the executed
environment, not a required repository dependency; use the project's test
environment to reproduce the same node IDs.

An earlier bounded AR-191/192 investigation at `08fab1c4` reported **64 passed
in 13.08 seconds**, with Windows cases excluded. That result is retained only
as a historical summary: its exact command and raw stdout are not reproduced
or invented here. It is separate from the fresh 23-case result above.

## Reused live evidence and its limits

The repository-owned
[AR-180 current-profile receipt](AR-180-current-profile-v6-delivery-20260907.md)
and [AR-404 audit](AR-404-live-header-audit-20260907.md) retain the actual
invocation, header and host-artifact correlation. The proof is Codex CLI
0.153.4 on Linux, exec depth one, one code-reviewer card, with no trust bypass.

- Trace: `01a07de5-15c3-7350-86c4-b38e886caa61`.
- Child: `01a07de6-532b-7e10-927e-fa1b2e7cc17d`.
- Installed runtime: `4329d76058d18eaa6b02f0b5750ff5533462064028c1178a8b5e913364774fac`.
- The host-written v6 developer record precedes child speech. Its sole card
  body digest is `e409b2c8b42430b9e69b1e0a93a42e8b790e6ae86c1a3e3e31c03ea0ed9820bd`.
- Child exit is zero, parent finalization is accepted, and the installation-bound
  v4 proof is `0bf5239c2caa6ca6b98f1346d697b07ae0009c46dcebacc50dc3f867fb55c7d6`.

The same card also appears in parent context, so child-only placement is not
literally proven. There was no fresh TUI approval, Desktop/TUI canary,
multi-card delivery or ordinary encrypted-spawn proof. A later hook refresh is
not a new canary. This does not certify the current review session as staffed
or claim that the whole source commit was installed. AR-180 retains these
broader boundaries; AR-255 remains the current staffing successor.

## Publication boundary

This slice changes the canonical issue, its bounded capsule, this receipt,
ADR-0236 and only AR-255's reciprocal `related` links. Its full publication
checkpoint also updates the ADR/roadmap registries and AR-404 queue/capsule,
removes AR-180's obsolete AR-191 dependency, and records a substantive/ledger
pair. The parent coordinates sequential review and PR publication after
AR-189/order43 and AR-190/order44; AR-191 reserves order45. No tracker is created for this pre-tracker
exempt record. No acceptance verifier is called, no criterion is flipped, and
no Windows, provider, full-corpus or hosted diagnostic is launched.

Initial draft checks: metadata passes for 1,240 Markdown documents; policy availability,
`git diff --check` and a byte-for-byte comparison of the original acceptance
block pass. Worklog check reports the base's unindexed `c64ce3ce` merge.
Documentation verification reports four publication-bound errors: two for that
missing/inaccurate ledger row, the intentionally not-yet-registered ADR-0236,
and AR-180's reciprocal `depends_on: AR-191` entry. The full checkpoint
fast-forwards to the faithful `d28ccc23` merge ledger and supplies the registry
and dependency reconciliation without runtime changes. The initial failed
gate remains historical rather than being relabelled as passing.

Full checkpoint checks then pass: metadata and
`scripts/verify_docs.py --require-tracker` for 1,240 Markdown files, policy
availability, worklog index (2,066 substantive commits before this new commit),
repository Ruff lint, format for 767 files and `git diff --check`. A second
byte-for-byte comparison confirms the canonical original acceptance block is
unchanged. `git diff --exit-code c64ce3ce HEAD -- agency_runtime tests scripts`
is empty after the merge-ledger fast-forward; the fresh 23-case source proof
still applies without rerunning it. No broad Python, UI, routing or full
mutation evaluation is repeated for this documentation-only checkpoint.

The immediate narrow ledger records the new substantive commit and reasoning
with `pr: null` until the parent authorizes sequential PR publication. Remote
tracker parity is deferred to the parent's concurrently prepared AR-409 filing;
this checkpoint neither ignores that filing nor claims a stale global count.
