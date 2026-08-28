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
branch: codex/ar297-host-live-closure
evidence_commit: aead84d0c89d13002d67d0a25d6978c8e6fca05e
minimum_ledger_commit: b25951bae8091b9906ffad628ac85e64afb4bc62
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2`; never touch the shared
  checkout. Host-live closure branch starts at `origin/main` `87231198`.
- All scoped matrix rows pass; final audit `3c82c16d...cd79` returns Linux
  **GO**. Clean reviewed head is `3a9a09c2`.
- AR-330 projects the real 0.150.1 role, nickname, activity, user-private-group,
  strict-lineage, and host-local rollout-filename shapes.

## completed-evidence

- Mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` hashes to
  `a4e213d6...97348`: strict assurance, additive dense recall, and every Agency
  inference route through authenticated LiteLLM aliases. No Jina route exists.
- Free Qwen 3 32B is promoted behind stable alias `task-agency-child-judge`.
  Promotion/metadata/final validation/literal/spend receipts are
  `6e19008f...1750`, `e1cba9f6...e841`, `42921a7e...867c`,
  `b686ab4b...9abe`, and `d7183bb5...2f07`. Temporary aliases are removed.
- Final named gates pass for `e0b0b25c`: 916 docs, Ruff lint/format, 860 Python
  tests with 3 skips, 138 dashboard tests, routing 1.4.0, and 167/167 killed
  decision mutations. Receipts are `6e0883bd...a98f`, `82b3e6a6...6b4f`,
  `b2a4a388...657f`, `3002917f...41c6`, `ac720857...8436`, and
  `547b518c...584f`; all final exits are 0.
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
- Final Claude receipt `7c4968e8...4dee` exits 0 for session `.303`: one exact
  3,227-byte card, all five alias receipts, accepted completion, `missing=[]`,
  native/Store response equality, exact config, and no bypass. The prior
  untrusted-`/tmp` Store attempt remains an honest bounded negative.
- Final-candidate Codex receipt `8b372e4c...2423` exits 0 for session
  `01a04546-933a-7c61-93a8-fb6129ffe24d`: one exact 2,659-byte card, four
  successful alias-only receipts, accepted completion, native/Store response
  equality, read-only/no-delegation execution, and unchanged exact runtime.
- Final-candidate Hermes receipt `9ee57328...f2f7` exits 0 for session
  `20260827_221502_139df0`: one exact 3,227-byte card, all five alias groups,
  accepted completion, `missing=[]`, exact visible accepted replay, healthy
  Stores, and byte-identical config. The corrected native source receipt is
  `d8e9eab7...9fe3`; the first helper-default mismatch remains retained.
- Final OpenClaw receipt `3c300451...5a02` exits 0: exact card/prompt visibility,
  sole LiteLLM host alias, thinking off, nonempty native response, accepted
  Store load/all Agency route receipts, unchanged config, and the explicit
  no-channel active-run limitation.
- Exact host refresh `68822689...33af` exits 1 only for normal attended Codex
  activation; Hermes, OpenClaw, Claude, and dashboard complete. Read-only
  attestation `64564e4a...bc24` exits 0 and binds wheel `75d63ff9...3762`,
  mode-0600 config `a4e213d6...97348`, all four final bundles, private runtime
  `d054649e...d3d7`, active zero-restart systemd-user dashboard, and restarted
  healthy OpenClaw receipt `561de9bd...df54`.
- HTTP/browser proofs `26923d58...bb2`/`65162e02...e32c` exit 0: auth is
  401/200 no-store, the exact 2,659-byte prompt `c3cfc098...5848` is fully
  visible, and screenshot `222d5109...b5ac` is retained without its token.
- Optional host Codex verifier `933bc916...bb4` fails before model invocation
  because attended hook trust is not ready; it changes nothing and uses no bypass.
- Teardown `40fa5062...1dc4` removes all 47 exact labelled containers with zero
  survivors; five images remain at `5c998f61...e276`, and host services stay healthy.
- Approved Qwen3 Coder aliases apply/verify `d69aa6b6...af4d`/`a1e2381d...a5dd`
  exit 0 at 65,536/no-thinking; unrelated aliases are unchanged. OpenClaw's
  three-pointer config transition/verify `e97e02e2...deba`/`a141d193...e1ce`
  exit 0; two stale-metadata attempts rolled back.

## exact-blocker

- No-bypass verifier `ef88754e...f2a4` passes 8/8 trust, then exits 1 because
  child `01a048b6...1301` receives generic identity.
- Rollouts `7a966722...3a9`/`8aa757e2...8f75` isolate the 0.149-only lineage and
  UTC reader; AR-330 resolves the real child and 103 tests pass. Rebuild/live
  proof and immediate fresh trust are next.
- Tracker audit `413c8a3a...1600` retains pre-existing parity debt; tracker
  writes/closure, signing, tagging, and release publication remain unauthorized.

## same-task-continuity

- Exact artifacts: `~/.agency-runtime/release-artifacts/dist-e0b0b25c30083b09743fe1a04f2a0ad4cdf4e533-linux-ar297`.
- Evidence/helpers: `~/.agency-runtime/evidence/ar297-go-e0b0b25c`, `/tmp/agency-runtime-ar297-evidence.pcLOZn/`.
- Protected Python: `~/.agency-runtime-ci/ar297-release-0827/venv/bin/python`.
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
4. [ ] Commit/build/install the completed AR-330 lineage repair, request fresh
   Codex trust immediately, then rerun all four harness/Store/prompt proofs.
5. [ ] Run every named repository gate, record exact hashes/exits, merge the
   authorized PR without bypass, and issue the final Linux-scoped verdict.

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
