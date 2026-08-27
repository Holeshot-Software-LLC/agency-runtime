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
evidence_commit: e0b0b25c30083b09743fe1a04f2a0ad4cdf4e533
minimum_ledger_commit: e0b0b25c30083b09743fe1a04f2a0ad4cdf4e533
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never touch the shared checkout.
- Clean ledger `6781c59b` admitted the sole final Codex canary; all four final installs now pass.
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
  `eeb12164...10d4`, and `9a45044f...0a71`; rerun is pending for `e0b0b25c`.
- AR-328 regression `751276ea...e3a` fails before repair. The exact cache guard
  preserves movable installs; 359 tests pass with 2 skips at
  `981fbbc8...ddd0`, and focused Ruff/docs pass with empty stderr.
- Exact `e0b0b25c` wheel/sdist are `75d63ff9...3762`/`2b1ae7ec...79d9`;
  manifest `fcfd0231...b1b0`, canonical/Twine/verification, and six final
  builds exit 0. R1 image verification correctly rejects Node 22; the pinned
  Node 24.15 rebuild passes at `07f372e3...eb9a`. Final image IDs begin
  `c8e7a265`, `93eb1f9e`, `3a4cac26`, `c3d712ec`, and `4d2ccddc`.
- Final Codex absence survives dry-run at `0aab382c...3163`; its sole live
  install `ce370bc8...1330`, Store `d9469980...d5b9`, artifacts
  `8831ece2...3940`, and status `e1c700b5...fd1f` exit 0. Bundle
  `96b44257...7785` has one native child, `missing=[]`, managed trust, no bypass.
- Final Claude install/status/artifacts `579d65c8...a0e9`/`98cbc224...897d`/
  `105bf8b0...6499` exit 0; bundle `b2151080...b119` is registered/enabled.
- Final UID-10000 Hermes install/status/artifacts `4d04f360...02d8`/
  `b9b6e7aa...a3f1`/`0cb3331c...2e8a` exit 0; bundle `eab39058...c15e`.
  Native doctor and strict post-load tree proof `d7bc15f0...d8f8` retain only
  the 0500/0400 manifested guard, no `.pyc`, and exact validation.
- OpenClaw dry-run truthfully leaves an empty runtime home at `8ffcb927...af70`;
  untouched R2 absence `5feaa49c...2cdd`, install `4debebf3...c748`, Store
  `c6da8137...0b12`, systemd, exact alias config, and 13-hook runtime all pass.
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

- Repeat all four ordinary rows and complete Claude's pending first-party
  login, then refresh the host/dashboard, named gates, records, and teardown.
- Cross-OS artifacts, signing, tracker parity, push/PR/merge/tag/publication,
  release, and exhaustive dispatch are unauthorized, not Linux-only GO gates.

## same-task-continuity

- Exact artifacts: `~/.agency-runtime/release-artifacts/dist-e0b0b25c30083b09743fe1a04f2a0ad4cdf4e533-linux-ar297`.
- Evidence: `~/.agency-runtime/evidence/ar297-go-e0b0b25c`; secret-safe helpers
  remain `/tmp/agency-runtime-ar297-evidence.pcLOZn/`.
- Protected Python: `~/.agency-runtime-ci/ar297-release-0827/venv/bin/python`.
- Exactly 47 labelled containers remain; six obsolete OpenClaw witnesses are stopped. Remove all at teardown.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Rebuild and independently verify final AR-328 artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [x] Test and remove exact Gemma 3 27B; it selects the wrong role.
4. [x] AR-327 repair/rebuild and one clean Codex install pass with verified
   current-profile attestation and no activation bypass.
5. [x] Refresh separate clean exact Codex, Claude, Hermes, and OpenClaw
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
