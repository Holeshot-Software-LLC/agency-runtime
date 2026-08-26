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
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 3023f0557e72911c4d42be53dccca3369b05ca8e
minimum_ledger_commit: a5cd7cae5f5874d50c75cb0c0a3d680e2195ab15
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
  requiring this clean checkpoint. Implementation remains preserved at
  `3023f055` and its ledger at `a5cd7cae`.
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
- Owner-approved exact config SHA-256 is
  `22eb6507e7eb5b4420196cb61c09121a66266537f3ead9e521ab51b8412657e4`.
  It uses strict assurance, additive recall, explicit local generation,
  critic/judge, embedding, and text-reranker profiles, exact 4096 dimensions,
  credential name `LITELLM_API_KEY`, and a separate Codex subscription child
  judge. No secret value is present in the config.
- Direct schema validation exited 0. Credential-aware
  `agency config validate` exited 2 only because cold discovered hosts were not
  yet registered. No model or host canary was invoked before this checkpoint.

## exact-blocker

- Local model routes still need bounded live receipts before container work.
- Clean Codex, Claude Code, Hermes, and OpenClaw production-container installs
  and later ordinary unattended invocations remain unrun.
- AR-298 still needs packaged/Agency-hired/historical CLI prompt proof and an
  installed authenticated owner-detail visual check.
- Wheel/sdist, fresh-environment, repository gates, signing, tag, publication,
  and complete release gates remain open or unauthorized.

## same-task-continuity

Use `/tmp/agency-runtime-ar297.WQUbF2` and the private evidence root recorded in
the active session. Keep discovery, registration, enablement, loading, canary,
host-written delivery, Store correlation, and model prose separate. Inject
credentials only by inherited environment or private runtime mounts; never
print, persist in YAML, bake into images, or copy into evidence.

## next-bounded-work-package

1. Exercise the four approved local routes and preserve sanitized requested/
   actual model receipts plus exact exits.
2. Build and verify wheel/sdist from the exact candidate.
3. Create four clean root containers and prove production install plus later
   ordinary unattended loading for Codex, Claude Code, Hermes, and OpenClaw.
4. Use a fifth isolated systemd container for authenticated dashboard and
   workforce-prompt proof, then run the named repository gates.
5. Update AR-297/AR-298/AR-290, this capsule, and release checklist; create the
   final substantive/ledger pair and issue the Linux-scoped verdict.

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
