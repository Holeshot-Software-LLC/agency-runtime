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
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 802a4b4fd74e4501f4b9d65b8cf6840bff7a4767
minimum_ledger_commit: 72d0965c42b372019b4ebc93631cb034f31165c5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- PR #326 is merged. The dedicated Linux worktree is based on clean
  `origin/main` commit `0a23983aa7b99ec27ef18b1a950f6a0327961f72` and is
  clean through evidence commit `802a4b4f` plus ledger `72d0965c`.
- Telemetry reported 12.6 percent remaining after gates. This refresh is the
  required clean checkpoint before another live model call.
- Tracker #335 remains linked and open. Tracker creation for AR-299 through
  AR-301 and every push, merge, tag, signing, publication, release, and hosted
  workflow action remain prohibited by the active task.

## completed-evidence

- Exact config: mode 0600, 3,642 bytes, SHA-256
  `cb569bf027133305df594d8ff029dffb8d38f545e960517d4431dfbf1b2bc2e1`.
  It uses strict assurance, additive dense recall, Qwen 14B abliterated
  generation, local Mistral 24B critic/reranker/judge, and LiteLLM
  `qwen3-embedding` at 4,096 dimensions. Jina was never configured or called.
- Final candidate is commit `987cee8ff01a4a16780eac15bb8120f828d4193d`.
  Build, strict Twine, and independent verification exited 0. The wheel is
  9,221,989 bytes with SHA-256 `17a3bc0053a882b22ff72d8b3a2ebcd23ef602c2b5c034e7a05e8ae10ff929f1`;
  the 25,223,088-byte sdist SHA-256 is
  `6551c43fc6fc7dfe7d8b9318e5b7605d1ecc8e214490eb7d0d2af001ffa9adb5`.
  The documented build under ambient umask 0002 still fails the independent
  `RECORD` permission contract; rebuilding under umask 0077 passes.
- Exact final image IDs are Codex `73e6110e7bbb`, Claude `7f83dcf5dea9`,
  Hermes `af242c17528c`, OpenClaw base `e7d713ed043e`, OpenClaw systemd
  `31bb75f7e075`, and dashboard `eb3dd7abcb67`.
- Claude production install exited 0 with bundle
  `68f2b48e1d97904bec4830b3a9c08b1ca1bd2a682b1cb5428b37bfdd234c770a`.
  Hermes UID-10000 install exited 0 with bundle
  `b8d3eb73364482696675e953c6e8ceb9121fc355a5f21dacfcc3d8b8cf76c5c2`.
  OpenClaw install exited 0 with bundle
  `270aec9ecef5581781d97bea45dfcff57ccb536d8f928dfc6273d46667044a0f`
  and loaded all 13 registration hooks. These are native registration proofs;
  they are not relabelled successful Agency turns.
- Two bounded Codex production attempts both installed bundle
  `54f7b16fd240f7cb158633284bde7c1e9ba1c433a31f62891ce5dac1e961b12c`
  and exact managed policy, then exited 1 at `staffing_critic_rejected` after
  additive embedding rejected invalid inputs. Store traces are
  `01a03e2b-01ba-7c02-962f-155b0fd8b3b8` and
  `01a03e2c-f2cc-7f83-93f7-42bfae07df79`. No route, specialist, child,
  finalization, or attestation proof exists. No bypass was used and no retry is
  authorized implicitly.
- Ordinary Claude timed out after 240 seconds with no output. Store trace
  `5e7cea73-3db3-400b-b083-0a9687180693`, session
  `c6710945-2869-4953-977f-3024662b7251`, ended with preflight still in progress.
- Hermes model `mistral-small3.2:24b` accepted 131,072 context, but Agency
  preflight failed and Ollama then rejected Hermes's retained `medium` thinking.
  Session `20260826_135649_5c52c9`, Store trace ending `95f4cb56`, no Agency
  model receipt, exit 1. A retry awaits approval for reasoning `none` and native
  auxiliary `free_only=true`; no paid auxiliary response succeeded.
- Ordinary OpenClaw loaded Agency but the strict `before_agent_run` hook timed
  out. Store trace `9b61694c-c562-498a-ab50-25aa2b5fcabd`, session
  `10ab5af0-1911-4833-8879-3202c63ffe6e`, retained an in-progress preflight and
  no failure receipt. Its systemd gateway/authentication path remains unresolved.
- Authenticated dashboard proof passed: unauthenticated health returned 401;
  authenticated health and workforce detail returned 200 with `no-store`.
  Accessibility Auditor rendered all 2,657 prompt characters with matching
  SHA-256 `c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`.
  The redacted screenshot SHA-256 is
  `7b60d2e963aaabba09399a07137b288e567a93f3466b1e167bb4b7496b5454de`.
  The installed CLI also returned the complete 2,709-character TypeScript
  contractor prompt at SHA-256
  `6b0d5cae3b65a44d56b22f51f5301bbd04f02bee7cdac9fe66bd9081b561c20f`.
  Both surfaces correctly say runtime delivery is not asserted. A fresh Store
  has no historical lineage, so historical visibility remains source-test proof.
- The exact wheel is installed on the Linux host at
  `~/.local/share/agency-runtime/venvs/987cee8f...`; the new launcher and exact
  config are owner-private. Hermes, OpenClaw, Codex, and Claude host bundles are
  respectively `2375e3c53797`, `305156f59d9b`, `848ba334a26e`, and
  `df70b0eae0c1`. Codex truthfully remains activation-required.
- Host dashboard installation rolls back cleanly. A normal non-root systemd
  user unit with `PrivateTmp=true` observes trusted `/` and `/home` ancestors as
  UID 65534, so the config namespace validator refuses cross-account path
  substitution. Foreground execution stays healthy. AR-301 records this defect;
  no hardening or ownership check was bypassed.
- Final gates: docs/Ruff/diff exit 0; fast spine 858 passed/3 skipped; UI
  138 passed; routing passed; decision conformance killed 160/160; fresh wheel
  and sdist smoke, MCP, dashboard, CLI, 8/8 deterministic smoke, and `pip check`
  all exit 0. AR-302 records ambient-umask/untrusted-interpreter failed runs.
- Host status exits 0 with all four bundles and no drift. OpenClaw user service
  and authenticated RPC are healthy; ordinary Agency-turn proof remains failed.

## exact-blocker

- Codex managed canary never completed; all four ordinary harness proofs are
  incomplete or failed, so unattended loading is not proven.
- Host dashboard service cannot start under its shipped Linux hardening because
  of AR-301. OpenClaw gateway health still needs a read-only final status check.
- AR-299 through AR-302 tracker parity is unauthorized. Signing, publication,
  tags, release, hosted cross-OS artifacts, and optional exhaustive workflows
  remain unrun and unauthorized.

## same-task-continuity

Use `/tmp/agency-runtime-ar297.WQUbF2` and the private evidence root retained by
the active session. Preserve the exact config and Store identities. Inject any
credential only through the existing private environment; never print it or
copy it into repository evidence.

## next-bounded-work-package

1. If the owner approves reasoning `none` and auxiliary `free_only=true`, run
   the same Mistral Hermes turn once and preserve exact terminal evidence.
2. Perform only the remaining read-only host/OpenClaw/status checks; do not
   retry Codex or weaken the dashboard service boundary.
3. Run every repository gate named in `AGENTS.md` and the applicable unsigned
   Linux release checks against the exact candidate.
4. Update AR-290 and AR-297 through AR-301, this capsule, and the release
   checklist with exact exits and unresolved gates; create the final
   substantive/ledger pair.
5. Remove exactly the five `agency-ar297-*` containers and issue the scoped
   Linux GO/NO-GO. Do not remove images or unrelated services.

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

- Keep discovery, registration, loading, canary, host delivery, Store
  correlation, and model prose distinct. Never expose or persist a secret.
- Do not configure or call Jina; do not overwrite foreign policy; do not use an
  activation bypass; do not touch the shared checkout.
- No tracker, push, merge, tag, signing, publication, release, or hosted
  workflow action is authorized.
