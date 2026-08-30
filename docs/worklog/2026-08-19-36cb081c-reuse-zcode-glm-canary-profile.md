---
title: "Worklog detail: reuse ZCode GLM profile for canary judges"
status: active
category: worklog
created: 2026-08-19
updated: 2026-08-19
tags: [canary, inference, providers, zcode, glm, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - agency_runtime/core/canary_judge_provider.py
  - agency_runtime/core/inference_profiles.py
supersedes: []
superseded_by: null
type: worklog
commit: 36cb081cccace4627d260aa159919973b7581111
short: 36cb081c
date: 2026-08-19
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
---

# Worklog detail: reuse ZCode GLM profile for canary judges

## Purpose

Option A needs one durable canary-only judge choice per harness. The owner chose
GLM for ZCode, and the installed configuration already contains bounded
Anthropic-compatible ZCode inference profiles. Adding GLM to the ordinary
provider chain would have changed real child staffing and exceeded the chosen
scope.

## Approach

The canary pin resolver now searches both configured CLI providers and named
inference profiles. It accepts exactly one identity, fails closed when a name
exists in both namespaces, and permits a profile only when its adapter is
Anthropic-compatible, its credential endpoint satisfies the existing safety
rule, and its credential is available. The selected profile is materialized as
the canary snapshot's sole provider; the original provider chain is untouched.

The existing profile-to-provider projection became a small public helper so
normal inference-profile routing and canary pinning share the same timeout,
model, endpoint, and credential translation. Native-child tests prove both the
initial judge and its one repair see only `zcode-recruiter` and record the
requested and actual provider independently.

## Challenges encountered

Historical GLM receipts prove that the ZCode profile family has executed, but
they predate this candidate and do not prove a current canary or native host
artifact. Read-only host inspection also showed that ZCode has no safe
noninteractive native-child canary backend. Documentation therefore separates
the locally executable profile path from installed and host-proven evidence.

The wider affected suite exposed one unrelated committed mismatch:
`test_default_workforce_mode_funds_one_repair_per_inference_stage` expects the
old `fast` default while `config_defaults.yaml` has contained `strict` since
2026-08-04. This bounded AR-119 package did not change that historical test.

## Decisions and alternatives

ADR-0160 remains the governing decision. Reusing a named profile was chosen
over adding GLM to `config.providers`, adding ambient fallback, or changing
ordinary child staffing. A historical receipt, subscription label, or parent
model label remains insufficient for ZCode host proof.

## Verification

- Focused affected slice: 132 passed.
- Wider affected slice: 293 passed, 1 skipped, with the unrelated historical
  default-mode assertion described above as the only failure.
- `python scripts/run_local_gates.py --fast`: all 12 gates passed, including
  161 workflow-contract tests and 134 dashboard tests.
- Ruff lint/format, documentation metadata/contracts, release hygiene,
  mutation-snippet checks, and `git diff --check` passed.
- The AR-119 recovery capsule remains within its fixed limit at 180 lines and
  10,072 bytes.

## Follow-ups

- Add a safe noninteractive native ZCode canary proof path under AR-253.
- Obtain renewed approval before installing, changing the owner profile, or
  collecting live Claude or ZCode evidence.
- Keep Codex parent/header support distinct from its upstream-blocked native
  child-artifact proof.
- Move no AR-119 matrix cell until current host-authored evidence satisfies the
  applicable rule.
