---
title: "AR-17: Complete production hardening and portable release gates"
status: in_progress
category: roadmap
created: 2026-07-12
updated: 2026-07-13
tags: [security, portability, quality, performance, dashboard, hosts]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0038-refuse-executable-git-configuration-during-delegation.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/decisions/0041-bounded-asynchronous-overload-responses.md
  - docs/decisions/0042-local-only-bounded-work-file-inference.md
  - docs/decisions/0043-prime-stdin-before-windows-child-resume.md
  - docs/decisions/0044-preclose-bounded-windows-child-stdin.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-17
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/17"
depends_on: [AR-18, AR-19, AR-20, AR-21, AR-22, AR-23, AR-24]
blocks: [AR-07]
---

# AR-17: Complete production hardening and portable release gates

## Problem

Broad feature coverage is not enough for an open-source production claim. The
runtime still needs a single adversarial pass across host installation,
selection and delegation, evidence, local HTTP, configuration, SQLite,
dashboard behavior, packaging, and CI. Several core files have grown too large
to review safely, and contract tests must remain distinct from live host proof.

## Current state

The session has surfaced concrete boundary defects: a late browser URL fragment
could leave an otherwise valid dashboard session unauthenticated; HTTP framing
and authorization edge cases needed explicit rejection; unchanged native
installs still performed unnecessary lifecycle work; and oversized facades
obscured platform-specific behavior. The CLI extraction also had to preserve
provider-discovery bounds and monkeypatch seams as explicit compatibility
contracts. This work is tracked under one release-gating item so each finding
has regression evidence and is not lost as an untracked cleanup.

The release audit also found that generated Python commands canonicalized the
interpreter target. On Linux that could replace a virtual-environment launcher
with the base interpreter and make an otherwise valid installed integration
unable to import Agency Runtime. Generated services and host payloads now keep
the absolute environment-owned launcher without dereferencing it. Hosted wheel
smoke also exercises real packaged MCP stdio, authenticated dashboard health,
configuration defaults, assets, and every generated host bundle outside the
checkout.

Hosted Windows also exposed a suspended-child stdin race in every PowerShell
companion case. Small bounded payloads now reach an explicitly closed pipe
before the child resumes; larger payloads retain the asynchronous writer so a
full pipe cannot deadlock a suspended reader. The regression continues to use
PowerShell's original Console.In behavior rather than substituting a different
reader. Hosted Linux exposed a second-match suffix bug in spaced-path recovery;
the scanner now skips recovered suffixes and path-like URL query or fragment
values while retaining assignment and colon-delimited local paths.

Final local evidence includes a Windows warning-strict coverage run with
`2303` passed, `5` skipped, and `2` performance tests deselected. All
`17,284` statements and `5,408` branches had zero missing lines or partial
branches (`100.00%`). Ubuntu 24.04 WSL/Python 3.12 passed `2215` tests with
`16` expected skips from native ext4, plus both performance tests. The final
performance selection passed both tests with `2308` deselected: routing p95
`8.640 ms`, cache p95 `0.385 ms`, `155.73` calls/second, and overlap `8`.
All `25` routing gates and `12/12` delegation cases passed. The dashboard
passed all `60/60` JavaScript tests at exact line, branch, and function
coverage across seven modules, plus authenticated browser smoke.

Codex 0.144.1 is registered and enabled, completed a live keyless judge result,
loaded the installed status skill, and passed direct CLI `off`/`on`. Generated-
bundle smoke validates the hook events, commands, and timeout schema. The
exact-confirmed native isolated-profile canary exited `0`, returned
`canary_passed=true` and `header_valid=true`, reported no missing header
fields, recorded one nonce-bound routing event and one correlated finalization,
and persisted the attestation for trace
`019f5bdd-612d-70c0-b369-2b038faa3d02`. It recorded no model receipt.

The canary used Codex's explicit one-invocation trust bypass only inside its
private profile. Real-profile `hooks/list` still reports the three hooks
parser-clean and enabled but untrusted. Agency Runtime conservatively reports
durable trust as `unverified`, never reads or mutates Codex's trust store, and
requires the operator to review `/hooks` and start a new session. The isolated
attestation does not promote real-profile maturity to `runtime-verified`, and
there is no live Linux Codex proof. Claude Code, Hermes, and OpenClaw were absent
and retain contract-only status.

The final security gate passed release hygiene over `377` inputs,
high-severity Bandit, strict offline Zizmor, dependency consistency, an exact
runtime dependency audit with no known vulnerability, Ruff/format over `259`
files, compileall, and whitespace validation. Fresh wheel/source artifacts
passed build, strict Twine, and distribution verification. Clean
Windows/Python 3.14 and WSL/Python 3.12 wheel installs exercised MCP and all ten
tools, authenticated dashboard health, configuration defaults, assets, and all
four generated host bundles.

## Approach

1. Threat-model every filesystem, network, process, protocol, evidence, and
   browser trust boundary; add bounded fail-closed regression tests.
2. Split the CLI, dashboard service, installer, and SQLite store along cohesive
   seams while preserving public APIs and test monkeypatch contracts.
3. Exercise selection, policy, provider fallback, delegation DAG execution,
   concurrency, headers, configuration parity, dashboard live behavior, and
   host bundle generation with deterministic and adversarial suites.
4. Add pinned lint, dependency, workflow, artifact, and code-scanning gates;
   remove dead code and keep source distributions self-contained.
5. Build and install clean artifacts on Windows and Linux, then install into the
   available real Codex profile and run a bounded native smoke/canary. Report
   absent hosts honestly instead of relabeling generated-contract evidence.

## Dependencies

This is the final integrated gate over the host, operations, provider,
dashboard, evaluation, and Linux-compatibility work. It supplies completion
evidence to AR-07 but does not authorize publication or issue closure.

## Acceptance

- [x] Warning-strict Windows and Linux suites pass from isolated environments.
- [x] Routing accuracy, policy, delegation, concurrency, and latency gates pass.
- [x] Security review, Bandit, dependency audit, CodeQL/workflow configuration,
      secret/path hygiene, and threat-model checks pass without unresolved high
      findings.
- [x] CLI, dashboard service, installer, and store are reviewable cohesive
      modules with preserved compatibility contracts and no dead facade logic.
- [x] Dashboard authentication, live updates, configuration, responsive layout,
      keyboard operation, charts, and route receipts pass deterministic and
      live browser checks.
- [x] Every measured production module reaches the documented coverage gate;
      any platform-only exclusion is narrow, justified, and reviewed rather
      than hidden by a broad omit rule.
- [x] Wheel and source distribution contents match policy and install cleanly
      on Windows and Linux without checkout-relative imports.
- [x] The installed Codex integration is registered and enabled, and its
      isolated-profile native canary is protocol-tested and smoke-tested with a
      valid evidence header; real-profile trust remains unverified and absent
      hosts remain contract-covered rather than live-verified.
- [ ] Hosted CI passes the supported Python, security, CodeQL, and artifact
      matrix for the reviewed commit, and the reviewed changes are merged.
- [ ] The working tree is clean after the implementation and its required
      worklog ledger commit; outward publication remains separately authorized.

## Verification

- The final Windows warning-strict coverage run passed `2303` tests with `5`
  skips and zero missing statements or branches. The native-ext4 WSL/Python
  3.12 suite passed `2215` tests with `16` expected skips; the final wheel
  then passed clean WSL installation and packaged-surface smoke.
- All `60/60` dashboard JavaScript tests reached exact line, branch, and
  function coverage. Authenticated Chrome loaded all seven scripts, rendered
  current state, exercised refresh, and produced no application console errors.
- The versioned routing, policy, delegation-detection, DAG, concurrency, and
  performance evaluations passed every checked-in threshold.
- Bandit, exact runtime dependency audit, offline workflow analysis, release
  hygiene, dependency consistency, formatting, compile, and whitespace gates
  passed without an unresolved high finding.
- Fresh wheel/source artifacts passed strict metadata and distribution checks;
  isolated Windows and WSL installs exercised MCP, dashboard health,
  configuration, assets, and every generated host bundle.
- The isolated Codex canary passed with a valid header and persisted
  nonce-bound evidence. Durable real-profile trust remains an explicit
  operator `/hooks` action and is not claimed by that attestation.
- Hosted CI, review/merge, the substantive/worklog ledger commits, and
  clean-tree proof remain open.
