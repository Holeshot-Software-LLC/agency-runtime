---
title: "AR-271 merged-main installation and scoped harness smoke"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, installation, smoke, evidence, backlog]
related:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/acceptance/issue-AR-271.md
  - docs/roadmap/acceptance/evidence/AR-271-stopped-uninstall-20260905.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-400-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-271 merged-main installation and scoped harness smoke

## Delivered source and recoverability

PR #678 merged the accepted AR-405 test-portability repair at 78e501b7 and
closed tracker #675. PR #679 merged the accepted AR-271 stopped-gateway
uninstall repair at 5434836eec4efe70432e50ca3c732dc65c63e209 at 19:55:36Z.
Both used ordinary clean merges; no hosted checks were registered and no
administrative bypass was used. Local verification is recorded separately.

At 20:00Z, a new owner-private, non-editable virtual environment installed the
official repository at that exact full merge SHA. The existing PATH launcher
was backed up before changing only its interpreter path. The old environment
and launcher backup remain available; no previous installation was deleted.
Package metadata inspected outside the checkout confirms the same VCS revision.
The package build produced wheel SHA-256
ad25cb02c79e5d8ad0ec19d20776b1dda5e26f83ca0a00e14fe5d3fec64e7bf8.

Observed `agency version --json`:

```json
{
  "build_identity": "0.1.0+g5434836eec4e",
  "install_kind": "vcs-package",
  "official_repository": true,
  "package_version": "0.1.0",
  "source_revision": "5434836eec4efe70432e50ca3c732dc65c63e209"
}
```

The refreshed launcher projection is
1d617ca589a24829dbae5601567ef8c1f576c2fecf7eae3bd43b912f8732155a.
`git diff --exit-code 4fdcd6a7 5434836e -- agency_runtime tests scripts
pyproject.toml` passed: the merged runtime/test/tool source matches the isolated
acceptance candidate. Subsequent delivery records do not change that source.

## Integration refresh: partial, not full live activation

`agency install --all --json` returned exit 1, partial=true, complete=false.
Seventeen existing contractors were observed; none were installed or upgraded.
The managed dashboard service reloaded and restarted successfully on the new
interpreter/projection and reported active, enabled and reachable.

| Host | Observed installation result | Remaining live boundary |
|---|---|---|
| Claude | Registered and enabled; refreshed owned bundle with backup | Fresh isolated readiness passed at 20:02:06Z; live execution was not attempted because this shell lacks the configured LITELLM_API_KEY. No current-build child or ordinary-session proof is claimed. |
| Codex | Registered and enabled; refreshed plugin/cache and owned bundle with backup | Activation incomplete; eight hooks need attended review in a fresh terminal TUI. No trust bypass or live activation is claimed. |
| Hermes | Registered and enabled; refreshed owned bundle with backup | Runtime loading is unverified; a supported fresh ordinary-session proof remains. |
| OpenClaw | Refused before plugin replacement; gateway status proved live | Existing integration remains in place. Stopped-gateway installation needs explicit service-interruption consent; no stop, restart or uninstall occurred. |
| ZCode | Seven owned handlers registered/enabled; global hooks switch preserved; backup retained | Runtime loading and an ordinary host session remain unverified. |

The installer reported an applied Claude trust-chain repair under its recorded
consent: fourteen owner-owned npm-package entries were group-writable and were
repaired, with zero failures or unowned entries. No additional manual permission
or credential repair was performed. Claude's enable subcommand reported
already-enabled; final inventory confirmed registration and enablement.
This managed installation activity is distinct from the preceding code-only
regression/acceptance package's no-permission-change claim.

The Claude preflight returned ready=true, unmet_prerequisites=[],
live_attempted=false, canary_passed=false and trust_bypass_used=false.
A separate presence-only configured-credential check returned
LITELLM_API_KEY=false; no credential value was printed, created or changed.
The earlier successful isolated Claude canary at 16:51:15Z belongs to build
1de05aea and is not transferred to this build. An already-running parent hook
process may still retain its older projection after installed files refresh.

Codex recovery remains attended: close the old terminal TUI, launch a fresh
`codex`, review all eight Agency hook events through the startup trust review
or terminal `/hooks`, then start a new session and run
`agency install --agent codex --verify-activation`. Desktop connector `/hooks`
is not the terminal command-hook trust screen.

## Installed-source deterministic smoke

Immediately-preceding context telemetry reported 82.3 percent remaining.
`agency smoke --all --json` on the installed build returned exit 0:
passed=true, passed_count=8, failed_count=0, skipped_count=0.

| Check | Result | Exact scope |
|---|---|---|
| SQLite store | pass | Disposable store initializes with expected tables |
| Routing roster | pass | Starter roster contains 265 agents |
| Host parity | pass | Five deterministic cases, zero failures |
| Claude plugin | pass | Generated bundle, ten hook events and MCP server |
| Codex plugin | pass | Generated bundle, eight hook events and MCP server |
| Hermes plugin | pass | HermesBridge and agency_finalize tool |
| OpenClaw plugin | pass | Generated JavaScript passes syntax check |
| ZCode hooks | pass | Process hook invocation, idempotence, preserved config and toggle |

These checks generate disposable host contracts from the installed source.
They do not prove five live native sessions, gap hiring, latency distributions,
or the real stopped-gateway uninstall transaction.

## Verification and remaining work

AR-271 has three satisfied isolated criteria against 4fdcd6a7; AR-405 has three
against 593f074f. AR-271 focused tests: 248 passed/two Windows-only skips;
named Python spine: 1030 passed/three skips; UI: 138 passed; docs/acceptance/
tracker tests: 104 passed. Routing passed. Protected decision conformance
passed baseline and killed 182/182 mutations with zero invalid/surviving and
source unchanged. The linked bounded evidence retains the red regression.

No native Windows execution, exhaustive warning-strict corpus, four-shard
coverage gate, six-interpreter matrix or workflow dispatch was run. No real
OpenClaw uninstall was used to force AR-271 or AR-285 completion. AR-285 still
needs its distinct two evidence gaps. AR-404 remains in_progress with 146
unfinished baseline items plus the coordinator; AR-298 verification and the
real AR-348/349 hiring-safety gaps remain bounded follow-up packages.
