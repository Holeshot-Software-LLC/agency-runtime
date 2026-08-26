---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/roadmap/issue-AR-301-private-systemd-dashboard-namespace.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
  - docs/roadmap/issue-AR-303-bound-full-roster-embedding-requests.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-305-normalize-planner-novelty-absence.md
  - docs/roadmap/issue-AR-306-bind-strict-critic-semantics.md
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 2a9dc984a904140fc0d744dd90629944cefeac53
minimum_ledger_commit: 2aa0b5a9c00763972ebea740cfe69aa6d2b4544b
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in the dedicated Linux worktree on
  `codex/ar297-production-container-live-evidence`, descended from clean
  `origin/main` `0a23983aa7b99ec27ef18b1a950f6a0327961f72`.
- The exact candidate is substantive `2a9dc984` plus ledger `2aa0b5a9`. The
  source was clean before live work. Telemetry immediately before the first
  clean Codex canary exited 0 at 21.1 percent; this recovery pair records the
  resulting smallest safe slice before another live call.
- The current Linux verdict remains **NO-GO**. AR-297 and tracker #335 remain
  open; AR-301/302 product acceptance now passes, while their unauthorized
  tracker parity remains explicit.

## completed-evidence

- Exact mode-0600 config SHA-256 is
  `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`:
  strict assurance, additive dense recall, Qwen 14B abliterated generation,
  Mistral 24B critic/reranker/recruiter/child judge, and LiteLLM
  `qwen3-embedding` at 4,096 dimensions. Jina is absent and was not called.
- Direct acceptance remains green: session
  `ar297-direct-50344949-2206-4286-8dc8-d73bf640399f`, trace
  `f8af12a9-2747-489d-879a-4a8417d1ef35`, run
  `61c2b08b-b32c-4493-89b1-777d5efde4f9`; five model receipts, one accepted
  route, and only Accessibility Auditor loaded with its complete 2,659-byte
  prompt at SHA-256 `c3cfc098...e185848`.
- Caller-umask-0002 build, strict Twine, and independent verification exit 0.
  The mode-0644 wheel is 9,239,034 bytes at `912220eb...3740a2`; the mode-0644
  sdist is 25,356,218 bytes at `b3a35227...163c7c`. The named fast spine exits
  0 with 859 passed and 3 skipped. Metadata, policy availability, worklog,
  docs, Ruff check/format, 138 UI tests, routing, diff, and decision conformance
  all exit 0; conformance kills 160/160 mutations with source unchanged.
- The exact wheel is installed on the host in the owner-private `2aa0b5a9...`
  venv; `pip check` exits 0. All four host bundles are current. The attended
  combined install exits 1 only because Codex truthfully remains
  activation-required; OpenClaw was safely stopped and restored.
- The real non-root dashboard service install exits 0. It is enabled,
  active/running at PID 496966 with zero restarts. Unit SHA-256 is
  `7824e756...d5f4e8`; its owner runtime directory is mode 0700. Health is 401
  unauthenticated and 200/no-store authenticated. Authenticated worker detail
  is 200/no-store and the browser clears its bearer fragment and renders all
  2,659 prompt bytes. Mode-0600 screenshot SHA-256 is
  `7b60d2e9...454de` (156,166 bytes).
- Fresh images bind candidate `2aa0b5a9...` and wheel `912220eb...3740a2`:
  Codex `d3a2e3bd...49e546`, Claude `eb720746...fda24d`, Hermes
  `6262bad6...be1443`, OpenClaw base `2bf86f32...ccea47`, and OpenClaw
  systemd `967c229c...f11ca`. Four fresh containers prove no initial Agency
  state. Claude, UID-10000 Hermes, and OpenClaw production installs exit 0;
  OpenClaw registers all 13 hooks.
- The first exact Codex production transaction installs current managed-only
  policy with all eight events and no bypass. Requirements and relay hashes are
  `240d0622...78613` and `4b06fde8...c58e`, but its canary exits 1. Session
  `01a03f2e-593d-7861-bd79-3ab68ca5a92f`, trace
  `01a03f2e-5948-7bc1-83d1-15d7d331ca95`, and Store
  `aabc7fa8...9beb3` correlate one run and one preflight failure. Planning and
  both Mistral stages apply; additive recall records `embedding_provider_failed`.
  No route, specialist, child, finalization, or attestation row exists.
- AR-307's no-model probe proves the exact declared credential is present in
  the installer and removed by the general CLI environment. The bounded
  candidate projects only exact config-declared, credential-shaped values into
  the tool-reduced canary, rejects process/control collisions before launch,
  and leaves the general allowlist unchanged. Focused slices pass 90 and 118
  warning-strict tests; no post-fix model call has run.

## exact-blocker

- Commit the focused AR-307 recovery pair, rebuild exact artifacts and images,
  and rerun the no-bypass Codex production transaction. Do not change the
  approved config, model, endpoint, dimensions, reranker, thinking, judge,
  auth, or service-manager choices without interviewing the owner.
- Codex still lacks an attestation. No later ordinary Codex, Claude, Hermes, or
  OpenClaw process has current successful Agency-turn evidence on this source.
- AR-299 through AR-307 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Prior artifacts remain under `~/.agency-runtime/release-artifacts/`
`dist-2aa0b5a9c00763972ebea740cfe69aa6d2b4544b-linux-ar297` and become
historical when AR-307 commits. Private live
evidence is under `~/.agency-runtime/evidence/ar297-go-zKOPE1b8`; the exact
config is `agency-exact.yaml`. The four current proof container IDs begin
`e55383162646`, `420e0d4b20f6`, `3ff874135b36`, and `59f2302ed9fe`.
The secret-safe helper remains
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

1. Create the AR-307 substantive/ledger recovery pair, rebuild exact artifacts
   and fresh images, and run telemetry immediately before the one no-bypass
   Codex canary retry.
2. Run later ordinary Conveyor-equivalent Codex, Claude, Hermes, and OpenClaw
   processes and correlate Store plus native host artifacts without changing
   the approved topology.
3. Update canonical records, copy/hash exact host evidence, tear down only the
   four proof containers, and issue the Linux-scoped verdict.

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
  prose distinct. Never expose or persist a secret.
- Do not configure/call Jina, overwrite foreign policy, use an activation
  bypass, or touch the shared checkout.
- No tracker, push, PR, merge, tag, signing, publication, release, hosted
  workflow, or new model/config choice is authorized.
