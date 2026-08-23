---
title: "Record authorized OpenClaw native skill reads"
status: in_progress
category: roadmap
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, skills, evidence, plugin]
related:
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/
  - tests/test_openclaw_adapter.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-274
priority: p0
tracker_url: null
depends_on: [AR-272]
blocks: [AR-119]
---

# AR-274: Record authorized OpenClaw native skill reads

## Problem

OpenClaw `2026.7.1-2` loads a bundled native skill by reading its `SKILL.md`
with the host's supported `read` tool. Before this repair, the generated bridge
dropped `path` and the adapter recognized only generic `skill_view`. A genuine
native skill read therefore could not create the Store-backed `skills_loaded`
evidence required for the five-line Agency header without a bounded,
host-authorized normalization.

## Current state

Fresh OpenClaw trace `402e37f5-f38e-425b-95c6-62e911be2566` and Store run
`4963f31f-e114-4fa0-b051-8ded1ded51a1` successfully exercised Agency workforce
inference through profile `linux-task-agency-router`, provider type `litellm`,
and exact requested alias/model-group `task-agency-router`. Routing decision
`982f6c68-ac38-41a3-a84a-b7b60bee39cb` accepted, specialists
`80c52f54-3390-4f06-81e1-0ddca89ebe27` and
`866003fb-e74a-491c-a422-1ea64dd4c677` loaded, and finalization
`cfb2e3de-9a2b-4fda-9194-6edcb52ca3a5` delivered a hash-matched response.

The native transcript records a successful `read` of the exact bundled
Weather skill path reported by `openclaw skills info weather --json`, followed
by `agency_finalize`. The visible prose says Weather was loaded, but the honest
header says `Skills loaded: none` and the Store contains no `skills_loaded`
row. This is failed skill evidence, not a successful skill-load claim. Current
OpenClaw exposes no `skill_view` tool.

Two focused regressions failed before repair: the generated JavaScript dropped
`path` and exited 37, while the OpenClaw adapter never consulted the injected
inventory authorizer or wrote a skill row. The retained JUnit receipt is
`/tmp/ar274-openclaw-native-skill-read-red.xml`.

The minimal repair carries only bounded `path`, rejects traversal-shaped and
non-skill paths before subprocess launch, and queries the supported native
`openclaw skills info <skill> --json` surface in a least-privilege OpenClaw-only
environment. It requires exact name, key, file path, base directory, eligibility,
model visibility, and every disable/block flag before normalizing to canonical
`skill_view`. The focused receipt passes 22 with one skip; the affected
installer/dispatch/inference/header/Store slice passes 453 with one skip. A
read-only live helper smoke authorized only `weather`. Commits `7fcd828d` and
`7d0460a3` carry the repair and ledger; ADR-0165 records the boundary.

The first Agency-only install attempt failed before mutation because the
checkout virtualenv was not a trusted persistent launcher. With the changed,
verified `/usr/bin/python3` input importing this checkout, install
`3aac2a46-e638-46d6-812d-d2df2ea3aa0b` completed with bundle `69783cf4...`,
runtime digest `6afbaf65...`, 15 unchanged contractors, and no runtime drift.

Fresh OpenClaw trace `11707056-a490-4cbc-97b6-9a8e621caa79` then read the exact
eligible bundled `healthcheck` path authorized by native inventory. Store run
`585f2dce-a867-4b83-9395-4b877718a22e`, skill row
`3dd34973-d2f5-4b38-adcf-51191f374214`, and finalization
`47c0a487-916a-42cb-9d97-54ee205a0a7f` completed; the native five-line header
records `Skills loaded: healthcheck`. All three workforce stages used the
OpenClaw-scoped LiteLLM profile and exact `task-agency-router` alias/model-group
without a protected-provider fallback. No actual answering model is claimed.

The later AR-278 awaited-middleware delivery repair regressed that evidence
path. In native session `5570abb9-eecc-4d77-be4b-bb9636bdf886`, trace
`6b18f9f0-a8bb-4a68-b70b-45ec7cdfe454` completed a new read-only `healthcheck`
request and delivered its response. Routing decision
`26492374-3d54-4da2-8bc6-0381e83813f4` accepted `code-reviewer`; all three
Agency inference receipts used OpenClaw profile `linux-task-agency-router`,
provider type `litellm`, and exact requested alias/model-group
`task-agency-router` with `fallback_applied=false`. The exact native inventory
still authorizes the read path, but the Store has zero skill rows and the honest
header says `Skills loaded: none`. Artifact
`/tmp/ar278-openclaw-sixth-live/healthcheck-correlation-diagnosis-redacted.json`
retains the failure without credential or channel identity values.

Installed OpenClaw 2026.7.1 source identifies the regression precisely. Its
tool-result middleware supplies `args`, but its OpenClaw runtime factory passes
only `runtime=openclaw` in middleware context and does not populate optional
session/run fields. The earlier generated test incorrectly supplied those
fields. Agency therefore invoked its bridge with empty correlation and failed
closed before recording the skill or returning an updated snapshot.

Expected-red exit 245 now models the installed contract. The bounded repair
captures session/run correlation from OpenClaw's supported `before_tool_call`
hook by `toolCallId`, consumes it once in the awaited middleware, expires and
caps the map, clears it when Agency is disabled, and rejects ambiguous ID
collisions. The affected OpenClaw installer, dispatch, inference, final-header,
and Store slice is 374 passed with 1 skipped.

Agency-only install `251c4349-f7e3-4640-980d-055b857c0abe` then installed the
repair from clean checkout `c0426ab9` while the native gateway was stopped. The
installer left it stopped; native restart loaded all 11 hooks, including
`before_tool_call`, with no exposed Agency tool or plugin diagnostic. Runtime
digest `70239e65...` and launcher SHA `3090708c...` bind to this checkout.
OpenClaw remains 2026.7.1-2 on `litellm/task-general` plus six fallbacks, and
its only semantic config delta is `meta.lastTouchedAt`. Agency config SHA
`43367ec9...` is unchanged. A later `/new` established native session
`b815780c-23fb-4fdb-8731-aed6d162b769`; its exact first `agency status` turn
completed as trace `7f4aa31c-9d93-4199-bac0-b5818cea91de` and delivered through
Telegram. Finalization accepted with no missing fields. The deterministic
control correctly created no skill, specialist, resident binding, or Agency
model receipt; response SHA is `a4c784dc...` and preserved transcript SHA is
`a2ec1af7...`. The genuinely changed `tmux` skill proof remains pending. Hermes
and protected hosts remain untouched.

## Approach

Preserve the bounded native path field through the generated bridge. Normalize
an OpenClaw `read` into Agency's canonical skill-view event only after the
candidate path is authorized by the installed host's native skill inventory
and exactly matches the eligible, model-visible skill's reported `filePath`.
Fail closed for arbitrary files, missing or malformed inventory receipts,
disabled or blocked skills, path ambiguity, and subprocess failure. Keep the
existing Store and final-header checks authoritative; do not weaken filesystem
or executable-namespace trust rules.

## Dependencies

- OpenClaw `2026.7.1-2` native `skills info --json`, `before_tool_call`, and
  awaited tool-result middleware contracts.
- Existing Agency skill evidence, Store correlation, and first-pass finalization.
- AR-272 native finalizer and AR-273 LiteLLM structured-inference repair.

## Acceptance

- [x] A focused regression fails before repair because the generated bridge drops the native `read` path and the adapter creates no skill row.
- [x] The generated bridge preserves only bounded path fields needed for OpenClaw skill evidence.
- [x] An inventory-authorized exact `SKILL.md` read normalizes to one canonical skill event and produces the matching Store row/header entry.
- [x] Arbitrary reads, lookalike paths, inventory mismatch/failure, disabled skills, and malformed receipts remain unrecorded.
- [x] Reinstall only Agency into OpenClaw and prove a genuinely different bundled skill in a completely fresh host session without delegation or child spawn.
- [x] Retain the later awaited-middleware skill-evidence regression with exact Store, header, delivery, and alias receipts.
- [x] Match the installed no-correlation middleware context in an expected-red regression and reject ambiguous tool-call correlation.
- [x] Reinstall only Agency from the correlation candidate while OpenClaw is natively stopped.
- [ ] Prove a genuinely different eligible skill without delegation or child spawn.
- [x] Focused OpenClaw adapter, installer, final-header, and Store tests plus proportionate local gates pass.
- [ ] Tracker creation remains pending separate authorization.
