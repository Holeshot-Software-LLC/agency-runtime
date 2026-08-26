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
evidence_commit: c8b97ee3efdcbcbc7c7eba4182903e31eaf0c179
minimum_ledger_commit: fc404c768d6d5d6c45e8cbfb5889d6b42ab3e386
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- PR #326 is merged. This dedicated Linux worktree is based on `origin/main`
  commit `0a23983aa7b99ec27ef18b1a950f6a0327961f72` and was clean through
  evidence `c8b97ee3` plus ledger `fc404c76` before this evidence refresh.
- Live-call telemetry exited 0 at 92.5 percent remaining. End-of-package
  telemetry exited 0 at 49.1 percent and requires this clean recovery pair.
- The exact unsigned Linux candidate is
  `987cee8ff01a4a16780eac15bb8120f828d4193d`. Its scoped verdict is
  **NO-GO**. AR-297 and tracker #335 remain open.

## completed-evidence

- Exact Agency config: mode 0600, 3,642 bytes, SHA-256
  `cb569bf027133305df594d8ff029dffb8d38f545e960517d4431dfbf1b2bc2e1`.
  It uses strict assurance/independence, additive dense recall, local Qwen 14B
  abliterated generation, local Mistral 24B critic/reranker/child judge, and
  LiteLLM `qwen3-embedding` at 4,096 dimensions. Jina was never configured
  or called.
- Build, strict Twine, and independent verification exit 0 under umask 0077.
  The 9,221,989-byte wheel SHA-256 is
  `17a3bc0053a882b22ff72d8b3a2ebcd23ef602c2b5c034e7a05e8ae10ff929f1`;
  the 25,223,088-byte sdist SHA-256 is
  `6551c43fc6fc7dfe7d8b9318e5b7605d1ecc8e214490eb7d0d2af001ffa9adb5`.
  Ambient umask 0002 still exposes AR-302; it is not relabelled successful.
- Final images are Codex `73e6110e7bbb`, Claude `7f83dcf5dea9`, Hermes
  `af242c17528c`, OpenClaw base `e7d713ed043e`, OpenClaw systemd
  `31bb75f7e075`, and dashboard `eb3dd7abcb67`.
- Clean production installation exits 0 for Claude, UID-10000 Hermes, and
  OpenClaw with bundles `68f2b48e1d97`, `b8d3eb733644`, and
  `270aec9ecef5`; OpenClaw loads all 13 registration hooks.
- Two Codex managed-policy attempts install bundle `54f7b16fd240` and then
  exit 1 at `staffing_critic_rejected`. Traces
  `01a03e2b-01ba-7c02-962f-155b0fd8b3b8` and
  `01a03e2c-f2cc-7f83-93f7-42bfae07df79` have no route, specialist,
  child, finalization, or attestation. No bypass or further retry was used.
- Ordinary Claude times out at 240 seconds with trace
  `5e7cea73-3db3-400b-b083-0a9687180693`. Ordinary OpenClaw loads Agency
  but times out in `before_agent_run` with trace
  `9b61694c-c562-498a-ab50-25aa2b5fcabd`. Neither is a successful turn.
- The first Mistral Hermes attempt exits 1 because retained `medium` thinking
  is unsupported. Session `20260826_135649_5c52c9`, Store trace ending
  `95f4cb56`, and request-dump SHA-256
  `2ac48175e48e1e1a011a2dc672c937a8fe55fc411ce1eb376b2942e1521e062e`
  remain exact failed evidence.
- The owner approved `agent.reasoning_effort=none`,
  `auxiliary.free_only=true`, and exactly one retry. Native config SHA-256
  was `b2540d6e86de4705fe20903b693a14906c7810c7e2d179811964e0b12706b0d4`.
  The same 246-byte prompt SHA-256
  `6b5c3c66979625bcc9b90a91978637ce15ca7fb3d3fa95da5b1df03c54c3b154`
  created session `20260826_143220_d88838` and trace
  `20260826_143220_d88838:59ceb645-aba9-4910-9cb6-1f25d61efd89:2f835640`.
- That command exits 0 only after Agency replaces the unverified draft with a
  refusal. Run `ecdff898-6dc7-42c9-b0f9-db3447f46623` is
  `preflight_failed`; receipt `ee306616-aa15-4262-b88f-b1e9818f0de0`
  records `workforce_inference_failed` and `inference_invalid`. Correlated
  rows exist only in `runs` and `preflight_failure_receipts`; there are no
  Agency model, route, skill, specialist, delegation, finalization, or canary
  records.
- Hermes itself completes two local Mistral calls with zero reasoning tokens
  but never invokes Agency. Its 1,367-byte draft SHA-256 is
  `b4dfa808fd380fd99439f55417fcfa09635ccb4bffdde2148a93aff1f12794e9`;
  the 16,912-byte system prompt SHA-256 is
  `e99111a2373e66b18fa7e3ecd1b4353105ed1cdd30bdd909476427ae8623855e`.
  No second request dump or retry exists.
- Authenticated dashboard proof passes: unauthenticated health is 401;
  authenticated health/detail are 200 and `no-store`. Accessibility Auditor
  renders all 2,657 characters at SHA-256
  `c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`;
  redacted screenshot SHA-256 is
  `7b60d2e963aaabba09399a07137b288e567a93f3466b1e167bb4b7496b5454de`.
  Installed CLI prompt proof also passes. Runtime delivery remains not asserted.
- The exact wheel and four bundles remain installed on the host. Final
  `agency status --json` exits 0 with no drift, Codex activation-required,
  the other hosts runtime-unverified, and every canary attestation absent.
  OpenClaw service/RPC/plugin checks exit 0; the service is active with zero
  restarts and Agency Preflight 0.1.0 loaded. Foreign device-auth policy was
  observed and not changed.
- Host dashboard installation still rolls back under non-root systemd
  `PrivateTmp=true` because remapped root ancestors appear as UID 65534.
  Foreground health passes. AR-301 owns the unresolved defect; no namespace or
  hardening check was bypassed.
- Every named repository gate exits 0: documentation, Ruff, diff, the
  858-pass/3-skip fast spine, 138 dashboard UI tests, routing thresholds, and
  decision conformance with 160/160 mutations killed. Fresh wheel and sdist
  smokes, eight MCP tools, dashboard health, deterministic smoke 8/8, and
  `pip check` also exit 0. The optional exhaustive workflow was not dispatched
  and is not required for this scoped verdict.
- `docker rm -f` exits 0 for exact container IDs `2ad5e056c84c`,
  `23d812c2bbf1`, `473cd5bd6059`, `ec5ea44a6f7a`, and
  `c7a713bb3b06`. The filtered container list is empty; all candidate images,
  the host installation, artifacts, and OpenClaw service remain.

## exact-blocker

- No harness has a current successful ordinary Agency turn. Codex has no
  managed canary attestation, so four-harness unattended loading is unproven.
- AR-301 blocks the shipped non-root dashboard service. AR-302 blocks ordinary
  ambient-umask/trusted-interpreter repeatability.
- AR-299 through AR-302 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, and release remain unauthorized.

## same-task-continuity

Build artifacts remain under `~/.agency-runtime/release-artifacts/`
`dist-987cee8ff01a4a16780eac15bb8120f828d4193d-linux-ar297`. The exact host
config remains at `~/.agency-runtime/configs/`
`ar297-987cee8ff01a4a16780eac15bb8120f828d4193d.yaml`;
the installed venv is under `~/.local/share/agency-runtime/venvs/987cee8f...`.
The redacted screenshot remains in the private evidence root. No
`agency-ar297-*` container remains; recreate only from retained images after a
new bounded package explicitly calls for live proof.

## next-bounded-work-package

1. Do not repeat this matrix unchanged. First repair or separately bound the
   additive embedding/recruiter failures that prevent a selected workforce and
   the AR-299/AR-300 child receipt.
2. Resolve AR-301 and AR-302 without weakening namespace, archive-mode, or
   interpreter trust. Create their trackers only after explicit authorization.
3. Build a new exact candidate, repeat the named gates, then create fresh
   dedicated containers and require one accepted, correlated ordinary Agency
   turn from each harness before reconsidering Linux GO.

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

- Keep registration, loading, canary, delivery, Store correlation, and model prose distinct. Never expose or persist a secret.
- Do not configure/call Jina, overwrite foreign policy, use an activation bypass, or touch the shared checkout.
- No tracker, push, PR, merge, tag, signing, publication, release, or hosted
  workflow action is authorized.
