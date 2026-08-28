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

- Work only in `/tmp/agency-runtime-ar297-main.JWaPCg`; never touch the shared checkout. PRs #339/#340 merged through `origin/main` `1e6f5d07`.
- Credential repair is installed. Stable `task-agency-generation` is rolled back
  to local Qwen 14B; Spark is excluded after its bounded call audit.
- Clean checkpoint `15cda0a4` precedes this recovery pair.

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
- Exact build/CI/AR-328 evidence remains canonical in the issue. Final images
  and distributions pass exact build, Twine, verification, install, security,
  and hosted-platform gates; no optional exhaustive workflow was dispatched.
- Strict container proofs pass separately: Codex `ce370bc8...1330` with one
  delivered native child; Claude `579d65c8...a0e9`; Hermes
  `4d04f360...02d8` with sealed tree `d7bc15f0...d8f8`; and OpenClaw
  `4debebf3...c748` with Store/systemd/13-hook evidence. All retain exact
  bundles and `missing=[]` where terminal delivery applies.
- Fresh ordinary Claude/Codex/Hermes/OpenClaw verifiers
  `ed965d7c...8ca9`/`db8f6780...e2f3`/`f64738b9...8ce9`/`61fd0b83...7fe7`
  prove exact full cards, required aliases, healthy Stores, and no bypass.
  Additive OpenClaw receipt `831edb7a...dd2f` preserves foreign policy, and
  authenticated systemd RPC passes at `a144aab9...172`.
- Teardown `40fa5062...1dc4` removes all 47 exact labelled containers with zero
  survivors; five images remain at `5c998f61...e276`, and host services stay healthy.
- Merged-main `dc8bbde6` wheel/sdist `c3f3cd0d...675c` / `dc57fa54...5325`;
  build, Twine, verification, install, and pip check pass in a fresh venv.
- Main-installed runtime is `2dd04fdc...9987`; Hermes/OpenClaw/Codex/Claude
  bundles `b03b47fe...e9b`/`1f88f2ef...2c8`/`cecc8993...b3b`/`5d178603...136`;
  exact attestation `93a25ad5...c25` passes all 18 checks.
- Canonical 300-second Codex retry `d90cfcd1...c47` passes managed
  trust/canary/attestation; OpenClaw RPC `48b73bba...393b` also exits 0.
- Dashboard `96d1a058...a515` passes auth, no-store, full prompt, and PID/port.

## exact-blocker

- Config repair `530b7837...1e5e` resolves ordinary-terminal auth. Two manual
  Qwen turns fail closed. Exact Luna Store `9c303400...ca81` passes in 96.72s;
  corrected alias transition `3e6b3491...d4c` preserves the stable ID and moves
  generation to subscription Luna-light at low reasoning.
- Hard planner receipts show Luna `aab403bd...6270` at 13,689ms fails one
  semantic gate while Terra `65427d17...36b` at 13,047ms passes. Profile
  `437b7ce3...9b83` attributes the remaining delay to two 4,096-dimension
  embedding batches and Mistral/embedding GPU reload churn.
- Subscription may replace every text stage when faster and accepted;
  embeddings remain local. GLM 5.2/5.3/Turbo fail at 46.32/23.01/21.88s;
  delete receipts `f228ab49...0c6`/`e90cc768...faf`/`745087c8...d01` pass.
  GLM 5.3 Flash low passes at 21.84s (`cdcca1ff...ae9d`) and remains temporarily
  available for verifier testing. Sol-light passes at 12.98s
  (`f1710b0a...ec6`), effectively tied with Terra's 13.16s single sample.
- Complete repeated Sol/Terra/Spark comparison, 1,024-dimension Qwen3
  embeddings, and subscription/local critic/reranker comparison. Target is
  <=20s warm and <=30s cold without weakening strict/additive behavior.
- Spark low/medium both pass the hard planner at 2.70/3.03s
  (`ce3a5eff...ed6`/`64ed8fa6...ce2`). Full Spark/Sol configs initially time out at
  60s cold and 45s repeated because the resident 8B embedding call alone takes
  about 34--37s; Store hashes are `d22dfc65...79f9`/`948df40a...fbc8`.
- Owner requests each stable text alias use the best measured primary plus an
  ordered cross-provider fallback. Use LiteLLM deployment `order`, zero
  per-deployment retries, cooldown, and forced-failure evidence.
- Approved 0.6B embedding pull/show/alias receipts pass. Cold 27-input probe
  `e861bd5d...ff0b` returns 27 uniform 1,024-value vectors in 2.148s. The first
  full run returns in 7.79s but fails strict planning twice; Store `d1562321...c09`.
- Journal audit `e307f2e5...784d` proves 12 distinct Spark completions. Stable
  generation rollback `75855980...6bc` restores local Qwen, and deletion receipts
  `bfb54a1f...86ae`/`b412d6cf...4851` remove both temporary Spark aliases.
- Frozen manifest `62f8bec4...c6fd` covers 67 approved non-Spark OpenAI,
  MiniMax, Z.AI, and local model/mode candidates over nine exact stages: 603
  screens, 18 local warm-ups, and at most 18 confirmations (639 hard maximum).
  Harness `226f4532...b4e8` passes no-call preflight. OpenAI ledger
  `a0c3f787...85e2` completes 270/270 cells: 238 structured, 197 eligible, 32
  bounded failures; Nano fails all nine. Corrected manager `8d7d884a...4d92`
  and post-block inspection leave zero temporary aliases.
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
5. [ ] Complete the capped per-stage quality/latency screen, promote repeated
   winners and cross-provider fallbacks, and prove <=20s warm / <=30s cold or
   report the exact feasible floor.
6. [ ] Complete Codex then Claude/Hermes/OpenClaw manual tests and issue the
   Linux verdict.

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
- Exclude Spark. One screen call per candidate/stage and one confirmation call
  only for the top two; zero deployment retries and retained call accounting.
- Do not create or close another tracker, tag, sign, publish a release, or make
  an unrelated model/config change without separate authorization.
