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
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: c8b97ee3efdcbcbc7c7eba4182903e31eaf0c179
minimum_ledger_commit: fc404c768d6d5d6c45e8cbfb5889d6b42ab3e386
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- PR #326 is merged. The dedicated Linux worktree is on
  `codex/ar297-production-container-live-evidence` at clean starting commit
  `3177638dd541c2d59c216627e2a6cd0d2112d561`, ahead of `origin/main` by 12.
- Bootstrap and first live-check telemetry exited 0 at 77.2 and 60.1 percent.
  Telemetry then required the clean `14a4346c` / `3841fcce` recovery pair at
  49.5 percent. Immediately before the authenticated check it exited 0 at 27.8
  percent; immediately before the bounded provider diagnostic it exited 0 at
  26.5 percent. The clean pair satisfied the checkpoint requirement.
- The exact unsigned Linux candidate remains
  `987cee8ff01a4a16780eac15bb8120f828d4193d`. Its scoped verdict is **NO-GO**.
  AR-297 and tracker #335 remain open.

## completed-evidence

- Exact Agency config mode 0600, 3,642 bytes, SHA-256
  `cb569bf027133305df594d8ff029dffb8d38f545e960517d4431dfbf1b2bc2e1`
  remains strict/additive with Qwen 14B abliterated generation, Mistral 24B
  critic/reranker/child judge, and LiteLLM `qwen3-embedding` at 4,096
  dimensions. Jina is absent and was not called.
- The retained exact artifacts remain wheel
  `17a3bc0053a882b22ff72d8b3a2ebcd23ef602c2b5c034e7a05e8ae10ff929f1`
  and sdist
  `6551c43fc6fc7dfe7d8b9318e5b7605d1ecc8e214490eb7d0d2af001ffa9adb5`.
  Clean installs previously passed for Claude, Hermes, and OpenClaw; Codex
  installed managed policy but its two canaries failed before attestation.
- The prior ordinary Claude and OpenClaw processes timed out. Hermes session
  `20260826_143220_d88838` exited 0 only after Agency replaced an unverified
  draft with a refusal; Store run `ecdff898-6dc7-42c9-b0f9-db3447f46623`
  remained `preflight_failed`. No harness has a successful ordinary Agency turn.
- Authenticated dashboard evidence remains valid: unauthenticated health is
  401; authenticated health/detail are 200 and `no-store`; Accessibility
  Auditor renders all 2,657 characters at SHA-256
  `c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`.
  Runtime delivery was not asserted.
- All earlier named repository gates passed on the exact candidate. The
  optional exhaustive workflow was not dispatched and is not required. All
  five proof containers were removed; retained images and the host install
  remain. No container was created in the current package.
- AR-303 now prevalidates one complete logical embedding set and permits at
  most two ordered scalar-safe calls. The exact 263-card/4,096-dimension test
  uses batches 243 and 21 including one query; warm uses one. Partial failure,
  model drift, and dimension drift discard all vectors and never seed cache.
  Cold recall and host timeouts cover two embeddings plus one reranker.
- AR-304 adds closed recruiter candidate and strict-critic semantic diagnoses.
  Provider-authored prose and unknown codes cannot enter repair or preflight
  receipts. The focused warning-strict set passes 139 tests and changed files
  pass Ruff.
- Private trace `ae75a071-1bc2-444c-821a-f616dfd1402a` ran from a mode-0700
  evidence root against the exact config. It crossed the former scalar failure,
  then LiteLLM returned 401 because the direct process did not inherit the
  configured `LITELLM_API_KEY`. The run is `preflight_failed`; its two recruiter
  attempts both persist `recruiter_candidate_score_invalid` without model prose.
- The 6,750-byte summary SHA-256 is
  `f2c434d9486528b5808b4d263b3609c2ef446c0325527fbe628d84a20202542d`;
  the 3,940,352-byte private Store SHA-256 is
  `8910f9167ac5ca731ff44d5b0498dad9977562fa9712ccc5cfc1dce6003dced2`.
  Both are mode 0600 under
  `~/.agency-runtime/evidence/ar297-bounded-recall-mRVUWN8y/`.
- The existing LiteLLM gateway credential is mode-protected and already
  matches the config's auth choice. One ephemeral one-input check using that
  service credential applied in 3,818 ms at exactly 4,096 dimensions. No secret
  was printed, copied into config, or persisted in evidence.
- Authenticated trace `7a45e47a-4fb1-4f19-b712-acd24743f910` received HTTP 200
  for the first 244-row embedding call but still failed closed before recall.
  A direct bounded reproduction identified `BoundedJSONError: JSON exceeds the
  structural-node limit`: 999,424 vector scalars fit the scalar cap, while the
  response's row/container nodes exceed the separate one-million-node parser
  cap. Its 6,947-byte summary SHA-256 is
  `31f8c8ad731a5e1f84bfd9037dd5a5457d386e4b213ec636b5d5c63227d8b326`;
  its 3,940,352-byte Store SHA-256 is
  `72b33ee665806d9c8b055379cd98a28441903250ef67d403b8a60ee9273355bd`.
- The corrected limiter reserves fixed and per-row response nodes, yielding a
  243-row maximum at 4,096 dimensions and 243+21 in the exact regression.
- Node-bounded authenticated trace `d055d5b4-4bb9-4f6a-993c-5364b27c9e2b`
  then applied both exact `qwen3-embedding` batches and exact Mistral reranking.
  It failed only at Qwen recruitment: first
  `recruiter_candidate_positive_evidence_invalid`, then
  `recruiter_candidate_score_invalid`. Its 7,395-byte summary SHA-256 is
  `ab15602d81642a384741c97e78d874cf5569816728579b13adc12ec4f5e934df`;
  its 3,936,256-byte Store SHA-256 is
  `accbf41b7991de4c5daaad79232feac11dd542bf53ad2dc54cd3d67d81fac4f9`.
- Recruiter and repair prompts now state the exact numeric-score and hyphenated
  evidence-code formats, and diagnostic feedback supplies the matching closed
  correction. Focused warning-strict coverage remains 139; no further model
  call preceded this recovery checkpoint.

## exact-blocker

- AR-303 recall is live-proven. The Qwen recruiter still must clear its exact
  evidence-format/score diagnoses before a specialist can load.
- AR-301 blocks the shipped non-root dashboard service. AR-302 blocks ordinary
  ambient-umask/trusted-interpreter repeatability. No harness has a current
  successful ordinary Agency turn or Codex canary attestation.
- AR-299 through AR-304 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, and release remain unauthorized.

## same-task-continuity

The exact artifacts remain under `~/.agency-runtime/release-artifacts/`
`dist-987cee8ff01a4a16780eac15bb8120f828d4193d-linux-ar297`; the config remains
under `~/.agency-runtime/configs/`. The corrected private probe script is
`/tmp/ar297_direct_preflight_probe.py`; preserved failures use `no-auth-*` and
`authenticated-node-limit-*`, while the next run targets fresh
`authenticated-agency.db` and summary artifacts. It obtains the
already-running LiteLLM service credential in process memory and persists no
secret. Do not recreate containers until a later bounded package requires it.

## next-bounded-work-package

1. After the recovery pair, rerun telemetry and execute the prompt-corrected
   authenticated private preflight once. Require Accessibility Auditor selection
   and full prompt inclusion; retain any closed recruiter/critic diagnosis.
2. Finish focused review, run the named fast spine and every repository gate,
   then update AR-297, AR-303, AR-304, and this capsule with exact exits, hashes,
   Store correlations, and unresolved gates.
3. Only after this layer is green, resolve AR-301/AR-302 and build a new exact
   candidate before fresh four-harness containers and ordinary-turn proof.

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
- No tracker, push, PR, merge, tag, signing, publication, release, or hosted
  workflow action is authorized.
