---
title: "AR-408 truthful staffing failure receipt evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, workforce, diagnostics, deadlines]
related:
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - tests/test_staffing_failure_receipts.py
  - tests/test_preflight_provider_deadline.py
supersedes: []
superseded_by: null
---

# AR-408 truthful staffing failure receipt evidence

## Live cause and bounded outcome

The existing September7 live Claude trace
`3615c4fb-1c2f-4a9c-b76f-bd8638f59385` contains two rejected subject calls,
one accepted planner, one rejected recruiter and one accepted recruiter repair:
five workforce calls against the configured strict limit of five. There is
no critic attempt. Its durable staffing reason nevertheless says
`staffing_critic_rejected`. This is a reproducible classification defect, not
evidence that an independent critic reviewed and rejected the team.

The same live investigation found that workforce routing dropped
`WorkforceInferenceAttempt.timeout_ms` before the already-existing bounded
durable projection. Exact Hermes receipt
`5135dd9b-da9a-4c57-b687-07cbcc7f7ee5` retained120206ms recruiter elapsed time
without the effective120000ms allowance.

Read-only SQLite used mode=ro/query_only. Eight inspected deadline, preflight,
budget, inference, cache and projection modules were byte-identical across
08fab1c4, installed4329d760 and OpenClaw1d617ca5. No profile, credential or
provider mutation was needed to identify these defects.

The repair preserves actual non-verdict reasons; genuine critic rejection and
approval are unchanged. It forwards positive effective timeout to the existing
allowlist and sets the attempt's allowance to zero when its deadline has
already expired before admission. The durable positive-only schema omits that
zero; it does not falsely report a configured positive allowance.

This package does **not** change budget/defaults, retry allocation, mandatory
critic, specialist selection, hiring policy, provider profiles or trust.
An allocation improvement is separate work; corrected output alone does not
make the former failed turn succeed.

## Latency interpretation

Hermes's individual preflight took270035ms. Its four provider attempts total
268046ms: planner66421, cold296-input embedding50467, reranker30952 and
recruiter120206. The remaining1989ms is0.74percent. Installed hook allowance
is595seconds, with ten seconds reserved and585seconds shared inference budget.
The75second legacy value is a floor, not this host's effective deadline.
This run is not evidence of large local serialization waste or exceeding a
75second staffing limit. Native420second battery wall time is a different
measurement with further host activity.

Warm vector reuse was visible in the two Claude traces: catalog_cache_hit=true,
one embedding input,5555ms and343ms. Hermes had a cold296-input call.
The reason for its cache miss is not retained; expiry, catalog change or slot
replacement are hypotheses, not findings. No paired model-quality claim follows
from cache hits.

## Regression first, then repair

The worker ran this exact command before the production fix:

~~~bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_failure_receipts.py tests/test_preflight_provider_deadline.py::test_actual_preflight_closes_with_deadline_receipt_and_scopes_vector_cache -q -W error
~~~

Recorded result: **8 failed,2 passed in3.29s**, exit1. This is a retained
command/result summary, not a reconstructed full raw pytest transcript.
Failures cover the real five-call starvation classification and missing
allowance projection; genuine critic approval/veto controls remain green.

After the narrow fix:

~~~bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_failure_receipts.py tests/test_preflight_provider_deadline.py -q -W error
~~~

Recorded result: **23 passed in2.97s**, exit0.

The new file drives the real `plan_and_staff_workforce` orchestration with
fixed provider responses. It projects actual routing through the production
failure allowlist into a real temporary Store preflight failure, then reads it
back. The provider is a deterministic fixture; this is not a new native
model-host canary or a claim that provider behavior improved.

The exact five-call case checks no selected team, unchanged five calls,
budget-exhaustion reason and no invented critic veto. Additional cases cover
missing provider, expired deadline, timeout, HTTP503 and invalid responses,
plus valid approval and valid negative verdict. The sensitive-field case
injects synthetic private key/body fields and proves they do not persist.

The existing real-preflight deadline regression now asserts the persisted
attempt's **clamped** positive timeout, not merely a hand-constructed field.
Already-expired deadline admission spends no provider call and preserves
`provider_deadline_exhausted` without positive allowance.

## Broader focused verification

~~~bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_failure_receipts.py tests/test_preflight_provider_deadline.py tests/test_transport_failure_causes.py tests/test_preflight_failure_diagnosis.py tests/test_strict_critic_doctrine.py tests/test_critic_eligibility_view.py tests/test_workforce_inference.py tests/test_preflight_bounds.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py -q -W error -k 'not windows'
~~~

Recorded result: **325 passed,1 skipped,1 deselected in27.53s**, exit0.
These are exact retained worker commands/results; full raw output was not
saved and is not fabricated here.

## Independent review

One independent read-only review found no concrete issue. Its narrow command:

~~~bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_failure_receipts.py tests/test_preflight_provider_deadline.py tests/test_strict_critic_doctrine.py tests/test_critic_eligibility_view.py -q -W error -k 'not windows'
~~~

Raw stdout, exit0:

~~~text
................................                                         [100%]
32 passed in 2.91s
~~~

The review checked that only a valid negative verdict creates the veto
sentinel; non-verdict failures retain their actual cause. The timeout change
does not change call consumption or provider invocation. Routing forwards the
existing safe field; the durable positive-only allowlist remains unchanged.
No credentials or raw responses are added to persistent output.

## Named fast verification

The parent ran the exact29-module named Python production spine in AGENTS.md
against the reviewed AR408 working delta after main2274823c. Later main changes
through c64ce3ce are records only. Final raw result, exit0:

~~~text
1085 passed, 3 skipped in 69.50s (0:01:09)
~~~

Dashboard command used the documented Node test coverage floors95/86/93:

~~~text
tests 224
pass 224
fail 0
skipped 0
duration_ms 263.395308
all files: lines96.93, branches86.78, functions95.74
~~~

The dashboard block is a selected-field projection of raw Node output.
Ruff, formatting, metadata, policy, worklog, docs, strict tracker and whitespace
are publication gates. No exhaustive corpus, coverage shards, compatibility
matrix or native Windows execution.

## Limitations and follow-up

The existing live failures establish why this code path matters; deterministic
responses make its fix reproducible. No new live provider request was needed
for this outcome. Native host health, specialist quality, launch-credential
inheritance and the ongoing parent's unverified header remain separate.
Do not claim a repaired critic review happened on the old failed trace, or
rewrite that immutable receipt to look successful.

## Exact portable artifact and installed smoke

Clean source `ef8c714f06aabd1fc0e0fcf4d22b50d31b402663` was built with
producer umask077 using the canonical builder and expected-commit check.
The independent explicit portable verifier and strict Twine both exited zero.

| Artifact | SHA-256 |
|---|---|
| Wheel | `78e838cf11d380ca3d81f757c7b7dd26066b06b34077a814c74d346898bf6ec0` |
| Sdist | `6bba101195b948fc314472fb39fcb82bf4f5aab979216e838322ad0c7bb6bb5d` |

Executed commands used private disposable `AR408_ARTIFACT_DIR` and the
trusted development interpreter; these names denote local temporary paths:

~~~bash
umask 077
python -m scripts.build_distributions "$AR408_ARTIFACT_DIR/dist" --expected-commit ef8c714f06aabd1fc0e0fcf4d22b50d31b402663
python scripts/verify_distribution.py "$AR408_ARTIFACT_DIR/dist" --expected-commit ef8c714f06aabd1fc0e0fcf4d22b50d31b402663 --artifact-set portable
python -m twine check --strict "$AR408_ARTIFACT_DIR/dist/agency_runtime-0.1.0-py3-none-any.whl" "$AR408_ARTIFACT_DIR/dist/agency_runtime-0.1.0.tar.gz"
python -m venv "$AR408_ARTIFACT_DIR/venv"
"$AR408_ARTIFACT_DIR/venv/bin/python" -I -m pip install "$AR408_ARTIFACT_DIR/dist/agency_runtime-0.1.0-py3-none-any.whl"
"$AR408_ARTIFACT_DIR/venv/bin/python" -I "$AR408_SOURCE_TREE/scripts/smoke_installed_distribution.py" --expected-version 0.1.0 --artifact-set portable
"$AR408_ARTIFACT_DIR/venv/bin/python" -I -m pip check
"$AR408_ARTIFACT_DIR/venv/bin/python" -I -m agency_runtime.cli smoke --all --json
~~~

Fresh environment installation selected only Agency0.1.0 and PyYAML6.0.3.
Actual isolated installed-distribution output:

~~~json
{"artifact_set": "portable", "assets": 10, "config": "passed", "dashboard": {"bind": "127.0.0.1", "health": "passed"}, "mcp": {"status_call": "passed", "tool_count": 8}, "roster": {"approved": 265, "quarantined": 0, "retired": 0, "total": 265}, "selection": {"cases": {"agency-runtime-dashboard": [], "ambiguous-help": []}, "forbidden_specialists": ["clinical-evidence-agent", "geographer", "language-translator"], "status": "passed"}, "version": "0.1.0"}
~~~

`pip check` returned `No broken requirements found.`
The subsequent aggregate smoke exited zero. Selected-field projection:

~~~json
{
  "passed": true,
  "passed_count": 8,
  "failed_count": 0,
  "skipped_count": 0,
  "checks": {
    "sqlite_store": "pass",
    "routing_roster_available": "pass",
    "host_parity_eval": "pass",
    "plugin_claude": "pass",
    "plugin_codex": "pass",
    "plugin_hermes": "pass",
    "plugin_openclaw": "pass",
    "plugin_zcode": "pass"
  }
}
~~~

Raw aggregate timing:

~~~text
real 5.03
user 3.86
sys 0.23
~~~

Generated host contracts ran for all five hosts, including actual generated
ZCode process-hook invocation and OpenClaw syntax check. This is fresh installed
CLI/MCP/dashboard/generated-host proof, not a new native model-host turn or an
owner CLI/host replacement. The publication keeps those claims separate.
