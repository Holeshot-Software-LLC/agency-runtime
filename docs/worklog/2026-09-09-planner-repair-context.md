---
title: "Planner repair context and native verification"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [workforce, planner, native, reliability]
related:
  - docs/roadmap/issue-AR-425-preserve-planner-repair-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/decisions/0243-supply-rejected-plans-as-untrusted-repair-data.md
supersedes: []
superseded_by: null
type: worklog
commit: 03a82c3b2314e847a70ae670b44c554ce67e94c7
short: 03a82c3b
date: 2026-09-09
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/821
related_issues:
  - docs/roadmap/issue-AR-425-preserve-planner-repair-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Planner repair context and native verification

## Purpose

Preserve the rejected planner answer for the existing inference-owned repair and
retain specific known parser failure identities. Owned branch
codex/ar404-planner-contract-20260909 starts from clean synchronized e3090882.

## Approach

A private bounded two-call diagnostic captures prompts and responses using the
existing shared planner profile and current roster. Its first answer repeats the
missing correctness review; its repair succeeds. This does not recover the
unknown second error in the original native receipt. No roster selection or
activation occurs in the planner-only diagnostic.

## Challenges encountered

The original terminal receipt discards raw parser detail. The diagnostic is a
new request without the original native correlated context, explicitly not an
exact replay. The regression first fails on the missing specific code and then,
with assertion order changed, on the absent rejected-plan field. Both old-source
failures are retained in the validation record.

## Decisions and alternatives

ADR-0243 governs bounded untrusted repair data and content-free receipt identity.
The same parser, independent critic, validators and call caps remain in force.

## Verification

Focused143passed (planner inference, repair boundaries and failure diagnostics).
Production1151passed/3skipped, UI224passed, metadata, policy, worklog, Ruff,
routing, docs1364 and tracker416 pass. Frozen conformance and native comparison
follow before acceptance. No exhaustive workflow dispatched.

## Follow-ups

Keep AR-404/418/423 and AR-425 open until their exact isolated gates are evidenced.
The parent hook process is stale; fresh native sessions supply acceptance proof.

## Frozen installation checkpoint

Source03a82c3b, ledger/artifact2b19cce6. Canonical portable build and installed
smoke pass;615package files match wheelcba264c1bdbd57730f7ba748af2b75a5971cd0c71e425ca6d9826c463fad2fcd.
All five hosts normally refreshed; gateway stop/start succeeds. Codex normal
inspection marks8modified/0trusted: waiting for the owner's normal fresh /hooks
review, requested once. Other native hosts proceed independently.

First frozen conformance fails in baseline fixture setup because the shell002
umask creates a nonprivate test directory;0mutations attempted. Preserve that
failure. Rerun uses077 without changing source or directory trust policy.

## Claude full-card native result

Session545f5ca7-2937-412f-a9be-6b4e4c665204, tracedf374667-2599-4798-a852-1e6f972aed25,
239.508s, exit0, no timeout:4exact selected full cards in native MCP results,
all5Store fields match, accepted response hashf9b78ee4a8b0fd116e18fcffa0a9328ba67ff1b102586bf387f94845583f423b.
Source2b19cce6;12Claude context regressions pass. Isolated acceptance follows.
Owner confirms Codex trusted; fresh inspection8/8trusted and0modified. Approved
OpenClaw bounded observer imported3hooks; RPChealthy after normal warmup.

## Frozen conformance outcome

Private077 rerun passes188/188 mutations,0invalid,0survived, source unchanged.
The native Claude full-card result used one rejected planner answer followed by
one applied repair and an applied independent critic; the retained successful
routing projection does not expose the first rejection's semantic detail.
Native hosts run sequentially. Isolated acceptance may overlap the fixed native
round; wall times are observed durations, not a controlled speed benchmark.

## First isolated Claude delivery pass

Criterion1absent for insufficient direct pointer citation; criterion2verifier
unavailable/outside vocabulary, no verdict; criterion3satisfied28567142. Preserve
all three outcomes. Exact original native attachment81a967a9 now supplies the
15.7KB pointer, saved16076bytes/16067UTF16units, exact prior trace in saved
content, and same-session Store correlation. No new native retry occurred.
The supplemented second packet uses the already available Codex verifier after
the Claude verifier failed to return a criterion2 verdict. No third pass planned.
An initial builder docs check rejected missing line locators; corrected before
any verifier call, with no acceptance inferred from the failed command.

## Second isolated Claude delivery pass

Codex second pass:1absentaff6ed5e,2absent779c4d4e,3satisfied4833b3df.
The verifier's bounded excerpt selection omitted the decisive pointer and card
rows behind long earlier citations. Native success is preserved, but AR-423
remains open; two independent passes have been used. A compact corrected packet
will be prepared without a third pass in this package. No failed verdict is
overridden or relabeled. AR-425 receives focused line citations before its first
isolated pass.

## Acceptance packet preparation corrections

Direct build_case inspection identifies the original-pointer row outside the
contiguous Markdown table, so it never reached criterion1. Criterion2's whole
file locator selected only the first120lines and omitted native card rows389-470.
The prepared AR-423 packet now places the pointer row inside the table and cites
those exact card lines. Its earlier verdicts remain in first/second evidence,
with no third review in this package.
AR-425's first attempted verification was refused before a model call because a
new compact artifact locator exceeded its actual line count; corrected and
structurally checked before starting its first real isolated pass.

## First planner isolated result

Criteria1/3/4satisfiedb925dd5e/79466089/9fedf21a; criterion2absente4da83a4
requests the exact existing call-budget enforcement and independent-assurance
checks. The second packet cites those unchanged source guards and complete
assertion ranges from the already passing focused suite. No source or criteria
change; first verdict remains retained.

## Final native sample and scoped disposition

All15fixed cases run once, sequential host order Claude/Codex/Hermes/OpenClaw/Zcode.
8pass: Claude2/3, Codex3/3, Hermes0/3, OpenClaw2/3, Zcode1/3. The separate Claude
large-card probe passes. All source JSONs preserve session/trace, duration,
headers, cards, response digest and terminal result; exit0 is never acceptance.
Zcode review/follow-up have matching final headers/cards but an earlier invalid
terminal; no manual reopening. Hermes review fails independent assurance and
follow-up/multi-step omit all five fields. The native Hermes upstream PR106490
remains open, default checkout7cd91114. Its version banner labels upstream and
is not the executing checkout identity.

OpenClaw observer is normally removed, files/permission gone, unchanged nonplugin
configuration sections; gatewayRPChealthy after warmup. Claude's two grants stay
present and deep semantic settings comparison is unchanged; its serialized file
hash differs. Shared planner/recruiter/critic routes remain owner-controlled.
All five native executables are available.

AR-425 second isolated pass satisfies all4criteria8862f6fa/d5fb19d3/e006aacb/1c0fa05a;
close only that issue on PR merge. AR-404/418/423 stay open. AR-423 full-card native
success is proved but its corrected isolated packet awaits a separately authorized
additional pass after two attempts in this package. The local eight-row acceptance
limit also caught an overlong draft AR-425 packet before inference; it was reduced
to the exact eight source/guard citations and validated before the second pass.

Unrelated tracked scratchpad edits in another worktree were observed and left
untouched. This package's commits and evidence will merge through PR821, followed
by one exact merge-ledger PR. No exhaustive workflow or Windows work was dispatched.

## Remote main delivery

PR821 merged at 2026-09-09T16:02:51Z as `f28b66d7e350a781325c55c91fa23bf267d9e7ff` with exact subject
`Merge pull request #821 from Holeshot-Software-LLC/codex/ar404-planner-contract-20260909`. The source and every retained native/isolated result are now
on remote main. AR-425 alone closes; AR-404, AR-418 and AR-423 remain open.
The following ledger-only PR records this merge under the documented
`docs(worklog):` exemption. Main was clean before its fast-forward.

## Authorized AR-423 acceptance continuation

Owner's 2026-09-09 "go for it" authorizes one additional isolated pass. New
owned branch codex/ar423-acceptance-20260909 starts at c6c3e7b5. The packet
now includes actual native tool results for all four selected cards, separating
immutable card hashes from appended tool-availability disclosures. Full response
and compact terminal evidence remain repository-local. No new native trial,
permission change or failed receipt acceptance is used. The third isolated pass
follows bounded packet inspection. AR-404 and AR-426 retain their separate gates.

Third authorized AR-423 pass: criterion 1 satisfied (481b2034), criterion 2 absent
(1cdde5fb), criterion 3 satisfied (c12f936f). The missing independent-assurance
evidence led to a concrete High finding: inference selected five workers but
only four prompt references survived, omitting the security reviewer. AR-427/#825
owns that defect. AR-423 remains blocked; no closure or fourth pass occurred.
