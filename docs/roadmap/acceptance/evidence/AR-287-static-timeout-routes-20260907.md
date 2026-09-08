---
title: "AR-287: Static timeout route repair source receipt"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, inference, host-integrations, timeouts]
related:
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/handoffs/issue-AR-287.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0192-route-content-invalid-completions-to-a-content-fallback-profile.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/worklog/2026-09-07-fb360485-static-timeout-routes.md
supersedes: []
superseded_by: null
---

# AR-287 static timeout route repair

## September 8 wrap-up update

The owner subsequently authorized tests and installed evaluation. On unchanged
source `fb360485` integrated at `6d0bb54a`, the command
`python -m pytest tests/test_native_installer.py tests/test_preflight_bounds.py -q -W error`
passed **186 cases with one skip in 29.28 seconds**, including all twenty-two
new cases. UNRUN statements below describe the initial checkpoint, not the
present result. Native/installed and isolated acceptance remain separate gates.

## Scope and provenance

Source candidate `fb36048537277833a41a5189bd29621514a6d0d5` repairs the
shared generated-hook/preflight-lease timeout calculation. Investigation base
was main `9b15107a3769ac475fd2d1a72d4f6598b7d1cef1`. Normal integration
`14899a51` includes published-main ledger `6d209d6d` without changing the
reviewed runtime or its written regressions. No owner configuration or installed
package was read or changed for this slice.

This is source evidence, not an acceptance verdict. The owner deferred tests,
CI and live/provider calls. Existing August 25 checkmarks and raw historical
claims remain in the canonical record; they do not verify this new delta.

## Producer/consumer defects and repair

| Boundary | Current source evidence | Repair |
|---|---|---|
| Independently routed safety repair | `agency_runtime/core/workforce/hiring.py`, `_safety_repair_loop`, resolves `workforce.hiring.safety_repair` and invokes that provider before renewed security review. | `agency_runtime/core/installer_payloads.py`, `_host_inference_budget_seconds`, includes that route when `hiring_repair_budget > 0`. It shares the existing hiring call ceiling, not a new allowance. |
| Slower content fallback | `agency_runtime/core/workforce/inference.py`, `configured_workforce_providers`, appends `resolve_content_fallback` after successful primary resolution only when profile names differ. `agency_runtime/core/inference_profiles.py` projects each profile's own bounded timeout. | `_static_route_timeout_seconds` mirrors that admission condition using config-only resolution for each reachable workforce/hiring route. A host with no primary does not acquire a fallback from another host or an environment override. |
| Premature deadline clamp | `agency_runtime/core/preflight.py`, `run_preflight`, uses `hook_timeout_seconds` for the Store lease and hiring deadline. `agency_runtime/core/workforce/hiring.py`, `_invoke`, clamps per-call timeouts with `remaining_provider_timeout`. | Producer and consumer keep the same helper. No lease renewal or change to ADR-0216's ten-second terminal reserve. |

ADR-0153 permits independently addressed stage profiles; ADR-0192 permits the
additional bounded content-fallback call and its latency; ADR-0216 requires
one enforced request deadline. This slice reconciles those existing contracts,
not a new latency policy. Profile selection, strict independence, call budgets,
legacy fallback floors, recall calculation and the 595-second ceiling remain.

## Written expected cases, not executed results

These figures are direct arithmetic and written assertions, **not measured
timings or test passes**. The fixture has one-second primaries and judge floor,
fast mode with four calls, one possible gap, six hiring calls and recall off.

| Configuration | Expected hook/lease seconds |
|---|---:|
| Baseline | 15 |
| Owning host's safety-repair primary is 20 seconds | 129 |
| Other host retains its own one-second routes | 15 |
| Planner/recruiter distinct content fallback is 20 seconds | 91 |
| Strict critic distinct fallback is 20 seconds, five workforce calls | 111 |
| Any hiring-stage distinct fallback is 20 seconds | 129 |
| Safety repair is 120 seconds, or strict planner fallback is 120 seconds | 595, unchanged cap |

`tests/test_native_installer.py` contains twenty new parameter cases, including
both host directions, inactive strict critic, disabled safety repair, duplicate
fallback profile, unrelated fallback route, absent primary, unchanged legacy
floor and ignored environment override. `tests/test_preflight_bounds.py`
contains two new cases capturing the actual Store admission arguments while
stubbing routing; they expect the same 129/91 values as the bridge helper.
All twenty-two cases are unrun. Written tests do not establish model quality,
successful hiring or native host delivery.

## Checks actually performed

```text
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format agency_runtime/core/installer_payloads.py tests/test_native_installer.py tests/test_preflight_bounds.py
1 file reformatted, 2 files left unchanged
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime/core/installer_payloads.py tests/test_native_installer.py tests/test_preflight_bounds.py
All checks passed!
git diff --check
<empty stdout; exit 0>
```

The interpreter path records the tool used; reproduction may use another Ruff
installation. Root's first independent source pass found no scoped finding on
the frozen 35-line runtime delta. No pytest, CI, full suite, acceptance verifier,
native command or model-backed canary ran. Formatting/lint and source review do
not discharge the original acceptance criteria.

## Remaining obligations

Run the focused installer/preflight regressions when authorized, then verify
the installed bridge and lease against the installed candidate and one suitable
fresh host turn. Reconcile the older pending Hermes proof without retrying its
failed input unchanged. Preserve the original canonical Acceptance wording and
checkbox states until an isolated acceptance record supports any change.
Owner-authorized tracker #756 now maps the existing legacy record, superseding
the original pending-mapping condition without changing its historical checkbox.
Normal PR publication remains a separate step.
