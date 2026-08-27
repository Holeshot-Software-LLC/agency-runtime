---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-27
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/issue-AR-328-seal-hermes-install-tree.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/decisions/0191-seal-managed-hermes-python-bundles.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: e17e5221657ec90df8092879cf9d5c79d65ecb50
minimum_ledger_commit: e17e5221657ec90df8092879cf9d5c79d65ecb50
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never touch the shared checkout.
- Clean ledger `5bd9cf80` retains the passing `e17e5221` artifacts and three
  ordinary rows; AR-328 now supersedes that final candidate pending rebuild.
- Linux remains **NO-GO**. AR-297/#335 remain open. No tracker write, push, PR,
  merge, tag, signing, publication, release, or hosted workflow is authorized.

## completed-evidence

- Mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` hashes to
  `a4e213d6...97348`: strict assurance, additive dense recall, and every Agency
  inference route through authenticated LiteLLM aliases. No Jina route exists.
- Free Qwen 3 32B is promoted behind stable alias `task-agency-child-judge`.
  Promotion/metadata/final validation/literal/spend receipts are
  `6e19008f...1750`, `e1cba9f6...e841`, `42921a7e...867c`,
  `b686ab4b...9abe`, and `d7183bb5...2f07`. Temporary aliases are removed.
- Prior named gates pass: 912 docs, Ruff lint/format, 860 Python tests with 3
  skips, 138 dashboard tests, routing 1.4.0, and 167/167 decision mutations;
  receipts are `c5f34de1...8b7f`, `25cc4f01...4cb`, `2eb1981a...3ef9`,
  `eeb12164...10d4`, and `9a45044f...0a71`; rerun is pending for `e17e5221`.
- AR-328 regression `751276ea...e3a` fails before repair. The exact cache guard
  preserves movable installs; 359 tests pass with 2 skips at
  `981fbbc8...ddd0`, and focused Ruff/docs pass with empty stderr.
- Exact Qwen2 committed-source replay `f98bb268...7cb3` exits 0: read-only and
  full restricted verification both return staffed `verified_existing_receipt`.
- Exact `e17e5221` wheel/sdist are `8b35c8f6...d897`/`7e9f7ad6...9287`;
  manifest `3ae9f798...86b6`, six builds, and independent image receipt
  `e3e6302d...f947` exit 0. Exact image IDs begin `28c3fd34`, `fa17365f`,
  `29acb4de`, `3739b180`, and `b89804f5`.
- Fresh Codex absence/install/Store/status receipts `ad4edec5...dfd6`,
  `c41e8eae...0039`, `1ca3bf03...cf6`, and `6754603c...4173` exit 0.
  Bundle `9bcb81e6...454e` has one exact child, valid header, `missing=[]`,
  current-profile attestation, and no activation bypass.
- Fresh Claude absence/dry/install/status receipts `5665ae9a...573`,
  `67f5125e...7467`, `1917bec2...575`, and `ab524382...ffc3` exit 0;
  bundle `7ffd1c4c...c53` is registered/enabled and native inventory is exact.
- Fresh UID-10000 Hermes R2 absence/config/dry/install receipts
  `4e962155...2b`, `880b3da3...aea`, `917e1577...06c`, and
  `5c3b902b...838` exit 0; bundle `06c68be0...b4e` registers one finalizer and
  eight hooks. Fresh OpenClaw R2 absence/config/install/runtime receipts
  `89c245f4...f2b`, `bdc0667b...873`, `df4601f0...b12`, and
  `2f0293a8...bee` exit 0; exact alias-only config loads all 13 hooks.
- Hermes R1-R3 prove one exact card and accepted routing; R3 receipts
  `80942b3b...3944`, `6d1d3f52...8a29`, `00211b3c...b1c`, and
  `f3b89dac...cf92` rule out missing task/bridge access. Mistral made zero
  finalizer calls in all three attempts and is rejected pending a new choice.
- Claude R2 and refreshed R3 receipts `a712f945...ba82`/`ea44335e...71b7`
  prove one exact 3,227-byte card and all five LiteLLM routes. Local status
  `ca740051...3af1` is not provider-valid: native stdout/exit
  `456775a6...e4b3`/`85acfd2e...5409` retain the OAuth refresh failure, so no
  unchanged R4 is admissible; package telemetry `b755a171...193c` is 56.9%.
- OpenClaw R2 native/Store receipts `bb90b2fc...9841`/`1a4a1a4f...a2f5` prove
  one exact card, all five routes, native exit 0, and a nonempty response. Its
  no-delivery run stays active; bounded loading passes without weakening policy.
- Fresh Codex receipts `8355a9a6...7590`/`7e39f736...d921`/`2ae0bdde...4a79`
  prove one exact card, four aliases, no delegation, exit 0, exact response
  correlation, `missing=[]`, and unchanged config/policy. Its ordinary row closes.
- Exact host venv/wheel/pip check pass. Combined install `00d51490...b559`
  exits 1 only for attended Codex activation; all four bundles are current and
  packaged-runtime attestation `ec2f8fdd...9292` binds `dbf1581f...f301`.
- Systemd contract `b3ffa572...f888`, restart `b72f17e7...94d8`, HTTP proof
  `358ab92e...d94f`, and browser proof `7b22dd85...c483` exit 0. Auth is
  401/200 no-store; exact 2,659-byte prompt `c3cfc098...5848` is untruncated.
- Optional host Codex verifier `933bc916...bb4` fails before model invocation
  because attended hook trust is not ready; it changes nothing and uses no bypass.
- Approved Qwen3 Coder aliases apply/verify `d69aa6b6...af4d`/`a1e2381d...a5dd`
  exit 0 at 65,536/no-thinking; unrelated aliases are unchanged. OpenClaw's
  three-pointer config transition/verify `e97e02e2...deba`/`a141d193...e1ce`
  exit 0; two stale-metadata attempts rolled back.
- Hermes R5 isolates rewritten accepted text; AR-288's trace-scoped replay and
  236 tests pass. Fresh default-config session `20260827_201909_a6a13c` exits 0;
  receipt `3c40a9bf...8959` proves one exact card/finalizer, Store acceptance,
  `missing=[]`, visible replay `ad8a06d3...eeaa`, healthy Stores, all aliases,
  and no post-install/live config drift. AR-288 is locally done.

## exact-blocker

- Checkpoint AR-328, rebuild the exact candidate, repeat final clean installs
  and ordinary rows, complete Claude's pending first-party login, then refresh
  the host/dashboard, named gates, records, and teardown.
- Cross-OS artifacts, signing, tracker parity, push/PR/merge/tag/publication,
  release, and exhaustive dispatch are unauthorized, not Linux-only GO gates.

## same-task-continuity

- Historical exact artifacts: `~/.agency-runtime/release-artifacts/dist-e17e5221657ec90df8092879cf9d5c79d65ecb50-linux-ar297`.
- Evidence: `~/.agency-runtime/evidence/ar297-go-e17e5221`; secret-safe helpers
  remain `/tmp/agency-runtime-ar297-evidence.pcLOZn/`.
- Protected Python: `~/.agency-runtime-ci/ar297-release-0827/venv/bin/python`.
- Exactly 42 AR-297-labelled containers remain; remove all only at final teardown.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [ ] Rebuild and independently verify final AR-328 artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [x] Test and remove exact Gemma 3 27B; it selects the wrong role.
4. [x] AR-327 repair/rebuild and one clean Codex install pass with verified
   current-profile attestation and no activation bypass.
5. [ ] Refresh separate clean exact Codex, Claude, Hermes, and OpenClaw
   systemd production-container installs.
6. [ ] Repeat ordinary unattended processes for the final four installs; retain
   native artifacts, Store correlations, and prompt visibility.
7. [ ] Refresh the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
8. [ ] Rerun every named repository gate and record exact exits and hashes.
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
