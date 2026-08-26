---
title: "AR-290 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [handoff, onboarding, install, configuration, dashboard, release]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/decisions/0172-compose-first-run-setup-from-guarded-owner-operations.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-290
branch: codex/ar290-guided-setup-readme
evidence_commit: 05291b0ecfdb1403b56ab9682d7fa04a0eb3648e
minimum_ledger_commit: b1211fe2ca3fe9a89cbc02e8313674a898ece419
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-290 active recovery capsule

## checkpoint

- Work remains isolated on `codex/ar290-guided-setup-readme`; the dirty shared `main` checkout was not switched, staged, cleaned, or committed.
- The branch contains locally complete AR-289 through AR-296. AR-296's exact install, authenticated visual proof, installed diagnostics, smoke, and repository gates pass.
- Remote `main` at `a19a1669` was merged without rewriting in `7487b31b`; verification completed at ledger `aa2830d0`. Re-fetch before publication and merge again only if remote advanced.
- Tracker creation still requires explicit tracker authorization. The rejected attempt created no issue, label, tag, release, or publication; draft PR #326 already exists for the branch.
- Pre-evaluation telemetry required a hard checkpoint. AR-296 was preserved at substantive `05291b0e` and ledger `b1211fe2` before its installed dashboard evaluation; end-of-package telemetry now reports 62.7 percent remaining and no additional hard checkpoint requirement.

## completed-evidence

- Merged source passed 1,127 expanded tests with 21 skips, 136 UI tests, Ruff/docs, 161 workflow contracts, all routing thresholds, and 160/160 decision mutations with unchanged source.
- AR-296 passes 138 UI tests and coverage at 96.92 percent lines, 86.74 branches, and 95.71 functions. It covers secret redaction, sanitized endpoints, strict/additive state, route/profile/thinking detail, judge roles, native-host ownership, and oversized-map refusal.
- The asset gate first failed at exactly 385,530 bytes. The audited 377 KiB ceiling leaves 518 bytes (0.13 percent); focused packaging and all documentation checks pass.
- Installed Windows setup registered Codex, Claude, ZCode, and dashboard, reported no drift, and passed deterministic smoke 8/8. Exit 2 preserves attended activation rather than mutation failure.
- Dense recall is `additive`; assurance is `strict`. The installed config names both Jina routes/profiles only through `JINA_API_KEY`, absent from YAML, argv, repository, Store evidence, and output.
- Bounded calls applied `jina-embeddings-v3` at 1,024 dimensions and `jina-reranker-v3.5` to an exact two-document permutation.
- Config validation degrades only for cold hosts and Codex hook trust, with the exact fresh-TUI/eight-hook/`--verify-activation` repair.
- Prior reinstall refreshed the owned dashboard launcher, cleared stale Claude projection, and left `runtime_drift: null`; service is enabled, active, current, reachable, and open on loopback port 7810.
- Source and installed dashboard assets hash-match exactly. Authenticated visual inspection shows 13 profiles and 11 routes, strict assurance, additive recall, both Jina roles, per-model thinking, active critic/security-review judge roles, and the Agency-staffing/native-host-spawn boundary without rendering a secret.
- Installed status exits 0 with direct generation 56 and Codex, Claude, and ZCode registered/enabled/current. Doctor exits degraded 2 only for Codex attended hook trust and cold loading proof. Deterministic installed smoke exits 0 with 8/8 checks passed.
- Final local gates pass: 839 fast-spine tests with 20 skips, 138 dashboard UI tests, Ruff, all documentation checks, routing evaluation, and 160/160 killed decision mutations with unchanged source.

## exact-blocker

- Windows still needs attended Codex hook trust and fresh Codex, Claude, and ZCode sessions before loaded/live claims; doctor cannot grant host trust.
- Linux can close only Linux artifact/install/service/local-provider/present-host evidence, not Windows, absent-host, five-host Rule-4, signing, tracker, tag, publication, or release gates.
- AR-119 still lacks all-host exact-candidate Rule-4 proof, benchmark-valid outcomes, and current artifact/OS evidence.
- AR-289 through AR-296 tracker mapping needs explicit authorization; tag/release remain premature and unauthorized. The draft PR cannot become a repository-complete main merge until tracker parity and required hosted checks are green.

## same-task-continuity

Recheck remote `main`, branch, and this capsule before publication. Keep command exits, artifact hashes, installed identity, host artifacts, and Store correlation separate; model text, copied plugins, and Store rows do not prove native delivery. Linux must update canonical evidence before claiming gates.

## next-bounded-work-package

Push the final recovery pair to draft PR #326, recheck its hosted checks and
remote `main`, and retain draft status while tracker parity is unauthorized.
After tracker authorization, create/link the missing issues and labels, run the
strict tracker gates, then merge only after the PR and repository policies are
green. No tag, signing, package publication, or release creation is authorized.

After this branch is merged to `main`, paste this prompt into the Linux task:

~~~text
You are continuing Agency Runtime release verification on a Linux machine that
has local models. Pull origin/main, record the exact clean commit SHA, and read
AGENTS.md, README.md, docs/RELEASE_CHECKLIST.md, the AR-07 release issue, the
AR-119 issue/matrix/handoff, and the AR-290 handoff before changing anything.

Do not configure or use Jina on this box. Inventory the actual Linux OS/Python,
installed harnesses, dashboard/service manager, local inference runtime, model
IDs, embedding dimensions, and reranker capability. If endpoint, model, width,
or harness choices are unknown, interview me before mutation. Prefer explicit
Ollama/local profiles; use LiteLLM only when it is actually installed and
intended. Keep credentials in environment variables or hidden prompts, never
argv, YAML, logs, evidence, or commits.

Install the exact current main candidate through the documented consumer path.
Run agency setup for detected harnesses and the dashboard, preserving valid
existing config. Set workforce.mode to strict and workforce.dense_recall_mode
to additive. Configure explicit
workforce.recall.embedding and workforce.recall.reranker routes for the verified
local models. Use a native reranker only if its adapter is supported; otherwise
use a structured text reranker. Run agency config validate, agency doctor --json,
agency status --json, dashboard service status, and deterministic agency smoke
--all. Capture native exit codes and distinguish pass, degraded, and hard fail.

Build the clean wheel and sdist from the exact candidate into an owner-private
artifact directory. Record SHA-256 hashes, run strict package metadata checks
and pip check, install the exact artifact in a fresh environment, run agency
version --json, then repeat the applicable Linux setup/config/doctor/status/
smoke/dashboard-service checks. Exercise the local embedding and reranker
through Agency's bounded provider seams and record only content-free provider,
requested/actual model, dimensions/count, status, and latency receipts.

Open the authenticated dashboard Settings view and verify that its effective
inference topology matches the redacted config: strict assurance, additive
recall, global and harness routes/defaults, local embedding/reranker profiles,
models, thinking levels, capabilities, dimensions, sanitized endpoints, and
credential indirection. Confirm that it labels critic/security-review routes as
the active judge roles and states that Agency selects staffing while the native
harness owns child spawning/execution. Capture no bearer or credential.

Run the repository's named fast Python spine from AGENTS.md, focused Linux
service/installer/config/provider tests, dashboard Node tests, full Ruff lint
and format checks, docs metadata/policy/worklog/verify checks, routing eval,
decision-conformance eval, release-hygiene checks, and git diff --check. Do not
dispatch optional exhaustive hosted matrices unless I explicitly authorize it.

For every installed harness, report discovery, registration, enablement,
loading, and live canary as separate facts. A Rule-4 claim requires the exact
inference-selected card hashes in a host-written pre-speech child artifact plus
correlated Store evidence. Do not count provider prose, plugin copies, or Store
staffing rows as native delivery. Do not run paid/live child canaries, change
external trackers, push, merge, tag, sign, publish, or create a release without
explicit authorization in this Linux thread.

Update the canonical roadmap issue, AR-119 matrix/handoff, AR-290 handoff, and
release checklist with dated Linux evidence, exact candidate/artifact hashes,
command exits, observed hosts, and unresolved gates. Create the required clean
substantive/ledger checkpoint. Finish with a GO/NO-GO scoped only to Linux and
an explicit list of gates Linux could not close. Never claim the whole release
ready unless every canonical checklist item has current authority-backed proof.
~~~

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused configuration/provider/setup/security tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Never expose the Jina credential. The owner intends to rotate it later.
- Do not touch the shared dirty `main` checkout or the separate AR-289 worktree.
- Preserve exact historical commit subjects and non-rewriting worklog SHAs.
- No deterministic smoke, dashboard status, or cold inventory is live-host or
  release proof. Missing lifecycle evidence remains unknown, never healthy.
- No tag, signing, package publication, or release creation is authorized.
