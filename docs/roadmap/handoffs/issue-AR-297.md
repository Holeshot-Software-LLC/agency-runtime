---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [handoff, containers, unattended, codex, claude, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
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
evidence_commit: c395bf4a6a7610a4a4084da783733fa308b9532c
minimum_ledger_commit: ff61aed838df00e0c337644b5ebf7481fb2082e3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- PR #326 is merged. Linux work is isolated from clean `origin/main` commit
  `0a23983aa7b99ec27ef18b1a950f6a0327961f72` on
  `codex/ar297-production-container-live-evidence`; the shared checkout and its
  untracked patch were not changed.
- Telemetry reported 32.8 percent remaining before the first live evaluation,
  requiring the first clean checkpoint at `c395bf4a` and ledger `ff61aed8`.
  It later reported 39.6 percent after the approved generation A/B, requiring
  the current local-judge implementation checkpoint before further live calls.
- Tracker #335 remains linked and open. No tracker, push, merge, tag, signing,
  publication, release, or optional hosted workflow action is authorized.

## completed-evidence

- The prior Windows source/install evidence remains as recorded in AR-297 and
  AR-298; it is not relabelled Linux or current live-container proof.
- Linux inventory: Ubuntu 24.04.4 LTS, kernel 7.0.0-29, Python 3.12.3,
  Docker 29.7.2, and systemd 255 with a running user manager.
- Harness inventory: Codex 0.149.1 with ChatGPT auth; Claude Code 2.1.239 with
  first-party subscription auth; Hermes 0.20.4; OpenClaw 2026.7.1-2 with its
  systemd-user gateway reachable.
- Local inference inventory: Ollama 0.30.0 exposes `qwen3.5:9b`, `qwen3.5:2b`,
  and `qwen3-embedding` with observed embedding width 4096. LiteLLM is reachable
  on loopback and maps aliases `qwen3.5-9b`, `qwen3.5-2b`, and
  `qwen3-embedding` to those local models. Jina was neither configured nor called.
- The owner-approved revised exact config SHA-256 is
  `8a67099de98bc0bae91bdfdaab3f8bfbc1134b904e72bd07eeb578601b5acb74`.
  It uses strict assurance/independence, additive recall, direct Ollama text
  routes, unchanged LiteLLM embedding at exactly 4096 dimensions, and a free
  local no-thinking Mistral child judge. No secret value is present.
- Direct schema validation exited 0. Credential-aware
  `agency config validate` exited 2 only because cold discovered hosts were not
  yet registered. No model or host canary was invoked before this checkpoint.
- Exact planner A/B evidence selected `qwen3-14b-abliterated:latest`: exit 0,
  23,774 ms, six units, no injection echo, and zero policy violations. The 9B
  challenger exited 1 after semantic validation. Synthetic request/system and
  response hashes are preserved in the private evidence root.
- `mistral-small3.2:24b` was downloaded with explicit approval; Ollama reports
  digest `5a408ab55df5`, 24.0B Q4_K_M, 131,072 context, and Apache 2.0. AR-299 and
  ADR-0174 add only safe named Ollama child-judge profiles. Focused tests pass
  13/13 with warnings as errors.
- Exact wheel/sdist verification is complete: wheel SHA-256
  `896200663b422978702333bde13f5a5833bc0d4642f9efd17c9e90e7f3827313`
  and sdist SHA-256
  `9f52bcbd0a3bfeb4f3e3109721d19cf45e789fcbbb31ca080ef0fa1e985381b9`.

## exact-blocker

- Critic, embedding, reranker, and local-child-judge routes still need bounded
  post-revision live receipts. The planner route passes.
- Five exact-artifact images and clean running containers exist with harness
  prerequisites proven, but no `agency install --production-container` or
  later ordinary unattended invocation has run.
- AR-298 still needs packaged/Agency-hired/historical CLI prompt proof and an
  installed authenticated owner-detail visual check.
- Fresh-environment installs, repository gates, signing, tag, publication, and
  complete release gates remain open or unauthorized. Artifact build and
  independent verification are complete; the documented command's ambient
  group-writable umask failure remains an explicit usability finding.
- AR-299 tracker creation is required by governance but prohibited by the
  active task; no outward write was attempted.

## same-task-continuity

Use `/tmp/agency-runtime-ar297.WQUbF2` and the private evidence root recorded in
the active session. Keep discovery, registration, enablement, loading, canary,
host-written delivery, Store correlation, and model prose separate. Inject
credentials only by inherited environment or private runtime mounts; never
print, persist in YAML, bake into images, or copy into evidence.

## next-bounded-work-package

1. Exercise critic, embedding, reranker, and local-child-judge routes and
   preserve sanitized requested/actual receipts plus exact exits.
2. Install the exact candidate independently in the four clean harness
   containers; prove later ordinary unattended loading and bounded turns.
3. Use the fifth isolated systemd container for authenticated dashboard and
   complete workforce-prompt proof, then install/prove the host runtime.
4. Run every named repository and applicable release gate.
5. Update AR-297/AR-298/AR-290/AR-299, this capsule, and release checklist;
   create the final substantive/ledger pair, tear down containers, and issue
   the Linux-scoped verdict.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
agency config validate
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused AR-297 and AR-298 tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
git diff --check
~~~

## constraints
- Do not configure or call Jina.
- Do not touch a shared checkout or overwrite foreign system policy.
- No deterministic smoke, dashboard status, copied plugin, Store row, or cold
  inventory is live-host or host-delivery proof.
- No tracker, push, merge, tag, signing, package publication, or release action
  is authorized merely by this handoff.
