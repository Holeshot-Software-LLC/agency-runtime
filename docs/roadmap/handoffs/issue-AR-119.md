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
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
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
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 29da6eca2b0dd73b37a91e6bfdb29881face5d56
minimum_ledger_commit: 29da6eca2b0dd73b37a91e6bfdb29881face5d56
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Exact tested release candidate: `29da6eca2b0dd73b37a91e6bfdb29881face5d56`.
- Branch is `main`, locally ahead of `origin/main`. This package performed no
  push, PR, tag, release, publication, hosted dispatch, tracker mutation, or
  repository-setting change.
- The user-owned untracked
  `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged and was
  excluded from every commit.
- Production remains **NO-GO**. The installed-artifact dashboard is a
  conditional demo **GO** only as a truthful read-only/observability surface.

## completed-evidence

- Deep security/optimization/traceability/UI review is complete. No Critical or
  High finding remains open in the reviewed source; repaired lower findings
  have cross-layer regressions. The older warning-strict corpus passed 8,021
  tests with 61 skips and 1 expected failure in 32:11.
- Exhaustive coverage and six-version compatibility are manual-only
  `workflow_dispatch` work. They do not run on PR/push and will not be run
  locally unless the owner explicitly asks. No hosted Actions ran here.
- Exact candidate `29da6eca` clean Windows artifacts pass strict metadata,
  independent verification, and fresh Python 3.10 wheel/sdist install smoke.
- The clean Linux producer emits the portable wheel and a byte-identical sdist;
  fresh Python 3.12 wheel/sdist installs pass. The portable wheel contains no
  executable or PE. Linux Node absence skipped only the OpenClaw syntax subcheck.
- The merged set contains exactly portable wheel `fc5e85a8...5618`, Windows
  wheel `eb8eb4b...f189`, and sdist `d95bb493...fea8`. Strict Twine and the
  independent `--artifact-set release` verifier pass.
- The freshly installed Windows wheel dashboard authenticated and rendered all
  seven sections, Refresh advanced sync time, and browser console warnings/
  errors were empty. Route Lab truthfully stayed disabled without a verified
  enabled host. The test listener is stopped.
- AR-179 binds named standards to typed review. Focused tests and fresh live
  routing prove a DO-178C gap now abstains rather than forming a false team.
- One-shot application evaluation is deferred to post-production AR-178 and is
  not an AR-119/125 release gate.

## exact-blocker

- Generic `agency install` has no prepared, frozen, replay-safe transaction or
  compensation contract. AR-143's only genuine positive mutation is exact
  prepared roster rollback; every generic install correctly remains blocked.
- AR-161 needs owner publisher identity, authorized legal/license disposition,
  protected signing/timestamp service, signed-delivery verification, and an
  attended Windows Hello success-and-denial canary. The remote session cannot
  supply human presence or invent publisher authority.
- GitHub Actions billing/spending rejects new jobs before steps run. PR/main
  speed, CodeQL, dependency review, and hosted portability lack current proof.
- `main` has neither authorized branch protection nor a repository ruleset.
  Applying required contexts is an outward setting change owned by AR-159.
- Normal-profile Codex hook trust requires the supported terminal-TUI user
  review. Five installed-host canaries remain open. Do not bypass trust while
  the owner is remote.
- AR-119/125 still require a benchmark-valid complete outcome corpus. Malformed,
  timed-out, no-response, and unknown upstream arms remain invalid, never losses.
- Tracker creation/closure for AR-160 through AR-176 and other outward writes
  remain pending owner authorization.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. Continue
the same persistent goal from the clean pair through normal compaction.

## next-bounded-work-package

1. Under AR-143, add a release-disabled prepared Codex-install coordinator that
   freezes Store/config generations, exact target/bundle/executable identities,
   expected deltas, and recovery consequences; revalidate before each owner
   mutation and prove drift, replay, substitution, and partial-failure behavior.
2. Add an enumerated `install.codex.v1` native protocol only after the prepared
   transaction exists. Keep it unsigned and release-disabled pending AR-161.
3. Add signed-delivery provenance and independent Windows default-policy
   verification. Publisher/legal/signing inputs remain owner/external gates.
4. With those gates satisfied, perform the attended normal-profile Codex install
   and five-host canaries, then the benchmark-valid AR-119/125 outcome trials.
5. Run exhaustive coverage/compatibility only on explicit owner request.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
python scripts/verify_docs.py
python -m scripts.verify_distribution <three-artifact-directory> --artifact-set release --expected-commit 29da6eca2b0dd73b37a91e6bfdb29881face5d56
git diff --check
# Owner-requested manual integration only:
python -m pytest tests -q -W error
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
