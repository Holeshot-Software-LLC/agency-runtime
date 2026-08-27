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
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 94d25bb42a8897505f25fb76b03821e954d28037
minimum_ledger_commit: 94d25bb42a8897505f25fb76b03821e954d28037
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never touch the shared checkout.
- Clean ledger `94d25bb4` binds evidence through approved harness aliases.
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
- Final named gates pass: 912 docs, Ruff lint/format, 860 Python tests with 3
  skips, 138 dashboard tests, routing 1.4.0, and 167/167 decision mutations;
  receipts are `c5f34de1...8b7f`, `25cc4f01...4cb`, `2eb1981a...3ef9`,
  `eeb12164...10d4`, and `9a45044f...0a71`. All final exits are 0.
- Qwen1's bounded Codex timeout is retained at `40c1c188...7f5a` and
  `5f76b443...6eaa`. AR-327's 211/17 tests and two mutations pass at
  `1b0fd16d...9ab3`, `f54f2441...aab`, and `527ff7d8...a78`.
- Exact Qwen2 committed-source replay `f98bb268...7cb3` exits 0: read-only and
  full restricted verification both return staffed `verified_existing_receipt`.
- Exact `7dbd0cbc` wheel/sdist are `e117b362...fc03d` and `ac30feb0...9fb6c`;
  manifest `780512b2...b7876`, six builds, and image receipt
  `00fcf8e6...5f76` exit 0. Exact image IDs are `206e94c4`, `237c788d`,
  `7869a7a3`, `91c3a5bc`, and `1b0653a5`.
- Fresh Codex `2ec2180b...17bb` passes absence `e857f524...d9bd`; its sole
  no-bypass install `54572077...ac82` exits 0 with one exact native child,
  `missing=[]`, valid header, and attestation `ded810a5...6e66`. Store/status
  correlations `ef8304ef...e30c` and `e4755e50...66a3` exit 0.
- Fresh Claude `d33914d6...9991` passes absence `f95648d6...9919`; dry-run
  `67f5125e...7467` and sole install `798da70f...5afa` exit 0 with bundle
  `ea4e9444...783f`. Hermes `9d5cfe07...ccf0` proves UID 10000 absence
  `c90213d8...175c`, dry-run `f9c06879...9c59`, and sole install
  `d2d7ce1b...5ae1` with bundle `d7a3a3a7...3a33`; both Stores pass quick-check.
- OpenClaw `512df094...1fff` passes absence `534327ca...74a`, dry-run
  `193e891f...6444`, and install `9a0f49b5...1b7a`; bundle `4d9afa0b...d79`
  loads all 13 hooks at `bfa7557a...b3f7` and Store
  `c53dc2a9...01b6` passes quick-check. Authenticated alias inventory
  `7163aa90...911a` caught the pre-turn `generator` typo; corrected native
  receipt `2180a4dc...23e8` binds `task-agency-generation` plus env SecretRefs.
- Hermes R1-R3 prove one exact card and accepted routing; R3 receipts
  `80942b3b...3944`, `6d1d3f52...8a29`, `00211b3c...b1c`, and
  `f3b89dac...cf92` rule out missing task/bridge access. Mistral made zero
  finalizer calls in all three attempts and is rejected pending a new choice.
- Claude R2 and refreshed R3 receipts `a712f945...ba82`/`ea44335e...71b7`
  prove one exact 3,227-byte card and all five LiteLLM routes. Local status
  `ca740051...3af1` is not provider-valid: native stdout/exit
  `456775a6...e4b3`/`85acfd2e...5409` retain the OAuth refresh failure, so no
  unchanged R4 is admissible; package telemetry `b755a171...193c` is 56.9%.
- OpenClaw R1 native/Store receipts `0e4ecc3d...c53`/`6bf28dbe...367b` prove
  one exact card, all five routes, and native exit 0; the approved 14B route
  returned exact `{}` and Agency recorded `response_invalid`.
- Direct-only Codex R2 native/Store receipts `53598f2a...5fd5`/
  `b269dc11...478d` prove one exact card, four alias receipts, no delegation,
  native exit 0, and accepted finalization with `missing=[]`; Codex row 6 closes.
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
  exit 0; two stale-metadata attempts rolled back. Docker receipt still binds 36.
- Tool smoke `2b25ad2a...d1f15` passes exact finalization for both aliases. Hermes
  R4 `c484e1bb...8fb1`/`d38412bb...5fbe` retains `response_invalid`: discovery
  deferred its finalizer. Sole native repair `tools.tool_search.enabled=off`
  passes `717d7279...a362`/`da5a737e...94ea`; all inference settings stay exact.

## exact-blocker

- Claude login, successful Hermes R5/OpenClaw R2/Claude R4, and teardown remain;
  telemetry `5f738310...ee5f` at 39.9% requires this clean pair before R5.
- Cross-OS artifacts, signing, tracker parity, push/PR/merge/tag/publication,
  release, and exhaustive dispatch are unauthorized, not Linux-only GO gates.

## same-task-continuity

- Exact artifacts: `~/.agency-runtime/release-artifacts/dist-7dbd0cbc5cbc77e46fc795568bb63ddcf5e3ee6f-linux-ar297`.
- Evidence: `~/.agency-runtime/evidence/ar297-go-7dbd0cbc`; receipt manifest
  `4b48dcc8...7e6b`; secret-safe helpers `/tmp/agency-runtime-ar297-evidence.pcLOZn/`.
- Protected Python: `~/.agency-runtime-ci/ar297-release-0827/venv/bin/python`.
- Exactly 36 containers carry label `dev.agency-runtime.proof=AR-297`; remove
  them only at final teardown.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Build and independently verify exact `c3493337` artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [x] Test and remove exact Gemma 3 27B; it selects the wrong role.
4. [x] AR-327 repair/rebuild and one clean Codex install pass with verified
   current-profile attestation and no activation bypass.
5. [x] Prove separate clean exact Claude, native-UID Hermes, and OpenClaw
   systemd production-container installs.
6. [ ] Run later ordinary unattended Conveyor-equivalent processes for all four
   harnesses; retain native artifacts, Store correlations, and prompt visibility.
7. [x] Install the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
8. [x] Run every named repository gate and record exact exits and hashes.
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
