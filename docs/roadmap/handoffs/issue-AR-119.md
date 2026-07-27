---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-27
tags: [handoff, routing, workforce, evaluation, recovery, production-readiness]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/issue-AR-171-redact-dashboard-lifecycle-reasons.md
  - docs/roadmap/issue-AR-172-make-roster-pages-snapshot-consistent.md
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 3e14f74041865bf93444d290197fb7062ea3ec31
minimum_ledger_commit: 874fb2a03f57d62da46c55cdd3507e01a2b8c589
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Clean local recovery pair: substantive `3e14f74`, ledger `874fb2a`.
- Branch is `main`, locally ahead of `origin/main`. No push, PR, tag, release,
  publication, hosted dispatch, tracker mutation, or repository-setting change
  was authorized.
- The user-owned untracked
  `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged and was
  excluded from every commit.
- AR-143, AR-156, and AR-160 through AR-175 have governed local implementations
  or explicit external gates. This checkpoint is not a production approval.

## completed-evidence

- AR-143: exact roster rollback is the first positive persistent mutation. It
  prepares complete config/database, generation, current/target revision,
  activation-authority, and workforce/effective-contract identity; invokes the
  fixed Windows 11 x64 app-owned consent helper; then revalidates inside
  `BEGIN IMMEDIATE` before commit. All other mutations/platforms remain blocked.
- AR-160/161: portable and `win_amd64` wheel profiles, one sdist, structural PE
  rejection, exact native/source/provenance/license hashes, and three-artifact
  parity are implemented. Current bytes are explicitly unsigned review inputs.
- AR-163: signed remediation history requires current candidate/download/audit/
  active-basis eligibility. Stale authority reopens the original queue, counts
  are disjoint, and UI pagination is bound to an exact remediation revision.
- AR-164: inert repository-ancestor discovery excludes hostile sibling `PATH`
  executables across direct CLI, delegation, first Git, installer, dashboard,
  and smoke launch surfaces before identity freeze/revalidation.
- AR-165/166: dependency-review fallback accepts only an exact authenticated
  capability boundary; dashboard persistent controls stay read-only, safe
  request IDs are operator-visible, and runtime-capture disclosure is precise.
- AR-170 through AR-173: browser headers and response identity fail closed;
  worker evidence is complete; lifecycle reasons expose presence only; roster
  pages bind Store and configuration revisions; public pages use one bounded
  SQL snapshot; control recaptures Store-generation churn; Route Lab carries
  one exact trace through observation correlation.
- AR-174: trusted-base classification selects a five-runner primary lane only
  for complete regular `docs/**/*.md` pull-request deltas. Linux and Windows
  artifacts and artifact parity remain mandatory. The 13-to-5 allocation
  change is structural local proof, not hosted savings evidence.
- AR-175: the unsupported non-atomic control fallback is removed. The browser
  requires `agency.dashboard.control.v1`, retains last-good state on failure,
  and cannot fan out to legacy endpoints. Ten shipped assets total 257,620
  bytes, 5,547 bytes below the unchanged release ceiling.
- CI retains every exact surface while pairing four coverage and six
  compatibility sessions and preflighting CodeQL once. Historical PR topology
  moves from 24 to 13 jobs and models 119.12 raw runner-minutes at approximately
  13.63 to 22.85. This is unmeasured projection, not a savings claim.
- Current bounded checks: 385 integrated dashboard/workforce/roster/CI/release
  tests passed with 4 platform skips; 105 UI tests; 435-document verification;
  focused Ruff; strict offline workflow security; Bandit on modified Python;
  independent final-delta review with no remaining actionable finding.

## exact-blocker

- AR-161 needs owner publisher identity, authorized legal/license disposition,
  protected signing/timestamp service, exact signed candidate verification, and
  an attended Windows Hello success-and-denial canary. The remote session cannot
  supply human presence or invent publisher authority.
- GitHub Actions billing/spending rejects new jobs before steps run. PR/main
  speed, cross-OS artifact, CodeQL, dependency-review, and portability behavior
  therefore lack current hosted measurement.
- `main` has neither authorized branch protection nor a repository ruleset.
  Applying or requiring hosted contexts is an outward setting change owned by
  AR-159.
- Normal-profile Codex hook trust requires the supported terminal-TUI user
  review. Do not bypass it while the owner is remote.
- AR-119/125 still require a benchmark-valid complete outcome corpus. Malformed,
  timed-out, no-response, and unknown upstream arms remain invalid, never losses.
- Tracker creation/closure for AR-160 through AR-175 and other outward writes
  remain pending owner authorization.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. Continue
the same persistent goal from the clean pair through normal compaction.

## next-bounded-work-package

1. Run the current-head warning-strict repository suite once, then exact
   coverage, performance, routing, security, docs, UI, and packaging gates.
2. Build from clean detached source on Windows and WSL/Linux; require one exact
   three-artifact set and byte-identical sdists/shared wheel payloads.
3. Install Windows wheel/sdist and Linux portable wheel/sdist into fresh Python
   runtimes; run distribution, CLI, smoke, and no-PE/profile checks.
4. Reinstall the reviewed Codex integration from the verified artifact and
   dogfood routing, staffing, contractors, specialist/model receipts, MCP, and
   host maturity without claiming manual subagents as Agency-selected.
5. Run final installed dashboard desktop/mobile/accessibility/console QA and
   update the production verdict. Keep external authorization, presence,
   hosted, tracker, and benchmark-valid corpus gates explicit.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m scripts.run_parallel_change_loop
python -m pytest tests -q -W error
python -m pytest tests -q -W error -p no:cacheprovider -m performance
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/verify_docs.py
python -m scripts.verify_distribution <clean-artifact-directory> --artifact-set release --expected-commit 3e14f74041865bf93444d290197fb7062ea3ec31
git diff --check
~~~

## constraints

- Telemetry immediately before every live evaluation, benchmark corpus, or
  attended canary; create/reuse a clean checkpoint when at or below 50 percent.
- Preserve fixed 15,000 ms cold and one-call fast AR-119 controls. Never weaken
  coverage, parser, authority, timing, artifact, or asset thresholds after data.
- Do not claim Agency superiority, activation, specialist loading, model
  receipt, delegation, contractor hire, or host canary without exact evidence.
- Do not alter unknown/unattested paths or the user draft.
- No push, PR, hosted dispatch, publication, tracker mutation, tag, release,
  trust-store action, or repository setting change without authorization.
