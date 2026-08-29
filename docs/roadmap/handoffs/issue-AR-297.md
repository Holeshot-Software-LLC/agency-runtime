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
branch: codex/ar297-manual-preflight-reliability
evidence_commit: e755ab539c317915f4a71fda2d4de4bb6cf27fd0
minimum_ledger_commit: 1a4402a3a61f717344e4456c7d4d19a3e7e5a93a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297-manual-preflight.1583934a`; never touch the shared checkout.
- PRs #341--#343 reach `origin/main` `1583934a`; exact product `341f472b...099b` stays installed unpinned.
- Clean checkpoint `71e3d8ca` / ledger `1a4402a3` precedes this recovery pair.

## completed-evidence

- Owner-private config `df75e01d...0922` resolves ordinary LiteLLM auth without
  printing the key; no Jina route exists.
- Free Qwen 3 32B promotion/validation/spend evidence is retained under stable
  `task-agency-child-judge`; temporary aliases are removed.
- Final named gates pass for `33d9503b`: 921 docs, Ruff/696 formats, 861 tests
  plus 3 skips, 138 UI tests, routing 1.4.0, and 167/167 mutations killed.
- Exact build, Twine, install, security, hosted-platform, and AR-328 evidence is
  canonical in the issue; no optional exhaustive workflow was dispatched.
- Strict container proofs pass separately: Codex `ce370bc8...1330` with one
  delivered native child; Claude `579d65c8...a0e9`; Hermes
  `4d04f360...02d8` with sealed tree `d7bc15f0...d8f8`; and OpenClaw
  `4debebf3...c748` with Store/systemd/13-hook evidence. All retain exact
  bundles and `missing=[]` where terminal delivery applies.
- Ordinary Claude/Codex/Hermes/OpenClaw verifiers prove full cards, aliases,
  healthy Stores, and no bypass; OpenClaw preserves foreign policy and RPC passes.
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
- M3 fallback `172ba9ac...5fc5` / `5106e992...1ee7`: planner repeats 100;
  generator varies; readiness is eight of nine.
- Local comparison `055044a5...b793`: Qwen3 Coder generation repeats quality
  100; Llama fails. Six zero-retry calls clean up; the matrix is nine of nine.
- All nine routes close: safety uses M3-off primary and GPT-5.4-mini fallback.
- Safety forced/normal calls score 100 in 14.382/11.446s with exact UUIDs.
- Routes `527ef79a...760b`: 10 aliases, 19 deployments, exact 1,024 dimensions.
- Gates `31896f7d...2f9a` and hosted run `33240382780` pass; PR #341 is merged.
- Main `341f472b...099b` is active; all four bundles pass. Attended Codex trust
  and no-bypass activation `01119a71...2d69` exit 0 with a fresh v4 canary,
  persisted attestation, `unmet_prerequisites=[]`, and empty stderr.
- Critic speed tie-break remains Terra-medium/local Qwen 2B. Four retained
  zero-retry fixture proofs score 100; ledger `a33d3810...3f67` closes 4/4.
- Audit `8103d4b9...8d1` passes seven checks, nine routes, ten aliases, nineteen
  deployments, exact config `756da1c4...1cb0`, and zero disposable aliases.
- Closure `c9f097bf...6844` rejects Flash-off/GLM-5.2; Turbo is 1/2 only because
  its exact codebase-discovery unit hits the legacy software-engineering-only policy.
- Policy `687386f6...093` plus replay `f3999625...88dd` makes Turbo 2/2; candidate
  `84581629...158a` passes 921 docs, Ruff/696 formats, 864+3 tests, 138 UI, routing, and 167/167 mutations.
- Build/Twine/verify/install exit 0; wheel/sdist `2c55fc54...f71ce` / `314208f3...1117e`, record `a01429a3...564b`; no model ran.

## same-task-continuity

- Main artifacts: `~/.agency-runtime/release-artifacts/dist-341f472ba3d57559b6730b66ec1504f5be52099b`.
- Main evidence: `~/.agency-runtime/evidence/ar297-main-install-20260829-341f472b...099b`.
- Exact config `ar297-litellm-v2-756da1c4c916006f.yaml` is unchanged; LiteLLM owns the critic swap and planner rollback.
- Zero AR-297 containers remain; older immutable artifacts stay available for rollback.

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
7. [x] All pairs/routes/gates, PR #341, exact main install, attended Codex trust,
   and the owner-selected speed-first two-route proof are complete.
8. [ ] Obtain outward authorization, push/PR/merge/install `84581629...158a`, spend
   the forced Turbo proof, then prove Codex `ready` and all four attended turns.

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
- Exclude Spark. The time-bounded model/config test grant expired at 11:00 AM;
  keep zero deployment retries and interview before any new model choice.
- Do not create or close another tracker, tag, sign, publish a release, or make
  an unrelated model/config change without separate authorization.
