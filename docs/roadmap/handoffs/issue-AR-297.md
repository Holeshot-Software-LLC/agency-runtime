---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-29
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

- Config repair `530b7837...1e5e` resolves ordinary auth. Stable generation is
  rolled back to local Qwen and Spark is excluded after 12 audited completions.
- Approved local Qwen3 0.6B embeddings return 27 exact 1,024-value vectors in
  2.148s (`e861bd5d...ff0b`); strict/additive behavior stays unchanged.
- Every stable text alias still requires the best repeated primary plus a
  different-provider fallback, LiteLLM order 1/2, zero retries, cooldown, and
  forced-failure evidence. Target remains <=20s warm and <=30s cold.
- Manifest/ledger `62f8bec4...c6fd`/`2080c834...d56` contain exactly 603
  screens, 18 warm-ups, and 18 confirmations (639 maximum). Replay audit/
  rankings/results `1823c21b...19e`/`ebd3f4fb...cee6`/`f6c92e4b...189a` pass.
- Owner-authorized remediation manifest/ledger `f7477f43...9e3` /
  `deedc130...a1` consume exactly 24 starts/finishes, zero retries. Replay
  `ce7704a5...b455` checks 16 saved responses; 20 alias receipts pass and
  authenticated inspection finds zero temporary aliases.
- Hiring critic is newly promotable: GPT-5.4-mini-low averages 2.085s and local
  Qwen 2B 6.258s including cold load, both 2/2 at quality 100. Planner,
  generator, and safety each have a repeated OpenAI primary but no fallback.
- Report `8fd5667f...a587` / validation `ce57492e...572c` preserve 313 rankings,
  reconcile 669 calls, and admit six of nine; plugin tooling is restored.
- Prompt repair `38f51f01...276f` pins the five top-level keys, closed arrays,
  nonempty strings/tools, and verbatim-source exclusion for all safety fields.
  Ruff passes; 137 focused tests pass with one intentional skip. No model ran.
- Follow-up and closure results `249ce089...95cc` / `19565ac0...0472` add no
  pair: planner and local generator fail; Z.AI generator varies 100/80; M3
  safety varies 100/85 then emits only two keys. Both finish with zero aliases.
- Shape/cache repair `863df134...a8d8` adds literal arrays, all five safety
  keys, and a noninstruction `repair_turn`; 188 focused tests pass.
- Hot closure rejects local-Qwen/Z.AI; M3 safety raises readiness to seven of nine.
- Final-pairs `33256428...7400`: OpenAI primaries repeat 100; M3 varies; eight calls clean up.
- Anti-echo intent/test `07fdffdc...2dfa` / `09b238ef...461c` pass Ruff and 188 tests; no model ran.
- M3 fallback manifest/ledger/results `172ba9ac...5fc5` / `5106e992...1ee7` /
  `c8f79895...d90b`: planner repeats 100; generator varies; readiness is eight of nine.
- Local comparison `055044a5...b793`: prewarmed Qwen3 Coder generation repeats
  quality 100 in 21.483/16.928s; Llama scores 47.5 twice. Six zero-retry calls,
  warmups, receipts, and cleanup pass; the matrix is nine of nine.
- Record audits exit 1 only on inherited parity debt; AR-297/#335 is aligned.

## same-task-continuity

- Artifacts: `~/.agency-runtime/release-artifacts/dist-dc8bbde6a884f72614dae32585e488ce4997b9ac`.
- Venv/evidence: `~/.agency-runtime/release-venvs/ar297-main-dc8bbde6` / `~/.agency-runtime/evidence/ar297-main-install-dc8bbde6`.
- Manual repair/evidence: config `ar297-litellm-df75e01d31dd8ebc.yaml` / `~/.agency-runtime/evidence/ar297-manual-live-20260828`.
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
5. [x] Execute the owner-authorized 24-call remediation and refresh the report;
   six of nine cross-provider pairs now qualify with no stable config change.
6. [x] Prompt hardening and the exact six-call follow-up are complete; no new
   repeated route qualifies and the stable config remains unchanged.
7. [ ] Under owner YOLO authority through 11:00 AM, all nine pairs are closed.
   Apply exact routes, prove forced fallback, and reinstall
   exact main artifacts without an Agency version pin.
8. [ ] Complete Codex then Claude/Hermes/OpenClaw manual tests and issue the
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
- Exclude Spark. Owner grants in-scope model/config test authority through
  11:00 AM local time; keep zero deployment retries and retained accounting.
- Do not create or close another tracker, tag, sign, publish a release, or make
  an unrelated model/config change without separate authorization.
