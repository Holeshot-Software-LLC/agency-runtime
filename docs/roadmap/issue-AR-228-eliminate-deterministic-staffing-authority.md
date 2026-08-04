---
title: "AR-228: Fail open with an honest header when no specialist is selected"
status: in_progress
category: roadmap
created: 2026-08-03
updated: 2026-08-03
tags: [bug, inference, routing, workforce, product, failure]
related:
  - docs/decisions/0152-fail-open-with-honest-header-when-no-specialist.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - agency_runtime/core/preflight.py
  - agency_runtime/adapters/hooks.py
  - agency_runtime/cli/roster_commands.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-228
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/237
depends_on: []
blocks: [AR-119]
---

# AR-228: Fail open with an honest header when no specialist is selected

## Problem

ADR-0122 mandated that a substantive turn with no accepted specialist must block
the parent model terminally. The intent was honesty, but in practice the
boundary bricked the host: any staffing hiccup (provider timeout, plan-policy
veto, recruiter abstention, verifier rejection) produced a `decision: block`
that locked the operator out of the main agent. The block message ("Restore
inference or staffing") pointed at inference even when the provider was
configured and successfully called, because the real reason was discarded before
the message was composed.

A prior framing of this issue alleged that "deterministic staffing authority"
remained on the live production path after ADR-0118. Source audit disproved
that: the deterministic staffing oracle (`fallback.py`) is already quarantined
off production by its own docstring, ADR-0118, and the keystone test
`test_production_staffing_entrypoints_have_no_deterministic_decider_dependency`.
The live path (`plan_and_staff_workforce`) is already inference-owned and
fail-closed. The real product defect was the hard block plus the misleading
message, not a surviving deterministic staffing path.

## Current state

The fail-open change is implemented on `codex/ar-228-fail-open-honest-header`
off merged main `c01f178`:

- `_require_substantive_specialist` raises `SubstantiveSpecialistUnavailable`
  carrying the exact persisted cause (`status`, `source`, `inference_mode`, and
  the joined `error`/`inference_failures` reason codes).
- `run_preflight` catches it, persists the failure receipt, and returns an
  honest zero-specialist `PreflightResult` instead of re-raising. The
  resident-manager kernel still binds evidence and the truthful header.
- The hook block remains only for non-staffing integrity failures, now with the
  exact cause appended.
- The CLI surfaces `status`, `error`, and `inference_failures` so
  `agency route "<prompt>"` is immediately diagnostic.
- ADR-0152 supersedes ADR-0122's fail-closed passages; ADR-0122's core decision
  (one Agency-native steward, inference owns staffing) stands unchanged.
- README, TROUBLESHOOTING, RELEASE_CHECKLIST, and THREAT_MODEL updated.

Verification: the rewritten contract tests pass (routing correctness, no-match
fallback, preflight bounds, unit-aware delegation, host hooks). The broader
workforce/header/mandatory-inference/child-routing cascade check passed 242
with 2 skips. Two pre-existing failures on clean main (`c01f178`) are unrelated
to this change: a header-field-name drift in
`test_same_specialist_can_activate_for_two_out_of_order_native_work_units` and a
Codex native-plan-scope validation issue in
`test_expired_owner_is_recovered_and_stale_token_cannot_commit_or_fail`.

Tracker creation is pending explicit authorization.

## Approach

1. Replace the hard staffing block with fail-open: the host answers as a
   generalist with a `Recruited via: none` header.
2. Persist the exact failure cause so the dashboard, logs, header, and CLI stay
   diagnosable.
3. Keep the hard block only for non-staffing integrity failures (evidence-store,
   lifecycle, assignment corruption).
4. Supersede ADR-0122's fail-closed passages with ADR-0152.

## Dependencies

AR-227 (roster expansion) is a separate package on its own branch. This change
starts from a clean branch off merged main so the roster PR stays isolated.

## Acceptance

- [x] A substantive turn with no accepted specialist fails open instead of
      blocking the parent model.
- [x] The response carries an honest `Recruited via: none` header.
- [x] The exact failure cause is persisted in the receipt and surfaced in the
      header and CLI.
- [x] Non-staffing integrity failures still hard-block with the exact cause.
- [x] ADR-0152 supersedes ADR-0122's fail-closed passages.
- [x] README, TROUBLESHOOTING, RELEASE_CHECKLIST, and THREAT_MODEL are updated.
- [x] The named fast production spine passes (659 passed, 6 skipped).
- [x] A live diagnosis matrix confirms ordinary prompts route or fail-open with
      truthful reasons (Package 3 — see findings below).
- [x] Specialist routing fires on ordinary prompts against a verified host
      capability receipt (Package 4 — see verification below).
- [ ] A follow-up pull request is open with exact verification evidence.

## Routing verification (Package 4)

After removing four deterministic gates that hid roster specialists (commit
`ed526b1`), specialist routing fires end-to-end against a real verified host
capability receipt. Five representative prompts tested with the native Codex
host capability set (`repository-read`, `repository-write`, `native-delegation`,
`test-execution`, `shell-execution`, etc.):

| Prompt | Status | Selected team |
|---|---|---|
| update the README install section | accepted | `technical-writer`, `code-reviewer` |
| review this code for correctness and security | accepted | `codebase-onboarding-engineer`, `code-reviewer`, `application-security-engineer`, `senior-secops-engineer` |
| fix the authentication bug in the Python code | accepted | `codebase-onboarding-engineer`, `python-application-engineer`, `software-test-engineer`, `code-reviewer`, `application-security-engineer`, `reality-checker` |
| add a docstring to the foo function | accepted | `codebase-onboarding-engineer`, `ai-engineer`, `technical-writer`, `software-test-engineer`, `code-reviewer`, `test-results-analyzer` |
| design a Git branching strategy | abstained | (genuine gap or recall miss; host answers as a generalist via fail-open) |

The recruiter model (`gpt-5.6-luna`, reasoning `low`) makes sound faithful-match
decisions once the deterministic gates stop hiding candidates. The
`agency route` CLI is an offline diagnostic that intentionally cannot prove host
tools (no verified native adapter receipt), so it reports the no-tool-context
abstention truthfully — that is correct by design, not a defect. The live host
path (Codex/ZCode hook with a native adapter event) provides the full native
capability set, where routing fires as shown above.

## Live diagnosis matrix (Package 3)

The truthfulness fix made the real remaining defect fully diagnosable. Every
substantive prompt now fails open with a truthful reason instead of blocking.
The provider is configured and both planner and recruiter calls succeed
(`status: applied`, model `gpt-5.6-luna`). The remaining product gap is that the
recruiter abstains on ordinary prompts:

| Prompt | Plan | Recruiter outcome | Candidates |
|---|---|---|---|
| `hello` (social) | n/a | n/a (deterministic, correct) | none |
| `review this authentication design and propose tests` | valid | `recruiter_abstained` | test-automation-engineer (19), test-results-analyzer (19) |
| `review this code for correctness and security` | valid | `recruiter_abstained` (inference-declared-gap) | ai-generated-code-security-auditor (32) |
| `update the README install section` | valid (documentation + review) | `recruiter_abstained` (inference-declared-gap), `decision=None` | technical-writer not surfaced |
| `add a docstring to the foo function` | valid | `recruiter_abstained` | score=0 across the board |

Two distinct defects surface:

1. The recruiter returns empty decisions (`decision=None`) and declares
   `inference-declared-gap` even when a faithful roster match obviously exists
   (e.g. `technical-writer` for a README change, `code-reviewer` for a review).
   Both planner and recruiter calls report `status: applied`, so this is an
   inference-quality / recruiter-prompt issue, not a provider failure.
2. Typed recall returns score=0 for some ordinary prompts (documentation, simple
   implementation), so the recruiter may not be shown the obvious specialist.

These are Package 4 work (recruiter prompt/conditions and recall), not fail-open
work. The fail-open change is complete: the operator is never locked out, and
the exact cause is now visible.
