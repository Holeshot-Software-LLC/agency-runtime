---
title: "AR-404 final exact-main installed evaluation"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [evidence, installation, verification, native]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/roadmap/acceptance/evidence/AR-409-installed-live-delivery-20260907.md
  - docs/worklog/2026-09-08-final-installed-evaluation.md
supersedes: []
superseded_by: null
---

# AR-404 final exact-main installed evaluation

## Outcome and scope

Owner requested a stopping point, all completed work on main, all-harness
installation and live evaluation. New backlog work stopped. Source candidate
`4cbebf73df18545120348628afd6848b8e67e3ff` is PR762 merged at02:06:31Z.
Earlier wrap-up PR757/759/760/761 carry fallback accounting, static timeout
routes, retention-safe resident recovery and process-drift guidance.
Native results remain pending at this clean pre-evaluation checkpoint.

## Executed source verification

- Named fast Python spine:1151 passed,3 skipped in69.91s. Dashboard224 pass.
- Fallback accounting/Store/inference:161 pass2.58s; installer/lease:186 pass,
  one skip29.28s; resident recovery/header:46 pass11.90s; explicit-file/parser:
  48 pass0.65s; runtime-staleness:39 pass0.17s; cache/Hermes:56 pass0.76s.
- Combined extra focused run:1 failed,371 passed,1 skipped39.47s. The failure
  counted UTF-8 decoration against an invented whole-card limit. Test-only
  correction proves the4096-byte content/line bound;61 card tests then pass
  in0.42s. Runtime source unchanged after the named production spine.
- Routing evaluation passed all checked-in gates, explicitly deterministic
  candidate recall only, not inference staffing or real task quality.
- Decision conformance: initial ambient umask0002 caused baseline private-path
  fixture setup failure before mutations. Corrected invocation umask0077 ran
  02:03:56.740969–02:06:56.763858Z and reached its180-second outer bound with
  no report. No success or mutation score is inferred; source unchanged and
  process inspection found no remaining owned evaluator.
- Metadata, policy, worklog, strict docs/tracker, Ruff and diff passed on the
  combined branch:1309 documents,403 roadmap items,776 Python files formatted.
  No exhaustive corpus, coverage shards, compatibility matrix or native Windows.

## Exact artifact and installation

Portable wheel SHA256:
`a02c3cb34d3fff080d674d1de14107c3342322fa0eeb7c6c16247ef0c38113dd`.
Source archive SHA256:
`c96f0a519ebc5aa5fe96ce45cf236a5d0509255ad08c58d2b9650ad7054bc9c2`.
Canonical build, independent verifier and strict Twine checks passed. Initial
build from main refused its locally ignored Claude settings file under strict
Git isolation; a fresh exact-commit detached tree passed. No user file removed.

Fresh portable wheel install:Agency0.1.0/PyYAML6.0.3, pip check clean.
Installed smoke proves10 dashboard assets, loopback health,8 MCP tools/status,
265 approved bundled roster cards and safe offline abstention. Aggregate smoke
passed8/8 with all five generated adapters, OpenClaw syntax and real generated
ZCode hook execution. These are not native host or provider results.

Owner CLI upgrade02:08:13.279188–02:08:18.707150Z exited0. Its immutable VCS
metadata names exact4cbebf73 and all614 package payload files match the wheel;
pip check is clean. Owner config SHA4913dacc8a46 and wrapper SHA c31ca4d10508
remain unchanged. No credentials or provider/profile settings were modified.

| Host | Normal installer UTC interval | Result |
|---|---|---|
| Codex | 02:09:01.715641–02:09:06.624515 | exit0; registered/enabled; activation required |
| Claude | 02:09:46.021879–02:09:48.981195 | exit0; registered/enabled; loaded unknown |
| Hermes | 02:09:49.002479–02:09:51.260723 | exit0; registered/enabled; loaded unknown |
| ZCode | 02:09:51.284265–02:09:52.587645 | exit0; registered/enabled; loaded unknown |
| OpenClaw | 02:09:52.609053–02:09:55.283488 | exit1; host_restart_consent_required; live gateway |

All staged host pointers name projection
`4d2934ddb59e70a94cab668077a84422a08cd1beb662adc2db578e39dd96e86b`.
OpenClaw's pointer changed during staging despite refused native installation;
do not equate the advisory pointer with successful native publication. Its
running gateway was not stopped. Restart consent was requested asynchronously.
Dashboard service was untouched throughout.

## Native evaluation checkpoint

Readiness is not execution. Codex/Claude isolated readiness returned ready;
actual current-profile Codex trust must be checked without bypass. Hermes and
OpenClaw lack a proven generic native-child canary mode, so use the existing
ordinary-session battery. ZCode reports no executable or proven version and
has no native-child mode; generated hook smoke does not satisfy native proof.

Current parent is old projection5059543ccea4 with LITELLM_API_KEY unset. The
pre-install doctor names that cause for eight configured inference profiles.
An install cannot retroactively staff this process. Do not reuse past headers.
Next: bounded real native output/own-session/header/injection/finalization
inspection, then final evidence publication and stop. Raw captures remain
owner-private; no prompt bodies, credential values or private transcripts here.
