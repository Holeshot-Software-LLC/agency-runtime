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
evidence_commit: 257fe30fe7325485dcbef30195451309bdba63af
minimum_ledger_commit: aa2830d0247489b8da3f0ef882c762955ea5d0fd
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-290 active recovery capsule

## checkpoint

- Work remains isolated in the linked worktree on
  `codex/ar290-guided-setup-readme`; the dirty shared `main` checkout was not
  switched, staged, cleaned, or committed.
- The branch contains AR-289 native Jina reranking, AR-290 guided setup and
  consumer documentation, AR-291 pointer isolation, AR-292 truthful degraded
  setup classification, AR-293 safe inference-profile config operations, and
  AR-294 expanded-regression fixture repair.
- Remote `main` at `a19a1669` was merged without rewriting history in
  `7487b31b`; current verification completed at the `aa2830d0` ledger. Re-fetch
  before publication and merge again without rewriting only if remote advanced.
- Tracker creation was attempted after the owner authorized push/merge, but the
  external approval boundary requires an explicit tracker authorization. No
  issue, label, PR, tag, release, or publication was created by that attempt.
- Context telemetry is below the fixed 50-percent threshold. Preserve this
  state in a substantive/ledger checkpoint before any live release evaluation.

## completed-evidence

- Current merged source passed the 1,127-test expanded configuration/security
  run with 21 skips, all 136 dashboard UI tests, full Ruff and documentation
  gates, every routing threshold, and all 160 decision-conformance mutations
  with a green baseline, zero survivors/invalid results, and unchanged source.
- Installed all-detected Windows setup registered Codex, Claude, ZCode, and the
  dashboard, reported no runtime drift, and passed deterministic smoke 8/8.
  Its exact exit 2 means attended activation remains, not mutation failure.
- `workforce.dense_recall_mode` is `additive`. The guarded installed CLI wrote
  Jina embedding and reranker profiles plus both recall routes using only the
  environment-variable name `JINA_API_KEY`; the credential is absent from YAML,
  argv, repository files, Store evidence, and displayed output.
- The supplied credential is stored in the current-user environment. One
  bounded Agency embedding call applied `jina-embeddings-v3` at exactly 1,024
  dimensions, and one bounded native rerank call applied
  `jina-reranker-v3.5` to an exact two-document permutation.
- `agency config validate` returns degraded 2 only for cold native-host loading
  and Codex hook trust. It prints the exact owner repair: start a fresh terminal
  Codex TUI, trust all eight Agency hooks, start a new session, then run
  `agency install --agent codex --verify-activation`.
- Reinstalling the candidate changed the owned dashboard launcher identity.
  The all-harness refresh cleared the one stale Claude projection, authoritative
  status reports `runtime_drift: null`, and the owned service is enabled,
  active, current, reachable, and open at `http://127.0.0.1:7810/`.

## exact-blocker

- Windows local completion still needs attended Codex hook trust and fresh
  Codex, Claude, and ZCode sessions before loaded/live claims. The owner will do
  that when physically present; doctor cannot approve host trust.
- The Linux machine can close Linux artifact, install, service, local-provider,
  and present-host evidence only. It cannot relabel itself Windows evidence or
  close absent-host, five-host Rule-4, signing, tracker, publication, tag, or
  release gates.
- AR-119 still lacks exact-candidate Rule-4 proof for all claimed hosts,
  benchmark-valid completed outcomes, and current-artifact host/OS evidence.
- AR-289 through AR-294 tracker mapping is blocked on explicit authorization.
  A tag or release is not authorized and would still be premature.

## same-task-continuity

Recheck remote `main`, the branch, and this capsule before publication. Keep
exact command exits, artifact hashes, installed identity, host-written evidence,
and Store correlation separate. Do not infer native delivery from model text,
copied plugins, or Store rows alone. A Linux continuation is a new operator
thread, so it must update canonical repository evidence before claiming gates.

## next-bounded-work-package

Paste this prompt into the Linux task after this branch has merged:

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
existing config. Set workforce.dense_recall_mode to additive. Configure explicit
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
