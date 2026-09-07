---
title: "AR-181 smoke implementation and Linux evidence reconciliation"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, smoke, performance, isolation, packaging]
related:
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
  - docs/roadmap/handoffs/issue-AR-181.md
  - docs/decisions/0026-explicit-test-home-boundaries.md
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
supersedes: []
superseded_by: null
---

# AR-181 smoke implementation and Linux evidence reconciliation

This is a source-and-execution receipt, not an acceptance verification verdict.
AR-181 remains open. The Windows-only timing criterion is explicitly unverified
by this Linux investigation. Commands/results below were already executed on
September 7; writing this receipt did not rerun them.

## Source contract and the contradictory home criterion

Implementation commit `c625bc76707e169f4c4100fb6dc1247bbddb77c7` added lazy
multi-host launcher reuse. Its parent already created one temporary home and
Store outside the host loop (`agency_runtime/core/smoke.py` at that parent,
lines 537-598). The implementation did not change that arrangement. Thus the
original criterion "Every selected host still receives its own isolated
temporary home" did not describe even the original code.

[ADR-0026](../../../decisions/0026-explicit-test-home-boundaries.md) requires an
explicit `home_dir` for generated host artifacts; changing home environment
variables is not an adequate substitute. It does not require host-to-host home
separation. Current [run_smoke](../../../../agency_runtime/core/smoke.py) at
lines 609-724 prepares once for a multi-host invocation, binds that launcher
around each generated-host check, and passes the same explicitly allocated
temporary home to each. Each host has a distinct plugin path. Configuration and
Store paths are scoped to that home, with process configuration caches reset
before and after execution.

[The isolation regression](../../../../tests/test_smoke_isolation.py) at lines
13-61 explicitly asserts one shared Store path, no creation of the simulated
operator Store, and zero installed-runtime pointer publications.
[The reuse regression](../../../../tests/test_smoke_coverage_complete.py) at
line 525 checks exactly one preparation and the same bound pair for all hosts.
[AR-291](../../issue-AR-291-isolate-smoke-runtime-pointers.md) owns the separate
pointer-isolation repair; `installer_orchestration.py` lines 338-357 suppress
pointer publication for explicit-home generation.

These facts explain the contradiction, not a new architecture. The parent
publication explicitly reconciles criterion 2 to ADR-0026's existing boundary:
full per-host contract checks within one explicitly supplied private invocation
home, isolated from the operator, with distinct host bundle paths. The original
wording quoted above is retained as provenance; it is not called satisfied.
This changes one erroneous checklist description, not runtime isolation.

## Focused Linux tests

Run from the repository checkout. Source was unchanged across the investigation
from `d2125438910d873a116a11b2ce2cb7f27209beeb` through `cbe82aaf`:
`git diff --exit-code d2125438 -- agency_runtime tests` exited zero. Local
interpreter paths identify the executed environment, not a prerequisite for
reading this receipt or a dependency on another repository.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest \
  tests/test_smoke_isolation.py tests/test_smoke_coverage_complete.py \
  tests/test_doctor.py::test_smoke_all_exercises_generated_host_plugins_with_fresh_roster \
  tests/test_doctor.py::test_openclaw_smoke_uses_static_validation_when_node_is_unavailable \
  -q -W error -k 'not windows'
```

Exit zero; raw stdout:

```text
.....................................                                    [100%]
37 passed, 2 deselected in 6.59s
```

The two deselections are the `windows_command` and `windows_call_operator`
parameters of `test_codex_marketplace_smoke_rejects_invalid_handler_schema`.
They were not executed or counted as Windows evidence.

## Existing installed CLI: 4.25 seconds

The actual installed `agency` command was run from `/tmp`, with source import
overrides removed. It used the existing AR-348 environment, not a newly built
AR-181 wheel. Read-only `cmp` checks for installed versus source `core/smoke.py`
and `core/installer_orchestration.py` both exited zero; this comparison does
not assert whole-package build identity.

```bash
umask 077
/usr/bin/time -p timeout 120s env -u PYTHONPATH agency smoke --all --json
```

Exit zero. The following is a **selected-field projection**, not the full raw
JSON. `<smoke-home>` replaces the invocation's removed private temporary root;
all generated paths shared that root. SQLite table counts are omitted, not
inferred. Every check and its status is retained.

```json
{
  "passed": true,
  "passed_count": 8,
  "failed_count": 0,
  "skipped_count": 0,
  "checks": [
    {
      "name": "sqlite_store", "status": "pass",
      "detail": {"db_path": "<smoke-home>/agency.db", "db_size_bytes": 950272,
                 "wal_size_bytes": 0, "shm_size_bytes": 0}
    },
    {
      "name": "routing_roster_available", "status": "pass",
      "detail": {"agent_count": 265, "source": "starter_roster"}
    },
    {
      "name": "host_parity_eval", "status": "pass",
      "detail": {"passed_count": 5, "failed_count": 0}
    },
    {
      "name": "plugin_claude", "status": "pass",
      "detail": {"host": "claude", "format": "claude-plugin-bundle",
        "mcp_server": "agency-runtime",
        "hooks": ["PostCompact", "PostToolUse", "PostToolUseFailure", "PreToolUse",
          "SessionEnd", "SessionStart", "Stop", "SubagentStart", "SubagentStop",
          "UserPromptSubmit"],
        "plugin_path": "<smoke-home>/.agency-runtime/marketplaces/claude/plugins/agency-preflight/.claude-plugin/plugin.json"}
    },
    {
      "name": "plugin_codex", "status": "pass",
      "detail": {"host": "codex", "format": "codex-plugin-bundle",
        "mcp_server": "agency-runtime",
        "hooks": ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
          "SubagentStart", "SubagentStop", "PostCompact", "Stop"],
        "plugin_path": "<smoke-home>/.agency-runtime/marketplaces/codex/plugins/agency-preflight/.codex-plugin/plugin.json"}
    },
    {
      "name": "plugin_hermes", "status": "pass",
      "detail": {"host": "hermes", "adapter": "HermesBridge",
        "tools": ["agency_finalize"],
        "plugin_path": "<smoke-home>/.hermes/plugins/agency-preflight/__init__.py"}
    },
    {
      "name": "plugin_openclaw", "status": "pass",
      "detail": {"host": "openclaw", "format": "openclaw-js",
        "syntax_check": "passed",
        "plugin_path": "<smoke-home>/.agency-runtime/host-plugins/openclaw/agency-preflight/index.js"}
    },
    {
      "name": "plugin_zcode", "status": "pass",
      "detail": {"host": "zcode", "format": "zcode-config-hooks",
        "hooks": ["SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
          "PostToolUse", "PostToolUseFailure", "Stop"],
        "idempotent": true, "preserved_existing_config": true,
        "process_hook_invoked": true, "toggle_verified": true,
        "plugin_path": "<smoke-home>/.agency-runtime/host-plugins/zcode/agency-preflight/zcode-hooks.json"}
    }
  ]
}
```

Raw timing:

```text
real 4.25
user 3.36
sys 0.22
```

The generated ZCode SessionStart subprocess and OpenClaw syntax check ran; no
native model-host session, staffing inference, or real host registration ran.
The ephemeral root was absent afterward (`test ! -e` exited zero).

Isolation does not mean zero filesystem writes: the smoke creates temporary
config/Store/bundles and may use or stage an immutable private launcher cache.
It does not prove byte-identical operator state through a before/after audit;
no such audit was performed for this run. Explicit-home source boundaries and
focused isolation tests are the evidence for destination isolation.

## Preparation-failure diagnostic

A separate in-memory probe replaced the host inventory with Claude, Codex and
Hermes, stubbed deterministic parity success, made launcher preparation raise
`OSError("AR181 diagnostic launcher unavailable")`, and made any generated-host
call an assertion failure. The production smoke aggregation returned:

```json
{
  "prepare_calls": 1,
  "generated_calls": 0,
  "passed": false,
  "failed_count": 3,
  "skipped_count": 0,
  "host_checks": [
    {"name": "plugin_claude", "status": "fail",
     "error": "RuntimeError: shared smoke launcher preparation failed: OSError: AR181 diagnostic launcher unavailable"},
    {"name": "plugin_codex", "status": "fail",
     "error": "RuntimeError: shared smoke launcher preparation failed: OSError: AR181 diagnostic launcher unavailable"},
    {"name": "plugin_hermes", "status": "fail",
     "error": "RuntimeError: shared smoke launcher preparation failed: OSError: AR181 diagnostic launcher unavailable"}
  ],
  "elapsed_seconds": 0.343
}
```

The diagnostic process exited zero after asserting these expected failure
properties. Its smoke result was false, not a product pass. This was not a new
committed regression test or a model-backed evaluation.

## Separate exact fresh wheel: AR-407

The [AR-407 receipt](AR-407-scoped-install-drift-20260907.md) owns the exact
producer/build/install commands, portable artifact verification, strict Twine,
packaged smoke, `pip check`, and aggregate run. Its clean candidate is
`ef6523b3779e7673051c1b758174d42ef64961d4`, built with producer umask `077`.
The wheel SHA-256 is
`f3e9cbfaf7db064725e39bb851a33f502a228400bf5842c697b919e32a8c949d`;
sdist SHA-256 is
`d1396b523570500146d15b71af3a51ab7c7e5634d36eb1373f329fb8c7f7f6c9`.

A new virtual environment installed that wheel with PyYAML 6.0.3. Isolated
installed-distribution smoke passed assets/config, loopback dashboard health,
MCP status/tool inventory and 265-member roster checks. Its subsequent
`python -I -m agency_runtime.cli smoke --all --json` passed eight checks with
zero failures or skips in `real 5.09`, `user 3.87`, `sys 0.24` seconds.

That Linux fresh-wheel result is reusable evidence for the original artifact
criterion; it is not the earlier existing-install 4.25-second result and is not
native Windows evidence. AR-407 merged in PR #729 as fdb010ff at23:01:56Z;
its exact receipt is integrated before this package's publication.

## Remaining boundaries

- Preserve the original Windows-only under-two-minute criterion. The owner will
  perform Windows work on Windows; Linux success neither fulfills nor waives it.
- Preserve the original separate-home wording as historical provenance while
  explicitly reconciling the canonical criterion to existing ADR-0026.
- This receipt assigns no acceptance verdict and does not mark AR-181 done.
- Generated bundle, hook syntax, temporary config, deterministic parity, and
  installed-package checks do not prove native model-turn injection, actual
  specialist delivery, trust approval, or production activation.
- No new runtime code, live canary, provider call, native registration, tracker
  write, exhaustive suite, coverage shard, or compatibility matrix was needed
  to record these already-observed facts.
