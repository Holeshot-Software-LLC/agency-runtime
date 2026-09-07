---
title: "AR-151 current host eligibility and dashboard contract evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, hosts, contract, acceptance]
related:
  - docs/roadmap/issue-AR-151-align-route-lab-host-eligibility.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - tests/test_dashboard.py
  - tests/dashboard_route_contract.mjs
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-151 current host eligibility evidence

## Current contract

Reviewed source baseline: main 460f319b, merge of PR #703. The production
renderer validates the complete inventory at dashboard-render.js:1043-1119;
the authoritative resolver independently checks it at server/dashboard.py:758-895
before catalog capture at 2775-2782. Duplicate identities are excluded, not
first-wins. Unrelated unique verified hosts remain eligible; more than ten rows
reject the entire inventory. Static bounded UI reasons reveal no raw host data.

## Direct UI-to-POST matrix

`tests/test_dashboard.py::test_dashboard_route_lab_ui_to_post_host_contract`
contains 13 scenarios: each of five supported hosts individually, all five
together, normalized duplicate, triple duplicate, duplicate plus unrelated valid
host, ten-row boundary, eleven-row rejection, disabled host and unproven host.

Each reads the actual authenticated GET host projection, sends it through
production renderer and action-controller modules using minimal DOM/transport
doubles, and sends the exact generated request bodies to the actual HTTP POST
handler. Valid choices must preserve host/capability identity. Excluded hosts
are also submitted directly, requiring 400 before any inference call. Every
unavailable UI reason stays within 160 characters. Native inspection and
inference are deterministic doubles; this is not a native canary or browser
installation claim. The JavaScript driver captures outbound bodies only.

Focused command:

```bash
PYTHONPATH=. python -m pytest tests/test_dashboard.py \
  -k route_lab_ui_to_post_host_contract -q -W error
```

Result: 13 passed, 161 deselected, zero skipped, 13.45s. The first development
run passed 12 and failed one because the new test expected 500 for an oversized
inventory. Inspection of do_POST:1518-1525 confirms deliberate 400 mapping for
RuntimeError; the assertion was corrected to the existing contract. No product
error mapping or rejection was changed.

## Initial dashboard verification

Core suite:

```bash
PYTHONPATH=. python -m pytest tests/test_dashboard.py \
  tests/test_dashboard_auth_boundary_regression.py \
  tests/test_dashboard_transaction_refactors.py -q -W error
```

Result: 193 passed, zero skips/failures, 40.75s.

Full source-only UI command:

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Result: 176 passed, zero skips/failures, 225.46ms. Coverage:
96.93% lines / 86.70% branches / 95.71% functions, unchanged 95/86/93 floors.

## Preserved broader failures

Adding `tests/test_dashboard_disconnects.py`,
`tests/test_dashboard_server_coverage_complete.py` and
`tests/test_dashboard_operational.py` to the core command gives **265 passed,
nine failed, zero skipped, 53.81s**, not a passing full-dashboard claim.

The nine exact failing cases reproduce on untouched main 460f319b: nine failed,
53 deselected, 4.81s. Selection command on the two additional failing modules:

```bash
PYTHONPATH=. python -m pytest tests/test_dashboard_server_coverage_complete.py \
  tests/test_dashboard_operational.py \
  -k 'miscellaneous_get_post or trim_is_denied or roster_actions_are_denied or host_toggle_is_denied or coordinator_error_stale or inference_projection_distinguishes' \
  -q -W error --tb=short
```

- Miscellaneous config mutation, four trim parameters, roster mutation and
  host toggle expect owner credentials to be read-only. ADR-0117 permits owner
  mutation and preserves broker denial; these fixtures must use broker tokens
  for their denial assertions, preserving no-dispatch expectations.
- The cache fixture injects a future cache expiry but leaves the separate
  stale deadline expired. Update both pieces of its intended fresh evidence;
  do not weaken production freshness.
- The inference fixture labels an explicitly configured legacy judge/fallback
  chain unconfigured. Current inference authority includes that chain; retain
  the genuinely unconfigured case and correct the configured-chain projection.

These are bounded blockers to this record's original full-dashboard criterion,
not reasons to reintroduce removed runtime policy. AR-176 retains its six other
previously recorded failures; those are not part of this repair.

## Scope and remaining gate

Product and scripts equal accepted AR-138 candidate 2ecde1a5 (`git diff
--exit-code 2ecde1a5 -- agency_runtime scripts` returns zero). Its rebuilt wheel
and 21 loaded-view checks remain byte-identical evidence, not a new run.
No native Windows, full corpus, aggregate coverage matrix or hosted dispatch.
The initial failure state above is committed at 58285009, not erased.

## Fixture reconciliation

Only tests change. The denial cases now explicitly send a separate broker
bearer and assert the existing exact `owner control required` 403. Owner-token
behavior is unchanged, and roster dispatch must still remain untouched.
The fresh-cache fixture supplies both cache and stale deadlines. The inference
test now separately verifies optional keyless Ollama, an explicitly configured
legacy judge chain, and an explicit typed provider. It does not turn a missing
provider into successful inference or relabel unavailable runtime state.

The first fixture rerun passed the cache/inference cases but retained seven
obsolete `read-only` message assertions. After correcting those to the current
broker-denial message, all nine focused cases pass (53 deselected, 4.71s).
A broader run started before the message correction completed 267 pass/seven
fail (54.42s); it is not a fresh corrected-candidate result.

## Final current verification

The following command was started after the fixture edits finished:

```bash
PYTHONPATH=. python -m pytest tests/test_dashboard.py \
  tests/test_dashboard_auth_boundary_regression.py \
  tests/test_dashboard_transaction_refactors.py \
  tests/test_dashboard_disconnects.py \
  tests/test_dashboard_server_coverage_complete.py \
  tests/test_dashboard_operational.py -q -W error
```

**274 passed**, zero failures/skips, **52.54s**. This includes all 13 new
UI-to-POST scenarios, all nine repaired cases and the complete named dashboard
API, auth, transaction, disconnect, server-branch and operational modules.
The separate complete UI run above passes 176 with unchanged production floors;
no JavaScript changed after that run.

The exact 29-module named Python production spine from AGENTS.md also ran:
**1,085 passed, three existing skips, 68.98s**. Current routing evaluation
returned `passed: true` for its 39 candidate-recall/policy/synthetic-performance
gates. Ruff check and format check pass (765 Python files); diff check passes.

Decision-conformance's earlier 184/184 killed, zero survived/invalid result is
scoped reuse: product/scripts and tests/test_decision_conformance.py are equal
to 2ecde1a5. The modified fixtures are not a new decision implementation. No new
conformance execution, exhaustive Python corpus or hosted workflow is claimed.

All four original AR-151 criteria still require isolated verdicts. The builder
supplies these commands, artifacts and limitations without judging acceptance.
