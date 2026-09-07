---
title: "AR-409 acceptance verification draft and command evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, workforce, budgets]
related:
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/decisions/0235-reserve-required-staffing-calls-before-optional-work.md
  - docs/roadmap/handoffs/issue-AR-409.md
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-409
candidate_commit: pending
evidence_cutoff: 2026-09-07
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/735
---

# AR-409 acceptance verification draft and command evidence

Builder evidence only; no acceptance verdict is supplied. The recorded tests
ran on the implementation based on `2274823ca3d56ddeaa78cd69cf8a6d9dedf3407c`,
branch `codex/ar409-reserve-required-staffing`; the branch has since normally
integrated `d28ccc23`. Filing `96a048d6` and ledger `e010ed2a` publish tracker
#735 and reciprocal records. AR-408's runtime integration remains pending.
Freeze this record only after the combined candidate exists in an ancestor commit.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Shared remaining ledger, stage-local total cap and pre-call reservation admission | 2026-09-07 | agency_runtime/core/workforce/inference.py:1244-1273 |
| 1 | file | Reservations are checked before consumption and actual invocation; refusals refund existing ledger | 2026-09-07 | agency_runtime/core/workforce/inference.py:1752-1867 |
| 1 | test | Explicit strict caps 1–8 and provider-fallback admission; no calls for an unaffordable uncached mandatory path | 2026-09-07 | tests/test_staffing_call_reservations.py:147-237 |
| 1 | test | Stage limits count actual requests after a refunded pre-request refusal | 2026-09-07 | tests/test_staffing_call_reservations.py:283-315 |
| 2 | test | One actual subject call across providers, including refunded refusal followed by fallback | 2026-09-07 | tests/test_staffing_call_reservations.py:179-192 |
| 2 | test | Valid inferred subject still reaches planner and recruiter documents | 2026-09-07 | tests/test_staffing_call_reservations.py:239-255 |
| 2 | test | Existing readable/prior-subject reuse and no-invented-hint contracts | 2026-09-07 | tests/test_workforce_subject_inference.py:86-175 |
| 2 | test | Existing zero-signal trigger is not a tunable low-confidence threshold | 2026-09-07 | tests/test_workforce_subject_inference.py:177-212 |
| 2 | file | Subject retains typed parsing, two-plus-critic floor and one-actual-call cap | 2026-09-07 | agency_runtime/core/workforce/inference.py:4608-4643 |
| 3 | test | Former response pattern reaches a real approving critic within strict five; no-subject defaults fund both repairs | 2026-09-07 | tests/test_staffing_call_reservations.py:116-145 |
| 3 | test | Subject plus both repairs requires six; strict five refuses the final recruiter repair after four calls | 2026-09-07 | tests/test_staffing_call_reservations.py:163-176 |
| 3 | test | Genuine veto remains terminal; available critic semantic repair remains permitted | 2026-09-07 | tests/test_staffing_call_reservations.py:206-216 |
| 3 | test | Invalid first critic reply receives its existing single semantic repair when funded | 2026-09-07 | tests/test_staffing_call_reservations.py:258-265 |
| 4 | test | Warm exact plan/recruiter cache spends no calls, including pre-used ledger; strict critic remains fresh | 2026-09-07 | tests/test_staffing_call_reservations.py:195-203 |
| 4 | test | Cached stages are used before their own admission floor | 2026-09-07 | tests/test_staffing_call_reservations.py:268-280 |
| 4 | test | Actual Store failure receipts for early zero-call and recruiter-reservation refusal retain budget cause | 2026-09-07 | tests/test_staffing_call_reservations.py:337-376 |
| 4 | test | Exact budget cause appends to existing verifier causes without duplication or status change | 2026-09-07 | tests/test_staffing_call_reservations.py:379-400 |
| 4 | file | Failure projection adds only the known missing closed budget reason | 2026-09-07 | agency_runtime/core/workforce/inference.py:4225-4260 |
| 5 | command-output | Focused/broad regression command outcomes, with source-stage and unsuccessful intermediate runs retained | 2026-09-07 | docs/roadmap/acceptance/issue-AR-409.md#test-command-evidence |
| 5 | command-output | Full 188 pre-refinement conformance and fresh five post-refinement subset, with initial setup failures distinguished | 2026-09-07 | docs/roadmap/acceptance/issue-AR-409.md#mutation-command-evidence |
| 5 | command-output | Routing corpus and source checks; no live model-quality inference | 2026-09-07 | docs/roadmap/acceptance/issue-AR-409.md#routing-and-source-checks |
| 5 | file | Four mutation anchors bind each reservation rule to its focused regression | 2026-09-07 | agency_runtime/core/evals/decision_conformance.py:1614-1659 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|

## Evidence scope

These are retained terminal summaries and report fields from September 7 local
commands, not an archive of every stdout byte. All paths below identify that
historical execution environment; tests and source citations remain in this
repository. No model/provider calls, installed activation, owner-profile edits,
tracker writes or isolated acceptance runs occurred in this worker package.

The routing corpus uses deterministic candidate recall and synthetic inference
receipts. A passing routing or mutation gate is not live staffing quality,
all-host delivery or end-to-end latency equivalence. Existing live receipt
`3615c4fb-1c2f-4a9c-b76f-bd8638f59385` motivates the regression; it is not a
successful execution of this candidate. Parent must integrate AR-408, adapt its
historical exhausted-critic test and record the installed combined-candidate
live checkpoint separately.

### Test command evidence

All commands ran in `/tmp/agency-runtime-ar409-reserve-required-staffing`.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py -q -W error
```

- First test draft: collection stopped because the test imported
  `PROVIDER_CREDENTIAL_ENV_UNSET` from the wrong module; 1 error in 0.08s.
- Corrected import, pre-runtime-change red: 15 failed, 4 passed in 0.53s.
- Initial reservation implementation: 19 passed in 0.20s.
- Expanded subject/cache/refund/critic controls: 26 passed in 0.26s.
  The later receipt cases were verified by the final related command below,
  not claimed as another standalone run of this command.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_workforce_inference.py tests/test_workforce_subject_inference.py tests/test_inferred_subject_beside_context.py tests/test_preflight_provider_deadline.py tests/test_transport_failure_causes.py tests/test_strict_critic_doctrine.py tests/test_critic_eligibility_view.py tests/test_configuration.py tests/test_decision_conformance.py -q -W error -k 'not windows'
```

Before the receipt-only refinement: 263 passed, 2 deselected in 6.10s.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_decision_conformance.py -q -W error
```

With 26 focused tests and four new mutation anchors: 43 passed in 0.29s.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_workforce_inference.py tests/test_workforce_subject_inference.py tests/test_inferred_subject_beside_context.py tests/test_preflight_provider_deadline.py tests/test_transport_failure_causes.py tests/test_strict_critic_doctrine.py tests/test_critic_eligibility_view.py tests/test_configuration.py tests/test_decision_conformance.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py -q -W error -k 'not windows'
```

Before the receipt-only refinement: 532 passed, 1 skipped, 3 deselected in 26.47s.
Windows-named cases were excluded; this is not Windows execution evidence.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py -q -W error -k 'reason'
```

Receipt-refinement red: 3 failed, 1 passed, 26 deselected in 0.35s. The failures
were both real Store projections losing the budget code and an existing
verifier cause missing the appended budget code; already-present no-duplicate
control passed.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_preflight_provider_deadline.py tests/test_preflight_failure_diagnosis.py tests/test_transport_failure_causes.py tests/test_workforce_inference.py tests/test_decision_conformance.py -q -W error -k 'not windows'
```

- First receipt implementation had a missing `AbstentionReason` import:
  7 failed, 194 passed in 3.05s; Ruff also detected the undefined name.
- After correcting that import: 201 passed in 2.99s.

### Independent review

The single independent reservation review found the missing durable budget
cause, then rechecked that bounded correction. Its initial exact command:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_workforce_subject_inference.py tests/test_inferred_subject_beside_context.py tests/test_workforce_hiring_contract.py tests/test_decision_conformance.py::test_curated_manifest_anchors_are_current_and_unique -q -W error -k 'not windows'
```

Result: 134 passed, 1 deselected in 1.09s. The deselection was Windows;
progress-dot stdout was not retained and is not reconstructed.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_preflight_failure_diagnosis.py -q -W error -k 'not windows'
```

Final bounded recheck: 62 passed in 0.38s, exit 0; no remaining findings and
`git diff --check` passed. This is code review, not an isolated acceptance
verdict or installed live test.

### Mutation command evidence

This attempted entrypoint was invalid because the package has no
`agency_runtime.__main__`; it made no evaluation or provider call:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m agency_runtime eval decision-conformance --repository . --json
```

The corrected exact CLI invocation was:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/agency eval decision-conformance --repository . --json
```

Its first run stopped at baseline before any of 188 mutations: the private
storage guard refused the test configuration directory under the generated
ephemeral test root. Baseline exit 1/duration 1231ms; source_unchanged=true.
No permission guard was relaxed. The repeat used a private process umask:

```bash
umask 077
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/agency eval decision-conformance --repository . --json
```

Before the receipt-only refinement: baseline exit 0/duration 101543ms;
overall passed=true, status=passed, source_unchanged=true for 188 curated
mutations, including the four new reservation anchors. The large output was
tool-truncated; individual full-run mutation durations are not reconstructed.

After receipt refinement, this exact first subset command failed its assertion
because a pre-existing staffing mutation also matched; no evaluation ran:

```bash
umask 077
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -B -c 'from agency_runtime.core.evals.decision_conformance import MUTATIONS,run_decision_conformance_eval
import json
selected=tuple(item for item in MUTATIONS if item.mutation_id.startswith("staffing-"))
assert len(selected)==4
report=run_decision_conformance_eval(".",mutations=selected)
print(json.dumps({key: report[key] for key in ("passed","status","source_unchanged","counts","baseline","mutations")},sort_keys=True))
raise SystemExit(0 if report["passed"] else 1)'
```

The four-only exact command then produced a baseline collection failure:

```bash
umask 077
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -B -c 'from agency_runtime.core.evals.decision_conformance import MUTATIONS,run_decision_conformance_eval
import json
selected=tuple(item for item in MUTATIONS if item.test_node.startswith("tests/test_staffing_call_reservations.py::"))
assert len(selected)==4
report=run_decision_conformance_eval(".",mutations=selected)
print(json.dumps({key: report[key] for key in ("passed","status","source_unchanged","counts","baseline","mutations")},sort_keys=True))
raise SystemExit(0 if report["passed"] else 1)'
```

The isolated copy omitted the new tests' imported
`tests/test_workforce_inference.py` fixture. Baseline exit 4/duration 928ms,
0/4 mutations, source_unchanged=true. A four-only standalone pass is not claimed.

The successful exact post-refinement subset command includes the existing
fast-budget mutation to supply that fixture and independently retain its
original default-repair control:

```bash
umask 077
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -B -c 'from agency_runtime.core.evals.decision_conformance import MUTATIONS,run_decision_conformance_eval
import json
selected=tuple(item for item in MUTATIONS if item.test_node.startswith("tests/test_staffing_call_reservations.py::") or item.mutation_id=="default-fast-budget-removes-stage-repair")
assert len(selected)==5
report=run_decision_conformance_eval(".",mutations=selected)
print(json.dumps({key: report[key] for key in ("passed","status","source_unchanged","counts","baseline","mutations")},sort_keys=True))
raise SystemExit(0 if report["passed"] else 1)'
```

Baseline exit 0/duration 2172ms. Final counts: 5 mutations, 5 killed, 0 survived,
0 invalid; passed=true, source_unchanged=true. Each anchor occurred once:

| Mutation | Result | Duration ms |
|---|---|---:|
| default-fast-budget-removes-stage-repair | killed | 1084 |
| staffing-subject-repair-spends-critic-call | killed | 1080 |
| staffing-subject-spends-mandatory-stage-calls | killed | 1072 |
| staffing-planner-spends-downstream-stage-calls | killed | 1096 |
| staffing-recruiter-spends-mandatory-critic-call | killed | 1095 |

### Routing and source checks

This attempted entrypoint likewise failed before evaluation:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m agency_runtime eval routing --json --no-details
```

The actual source-bound command:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/agency eval routing --json --no-details
```

passed every gate: 45 routing cases, 30 policy cases, 22 delegation cases;
required candidate recall 1.0, forbidden candidate rate 0.0, deterministic
performance p95=1.122ms/cache-hit p95=0.208ms. These are synthetic routing
benchmarks, not the 75-second native staffing metric or a model speedup claim.
This run preceded the receipt-only refinement, which did not change allocation.

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/python -m ruff check agency_runtime/core/workforce/inference.py tests/test_staffing_call_reservations.py
/tmp/agency-ar404-venv.AUBJlC/bin/python -m ruff format --check agency_runtime/core/workforce/inference.py tests/test_staffing_call_reservations.py
```

Initial lint detected `_invoke_stage` complexity 17 over 15; extracting the
bounded reserve calculation restored the limit. The new test needed formatting.
Subsequent format commands were:

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/python -m ruff format tests/test_staffing_call_reservations.py
/tmp/agency-ar404-venv.AUBJlC/bin/python -m ruff format tests/test_staffing_call_reservations.py agency_runtime/core/workforce/inference.py
```

The first receipt refinement also exposed the missing import described above.
Final source checks passed:

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/python -m ruff check agency_runtime/core/workforce/inference.py agency_runtime/core/evals/decision_conformance.py tests/test_staffing_call_reservations.py
/tmp/agency-ar404-venv.AUBJlC/bin/python -m ruff format --check agency_runtime/core/workforce/inference.py agency_runtime/core/evals/decision_conformance.py tests/test_staffing_call_reservations.py
git diff --check
```

Output: All checks passed; 3 files already formatted; no diff-check findings.
No exhaustive workflow, coverage shard or interpreter matrix was run.

### Draft documentation checks

The four new records were parsed through `scripts.verify_docs` using
`parse_document`, `validate_schema`, `validate_metadata_references`,
`validate_links_and_boundaries`, `validate_handoffs` and
`validate_acceptance_record`. Their schemas, source ranges, links, capsule
and pending acceptance record passed; five criteria were parsed. The capsule
is 111 lines and below its 12 KiB limit.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python scripts/docs_metadata.py --check
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_docs.py
git diff --check
```

Metadata passed: checked 1236 Markdown documents. Diff check passed. Full docs
validation did not pass: it reported six publication/base-ledger errors left
for the parent, without modifying those shared records:

- AR-409 is absent from the roadmap registry.
- AR-408 does not yet reciprocate `blocks=AR-409`.
- AR-404 does not yet reciprocate `depends_on=AR-409`.
- The old branch base merge `2274823c` is missing from the worklog index.
- That missing `2274823c` row is also reported as inaccurate.
- ADR-0235 is absent from the decision registry.

Those six historical errors were resolved by normal integration through
`d28ccc23` and filing `96a048d6`/ledger `e010ed2a`. A follow-up first found only
the two local draft tracker URLs still null; after setting both to #735,
`scripts/verify_docs.py` passed for 1242 Markdown files and
`scripts/update_worklog.py --check` reported a current 2067-commit index.
Candidate freezing remains pending; these checks do not waive tracker parity.

## Remaining delivery and quality boundary

After normal integration through `d28ccc23` and filing checkpoint `e010ed2a`,
the same final related command above passed again: `201 passed in 3.05s`.
Focused Ruff check and format check passed for the two runtime files and new
test file; metadata checked 1242 Markdown documents; `git diff --check` passed.

All five criteria await isolated candidate-bound verification; this draft
supplies no judgments. Parent must complete AR-408 integration, source/record
publication and the exact combined-candidate installed live checkpoint.
Subject plus both repairs and critic needs six calls, not five. Conservative future
cache/gap reservations may abstain sooner, and no paired live quality,
hiring-success or end-to-end latency-equivalence claim is supported.
