---
title: "AR-409 exact-main installed delivery, 2026-09-07"
status: active
category: acceptance
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, installation, live-evidence]
related:
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/roadmap/handoffs/issue-AR-409.md
  - docs/roadmap/acceptance/issue-AR-409.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# Exact-main installed delivery

## Scope and source

Source PR #739 merged as `4db6be169a4f86185c261d93814f1106d79f0136`
at 2026-09-08T00:15:47Z. All five isolated source criteria are satisfied
against frozen candidate `f670e6b5`. This receipt does not replace their
judgments or assert native success from generated-host checks.

## Exact-main artifact

A detached clean checkout of the merge was built under umask 077; canonical
build, independent portable verifier and strict Twine check all exited zero.

- Wheel SHA256: `8b99fb08e6b6f8e333db00f673540dc4f118316ccde29b76b1ca83710cb9d67f`.
- Sdist SHA256: `2fc3a119d60755644393538c3d469c89a2f76f08122e4313cba9a38669464960`.
- Fresh isolated wheel installation: Agency 0.1.0, PyYAML 6.0.3, pip check clean.
- Installed distribution smoke: ten assets, configuration, loopback dashboard
  health, eight MCP tools/status, 265 approved roster cards and safe offline
  selection abstention passed.
- Installed aggregate smoke: eight passed, zero failed/skipped, all five
  generated hosts, actual generated ZCode hook execution and OpenClaw syntax.
  Elapsed 5.73 seconds; this is not native provider/harness proof.

## Owner installation and preservation

The existing owner CLI environment was upgraded from VCS `0309f251` to exact
merge `4db6be16` using the public pip command emitted by the read-only upgrade
plan. Installation ran 00:18:33.222144–00:18:39.688271Z and exited zero.
Installed direct-url metadata names the exact merge; all 613 package payload
files byte-match the independently built wheel. Pip check remains clean.
The environment's historical directory name does not identify its source.

The owner wrapper and configuration stayed byte-identical and retained their
recorded inode/mode/timestamps. Four normal `agency install --agent HOST
--no-dashboard --json` commands exited zero:

| Host | UTC interval | Observed scope |
|---|---|---|
| Codex | 00:19:12.161427–00:19:17.108567 | Registered/enabled; activation unverified, restart required |
| Claude | 00:19:55.986549–00:19:58.964779 | Registered/enabled; loaded unknown |
| Hermes | 00:20:26.002348–00:20:28.374032 | Installer exited zero |
| ZCode | 00:20:27.208560–00:20:28.532534 | Installer exited zero |

All four current-host pointers now identify runtime
`1b6aafe178de51ba79ac95fa1126ccdf3448855903f73d6da22f158835549edd`
instead of `4329d76058d1`. Codex plugin version is
`0.1.0+codex.426db7dc3495`; bundle digest is
`de0ad33410b550feae573076f40e04498902327d17f851dca5177f0e04cc9f2f`.
Its installation explicitly did not claim activation or native trust proof.

OpenClaw's separate installation was intentionally preserved: runtime
`1d617ca589a24829dbae5601567ef8c1f576c2fecf7eae3bd43b912f8732155a`;
pointer SHA256
`b9072db1ec008765e797f2982b90a3cd316f0d1f2efb02e0b15e5a2fafa6c39a`,
inode, mode and timestamps unchanged. The existing dashboard service was not
replaced or restarted. No profile, budget, credential or trust-policy change.

Before Claude refresh, the two exact owned executable namespace directories
were again 0775; one nonrecursive removal of group-write restored the existing
guard's required state. Recurrence actor remains unknown; no updater was stopped.

## Native checkpoint

Pending fresh installed native tests. Existing earlier Codex and OpenClaw live
receipts remain historical and keep their exact source scope. A refreshed
on-disk hook does not retroactively replace the running parent process.

Raw installation, artifact and pointer receipts remain owner-private; this
repository contains their bounded evidence projection, not credentials or model
bodies. No exhaustive workflow or native Windows work was run.

