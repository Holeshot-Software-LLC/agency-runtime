---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-28
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/issue-AR-328-seal-hermes-install-tree.md
  - docs/roadmap/issue-AR-329-freeze-codex-inspector-bootstrap-as-persistent-input.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/decisions/0191-seal-managed-hermes-python-bundles.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-manual-live-fix
evidence_commit: 7b7fd6a776ffe4230e45216c1951dec2a62ec6b0
minimum_ledger_commit: 7079b27e762df7dd73f580eb06dd6b70985f0cdf
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297-main.JWaPCg`; never touch the shared checkout.
- PRs #339/#340 merged product/evidence through clean `origin/main` `1e6f5d07`.
- Manual Codex loaded the steward but exposed missing ordinary-terminal LiteLLM
  auth; exact config repair is installed and awaits fresh attended hook trust.
- Clean merged checkpoint `1e6f5d07` precedes this recovery pair.

## completed-evidence

- Baseline mode-0600 config `a4e213d6...97348` routes every Agency call through
  LiteLLM aliases, but ordinary terminals lack its referenced environment key.
  Write-only projection from owner-approved `~/.openclaw/.env` creates exact
  mode-0600 config `df75e01d...0922`; no value is printed and no Jina route exists.
- Free Qwen 3 32B is promoted behind stable alias `task-agency-child-judge`.
  Promotion/metadata/final validation/literal/spend receipts are
  `6e19008f...1750`, `e1cba9f6...e841`, `42921a7e...867c`,
  `b686ab4b...9abe`, and `d7183bb5...2f07`. Temporary aliases are removed.
- Final named gates pass for `33d9503b`: 921 docs, Ruff/696 formats, 861 tests
  with 3 skips, 138 dashboard tests, routing 1.4.0, and 167/167 mutations killed.
  Manifest `ef8d8abc...1b09` records every accepted exit/hash and rejected
  environment preflight; every accepted exit is 0.
- Clean repair ledger `6e78b146` builds portable wheel `cf32f861...b2a7` and
  sdist `1b40ca8f...e228`; independent verification and separate installed
  8/8 wheel/sdist smoke runs exit 0 in the retained owner-private artifact root.
- Fresh CI `33139352190` has 16 successes and three intended integration skips:
  Ubuntu/Windows distributions, aggregate gates, and artifact assembly pass.
  Dependency review `33139352171` and CodeQL `33139352213` also pass.
- AR-328 regression `751276ea...e3a` fails before repair. The exact cache guard
  preserves movable installs; 359 tests pass with 2 skips at
  `981fbbc8...ddd0`, and focused Ruff/docs pass with empty stderr.
- Exact `e0b0b25c` wheel/sdist are `75d63ff9...3762`/`2b1ae7ec...79d9`;
  manifest `fcfd0231...b1b0`, canonical/Twine/verification, and six final
  builds exit 0. R1 image verification correctly rejects Node 22; the pinned
  Node 24.15 rebuild passes at `07f372e3...eb9a`. Final image IDs begin
  `c8e7a265`, `93eb1f9e`, `3a4cac26`, `c3d712ec`, and `4d2ccddc`.
- Strict container proofs pass separately: Codex `ce370bc8...1330` with one
  delivered native child; Claude `579d65c8...a0e9`; Hermes
  `4d04f360...02d8` with sealed tree `d7bc15f0...d8f8`; and OpenClaw
  `4debebf3...c748` with Store/systemd/13-hook evidence. All retain exact
  bundles and `missing=[]` where terminal delivery applies.
- Fresh Claude verifier `ed965d7c...8ca9` exits 0 for session `.403`: exact
  3,227-byte card, no tool use, all five alias receipts, accepted completion,
  `missing=[]`, native/Store response equality, existing subscription auth,
  normal default model, and no bypass.
- Fresh ordinary Codex verifier `db8f6780...e2f3` exits 0 for session
  `01a048dd-10f0-77e2-94bd-d5e4c4572a4f`: exact 2,659-byte card, four
  alias-only receipts, accepted completion, `missing=[]`, native/Store response
  equality, read-only/no-delegation execution, and exact runtime/config.
- Final-candidate Hermes receipt `9ee57328...f2f7` exits 0 for session
  `20260827_221502_139df0`: one exact 3,227-byte card, all five alias groups,
  accepted completion, `missing=[]`, exact visible accepted replay, healthy
  Stores, and byte-identical config. The corrected native source receipt is
  `d8e9eab7...9fe3`; the first helper-default mismatch remains retained.
- Hermes R1/R2 retain fail-closed negatives; least-privilege R3 verifier
  `f64738b9...8ce9` proves exact card, Agency-only finalizer, accepted replay,
  `missing=[]`, unchanged config, and complete Store correlation.
- Fresh host OpenClaw verifier `61fd0b83...7fe7` exits 0: exact 684-byte task and
  2,659-byte card, approved LiteLLM alias, thinking off, five successful Agency
  receipts, healthy Stores, and the explicit no-channel active-run limitation.
  Additive allow-list receipt `831edb7a...dd2f` preserves all foreign policy;
  restarted authenticated systemd RPC passes at `a144aab9...172`.
- Teardown `40fa5062...1dc4` removes all 47 exact labelled containers with zero
  survivors; five images remain at `5c998f61...e276`, and host services stay healthy.
- Qwen3 Coder aliases `d69aa6b6...af4d`/`a1e2381d...a5dd` pass at 65,536;
  OpenClaw transition/verify `e97e02e2...deba`/`a141d193...e1ce` pass.
- Merged-main `dc8bbde6` wheel/sdist `c3f3cd0d...675c` / `dc57fa54...5325`;
  build, Twine, verification, install, and pip check pass in a fresh venv.
- Main-installed runtime is `2dd04fdc...9987`; Hermes/OpenClaw/Codex/Claude
  bundles `b03b47fe...e9b`/`1f88f2ef...2c8`/`cecc8993...b3b`/`5d178603...136`;
  exact attestation `93a25ad5...c25` passes all 18 checks.
- Codex's default 180-second verification times out safely; the canonical
  300-second retry `d90cfcd1...c47` passes managed trust/canary/attestation;
  OpenClaw RPC `48b73bba...393b` also exits 0.
- Dashboard `96d1a058...a515` passes auth, no-store, full prompt, and PID/port.
- No-bypass Codex receipt `eca6fcb4...647c` exits 0 at trace
  `01a048d3-5687-7c11-a0a9-b1f3abbb7402`; rollouts
  `299542c3...7158`/`a8525798...c707` bind the real child and finalization.
- Private Store `cbaec4a8...01f8` passes quick-check; correlation
  `0fe1ac45...a34b` binds accepted selection/load, alias receipts, and `missing=[]`.

## exact-blocker

- Config repair `530b7837...1e5e` resolves ordinary-terminal auth. Two later
  manual Qwen turns `01a049a6...db07`/`01a049ab...9f76` still fail both bounded
  planner attempts; no route/load/finalization is promoted. Isolated exact-prompt
  Qwen and Mistral trials both accept `accessibility-auditor` with byte-identical
  5,858-byte context; repeated real Qwen failures make generation-route choice
  the current operator interview.
- Record audits `769fb577...6056`/`e98fd0e5...64a7` exit 1 only on inherited
  parity debt; AR-297/#335 has no mismatch. Tracker/release writes stay unauthorized.

## same-task-continuity

- Artifacts: `~/.agency-runtime/release-artifacts/dist-dc8bbde6a884f72614dae32585e488ce4997b9ac`.
- Venv/evidence: `~/.agency-runtime/release-venvs/ar297-main-dc8bbde6` /
  `~/.agency-runtime/evidence/ar297-main-install-dc8bbde6`.
- Manual repair/evidence: config `ar297-litellm-df75e01d31dd8ebc.yaml` /
  `~/.agency-runtime/evidence/ar297-manual-live-20260828`.
- Earlier live evidence remains under `~/.agency-runtime/evidence/ar297-host-live-20260828`.
- Zero AR-297 containers remain; five exact images and healthy host services remain.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Point ordinary Hermes at the existing owner-private OpenClaw/LiteLLM
   secret source without copying or printing the key; align only OpenClaw's
   client gateway port with its healthy service.
2. [x] Repair AR-329 with a mode-0400 regression and focused Codex suites.
3. [x] Commit the repair ledger, build/install the exact candidate, and restore
   healthy dashboard/OpenClaw services.
4. [x] Codex/Claude/scoped-Hermes/OpenClaw, authenticated dashboard, and every
   named repository gate pass with exact retained hashes and exits.
5. [ ] Obtain generation-route choice, apply/verify it without changing the
   stable alias contract, complete Codex then Claude/Hermes/OpenClaw manual
   tests, and issue the Linux verdict.

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
- Do not call Jina, overwrite foreign policy, bypass activation, or touch the shared checkout.
- All Agency inference on this system stays behind LiteLLM aliases. Any unknown
  model, endpoint, dimension, reranker, thinking level, judge route,
  harness-auth, or service-manager choice requires an owner interview.
- Do not create or close another tracker, tag, sign, publish a release, or make
  an unrelated model/config change without separate authorization.
