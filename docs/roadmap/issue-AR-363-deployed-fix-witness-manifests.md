---
title: "AR-363: Attest deployed fixes with per-host witness manifests"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [install, drift, attestation, baseline]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-358-installer-doctor-trust-chain-self-healing.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-363
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/436
depends_on: []
blocks: []
---

# AR-363: Attest deployed fixes with per-host witness manifests

## Problem

Nothing attests that the runtime a host actually executes carries the
fixes main claims to ship. Measured 2026-09-01: a live session ran
launcher projection `e5e2e193` while the last install had published
`8698cca9` — stale hooks executing pre-fix code, detected only because
a SessionStart notice happened to say so. Version stamps prove what was
installed, not that each documented fix's load-bearing code is present
in what runs.

## Current state

The battery baseline records harness versions per host. Fix presence
is unverified; drift between published projection and wired host is
surfaced ad hoc.

## Approach

Adopt a witness layer (concept lifted from ruflo's verification
system, owner-approved 2026-09-01):

- A registry of documented fixes, each with the file and a load-bearing
  marker (e.g. AR-345's clause-boundary regex, AR-346's
  `_FAIL_OPEN_RUN_STATUSES`).
- Per-host manifests recording projection digest + per-fix marker
  verification for the projection each host's wiring points at,
  written at install/battery time.
- An append-only history log per host so drift can be bisected to the
  snapshot that introduced it.
- The battery fails a host whose wired projection lacks a registered
  fix marker or diverges from the published projection.

## Implementation (2026-09-01)

Landed as the witness layer described above, in
`agency_runtime/core/deployed_fix_witness.py`:

- `FIX_REGISTRY`: six `DocumentedFix` entries, each pinning one
  site-packages-relative file to one load-bearing literal: AR-345
  (`_VERIFICATION_CLAUSE_BOUNDARY` in `core/workforce/plan_policy.py`),
  AR-346 (`FAIL_OPEN_RUN_STATUSES`) and AR-366
  (`turn_never_received_staffing_contract`) in `core/rule8_evidence.py`,
  AR-355 (the kernel v5 "A governed workforce of specialists exists" line
  in `core/resident_managers.py`), AR-365 (`def get_latest_run_for_session`
  in `core/store/evidence.py`) and AR-366's Stop-path reason
  `turn_closed_fail_open` in `adapters/hooks.py`.
  `test_every_registry_marker_is_present_in_the_working_tree` asserts each
  literal against the checkout so the registry cannot rot silently.
- `attest_host(host, *, agency_home, claude_home, source_package, record)`
  resolves the *published* digest from the per-host install pointer
  (`installed_runtime_pointer`) and the *wired* digest from `host_wiring`
  where that is measured (Claude only today); every other host is attested
  against its published pointer and the manifest records
  `wired_source: installed-pointer` instead of implying a measurement.
  Each registered file is read from the wired projection with a bounded,
  link-resistant read below the owner-private launchers root
  (`validate_private_directory`), recording `{fix_id, present, state,
  file_sha256}`. Status vocabulary: `attested`; `drift`
  (`published_projection_mismatch`, the stale-hook shape, or
  `source_projection_mismatch` when a source package was given and
  `plan_private_package_runtime` disagrees); `missing_fix`
  (`fix_marker_absent`, naming the fixes); `unavailable`
  (`no_installed_pointer`, `projection_missing`, `projection_untrusted`).
  Drift outranks availability: a host provably invoking something other
  than what was published is the headline even if that projection is gone.
- Records: `~/.agency-runtime/witness/<host>.json` (schema
  `agency.deployed-fix-witness.v1`, atomic replace, mode 0600) and the
  append-only `~/.agency-runtime/witness/<host>.history.jsonl`, one
  compact line per attestation with timestamp, digests, status and per-fix
  presence; a full window (1 MiB) is rotated aside once so the newest
  entries always survive. `witness_history(host, limit)` reads newest-last,
  bounded to 1000 entries, skipping malformed lines rather than trusting
  them.
- CLI: `agency evidence witness [--host H] [--json]`
  (`cli/evidence_commands.py::cmd_evidence_witness`, parser entry beside
  `evidence wiring`). It defaults to every host with a recorded pointer
  (`runtime_staleness.recorded_hosts`, a new public wrapper), records the
  verdict, and exits 1 unless every host is attested.
- Battery: `harness_battery._witness_detail(host)` (never raises) attaches
  `detail["witness"]` after the posture scan; a `drift` or `missing_fix`
  verdict flips a passing host to `failed` with reason
  `deployed_fix_witness_failed`, so the proven version is not advanced. An
  `unavailable` witness is reported and counted neither way.

Tests: `tests/test_deployed_fix_witness.py` (26: registry integrity;
attested; stale-hook drift; drift with the projection gone; missing marker;
missing file; history append order and bound; rotation; malformed lines;
pointer fallback for unmeasured and unreadable wiring; no pointer; absent
or untrusted projection; source drift and unplannable source;
`record=False`; recording failure; invalid host; CLI text, JSON and empty
paths),
`tests/test_harness_battery.py::test_witness_drift_fails_a_host_whose_canary_passed`
and `::test_an_unavailable_witness_never_flips_a_passing_host`,
`tests/test_runtime_staleness.py::test_recorded_hosts_lists_every_host_with_a_pointer_by_name`,
and the refreshed parser golden in `tests/test_cli_parser_contract.py`.

Design decisions and findings:

- Only Claude's wiring is measured (`host_wiring_drift`), so the stale-hook
  shape is provable only there; codex, hermes and openclaw attest the
  published projection and say so. Measuring their wiring is one
  `host_wiring_drift` table entry each, not a witness change.
- The battery runs the witness only for hosts that are *due* (observed
  harness version changed, or `--force`); `agency evidence witness` is the
  on-demand path and records the same manifest and history. Install-time
  recording (the Approach's "install/battery time") is not wired here: the
  installer already writes the pointer the witness reads, and a follow-up
  can call `attest_host` right after `record_installed_runtime`.
- `source_package` is opt-in because planning hashes the whole
  distribution closure and a digest from another environment never agrees
  (see `runtime_staleness`); a refused plan is `unplannable`, never drift.
- The witness never parses `runtime-manifest.json`; it hashes the files it
  reads, so a bisect compares `file_sha256` across history lines directly.
- Verified before pinning: every registry literal exists on main at
  `9558e806` (`grep -n` per file, then the tree-integrity unit test).

## Dependencies

- Extends the AR-337 battery-on-version-change discipline.

## Acceptance

- [x] Each host's wired projection is attested against the fix registry
      at battery time; a missing marker or projection drift fails that
      host. Evidence: `harness_battery._witness_detail` plus the
      `run_battery` outcome flip;
      `tests/test_harness_battery.py::test_witness_drift_fails_a_host_whose_canary_passed`,
      `::test_an_unavailable_witness_never_flips_a_passing_host`;
      `tests/test_deployed_fix_witness.py::test_a_projection_missing_one_marker_is_missing_fix_and_names_it`.
      Scope: the wired projection is measured for Claude; the other hosts
      attest their published pointer and the manifest says so.
- [x] The stale-hook shape (wired digest != published digest) is
      detected by the witness check, covered by a regression test.
      Evidence:
      `tests/test_deployed_fix_witness.py::test_the_stale_hook_shape_is_detected_as_drift`
      and `::test_drift_is_reported_even_when_the_invoked_projection_is_gone`.
- [x] Witness results append to a per-host history usable for bisecting.
      Evidence:
      `tests/test_deployed_fix_witness.py::test_history_appends_one_line_per_attestation_newest_last_and_bounded`
      (per-fix presence flips from `true` to `false` on the line that
      introduced the regression) and
      `::test_a_full_history_is_rotated_so_the_newest_window_survives`.
