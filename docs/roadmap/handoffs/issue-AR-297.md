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
  - docs/roadmap/issue-AR-308-bind-activation-canary-delegation.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
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
evidence_commit: 131f57e5360407176cebd34c90b935f6c196f509
minimum_ledger_commit: 139192da8d2bf8ba1e67211695405219027058c2
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in the dedicated Linux worktree on branch
  `codex/ar297-production-container-live-evidence`, from clean `origin/main` `0a23983a`.
- The last clean recovery pair is goal ledger `131f57e5` plus worklog
  `139192da`. The AR-310 restricted-Store repair now passes 268 warning-strict
  focused tests and is being checkpointed before rebuilding the live candidate.
- The current Linux verdict remains **NO-GO**. AR-297 and tracker #335 remain
  open. No tracker, push, PR, merge, tag, signing, publication, release, or
  hosted workflow action is authorized.

## completed-evidence

- Exact mode-0600 config SHA is `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`:
  strict assurance, additive dense recall, Qwen 14B abliterated generation,
  Mistral 24B critic/reranker/recruiter/child judge, and LiteLLM
  `qwen3-embedding` at 4,096 dimensions. Jina is absent and was not called.
- Rebuilt caller-umask-0002 artifacts at ledger `fd163da2` pass build, strict
  Twine, and independent verification. The mode-0644 wheel is
  `2d78f9c...16ab5` (9,291,917 bytes) and sdist is `cf160e6a...d06a`
  (25,479,108 bytes).
- Five exact image IDs begin `226afba9` (Codex), `507328b7` (Claude),
  `8a50f5cb` (Hermes), `fd9967a0` (OpenClaw base), and `893b88eb`
  (OpenClaw systemd). Four fresh containers bind candidate `1f32915d`; their
  pre-install absence receipt passes at SHA `58e279f1...d128`.
- All named repository gates already pass at `1f32915d`: 860 Python spine
  tests with three skips, 138 dashboard tests, routing, and 161/161 killed
  decision mutations. The decision-conformance JSON SHA is
  `b0636470...0a6`, and source remained unchanged.
- The sole fresh Codex install exits 1 with empty stderr and exact JSON SHA
  `72c4ba0...6e4ab`. Managed-only policy and no bypass are preserved. Session
  `01a03f83-bb05-7c43-b9b3-38cb8d9e30dd` proves Qwen planning, exact
  4,096-wide LiteLLM embedding, Mistral recruiting/criticism, accepted
  `delivery=delegate`, one loaded `code-reviewer`, one native spawn, one child
  answer, and one completed wait.
- Parent/child rollout SHAs `5a548331...2af2` and `4732afb2...225e` prove the
  actual Codex 0.149 lifecycle. The newer V2 envelope redacts the decrypted
  child launch and omits Agency's post-wait header context; Store finalization
  is `response_invalid`, no host delivery verifies, and no attestation exists.
- The one supported-`multi_agent` comparison exits 0 but records zero native
  deliveries/delegations/worker runs for session `01a03f94...e55`, trace
  `01a03f94...a`, and query hash `4d160cfe...c652`. Its mode-0600 stdout,
  stderr, Store, and rollout SHAs are `356d36d1...bc6`, `dc6b6525...f5a`,
  `bb518e7c...20d`, and `95329525...a3`: the actual plan row is absent, so
  stable cannot replace the V2 surface that spawned the child.
- AR-308 is therefore live-proven through its exact delivery boundary. AR-309
  now owns the later host-artifact/header defect. No model, endpoint, dimension,
  reranker, thinking, judge, auth, or service-manager choice changed.
- AR-309 now has a bounded implementation: exact 0.149
  `item_completed/SubAgentActivity` and quiet-root parsing, real child-UUID
  `SubagentStart` v6 delivery, one-use canonical-rollout receipt verification,
  post-spawn execution reconciliation, and receipt-backed final headers. The
  public Codex artifact parser remains diagnostic-only and ordinary opaque
  children remain unstaffed.
- Warning-strict AR-309 verification passes 328 Codex delivery/canary/hook/
  header and 109 Store/contract/security tests. Fresh `fd163da2` absence passes,
  but live install stops before Codex because its managed canary omits the exact
  existing-Store marker; AR-310's repair passes 268 focused tests.

## exact-blocker

- Codex still lacks an attestation. Exact install JSON `64b021ce...1b54` and
  diagnostic `d55536f7...2845` exit 1 before any rollout or Store run; private
  traceback `a2821a18...ba65` isolates AR-310's missing restricted-Store flag.
- Rebuild that repair, replace the now-mutated proof container, and require one
  canonical child artifact, consumed receipt, current delegated header,
  accepted first finalization, and no-bypass attestation in one invocation.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-310 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts are under `~/.agency-runtime/release-artifacts/`
`dist-fd163da266b309266b8bfd14a3363236d7853d43-linux-ar297`. Private current
evidence is `~/.agency-runtime/evidence/ar297-go-fd163da2`; historical evidence
remains retained. Codex image `9afefdb2...39442` and container
`570506ea...39b9` retain the failed proof; replace it after rebuild. All AR-297
containers await teardown. Helper: `/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Rebuild and verify exact `fd163da2` artifacts plus the Codex image.
2. [ ] Prove fresh Codex absence, then one exact no-bypass V2 install with one
   canonical child artifact, consumed receipt, current header, accepted
   finalization, Store correlation, and attestation.
3. [ ] Build and prove separate clean exact Claude, native-UID Hermes, and
   OpenClaw systemd production-container installs.
4. [ ] Run later ordinary unattended Conveyor-equivalent processes for all four
   harnesses; retain native artifacts, Store correlations, and full workforce
   prompt visibility without treating definition presence as runtime delivery.
5. [ ] Install the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
6. [ ] Run every named repository gate and record exact exits and hashes.
7. [ ] Update canonical issues/capsule and make the required local substantive
   and `docs(worklog):` ledger commits.
8. [ ] Resolve and remove every container labelled `AR-297`; retain teardown
   evidence and verify zero labelled survivors.
9. [ ] Issue the Linux-scoped GO/NO-GO and complete the persistent goal only
   when all required items above are truthfully closed.

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
