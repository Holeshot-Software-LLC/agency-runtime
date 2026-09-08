---
title: "AR-410 Claude warm-up control evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, claude, canary, performance]
related:
  - docs/roadmap/issue-AR-410-disable-claude-warmup-staffing.md
  - docs/decisions/0237-isolate-claude-bootstrap-from-agency-evaluation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-410 Claude warm-up control evidence

## Installed pre-fix observation

Exactly one installed `4db6be16` native canary ran from
2026-09-08T00:31:38.851940Z to 00:34:43.527843Z (184.675903 seconds including
capture overhead). Native timeout remained 180 seconds; outer bound 420.
An approved observation wrapper returned the original canary record unchanged.
Existing owner-private credentials were reused, never printed or changed.
Actual 0775 Claude package/bin directories were restrictively repaired once
to 0755 before launch; local CLI 2.1.263 then passed existing trust/auth checks.
The actor behind the mode recurrence is unknown.

The original verdict was failure: CLI exit 1, native 124, timed_out,
claude_exec_timed_out. Response/stdout/stderr were empty, all five header fields
absent, child collection no_child_artifact, no accepted finalization or
attestation. Registration/enabled/load_requested were individually true;
loaded remained unknown. No native quality/activation success is inferred.

Read-only SQLite fingerprint correlation distinguishes the two sessions:

| Role | Trace | Exact request fingerprint | Outcome |
|---|---|---|---|
| Fixed warm-up | `814cf677-78fb-42ba-87ce-954cc96f57d9` | `98976a3a0ed01514b7319c96bde352e06c6bd47e15723dc9d0be2ad77f2253d0` | preflight_failed |
| Nonce request | `079be203-53da-4769-9887-859853b1a242` | `c86f13550c4ef2cd4286a2dfcbe659450d2ecf97251c0f047816d0ca4e81ddf8` | canary_failed |

`preflight.py` stores SHA256 of the exact request independently of disabled
content capture. Warm-up fingerprint matches the fixed literal; nonce matches
the report query hash. Receipt `d5733900-3e5c-43b3-b6ea-ba1061480a2c`
belongs only to warm-up, with workforce_inference_failed/inference_invalid:

| Stage | Requested / actual model | Closed outcome | Latency / effective allowance ms |
|---|---|---|---|
| subject | task-agency-planner-v2 / glm-5.3-flash | provider_response_contract_invalid | 4459 / 60000 |
| planner | task-agency-planner-v2 / task-agency-planner-v2 | provider_response_contract_invalid; plan_response_semantic_invalid | 24747 / 60000 |
| planner | task-agency-planner-v2 / unavailable | provider_call_timed_out | 60094 / 60000 |

Those attempts sum to 89,300 ms. No recruiter or critic appears in this
receipt. The actual nonce request began at 00:33:25.677771Z and has no retained
provider-attempt receipt; this does not establish zero actual provider calls.
No route or native verification was retained for either session. The facade's
empty route-based correlated_trace_ids does not invalidate the separate exact
run-fingerprint correlation.

The safe private projection is content-free and reproduced using SQLite
mode=ro, with no Store constructor or verification replay. Its SHA256 is
`b2fedd31231310bb6ca6c8704bb154dbbe00283a120a1bd7581d487f86110241`;
the replay script SHA256 is
`aebe255f173728a1c2fb699de4331cfd7f7ee49d970ec3dae97628183bb19ccd`.
Installed inference, routing_projection, preflight and canary_backends source
bytes were independently identical to Git `4db6be16`. No bodies are retained
in this committed receipt.

## Source regression checks

Executed in the issue worktree from base `a8c2ca54`, using
`env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python`:

```bash
python -m pytest tests/test_claude_canary_warmup_control.py -q -W error
python -m pytest tests/test_claude_canary_warmup_control.py tests/test_host_canary.py -q -W error -k 'not windows'
ruff format agency_runtime/core/canary_backends.py tests/test_claude_canary_warmup_control.py
ruff check agency_runtime/core/canary_backends.py tests/test_claude_canary_warmup_control.py
git diff --check
```

First command before runtime edit: **5 failed, 2 passed in 0.51s**. The failures
demonstrated initially enabled bootstrap and missing restoration verification.
Second after the initial private-control edit: **40 passed in 5.89s**. This
approach was subsequently rejected, not approved: independent review found
installed hooks carry an explicit owner `--runtime-control` path and ignore
the disposable path. Installed hooks JSON hash was
`880ecdb07b4f9065d2825a1e1e94af7882961d18b1f0bd22f3931c2302de5868`.
The ineffective flip was removed entirely.

The final source `0e8e9307` adds only warm-up argv
`--settings '{"disableAllHooks":true}'`. Existing private control and the actual
nonce argv remain unchanged. Installed CLI 2.1.263 help confirms inline
settings; independent review checked the official Claude setting documentation.
Managed-policy hooks may override this setting; no policy is bypassed.

During corrected test development, the bound-hook fixture first used the wrong
generator argument name, then assumed a shell-command string instead of the
actual command/args shape. These runs returned 1 failed/60 passed in 7.00s and
6.87s respectively. The final focused command returned 7 passed in 0.22s:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_claude_canary_warmup_control.py -q -W error
```

Independent second review corrected its own corresponding command/args fixture
observation (1 failed/27 passed in 1.32s), then obtained **28 passed in 1.37s**:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_claude_canary_warmup_control.py tests/test_canary_modes.py tests/test_canary_cohesion.py -q -W error
```

Final independent review found no scoped Critical/High/Medium source finding.
Runtime SHA256 `a50abf9c3b7210ab0e2cac5adbe3151c96c236b5050aafca3961602fb2e7dfb5`;
test SHA256 `0909c3f77bde65c779e1abbdc393d2a2f315ea04438b54524df4862aacc72f44`.
Focused Ruff and diff checks passed. These are source checks, not isolated
acceptance verdicts or native activation evidence. The owner subsequently
directed no additional test/model launches before the stopping checkpoint.

## Remaining scope

Record parity, isolated acceptance and exact-installed native verification
remain at source publication. Disabling only bootstrap is expected to remove
warm-up staffing, but second-session activation and total native wall time
must still be observed. No budget, model-quality or all-host claim is made.
