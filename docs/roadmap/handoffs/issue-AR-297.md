---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-29
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-331-align-plan-policy-discovery-inventory-with-deterministic-oracle.md
  - docs/roadmap/issue-AR-332-pin-private-umask-for-canary-child-launches.md
  - docs/roadmap/issue-AR-333-report-unsupported-codex-isolated-agency-canary.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/decisions/0191-seal-managed-hermes-python-bundles.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: claude/ar336-requalification-evidence
evidence_commit: 233e122d543040ad656b8b33be79093c934e6ad8
minimum_ledger_commit: b81dd8663ea52ca1c4ed9c6b40f98f2ff4270b61
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Exact merged `origin/main` `755efedc...5455` is installed as the active
  commit-named venv; the 2026-08-29 independent review re-verified every
  retained hash, both distributions, and hosted runs `33265165087`/`160`/`174`.
- The full pre-promotion history is canonical in the issue document; this
  capsule projects only the post-promotion state.

## completed-evidence

- Owner-approved one-call Turbo promotion executed 2026-08-29 and passed:
  forced production fallback through `task-agency-planner-v2`, HTTP 200,
  `attempted-fallbacks=1`, identity `ed1b5bbc...e4c1`, semantics valid under
  installed policy `687386f6...093`, 29,667 ms, one call, zero retries, zero
  cleanup errors. Summary/final-info/ledger `8faaf337...0e37` /
  `79ce0c47...2f67` / `d3f28963...8bc5`.
- Final planner route: GPT-5.5-low order 1 (`c2692490...0cbb`) plus GLM-5
  Turbo thinking-on order 2 (`ed1b5bbc...e4c1`). Agency and shared LiteLLM
  configs stay byte-identical (`756da1c4...1cb0` / `d2811be7...ecec`); the
  route lives in LiteLLM's database and survives restarts.
- Owner accepted the fallback latency exception (23.9-30.2 s observed vs the
  20 s warm / 30 s cold target) for the order-2 slot only.
- Agency master control was enabled for the live phase and is restored to OFF
  (generation 3) after the ordinary-turn matrix failed; per-host runtime
  controls stay as installed.
- Live isolated Claude agency canary PASSES end to end on the promoted route
  under `umask 077`: run/delegation/finalization, `code-reviewer` selected and
  loaded, zero preflight failures, verified child card delivery `collected`.
  Receipts under `~/.agency-runtime/evidence/ar297-live-harness-20260829/`.
- Codex isolated agency canary deterministically refuses pre-invocation
  (restricted current-profile contract, AR-333); zero model calls spent.
  Hermes/OpenClaw expose no noninteractive canary mode; OpenClaw deep RPC
  exits 0 and both user services are active. zcode is not installed here.
- New findings recorded: AR-331 (oracle vs policy discovery inventory),
  AR-332 (canary child umask), AR-333 (unsupported Codex isolated canary
  reported as ready); trackers #345-#347 exist and are linked.
- Post-trust verification 2026-08-29: attended Codex trust succeeded, then
  verify-activation exits 1 on codex-cli 0.151.0 contract drift (AR-334,
  #349); the current-profile canary reproduces the deterministic refusal.
- Ordinary-turn matrix 2026-08-29: all four hosts fail preflight on
  content-invalid completions (AR-335, #350). Planner stray-`]}` specimen
  `6b742a20…` retained; recruiter contract-invalid pattern on hermes and both
  codex canary parents. The same alias returned valid plans for fixture,
  route, and canary calls in the same hour.

- Rollout 2026-08-29 evening: exact main `6606ebed` built/verified/installed
  (wheel `c7e365bf...abcc`); config v4 `3cf8a566...78fa` live everywhere;
  content-fallback aliases `fe551fea...6321`/`03d783b3...692a`; forced proof
  and three live planner rescues receipted under
  `~/.agency-runtime/evidence/ar335-content-fallback-aliases-20260829/`.

- AR-336 receipts: matrix `cd4ef06c…`, repairs `eed4fc7a…`/`45211b19…`;
  four-turn receipts `54db6a8e…` (claude, ok true), `7fc4eb2f…` (codex, ok
  true), `c5b5a706…` (openclaw), `a74a20e9…` (hermes). LiteLLM response
  cache identified as a fixture-probe hazard; use nonce-busted sampling.

## exact-blocker

- The sole open codex item is the restricted current-profile canary's
  child-side delivery join (AR-334): parser and parent snapshot proven,
  mid-turn open-trace state unobservable post-hoc; use the hook diagnostics
  environment on the next attempt.
- Codex gates wait on one fresh attended trust (the 6606ebed install rotated
  the launcher digest inside the hook commands); after trust,
  verify-activation is expected to exit 0 on 0.151 via ADR-0193.
- Diagnosis caution: bare `run_preflight` without capability receipts runs
  with `context_host=unknown` and fabricates host/tool rejections.
- claude-code 2.1.251 ships group-writable npm directories; the tree was
  tightened with `chmod -R g-w` so the host-version probe passes. A future
  claude-code upgrade may need the same tightening until AR-332 lands.
- Live canaries must launch under a private umask (`umask 077`) until AR-332
  pins one in the backend.

## same-task-continuity

- Promotion evidence: `~/.agency-runtime/evidence/ar297-planner-turbo-promotion-20260829`.
- Live harness receipts: `~/.agency-runtime/evidence/ar297-live-harness-20260829`.
- Review handoff consumed: `~/.agency-runtime/evidence/ar297-independent-review-20260829`.
- Main artifacts: `~/.agency-runtime/release-artifacts/dist-755efedcfa836bf439062e7b62e64aff9c485455`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the
first unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Independent review of the prepared promotion; owner GO with the
   latency exception recorded.
2. [x] Spend the retained forced Turbo proof; retain Turbo order 2 with exact
   final-route evidence.
3. [x] Enable master control and pass the live isolated Claude agency canary
   on the promoted route.
4. [x] Operator completed attended Codex trust; verify-activation exits 1 on
   the codex-cli 0.151.0 contract drift (AR-334), not on trust. No bypass.
5. [x] Restricted current-profile Codex canary attempted: deterministic
   `codex_collaboration_projection_unavailable` refusal retained (AR-334).
6. [x] All four ordinary host turns attempted unattended and failed preflight
   on content-invalid completions (AR-335); receipts and the planner
   stray-`]}` specimen are retained. Master control restored to OFF.
7. [x] Owner decided 2026-08-29: no host pin, the code accounts for new
   versions (AR-334, ADR-0193); content-fallback routes selected (ADR-0192).
8. [x] AR-334/AR-335 merged as `ec46aced`; exact main `6606ebed` installed
   with config v4; forced content-fallback proof passed; the planner rescue
   is live-proven in three consecutive ordinary turns.
9. [x] AR-336 executed: matrix revalidation, luna order-2 replaced with
   gpt-5.5-low, planner content-fallback settled on gpt-5.6-terra medium;
   all four ordinary host turns staff (claude/codex full bar with
   finalization and header; openclaw/hermes staffing-complete per host
   contract); master control ON (generation 6), inference operational.
10. [x] Fresh attended Codex trust is complete and the ordinary codex turn
   passes the full bar on 0.151 with Stop-gated publication.
11. [ ] Close the last codex formality: run the restricted current-profile
   canary under `AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS=1`, give the child-side
   delivery join a recorded content-free refusal reason if needed (AR-334),
   and land `verify-activation` exit 0 with a persisted attestation.
12. [ ] Decide whether openclaw/hermes one-shot finalization observability
   needs its own bounded item, then close AR-297 on the retained four-turn
   evidence.

## verification

~~~text
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
- Do not call Jina, exclude Spark, overwrite foreign policy, bypass Codex
  activation, or touch the shared checkout. All Agency inference stays behind
  LiteLLM aliases with zero deployment retries.
- Any unknown model, endpoint, dimension, reranker, thinking level, judge
  route, harness-auth, or service-manager choice requires an owner interview.
- Do not create or close another tracker, tag, sign, publish a release, or
  make an unrelated model/config change without separate authorization.
