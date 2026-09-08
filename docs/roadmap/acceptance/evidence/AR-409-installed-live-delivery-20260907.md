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

### Codex: new hook hashes require approval

The installed read-only trust inspector ran at 00:30:44.246566–.789038Z,
exit zero, with its existing ten-second bound. It found all eight expected
events enabled and present, but all eight modified and zero trusted; all other
inventory discrepancy/error counters were zero. This differs from the earlier
trusted inventory because the exact installed hook definitions have changed.

One normal current-profile activation verification ran at
00:30:45.752193–00:30:49.240622Z and exited one. It reported
`verification_only=true`, `installation_attempted=false`,
`canary_passed=false` and no attestation. Its invocation refused at
`codex_hook_trust_not_ready` before producing native output or child evidence.
The outer report labels the request `live_attempted=true`; this is not proof
that a model call or native child ran. No approval, bypass or retry was used.
AR-192 retains the attended operator-trust gate.

### ZCode: native test unavailable

The first diagnostic attempted the ordinary battery API with ZCode and received
`ValueError: unsupported battery harness: zcode` before any host launch. This
was an orchestration mistake, not a discovered product regression or pass.
The supported read-only `agency host-canary zcode` inspection then ran
00:31:53.492462–00:31:54.397299Z, exit one: installation registered/enabled,
launcher artifacts current, no configuration drift, but executable absent,
version unproven and no proven bounded native-child noninteractive mode.
`live_attempted=false`, no attestation. Generated-hook process smoke passed
separately; it cannot replace this unavailable native check.

### Claude: warm-up consumed the real task's shared deadline

One native isolated-profile attempt ran 00:31:38.851940–00:34:43.527843Z
(184.675903 seconds including capture), CLI exit one/native exit 124:
`claude_exec_timed_out`. The native 180-second deadline and outer 420-second
capture limit were unchanged. An observational wrapper retained safe header
fields/body hashes and returned the original result unchanged. Actual response,
stdout and stderr were empty: no five-field header, child artifact, accepted
finalization or attestation. Isolated plugin fields were registered/enabled;
the aggregate successful-profile predicate was not satisfied. No loaded claim.

Read-only Store inspection binds two different sessions by exact message
fingerprint, not time-window inference:

- Fixed warm-up trace `814cf677-78fb-42ba-87ce-954cc96f57d9`, fingerprint
  `98976a3a0ed01514b7319c96bde352e06c6bd47e15723dc9d0be2ad77f2253d0`,
  is SHA256 of the literal one-word-response warm-up. Its preflight ran
  00:31:45.709785–00:33:17.796000Z and failed with `inference_invalid`.
  One subject attempt was rejected (4,459ms), planner rejected
  `plan_response_semantic_invalid` (24,747ms), planner retry timed out (60,094ms).
  Each effective allowance was 60,000ms; total recorded provider time 89,300ms.
  Provider `agency-planner` requested `task-agency-planner-v2`; subject returned
  actual model `glm-5.3-flash`, planner returned the alias, timeout had no model.
- Actual nonce trace `079be203-53da-4769-9887-859853b1a242`, fingerprint
  `c86f13550c4ef2cd4286a2dfcbe659450d2ecf97251c0f047816d0ca4e81ddf8`,
  equals the canary's expected query hash. It began only at 00:33:25.677771Z
  and ended `canary_failed`. No routing or provider-attempt receipt survived;
  absence of that receipt does not establish zero actual provider calls.

The warm-up alone triggered full staffing. Its three attempts must not be
attributed to the nonce task. The safe receipt SHA256 is
`b2fedd31231310bb6ca6c8704bb154dbbe00283a120a1bd7581d487f86110241`.
Four installed staffing/preflight/canary modules byte-match `4db6be16`.
This reveals concrete avoidable canary bootstrap work, being scoped separately
under AR-410; it does not justify bypassing staffing on the actual test task.

### Hermes: native process returned, staffing did not complete

The actual shipped ordinary read-only task on Hermes 0.21.0 ran
00:30:27.290257–00:37:08.893337Z, exit zero without timeout (401.603080s).
Battery result correctly failed `ordinary_turn_not_staffing_complete`.
Its source witness identifies current runtime `1b6aafe178de`, no pointer drift.
There were 2,900 stdout characters, zero stderr; SHA256
`bb9b62b8ec4d90b4aa65a076724bde1492e7cae830c368b11aa22b94f0a3e8b8`.
Neither strict parsing nor an independent literal-label scan found any of the
five Agency header labels. Process exit zero is not an Agency success.

Exact own session `20260907_203036_7a0d10`, trace
`20260907_203036_7a0d10:251065a8-219a-45f2-bc69-4f7b98561706:5a031108`,
failed preflight with receipt `60360f4b-e0ff-4724-98fa-90e869c9e84f`:
`workforce_inference_failed`, staffing `inference_invalid`, not a critic veto.

| Stage | Recorded time | Result |
|---|---:|---|
| Planner, task-agency-router | 49,849ms | Applied |
| Embedding, qwen3-embedding:latest | 43,371ms | Applied; cold cache, 296 inputs |
| Reranker, qwen3-14b-abliterated:latest | 31,040ms | Response contract rejected |
| Recruiter, task-agency-router | 120,226ms | Provider timeout; 120,000ms allowance |

Run start to failure receipt is 246,407ms; summed provider times are 244,486ms,
leaving 1,921ms unattributed. This single run's provider time dominates; it is
not a paired speed/quality comparison or a CPU profiler. Claude ran concurrently.
No recruiter success or critic execution is claimed. The battery separates
foreign Claude activity from its own session rather than crediting it as proof.

### Overall boundary

AR-409 remains in_progress: the source repair, installation and truthful failure
receipts are proven; successful end-to-end installed staffing is not.
Existing earlier Codex and OpenClaw live receipts keep their source scope. OpenClaw's
installation is unchanged, so its earlier ordinary native pass remains the
available host evidence, not proof of AR-409's new source. A refreshed on-disk
hook does not retroactively replace the running parent process.

Raw installation, artifact and pointer receipts remain owner-private; this
repository contains their bounded evidence projection, not credentials or model
bodies. No exhaustive workflow or native Windows work was run.
