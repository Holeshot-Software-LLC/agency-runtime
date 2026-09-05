---
title: "AR-348 merged-main installation and scoped harness smoke"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, hiring, installation, smoke, evidence]
related:
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/roadmap/acceptance/issue-AR-348.md
  - docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md
  - docs/decisions/0221-enforce-hiring-independence-on-resolved-provider-chains.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: evidence
---

# AR-348 merged-main installation and scoped harness smoke

## Published outcome

PR #687 merged the accepted strict hiring-independence repair at
0309f251c6cf1c6c22b3a4458302c8b2cad78734 on 2026-09-05 at 22:19:51Z.
The ordinary merge matched reviewed head 2cacdfce; no hosted checks were
registered and no administrative bypass was used. Local gates are recorded
separately. Tracker #406 (AR-348, not AR-406) closed as completed at 22:20:23Z;
read-back confirmed CLOSED. Fresh enumeration returns 42 open tracker issues.
The separate unfinished local queue is 141: 42 mapped plus 99 legacy records.
Those legacy records are not 99 demonstrated current defects.

Both unchanged AR-348 criteria are satisfied against c9b678a5. Git comparison
confirms runtime/test/project source is unchanged between that candidate and
the delivered revision. The linked evidence preserves the 20-failure red
reproduction, 413 focused passes/one skip, 1075 named-spine passes/three skips,
138 UI passes, routing pass, and protected baseline plus 184/184 mutation kills
with zero survived/invalid and source unchanged. The two ambient-umask fixture
failures remain failures, not retroactively successful evaluations.

## Immutable installation and recovery

A new owner-private non-editable environment installed the official repository
at the exact full merge SHA with a process-local 0077 umask. The previous
environment remains intact. The PATH launcher was backed up with metadata
before changing only its interpreter path. Nothing was deleted. The built
wheel SHA-256 is
b2a5bd7a63f9ab4c6df70cc893f55a69b5d542f684f9562b0c7fad885910ec1d.

Outside the checkout, agency version --json reports:

```json
{
  "build_identity": "0.1.0+g0309f251c6cf",
  "install_kind": "vcs-package",
  "official_repository": true,
  "package_version": "0.1.0",
  "source_revision": "0309f251c6cf1c6c22b3a4458302c8b2cad78734"
}
```

Every Git-tracked agency_runtime file was compared byte-for-byte with its
installed site-packages counterpart; every comparison passed. pip check reports
no broken requirements. The managed dashboard launched the new immutable
runtime projection 4329d76058d18eaa6b02f0b5750ff5533462064028c1178a8b5e913364774fac.
This is a local VCS package delivery, not a signed release or cross-OS artifact
publication.

## Installed behavior, not just source tests

From outside the checkout, the test-equipped development interpreter explicitly
imported the new installed package and asserted its exact module origin before
calling pytest.main. PYTHONPATH selected only that installed site-packages
directory, not repository runtime source. The committed dynamic-hiring tests
were selected with -k strict_independence -q -W error --tb=short:
45 passed, 70 deselected, 11.94s. No pytest dependency was added to the installed
runtime. Providers were deterministic fakes and Store state was disposable.

Immediately-preceding smoke telemetry reported 62.8 percent remaining.
agency smoke --all --json from the installed PATH launcher, outside the
checkout, returned exit 0: passed=true, passed_count=8, failed_count=0,
skipped_count=0.

| Check | Result | Scope |
|---|---|---|
| SQLite store | pass | Disposable schema and table initialization |
| Routing roster | pass | 265 starter agents available |
| Host parity | pass | Five deterministic cases, zero failures |
| Claude plugin | pass | Generated bundle, ten hook events and MCP server |
| Codex plugin | pass | Generated bundle, eight hook events and MCP server |
| Hermes plugin | pass | HermesBridge and agency_finalize tool |
| OpenClaw plugin | pass | Generated JavaScript syntax |
| ZCode hooks | pass | Process invocation, idempotence, preserved config and toggle |

## Native refresh remains partial

Hosts were refreshed sequentially. Codex used agency install --agent codex
--json, which also refreshed the managed dashboard. Claude, Hermes and ZCode
used their explicit --agent with --no-dashboard --json to avoid redundant
dashboard restarts. Seventeen existing contractors were observed; none were
installed or upgraded.

| Host | Observed result | Remaining boundary |
|---|---|---|
| Codex | Owned files backed up and refreshed; registered/enabled; command exit 1 because activation remains incomplete | Attended terminal hook trust unverified; loaded=null, canary=false; no bypass |
| Claude | Command exit 0; registered/enabled with backup | loaded=null, enabled-runtime-unverified; fresh live session not claimed |
| Hermes | Command exit 0; registered/enabled with backup; hook budget read | loaded=null, enabled-runtime-unverified; fresh live session not claimed |
| ZCode | Command exit 0; seven owned handlers registered/enabled; config merged with global hook state preserved | loaded=null, enabled-runtime-unverified; fresh live session not claimed |
| OpenClaw | Not refreshed; existing running-gateway boundary respected | Still references prior 1d617ca589a2 projection; no stop/restart/uninstall consent inferred |

The managed dashboard reloaded and restarted successfully, active/enabled and
reachable on the new projection. Claude's installer reported its consented
trust-chain repair: fourteen owner-owned group-writable package entries changed,
zero failures/unowned entries. The already-enabled native subcommand returned
1; final inventory confirmed enabled, and the overall Claude install returned
0. These are observed managed-install side effects, separate from the code
package's no-permission-change scope. No manual permission repair was made.

Codex recovery is attended: close the old terminal TUI, launch a fresh codex,
review all eight Agency hook events in startup review or terminal /hooks, then
start a new session and run agency install --agent codex --verify-activation.
The Desktop connector /hooks screen is not this local hook-trust surface.
An already-running parent process can retain old runtime code after file
refresh; no claim is made that this session hot-reloaded it.

A presence-only check found LITELLM_API_KEY absent from this shell; no credential
value was printed by that check, created or changed. No current-build live
Claude inference was attempted. The eight smoke checks establish disposable
host contracts, not five live native sessions, hiring quality or a new staffing
latency distribution. No Windows execution, exhaustive corpus/coverage matrix,
cross-interpreter matrix, workflow dispatch, or real OpenClaw lifecycle action
was run. AR-348's bounded contract is done; AR-349 remains the next separate
rejected-hire persistence package and AR-404 remains in_progress.
