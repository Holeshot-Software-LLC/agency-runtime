---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-27
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: c34933377f7fb16431120f21d487bfbc9910cd55
minimum_ledger_commit: c34933377f7fb16431120f21d487bfbc9910cd55
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never touch the shared checkout.
- Clean ledger `c3493337` binds the previous source and exact artifacts. The
  current bounded package is AR-325's callback reconciliation repair; live work
  starts only from its clean substantive/worklog checkpoint.
- Linux remains **NO-GO**. AR-297/#335 remain open. No tracker write, push, PR,
  merge, tag, signing, publication, release, or hosted workflow is authorized.

## completed-evidence

- Mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` hashes to
  `a4e213d6...97348`: strict assurance, additive dense recall, and every Agency
  inference route through authenticated LiteLLM aliases. No Jina route exists.
- Exact `c3493337` build/Twine/verifier/manifest exit 0. Wheel
  `3ee91ef7...6626` is 9,317,437 bytes; sdist `5a762480...9455` is 25,765,853
  bytes; manifest is `7fa7d2c1...3bfd`. Codex/Claude/Hermes/OpenClaw/dashboard
  images are `2d0b6555...0272`, `c731f8c8...ba8`, `56645dba...dae8`,
  `f87f2ab8...218`, and `951618f1...66a`; verification exits 0.
- Free Qwen 3 32B is promoted behind stable alias `task-agency-child-judge`.
  Promotion/metadata/final validation/literal/spend receipts are
  `6e19008f...1750`, `e1cba9f6...e841`, `42921a7e...867c`,
  `b686ab4b...9abe`, and `d7183bb5...2f07`. Temporary aliases are removed.
- Fresh exact Codex absence
  `eb44d7eefef2e18daf408cf70da02d8f87155aa69b1a325b53f67b7601afc7e1`
  exits 0. The sole no-bypass install JSON hashes to
  `c56eb749f236f63b0b87a3439b9f58eb2aa8a2a0078d0a2253168ce334bc3c44`
  and exits 1 only at finalization.
- Parent `01a04311-f671-7e70-b8cc-accd93ef10a4`, trace
  `01a04311-f6a8-73a2-8318-3cb72700b7ed`, route
  `8a7b167a-cda0-421e-a5e4-8e0a06e2cee4`, and child
  `01a04313-bcd6-79b1-b304-f37769d1872e` agree. Qwen selects sole
  `code-reviewer` at 0.9; the complete 2,379-character card hashes to
  `e409b2c8...20bd`, native delivery is verified, child exit is 0, and the one
  300-second wait completes without timeout.
- Parent/child/Store hashes are `fb580c43...a383`, `c60cc6a6...d079`, and
  `3e41479f...48a6`. This live-proves AR-321's model and AR-324's lineage/full
  prompt delivery, but finalization `eaea50d9...3833` rejects
  `missing=[evidence_verification]`.
- AR-325 isolates the contradictory opaque failure route and the synthetic
  wrong-unit delegation left beside the real unbound worker. The repair keeps
  ordinary opaque diagnostics, preserves a fixed-unit pending dispatch,
  atomically rekeys/merges the real child, supports both callback orders and
  replay, and rejects a conflicting real dispatch.
- Five targeted cases pass. The six-file warning-strict suite passes 149/149,
  decision evaluator tests pass 17/17, and both new mutations are killed with
  source unchanged. Retained stdout hashes are `394d9276...1c4d`,
  `74a9f4f9...4141`, and `ea4477e5...3695`; all exit 0 with empty stderr.
- A separate security/atomicity slice passes 145/145 at stdout
  `ae7689e3...7a84`, exit 0, and empty stderr.
- Documentation checks pass for 893 files at `c5d005ae...18ac`; repository-wide
  Ruff/format passes at `94423e2d...0564`; diff-check output is empty. All exit 0.

## exact-blocker

- Reuse a clean AR-325 source checkpoint or finish its substantive/worklog pair,
  then rebuild and independently verify exact artifacts/images.
- A fresh clean no-bypass Codex install must prove accepted finalization, exact
  Store/header correlation, and current-profile attestation. Existing live
  evidence cannot be relabelled after source repair.
- Claude, Hermes, OpenClaw, later ordinary processes, exact host install,
  authenticated dashboard, named gates, and final teardown remain pending.
- Cross-OS artifacts, signing, tracker parity, push/PR/merge/tag/publication,
  release, and exhaustive workflow dispatch remain unauthorized—not GO gates
  for this Linux-only bounded task unless authority changes.

## same-task-continuity

- Exact artifacts: `~/.agency-runtime/release-artifacts/`
  `dist-c34933377f7fb16431120f21d487bfbc9910cd55-linux-ar297`.
- Evidence: `~/.agency-runtime/evidence/ar297-go-c3493337-qwen3-32b` and
  `~/.agency-runtime/evidence/ar325-callback-reconciliation-precheckpoint`.
- Secret-safe helpers: `/tmp/agency-runtime-ar297-evidence.pcLOZn/`
  `run_with_litellm_key.py` and `capture_command.py`. Never print the key.
- Protected test Python is
  `~/.agency-runtime-ci/ar297-repair-0827/venv/bin/python`.
- Exactly 28 containers currently carry label
  `dev.agency-runtime.proof=AR-297`; latest is
  `agency-ar297-codex-c3493337-qwen2`. Remove all 28 only at final teardown.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Build and independently verify exact `c3493337` artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [x] Test and remove exact Gemma 3 27B; it selects the wrong role.
4. [ ] Checkpoint AR-325, rebuild exact artifacts/images, then prove fresh Codex
   delivery, dispatch, header, accepted finalization, Store correlation, and
   current-profile attestation in one new clean container.
5. [ ] Prove separate clean exact Claude, native-UID Hermes, and OpenClaw
   systemd production-container installs.
6. [ ] Run later ordinary unattended Conveyor-equivalent processes for all four
   harnesses; retain native artifacts, Store correlations, and prompt visibility.
7. [ ] Install the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
8. [ ] Run every named repository gate and record exact exits and hashes.
9. [ ] Update canonical issues/capsule and make each required substantive and
   `docs(worklog):` checkpoint pair.
10. [ ] Remove every container labelled `AR-297`; retain teardown evidence and
    prove zero labelled survivors.
11. [ ] Issue the Linux-scoped GO/NO-GO and complete the persistent goal only
    when every in-scope item above is truthfully closed.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Keep registration, loading, canary, delivery, Store correlation, and model
  claims distinct. Never expose or persist a secret.
- Do not configure/call Jina, overwrite foreign policy, use an activation
  bypass, or touch the shared checkout.
- All Agency inference on this system stays behind LiteLLM aliases. Any unknown
  model, endpoint, dimension, reranker, thinking level, judge route,
  harness-auth, or service-manager choice requires an owner interview.
- No tracker creation, push, PR, merge, tag, signing, publication, release,
  hosted workflow, or unrelated model/config change is authorized.
