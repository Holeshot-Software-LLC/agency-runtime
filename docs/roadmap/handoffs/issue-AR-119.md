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
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 77ec4f62e001aae07f8a52437749d695397437bb
minimum_ledger_commit: af892aec694b8ca912fa78c1d55bc33c15a443cf
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Exact locally tested code/ledger pair: `9aa317c`/`5681a3f`.
- Branch `main` resolves to `5681a3f`; `origin/main` remains `880a5ce` because
  no new push was authorized. Earlier automatic CI and CodeQL were rejected before any
  step or runner started by the account billing/spending gate. No manual or
  exhaustive workflow was dispatched.
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
- The exact installed-wheel dashboard authenticated and rendered all seven
  sections. A 390 px live pass exposed a vertical mobile heading basis; source
  commit `9aa317c` fixes it with 106 green UI tests and clean desktop/mobile
  browser rechecks. The exact next package still needs that visual rerun. Both
  temporary listeners are stopped.
- The named fast production spine passes 521 tests with 5 platform skips in
  74.94 seconds at pushed head `880a5ce`. The new exact candidate passes 522
  with 5 skips in 75.89 seconds; all 106 dashboard UI tests, Ruff, formatting,
  docs, focused high-severity Bandit, and every routing-evaluation gate pass.
- ADR-0104's exact existing-install Codex refresh passes attended Windows Hello,
  atomic publication, native remove/add, and postcondition proof. New install ID
  is `7761d792-3dc3-4c92-8084-5cd524c63103`; bundle is `0c3696e1...084f3`;
  native version is `0.1.0+codex.a106953cb0c7`; the exact prior backup remains.
- AR-179 binds named standards to typed review. Focused tests and fresh live
  routing prove a DO-178C gap now abstains rather than forming a false team.
- One-shot application evaluation is deferred to post-production AR-178 and is
  not an AR-119/125 release gate.
- AR-180's local candidate now deterministically plans one child and proves the
  exact Codex JSONL tool call, native-hook grant provenance, child lifecycle,
  single consumption, model receipt, delegation, accepted finalization, header,
  and install-bound attestation. Ambiguous/unmatched native calls remain Codex
  scheduler decisions. Focused suites pass 33 canary/output tests, 11 schema/
  provenance migrations, dashboard API checks, and all 106 UI tests.
- Expired dashboard host inspection now neutralizes canary and maturity claims;
  the Codex card labels verified evidence as the last successful activation
  proof and renders its full content-free fingerprint without an execute button.
- Canonical private Windows build for exact head `af892ae` produced wheel
  `4cf51159...a53a8` (7,465,173 bytes) and sdist `daabe206...297c`
  (18,136,468 bytes). Independent Windows artifact verification and a fresh
  Python 3.13 wheel install passed.
- Running the source installer from the permissive workspace correctly failed
  before mutation. The same exact installed wheel from a private environment
  passed Windows operator presence and refreshed Codex in 182.5 seconds. The
  previous bundle remains at backup `20260727T183215.488516Z`; the new plugin is
  `0.1.0+codex.92db70112a1a`, bundle `e0c19b9d...ea387`, install ID
  `fe76121b-9911-497d-b853-685d39b0e830`.
- Exactly one current-profile canary then completed in 36.9 seconds and failed
  truthfully with `route_not_found`: zero route, header, collaboration calls,
  activations, delegations, finalizations, runs, or traces. Evidence SHA-256 is
  `b5bb99e1...4750`; no attestation persisted and no retry ran.

## exact-blocker

- Generic and missing-host installation remain unavailable, but exact existing-
  install Codex refresh is now a positive prepared transaction. The exact new
  AR-180 bundle is registered and enabled, but its only current-profile canary
  produced no hook event. Hook approval happened before the refresh; renewed
  terminal-TUI approval for this exact bundle is the next human security gate.
  Codex has no supported trust-state read API, so this remains a bounded
  inference from the evidence, not a claimed diagnosis. No preexisting
  attestation may satisfy the next recheck.
- AR-161 needs owner publisher identity, authorized legal/license disposition,
  protected signing/timestamp service, signed-delivery verification, and an
  attended Windows Hello success-and-denial canary. The remote session cannot
  supply human presence or invent publisher authority.
- GitHub Actions billing/spending rejects new jobs before steps run. PR/main
  speed, CodeQL, dependency review, and hosted portability lack current proof.
- `main` has neither authorized branch protection nor a repository ruleset.
  Applying required contexts is an outward setting change owned by AR-159.
- Five installed-host canaries remain open, including the Codex recheck after
  exact-bundle terminal-TUI trust.
- AR-119/125 still require a benchmark-valid complete outcome corpus. Malformed,
  timed-out, no-response, and unknown upstream arms remain invalid, never losses.
- Tracker creation/closure for AR-160 through AR-176 and other outward writes
  remain pending owner authorization.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. Continue
the same persistent goal from the clean pair through normal compaction.

## next-bounded-work-package

1. When the operator is present, approve the exact refreshed Agency hook set in
   the Codex terminal TUI. Then run one bounded current-profile canary without a
   hook-trust bypass and preserve its exact evidence. Do not retry before that
   state change.
2. Add signed-delivery provenance and independent Windows default-policy
   verification. Publisher/legal/signing inputs remain owner/external gates.
3. Design fresh missing-host bootstrap separately if it is a claimed v1 surface.
4. Complete the other host canaries and benchmark-valid AR-119/125 outcome trials.
5. Run exhaustive coverage/compatibility only on explicit owner request.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
python scripts/verify_docs.py
python -m scripts.verify_distribution <candidate-directory> --expected-commit af892aec694b8ca912fa78c1d55bc33c15a443cf
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
