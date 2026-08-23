---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-23
tags: [handoff, contractors, hiring, prompts, workforce]
related:
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-265-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-266-accept-openclaw-numeric-package-revision.md
  - docs/roadmap/issue-AR-267-create-nested-config-parents-privately.md
  - docs/roadmap/issue-AR-268-accept-null-openclaw-control-errors.md
  - docs/roadmap/issue-AR-269-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/issue-AR-270-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-271-preserve-openclaw-model-receipt-fields.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-274-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-277-keep-openclaw-finalization-first-pass.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar278-openclaw-one-pass
evidence_commit: da184b4fc6170ff1bffcff8d827910e09b848f6a
minimum_ledger_commit: 773d90807ce17378753af834ce93b1882f31de68
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- The active branch is `codex/ar278-openclaw-one-pass`; clean pair `da184b4f` / `773d9080` precedes the current OpenClaw-only fix, and `f76050d7` remains an ancestor.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six original fallbacks. Agency remains scoped to `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, and the free target. No host or protected-harness routing changed.
- Agency-only install `514528d9-e373-4f87-b1c0-9d53edb9401b` is active from this checkout. The plugin is loaded with ten hooks, awaited OpenClaw middleware, no finalizer tool, and zero diagnostics; gateway RPC plus Telegram/Slack probes are green. OpenClaw config changed only its timestamp and Agency enabled flag.
- The fourth fresh Telegram attempt reached OpenClaw, completed three native `task-general` calls, and authored a 665-character Store-backed status response. No reply was queued because finalization failed closed on `actual_model_selected`.
- Trace `a9afc0e8-c998-4bff-9c9e-6dce27628bb2`, run `24104a10-ad68-43a3-9a79-92603687cd1b`, routing `30f6b37b-610e-4f4c-8fce-593fe4cd6d8f`, terminal `625e3e8c-e82c-4918-a23e-5c180760676b`, and transcript SHA `13300aef...` are retained. Status routing was deterministic, so this turn does not claim Agency workforce inference.
- OpenClaw's model hook exposed LiteLLM plus requested alias `task-general`, not the answering model. Three alias-only receipts arrived after response authorship and changed the authoritative header from the requested-alias line to an unavailable-receipt line. This is a causal evidence mutation, not an endpoint, credential, router, or host-channel failure.
- A focused expected-red now proves the mutation. The bridge omits only alias-only LiteLLM events from actual-model completion evidence while retaining genuine resolved telemetry. Focused OpenClaw tests pass 31 with 1 skip.
- Store integrity remains `ok`, schema 47, contractor count 15. Hermes remains break glass; Codex OAuth/config/canary, Claude, and ZCode remain untouched. No child-delivery or matrix-cell claim moves.

## completed-evidence

- The awaited middleware itself passed live: native tools continued, updated Store context reached the model, and one natural final was authored without a finalizer or correction pass.
- AR-273's prior substantive turn remains the current proof for exact Agency profile/provider/alias selection and zero protected-host fallback. The alias is not promoted into an answering-model claim.
- The current change affects only Agency's OpenClaw bridge and one regression; shared inference/profile semantics and every other harness are unchanged.

## exact-blocker

1. Checkpoint and reinstall the two-file OpenClaw bridge fix; the consumed status attempt must not be retried unchanged.
2. Re-prove fresh host-written status delivery before skill loading or substantive inference.
3. Keep Hermes and every proven host untouched.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package.

## next-bounded-work-package

1. Complete focused/docs/lint gates and create the substantive/ledger checkpoint.
2. Stop OpenClaw natively, reinstall Agency only from the checkpoint, restart it natively, and recheck config/plugin/channel/Store invariants.
3. Run a genuinely new Telegram status work unit, then harmless skill and substantive proof only after status delivery passes.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_openclaw_adapter.py tests/test_security_turn_boundaries.py -k openclaw -q
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Preserve credential values and channel/user numeric identifiers; record only names, presence, hashes, and redacted sources.
- Do not run unsupported OpenClaw/Hermes child canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
