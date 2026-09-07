---
title: "AR-407 scoped install-drift verification"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, install, drift, live-state]
related:
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
supersedes: []
superseded_by: null
---

# AR-407 scoped install-drift verification

## Outcome and scope

Generic install residual drift now uses resolved installation targets. The
existing all-host status report remains intact. This repairs misleading output,
not cached host definitions, credential inheritance, hook trust or activation.
Prepared Codex refresh and verification-only paths return before this generic
helper; their separate behavior is not changed.

## Source and focused contracts

The cmd_install call passes its actual targets into the projection helper.
The helper takes the first report belonging to those targets, not the first
machine-wide report. Global cmd_status still uses the full list.

New tests use real pointer serialization and comparison in a private test
namespace. The 32-case matrix spans text/JSON, same/foreign package and eight
explicit/default/all/empty/skip-first scopes. Three additional cases cover
selected foreign drift, advisory comparison failure and unchanged global status.
Two old doubles now assert the exact resolved target list.

Valid initial 19-case regression run used --profile standard --no-dashboard to
select the generic install path; 12 failed/7 passed in 0.50s. Ten are reproduced
user-output failures; two expose the not-yet-added helper argument. The same
19 cases pass after repair in 0.46s. The earlier initial fixture accidentally
selected the prepared fast path and failed 14/5 in 1.08s; that fixture result
is not counted as bug proof. Final matrix expands to 35 cases.

## Fresh focused command

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_cli_install_drift.py tests/test_runtime_staleness.py tests/test_cli_coverage_complete_install.py tests/test_coverage_final_host_cli.py -q -W error -k 'not windows' --tb=short
```

```text
........................................................................ [ 45%]
........................................................................ [ 91%]
..............                                                           [100%]
158 passed, 1 deselected in 1.51s
```

One Windows-named case deselected; no source tests disabled. Independent first
focused review reported no findings and reran the 35 new cases: 35 passed in
0.69s. It checked target resolution, empty/default/all selections, typed pointer
normalization, advisory failures, global status and untouched fast paths.

## Actual mixed-host pointer check

A strictly read-only diagnostic compiles the two exact candidate helper
FunctionDefs into an isolated namespace while importing runtime comparison from
the real installed AR-348 interpreter. It does not import the checkout as the
installed package. The two normal directory accessors are bound in memory to
validation-only access of the already-existing launcher directory, so they
cannot perform permission repair. A direct uncaught report call additionally
ensures an inspection error cannot masquerade as an empty healthy result.

```bash
/home/holeshot/.local/share/agency-runtime/venvs/ar348-20260905.qq1DjJ/bin/python3 -I -B /tmp/agency-ar407-live-pointer.nPO3HV/probe.py
```

Exit zero. Safe field projection of its JSON follows; raw JSON SHA-256:
6967cc102926248408caff525b9ea8e5556d0be7c54e8eb6cd3390e5a3bd1f86.
All-recorded means five recorded pointer hosts, not native auto-detection.
Before and after snapshots compare hashes, modes, ownership, device, inode,
size and mtime for all five pointer files, plus parent/launcher directory
identity, permissions and mtime. Every compared field is unchanged.

```json
{
  "scope": "candidate helper fragments against live installed-package pointers",
  "started_at": "2026-09-07T22:40:47.141110+00:00",
  "ended_at": "2026-09-07T22:40:47.640892+00:00",
  "candidate_source_sha256": "659b42b2f0fe8a1321722b39c5424a46439a4f778f916def26dadf63148fbe3f",
  "candidate_helper_sha256": {
    "_cli_install_drift_projection": "ab95b45738d81554e181e31cdef9ca434baf4af1bce2bbf8920f16d7a9c47e91",
    "_cli_install_drift_projections": "e58efac09397363a4810ddb0af68b7ad177d8729df92403d2b2c95d9d5455d83"
  },
  "installed_package_root": "/home/holeshot/.local/share/agency-runtime/venvs/ar348-20260905.qq1DjJ/lib/python3.12/site-packages/agency_runtime",
  "comparison_package_root": "/home/holeshot/.local/share/agency-runtime/venvs/ar348-20260905.qq1DjJ/lib/python3.12/site-packages/agency_runtime",
  "comparisons": {
    "all_recorded": {
      "resolved_targets": [
        "claude",
        "codex",
        "hermes",
        "openclaw",
        "zcode"
      ],
      "before_host": "openclaw",
      "after_host": "openclaw",
      "after_foreign_package": true
    },
    "codex": {
      "resolved_targets": [
        "codex"
      ],
      "before_host": "openclaw",
      "after_host": null,
      "after_foreign_package": null
    },
    "empty": {
      "resolved_targets": [],
      "before_host": "openclaw",
      "after_host": null,
      "after_foreign_package": null
    },
    "openclaw": {
      "resolved_targets": [
        "openclaw"
      ],
      "before_host": "openclaw",
      "after_host": "openclaw",
      "after_foreign_package": true
    }
  },
  "pointers_unchanged": true,
  "directories_unchanged": true,
  "permission_repairs_performed": false,
  "pointer_hashes": {
    "current-claude.json": "62928de3fb02112d0ca95b29b9375f49fbc099dd4b566c608d9d77dbc2a72475",
    "current-codex.json": "961801c01d60f1117fe766dd0933c183575e08e2b0efef1b634707e0590dd6af",
    "current-hermes.json": "0841e5b0f48ffb1b2a021195032e2e539c534ae9bbe3b5d9ff3acb257242a14d",
    "current-openclaw.json": "b9072db1ec008765e797f2982b90a3cd316f0d1f2efb02e0b15e5a2fafa6c39a",
    "current-zcode.json": "13d58e9262a6ebf56b3f5c451308e2835dc445159a836e797c28cd860bde9d76"
  },
  "not_proven": [
    "candidate installed",
    "full install command",
    "native hooks",
    "staffing"
  ]
}
```

This is exact candidate-helper behavior against actual installed mixed-host
state, not an installed-candidate/full-install command or native staffing test.
The full cmd_install path is exercised separately by the focused regressions.

## Fresh fast verification

Named 29-module Python production spine, exact AGENTS.md argv:
1085 passed, 3 existing skips in 69.45s. Dashboard Node production coverage:
224 passes, zero failures/skips, 96.93/86.78/95.74 percent against unchanged
95/86/93 floors, duration 265.369544ms. Metadata, strict docs, Ruff and 767-file
formatting pass; full records/parity are rerun at publication.
No exhaustive corpus, coverage shards, compatibility matrix or native Windows.

## Valid baseline failure output

```text
FF..FFFF..FFFF..FF.                                                      [100%]
=================================== FAILURES ===================================
_ test_install_residual_drift_matches_resolved_targets[unselected-stale-host-text] _
tests/test_cli_install_drift.py:130: in test_install_residual_drift_matches_resolved_targets
    assert ("Install finished but" in output) is (expected_host is not None)
E   AssertionError: assert ('Install finished but' in '✅ Agency Runtime profile: standard\n✅ Starter roster added: 0 agents\n✅ Legacy bundled contracts upgraded: 0 agents\n...is CLI runs from: /tmp/pytest-of-holeshot/pytest-1970/test_install_residual_drift_ma0/current-package/agency_runtime\n') is (None is not None)
_ test_install_residual_drift_matches_resolved_targets[unselected-stale-host-json] _
tests/test_cli_install_drift.py:126: in test_install_residual_drift_matches_resolved_targets
    assert report["runtime_drift"] is None
E   AssertionError: assert {'source_digest': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'installed_digest': 'aaaaaaaaaaa...ource_root': '/tmp/pytest-of-holeshot/pytest-1970/test_install_residual_drift_ma1/current-package/agency_runtime', ...} is None
_ test_install_residual_drift_matches_resolved_targets[skip-first-unselected-report-text] _
tests/test_cli_install_drift.py:132: in test_install_residual_drift_matches_resolved_targets
    assert f"agency install --agent {expected_host}" in output
E   AssertionError: assert 'agency install --agent openclaw' in '✅ Agency Runtime profile: standard\n✅ Starter roster added: 0 agents\n✅ Legacy bundled contracts upgraded: 0 agents\n...is CLI runs from: /tmp/pytest-of-holeshot/pytest-1970/test_install_residual_drift_ma4/current-package/agency_runtime\n'
_ test_install_residual_drift_matches_resolved_targets[skip-first-unselected-report-json] _
tests/test_cli_install_drift.py:128: in test_install_residual_drift_matches_resolved_targets
    assert report["runtime_drift"]["host"] == expected_host
E   AssertionError: assert 'codex' == 'openclaw'
E     
E     - openclaw
E     + codex
_ test_install_residual_drift_matches_resolved_targets[default-resolved-subset-text] _
tests/test_cli_install_drift.py:130: in test_install_residual_drift_matches_resolved_targets
    assert ("Install finished but" in output) is (expected_host is not None)
E   AssertionError: assert ('Install finished but' in '✅ Agency Runtime profile: standard\n✅ Starter roster added: 0 agents\n✅ Legacy bundled contracts upgraded: 0 agents\n...pytest-1970/test_install_residual_drift_ma6/current-package/agency_runtime\n\n🔍 Auto-detected 1 agent host(s): codex\n') is (None is not None)
_ test_install_residual_drift_matches_resolved_targets[default-resolved-subset-json] _
tests/test_cli_install_drift.py:126: in test_install_residual_drift_matches_resolved_targets
    assert report["runtime_drift"] is None
E   AssertionError: assert {'source_digest': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'installed_digest': 'aaaaaaaaaaa...ource_root': '/tmp/pytest-of-holeshot/pytest-1970/test_install_residual_drift_ma7/current-package/agency_runtime', ...} is None
_ test_install_residual_drift_matches_resolved_targets[no-detected-hosts-text] _
tests/test_cli_install_drift.py:130: in test_install_residual_drift_matches_resolved_targets
    assert ("Install finished but" in output) is (expected_host is not None)
E   AssertionError: assert ('Install finished but' in '✅ Agency Runtime profile: standard\n✅ Starter roster added: 0 agents\n✅ Legacy bundled contracts upgraded: 0 agents\n...es were detected; other requested components ran.\n   Run `agency dashboard` to open the local operations dashboard.\n') is (None is not None)
_ test_install_residual_drift_matches_resolved_targets[no-detected-hosts-json] _
tests/test_cli_install_drift.py:126: in test_install_residual_drift_matches_resolved_targets
    assert report["runtime_drift"] is None
E   AssertionError: assert {'source_digest': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'installed_digest': 'aaaaaaaaaaa...urce_root': '/tmp/pytest-of-holeshot/pytest-1970/test_install_residual_drift_ma11/current-package/agency_runtime', ...} is None
_ test_install_residual_drift_matches_resolved_targets[all-resolved-subset-text] _
tests/test_cli_install_drift.py:130: in test_install_residual_drift_matches_resolved_targets
    assert ("Install finished but" in output) is (expected_host is not None)
E   AssertionError: assert ('Install finished but' in '✅ Agency Runtime profile: standard\n✅ Starter roster added: 0 agents\n✅ Legacy bundled contracts upgraded: 0 agents\n...ytest-1970/test_install_residual_drift_ma12/current-package/agency_runtime\n\n🔍 Auto-detected 1 agent host(s): codex\n') is (None is not None)
_ test_install_residual_drift_matches_resolved_targets[all-resolved-subset-json] _
tests/test_cli_install_drift.py:126: in test_install_residual_drift_matches_resolved_targets
    assert report["runtime_drift"] is None
E   AssertionError: assert {'source_digest': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'installed_digest': 'aaaaaaaaaaa...urce_root': '/tmp/pytest-of-holeshot/pytest-1970/test_install_residual_drift_ma13/current-package/agency_runtime', ...} is None
_________ test_targeted_install_retains_selected_foreign_package_drift _________
tests/test_cli_install_drift.py:138: in test_targeted_install_retains_selected_foreign_package_drift
    report = install_commands._cli_install_drift_projection(["codex"])
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: _cli_install_drift_projection() takes 0 positional arguments but 1 was given
____________ test_install_drift_reporting_failure_remains_advisory _____________
tests/test_cli_install_drift.py:151: in test_install_drift_reporting_failure_remains_advisory
    assert install_commands._cli_install_drift_projection(["codex"]) is None
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: _cli_install_drift_projection() takes 0 positional arguments but 1 was given
=========================== short test summary info ============================
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[unselected-stale-host-text]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[unselected-stale-host-json]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[skip-first-unselected-report-text]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[skip-first-unselected-report-json]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[default-resolved-subset-text]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[default-resolved-subset-json]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[no-detected-hosts-text]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[no-detected-hosts-json]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[all-resolved-subset-text]
FAILED tests/test_cli_install_drift.py::test_install_residual_drift_matches_resolved_targets[all-resolved-subset-json]
FAILED tests/test_cli_install_drift.py::test_targeted_install_retains_selected_foreign_package_drift
FAILED tests/test_cli_install_drift.py::test_install_drift_reporting_failure_remains_advisory
12 failed, 7 passed in 0.50s
```
