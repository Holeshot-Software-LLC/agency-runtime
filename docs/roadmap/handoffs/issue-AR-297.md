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
branch: claude/ar297-turbo-live-evidence
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
- Agency master control is ON globally (generation 2); per-host runtime
  controls are enabled.
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

## exact-blocker

- Codex activation is attended by design: the refreshed bundle invalidated the
  prior trust attestation. Fresh terminal `codex`, `Trust all and continue`
  with all 8 Agency hook events listed, then
  `agency install --agent codex --verify-activation`. No bypass.
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
4. [ ] Operator completes attended Codex trust in a fresh terminal, then
   `agency install --agent codex --verify-activation` exits 0 with a fresh
   persisted attestation and no bypass.
5. [ ] Run the restricted current-profile Codex canary and retain its receipt.
6. [ ] Run the four ordinary attended host turns (Codex, Claude, Hermes,
   OpenClaw) against the promoted route and close AR-297 with exact evidence.

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
