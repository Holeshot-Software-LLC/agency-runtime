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

- OpenClaw `2026.7.1-2` native `skills info --json` and `after_tool_call` contracts.
- Existing Agency skill evidence, Store correlation, and first-pass finalization.
- AR-272 native finalizer and AR-273 LiteLLM structured-inference repair.

## Acceptance

- [x] A focused regression fails before repair because the generated bridge drops the native `read` path and the adapter creates no skill row.
- [x] The generated bridge preserves only bounded path fields needed for OpenClaw skill evidence.
- [x] An inventory-authorized exact `SKILL.md` read normalizes to one canonical skill event and produces the matching Store row/header entry.
- [x] Arbitrary reads, lookalike paths, inventory mismatch/failure, disabled skills, and malformed receipts remain unrecorded.
- [ ] Reinstall only Agency into OpenClaw and prove a genuinely different bundled skill in a completely fresh host session without delegation or child spawn.
- [ ] Focused OpenClaw adapter, installer, final-header, and Store tests plus proportionate local gates pass.
- [ ] Tracker creation remains pending separate authorization.
