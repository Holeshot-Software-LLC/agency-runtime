---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-25
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
branch: codex/ar290-guided-setup-readme
evidence_commit: 3023f0557e72911c4d42be53dccca3369b05ca8e
minimum_ledger_commit: a5cd7cae5f5874d50c75cb0c0a3d680e2195ab15
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-297 active recovery capsule

## checkpoint

- Work is isolated on `codex/ar290-guided-setup-readme`; the shared `main`
  checkout was not switched, staged, cleaned, or committed.
- Implementation is preserved at `3023f055` and its ledger at `a5cd7cae`.
  Draft PR #326 is the publication surface; tracker creation still requires
  explicit tracker authorization.
- Windows installation uses strict assurance and additive dense recall. This
  attended workstation correctly reports Codex managed policy absent and
  attended hook trust unverified; no system policy was installed or simulated.
- The Jina key was consumed only through environment indirection and was not
  written to config, repository, Store evidence, argv, or this capsule. The
  owner will rotate it.

## completed-evidence

- `agency install --production-container --config <path>` now binds one exact
  validated config and host scope through Store, native payloads, optional
  dashboard service, and activation evidence.
- Codex production-container mode installs owned system managed-hook policy,
  refuses foreign or modified policy, invalidates stale activation proof before
  mutation, and requires a fresh normal-invocation managed-policy canary.
- Store, CLI, and authenticated dashboard backend expose complete current or
  historical workforce prompts across every standing, with exact lineage,
  version, content hash, truncation, and stored-definition provenance. They do
  not claim runtime delivery.
- The installed Windows runtime hash-matches source for the dashboard renderer,
  managed-policy module, and workforce Store reader. Installed prompt lookup
  returned schema `agency.workforce.prompt.v1`, active standing, an immutable
  version, 160 bounded body characters of 2,791, a content hash, exit 0, and
  `runtime_delivery_proof=not_asserted`.
- Installed `agency install --all --json` refreshed Codex, Claude, ZCode, and
  dashboard projections. Its only incomplete condition is attended Codex hook
  trust; OpenClaw and Hermes are absent and were skipped. Dashboard service is
  owned, current, enabled, active, reachable, and opened on loopback.
- Installed deterministic smoke passes 8/8. Status shows no runtime drift;
  doctor is degraded only for cold host loading and attended Codex trust.
- Repository verification passes: 840 fast-spine tests with 20 skips, 138
  dashboard UI tests, Ruff and documentation gates, all routing thresholds,
  and the curated decision-conformance evaluator with a passing baseline,
  every mutation killed, and source unchanged.
- The installed dashboard renderer is exact, but the controllable authenticated
  tab expired before the new prompt/policy surfaces could be visually checked.
  Source UI tests are proof of behavior, not installed authenticated visual proof.

## exact-blocker

- A clean Linux Codex container must prove owned `/etc` policy installation,
  a no-bypass activation canary, persisted current attestation, and a later
  ordinary Conveyor-equivalent invocation that loads Agency unattended.
- Clean Linux Claude Code and OpenClaw containers must separately prove native
  registration, enablement, loading, and one bounded Agency turn.
- AR-298 still needs an installed authenticated owner-detail visual check.
- Exact wheel/sdist, fresh-environment, hosted-check, tracker, signing, tag,
  publication, and release gates remain open or unauthorized.

## same-task-continuity

Fetch before publication and compare `origin/main` with this branch. Preserve
discovery, registration, enablement, loading, live canary, host-written prompt
delivery, Store evidence, and model prose as separate claims. Never convert an
absent host or failed pre-allocation launch into runtime evidence.

## next-bounded-work-package
After this branch is pushed, paste the following prompt into the Linux task:

~~~text
Continue Agency Runtime release verification on this Linux machine. Pull the
exact merge candidate: use origin/main if PR #326 is merged; otherwise fetch
and check out origin/codex/ar290-guided-setup-readme. Record the clean commit
SHA. Read AGENTS.md, README.md, docs/RELEASE_CHECKLIST.md,
docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md,
docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md,
docs/roadmap/handoffs/issue-AR-297.md, and ADR-0173 before mutation.

This box has local models. Do not configure or call Jina. Inventory the exact
Linux distribution, Python, container runtime, Codex/Claude Code/OpenClaw
versions and auth, local inference server, model IDs, embedding dimensions,
reranker capability, LiteLLM availability, and service manager. If any model,
dimension, endpoint, credential-variable name, or harness choice is unknown,
interview me before mutation. Keep secrets in environment variables or hidden
input, never YAML, argv, logs, evidence, or commits.

Create a valid exact config outside the repository with workforce.mode=strict,
workforce.dense_recall_mode=additive, explicit local generation/judge/embedding/
reranker routes, correct capabilities, thinking levels, and verified dimensions.
Run agency config validate. In clean dedicated root containers, install the
exact candidate and run, separately for Codex, Claude Code, and OpenClaw:
agency install --production-container --config <absolute-config> --agent
<host> --no-dashboard --json. Inject harness auth and model environment before
installation. Do not use an activation bypass or attended trust prompt.

For Codex require exit 0, managed_hook_policy.status=current, trust mode
managed_policy, all eight owned managed events, a persisted current activation
attestation, and no bypass. Then start a new ordinary Codex process using the
same argv shape Conveyor will use and prove Agency loads unattended. For Claude
Code and OpenClaw, start a new ordinary process after install and prove native
registration, enablement, loading, and one bounded Agency turn. Report each
lifecycle stage separately. A copied plugin, Store row, or model statement is
not host delivery; prompt/delegation delivery needs the correlated host-written
artifact required by the repository contracts.

Verify `agency workforce prompt` for a packaged active worker, an Agency-hired
worker, and a retired or exact historical version. With the dashboard enabled
in a separate clean install, open its authenticated owner view and verify full
prompt provenance plus the real strict/additive topology, generation/judge/
embedding/reranker providers, requested and actual models, thinking levels,
capabilities, dimensions, sanitized endpoints, credential indirection, and the
Agency-selection/native-host-execution boundary. Capture no bearer or secret.

Build wheel and sdist from the exact clean candidate, record SHA-256 hashes,
check metadata and dependencies, install the exact artifact in a fresh venv,
and repeat applicable config/install/status/doctor/smoke checks. Run focused
Linux installer/provider/service tests, the named fast Python spine, 138-or-more
dashboard Node tests, full Ruff lint/format checks, docs checks, routing eval,
decision-conformance through the development interpreter, release hygiene, and
git diff --check. Do not dispatch optional exhaustive hosted matrices.

Update the canonical AR-297/AR-298 issues, this capsule, AR-290 where affected,
and the release checklist with dated command exits, exact hashes, observed host
artifacts, Store correlations, and unresolved gates. Make the required clean
substantive/ledger checkpoint. Do not create trackers, push, merge, tag, sign,
publish, create a release, or run paid external canaries without explicit
authorization in that Linux task. End with a Linux-scoped GO/NO-GO and list
every release gate this machine could not close.
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
python -m pytest <focused AR-297 and AR-298 tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
git diff --check
~~~

## constraints
- Never expose the Jina credential; rotate it before broad release use.
- Do not touch a shared checkout or overwrite foreign system policy.
- No deterministic smoke, dashboard status, copied plugin, Store row, or cold
  inventory is live-host or host-delivery proof.
- No tracker, push, merge, tag, signing, package publication, or release action
  is authorized merely by this handoff.
