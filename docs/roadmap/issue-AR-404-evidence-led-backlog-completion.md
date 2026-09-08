---
title: "AR-404: Complete the backlog through evidence-led delivery packages"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-08
tags: [backlog, review, acceptance, delivery]
related:
  - docs/roadmap/acceptance/evidence/AR-404-codex-roundtrip-20260908.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/roadmap/AR-404-next20-triage-20260907.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/roadmap/acceptance/evidence/AR-194-service-runtime-reconciliation-20260907.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/acceptance/evidence/AR-191-v2-checklist-retirement-20260907.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/acceptance/evidence/AR-189-owner-cli-reconciliation-20260907.md
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/acceptance/evidence/AR-348-installed-delivery-20260905.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
  - docs/roadmap/AR-404-backlog-inventory-20260905.md
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-361-builder-evidence-isolated-verification.md
  - docs/roadmap/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-404
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
depends_on: [AR-400, AR-401, AR-402, AR-403, AR-409]
blocks: []
---

# AR-404: Complete the backlog through evidence-led delivery packages

## Problem

The owner requested committed review artifacts, a plan covering the findings,
implementation, and backlog cleanup/completion. The first inventory found 155
unfinished records but only two existing acceptance files. Many entries already
describe implementation, others wait on native proof, and some still propose
behavior later decisions replaced. Treating all of them as new code fixes would
repeat work and risk reintroducing superseded behavior.

## Current state

### Resumed Codex roundtrip package, September 8

The owner confirmed Codex trust and approved the next bounded package. Fresh
inspection proves eight trusted hooks and a working newly launched MCP server;
the current conversation connection remains closed. The owner Codex launcher
now provisions the existing configured LiteLLM credential without changing
subscription login, inherited keys or gateway routing. Product code is unchanged.
Two metadata-only launch probes and the fresh trusted activation pass: accepted
staffing, native child completion, finalization and persisted attestation, no
bypass. Total129.6seconds includes97.454second staffing and one recruiter retry.
Two ordinary turns fail at the planner after45774/45791ms HTTP errors. Actual
public MCP status/host-status reads pass; the read-only native test's finalizer
requires unavailable approval and lacks a failed-preflight binding. No ordinary
accepted finalization, reliable staffing or speedup is claimed. AR-413/#765
tracks the newly demonstrated HTTP-status loss in staffing receipts;
see the [current receipt](acceptance/evidence/AR-404-codex-roundtrip-20260908.md).
The broader backlog and other-harness restart remain outside this package.

### Final delivery checkpoint, September 8

The owner superseded the midnight extension with a stopping-point request:
merge completed changes, install all harnesses and evaluate. All workers have
stopped new work. Exact main `4cbebf73` contains the completed source slices;
the owner CLI now matches all 614 files in its independently verified wheel.
Four host installations succeeded. OpenClaw staging occurred but its native
transaction stopped at the live-gateway restart-consent boundary; no gateway
restart or native registration success is claimed. The final native verdict is
not an all-harness pass: Codex requires normal trust; Claude produced a valid
header but no staffing/injection/finalization proof; Hermes timed out after a
reranker-contract failure and recruiter timeout. The existing OpenClaw gateway
staffed and emitted a five-field header, but has no accepted finalization.
ZCode has no native executable. All bounded checks and workers are terminal;
the owner requested a pause, not another implementation or retry wave.

The named production spine passed 1151/three skips and dashboard passed224;
focused results and honest conformance limits are in the
[final delivery receipt](acceptance/evidence/AR-404-final-installed-evaluation-20260907.md).
Current count is120 unfinished =48 mapped +72 legacy. No new isolated
acceptance or blanket issue closure follows from these source/install results.
On explicit continuation, prioritize one fully evidenced native staffed turn
before broad backlog cleanup. Record provider, header, exact injection and
accepted finalization separately; preserve trust and shared-service boundaries.

### Historical midnight code-first checkpoint

The owner extended the September7 session through midnight Eastern
(September8 04:00UTC) and explicitly prioritized code over waiting for CI/tests.
Further test execution and acceptance remain deferred, not silently satisfied.
Three native workers run within the session's four-agent total capacity; the
next twenty unfinished non-Windows records have been triaged for real source
gaps versus implemented/superseded work. Publication remains normal branch/PR/
merge, and native Windows/owner trust changes stay outside unattended work.

Main includes AR194 PR743/cbba0fd9 and AR410 PR745/7c0c1221. The installed CLI
is exact0e8e9307, all613 payload files matched, with four refreshed hosts on
runtime d542bee67724. Owner configuration, wrapper, separate OpenClaw install
and running dashboard remain preserved. The planned new410 native test was not
launched after the owner deferred tests. See the
[installed and actual native receipt](acceptance/evidence/AR-409-installed-live-delivery-20260907.md).
AR409/410 remain in_progress; no current all-host success is claimed.
AR411's validated recall-catalog digest preservation is on main through PR747/
e790c4d4; its written regressions and installed delivery remain deferred.
Count after AR411 filing:119 unfinished =43 mapped +76 legacy; mapping a legacy
item later changes that split, not the unfinished total.

The [twenty-record source triage](AR-404-next20-triage-20260907.md) found eleven
proof-held records, six stale or scope-reconciliation records, and three code
scope rows: concrete gaps AR251/270 and the AR236 umbrella, not three new bugs.
Those two implementations are in independent worktrees. A separate AR280 native
source inspection found no authenticated invocation-purpose hook field; do not
skip background calls using prompt text or an unbound private context label.
The required Codex refresh at01:10UTC returned `already_current`, no-op and
`enabled-runtime-unverified`; refreshing disk cannot restaff this older process.

### Earlier September6–7 chronology

**Resumed by the owner on September 6 at AR-131.** The previous pause checkpoint
is on main through PR #696/f38720c7 and the exact PR #697 ledger/c1c5d9d9.
AR-131 is done after repairing public identifier admission; all six isolated
criteria satisfy at 973acdb9, with first verdicts preserved at 6a139e23. PR #698
merged at ac1ce173. AR-135 retains current native Agent/record-zero/full-Stop
proof: 33 selected contracts and generated ZCode smoke 4/4 pass, but installed
state is enabled-runtime-unverified, with no native executable/canary. Its
retention merged in PR #699 at e2f7a5f2; August evidence remains historical.

AR-138 is done and merged through PR #700 at 1ada216c. Browser review repaired
accessibility/clipping defects; the first isolated review exposed a stale-error
race and is preserved at 25b9a67a. The repaired candidate 2ecde1a5 satisfies all
six original criteria: 172 UI tests, 21 rebuilt-wheel loaded browser checks,
180 dashboard Python tests and repeated named spine 1085/three skips (99.40s).
No native-host or full accessibility certification is implied.

AR-140 is a retained implemented optimization, not a rewrite:
all 39 current local Linux routing/performance gates and 202 focused tests
pass. Cache/narrowing p95 are 0.201/1.081 ms; fresh CLI version median 16.989 ms.
All retrieval-size budgets pass. The original isolated supported-runner gate
still needs evidence, including the owner's Windows arm. ADR-0121 governs
candidate recall/synthetic cache evidence; AR-253 retains real staffing latency.
Its disposition merged in PR #701 at 7afa4b4d.

AR-145 retires a duplicate mandatory-coverage checklist under
ADR-0224, not an accepted 97-percent pass. Its original repairs pass 41 focused
tests under branch instrumentation; AR-176 explicitly retains actual fixture
and requested aggregate-diagnostic work. ADR-0105 already made exhaustive
checks optional. Keep the configured 97-percent floor and all historical
failures. AR-156 records the release checklist's stale UI coverage command for
its upcoming reconciliation. PR #702 merged at cd061668. AR-146/148/149 are done
and Windows-only AR-147 stays with the owner.

AR-150 is done: existing shared dashboard commit epochs verified, with four
direct inverse-order tests added at ae71761f. First review's missing criterion-2
evidence remains preserved at 4e820ff4; all four second-pass criteria satisfy.
Full UI passes 176 at 96.93/86.70/95.71, server/auth/transaction passes 180 in
28.82s. Unchanged product bytes bind the existing 21-case installed-wheel receipt;
no runtime change or new installation claim. PR #703 carries the completion.
PR #703 merged normally at 460f319b, September 7 at 06:18:49Z. Main was clean
and fast-forwarded before the separate AR-151 worktree was created.

AR-151 confirms the original host-eligibility repair already exists. Thirteen
direct GET → production JavaScript → POST contract cases pass; core dashboard
193 pass and UI 176/current floors pass. The broader six-module run is
265 pass/nine failures; all nine reproduce on unchanged main 460f319b. The
bounded owner-token, cache and inference-projection fixtures are now repaired:
274 dashboard cases pass, and the named spine passes 1085/three existing skips.
No runtime change. First isolated review satisfies 2/3/4 but contradicts the
blanket duplicate-inventory criterion. Verdicts remain at f954d1e9. ADR-0225
explicitly revises only that criterion to per-host ambiguity and whole-inventory
size rejection, preserving unique verified-host availability. All four second-pass
criteria satisfy at 791820bb. AR-151 is done; PR #704 carries completion.
PR #704 merged at 5a12f357 on September 7 at 06:46:57Z; clean main was
fast-forwarded before the separate AR-153 worktree. AR-152 is already done.

AR-153 confirms existing worker-filter-before-limit, bounded lineage and exact
count/truncation projection. Fresh focused worker-detail tests pass six; complete
workforce lifecycle passes 25; UI passes 176/current floors. Product/tests/scripts
equal 99e05d1f, supporting explicit 274-dashboard/1085-spine receipt reuse.
ADR-0105 replaces only the stale mandatory-full-corpus criterion with current
bounded verification; original wording remains. All four isolated criteria
satisfy at ea577285; AR-153 is done. PR #705 merged normally at 8b36ea28 on
September 7 at 07:06:14Z; clean main was fast-forwarded before AR-154's worktree.

AR-154's initial-page repair is present. Twelve new direct full/control refresh
cases prove last-good state and revisions survive missing initial cursor/revision
across roster, snapshots and reviews. Focused cursor/activity/observation passes
13, full UI passes 188/current floors. No runtime or criterion change; unchanged
Python/source receipts are explicit reuse. All four original criteria satisfy
at e1c3069c; AR-154 is done. PR #706 merged at 434175f0 on September 7 at
07:17:59Z; main was clean and fast-forwarded before the owned AR-155 tree.

AR-155 confirms the existing metadata-only 200-row/1 MiB hiring page and exact
full-document endpoint, with explicit UI inspection and stale-response guards.
Fresh Store/HTTP four, workforce 25 and UI 188 pass; Python/source receipts are
explicit reuse. No code/test change; ADR-0105 reconciles only its obsolete fifth
verification gate, preserving historical wording. All five criteria satisfy at
6ed24943; initial criterion-3 unavailability is preserved at a3e00bd5 and its
single unchanged-candidate retry passes. AR-155 is done; PR #707 merged at
729e7dc4 on September 7 at 07:34:42Z before the separate AR-156 worktree.

AR-156 retains its hosted/Windows proof; current bounded workflow and paired
controller exist. The local missing-Node false-success path is repaired before
gate execution, and documented UI argv now matches local/hosted unchanged floors.
Three comments restore the 378 KiB asset budget without executable changes.
Workflow 165 pass/five Windows-named deselections, spine 1085/three skips and UI
188 pass. Four Windows-profile assumptions still fail on Linux unchanged main;
no guard is weakened. Exact clean dccb4e85 wheel QA passes 21 loaded browser
checks, with polling preservation and failure recovery at all three widths.
Scoped receipts and screenshots are committed; normal publication precedes AR-157.
PR #708 merged 6b4650b3 at 08:00:11Z on September 7 before the AR-157 tree.

AR-157 confirms existing quiet HTTP disconnect handling. Two direct primary
observation tests are strengthened, and two stale HTTP fixtures are repaired
without runtime changes. Full HTTP/disconnect/runtime-observation package passes
104 with three existing skips; targeted transport coverage is 100 percent.
Exact-byte spine/UI/wheel reuse is explicit. Only criterion 6 is reconciled under
ADR-0105; all six isolated criteria satisfy at a35657e1. AR-157 is done, with
normal PR publication next and no duplicate legacy tracker.
PR #709 merged ea6864b1 on September 7 at 08:17:39Z before the AR-158 tree.

AR-158 retains existing MCP/HTTP selectors and restores hook observation proof
on the current R8 three-host failure test, not retired child denial. Store
busy selection now uses the exact request ID; matching unrelated Store events
and all-envelope privacy checks are explicit. Thirteen focused cases and ten
five-case repeats pass; complete five-module package passes 135/five existing
skips. Runtime/scripts unchanged, spine/UI/wheel reuse explicit. Only criterion
7 is reconciled under ADR-0105. All seven criteria satisfy at 95085a30 after
one citation-only criterion-7 recheck; first review remains at 809354be and the
six accepted checks were not repeated. AR-158 is done; PR #710 merged b2ea5946
at 08:41:00Z on September 7 before the separate AR-159 tree.

AR-159 remains relevant and open: fresh API readback shows main unprotected,
no rulesets, and no current check runs/status contexts. The latest listed CI
and repository CodeQL runs are August 31/cancelled; the historical billing
explanation is not a current diagnosis. All 104 focused aggregate/security
contract tests pass. The original seven criteria are unchanged; an explicit
owner-approved enforcement/check-identity/bypass/readback plan is recorded.
No hosted setting, unsafe main probe, workflow dispatch or subscription change.
PR #711 merged b499e7fb at 08:57:15Z September 7 before the AR-160 tree.

AR-160 retains the current no-helper paired-artifact contract under ADR-0219.
Fresh Linux verification passes 258 focused cases, with one native-Windows
case deselected. Clean f1c7d0b0 produces a canonical portable wheel/source pair;
independent verification and strict Twine pass. Separate fresh wheel/source
installs each pass CLI, pip check, packaged MCP/dashboard and all eight generated
smoke checks across all five hosts, without skips. This is not native activation
or Windows producer/assembled release-set proof. All five current criteria stay
unchanged; historical helper prose is explicitly separated from current state.
PR #712 merged f18b5acf at 09:07:33Z September 7 before the AR-162 tree;
native Windows remains owner work and AR-161 is already retired.

AR-162's one-preflight fan-out redesign exists. Review reproduced a real
HTTP-200/no-body availability gap; the repaired bounded classifier rejects it
and malformed/ambiguous inputs before publishing availability. Sixty-five
CodeQL focus cases, 210 workflow cases and the named 1085/three-skip spine pass.
Read-only identity now reports public and code scanning available for the calling
identity, not a hosted workflow pass. ADR-0226 initially revised only criterion
8 to require matched measurements for any savings claim; none is made. First
review c456b6bd accepted 1–6 and 8 but lacked a prior event comparison and old
tracker-parity proof. The correction records exact historical/current projection
equality and explicitly reconciles 9 to AR-347's existing legacy exemption.
Criteria 1–7 and all workflow/test/runtime bytes remain unchanged. All nine
current criteria satisfy at d30b8ae0 in the second and final isolated review.
AR-162 is complete; hosted enforcement remains with AR-159.
PR #713 merged a01abe81 at 09:53:40Z September 7, read back before AR-163.

AR-163's historical signed-authority repair is still implemented and relevant.
Fresh local Store/API-projection tests pass 167 and DOM tests pass 188 with no
failures/skips. All eight original criteria are unchanged; no runtime or test
change is needed. Exact-byte named-spine reuse is explicit. All eight original
criteria satisfy in the first isolated review at fd551fd4; AR-163 is complete.
PR #714 merged 6d1ca01f at 10:04:47Z September 7 before the AR-164 tree.

AR-164's ancestor boundary remains implemented. Fresh discovery/current-launch/
surviving Git packages pass 38/129/24 cases without skips or failures; Windows
deselections and portable spelling/PATHEXT simulations are explicit. ADR-0227
reconciles only obsolete criterion 5's deleted worker backends to current
CLI-provider, installer, dashboard and smoke launch paths. Original wording
remains; no runtime or test change. First review at 083ae8b5 lacked actual tree
output for criterion 5; its verdict remains at 6ac3b1aa. Exact Git evidence was
added and all seven current criteria satisfy at 2a7c20c5 in the second review.
AR-164 is complete within that scope, not a native Windows qualification claim.
PR #715 merged ba6e55cb at 10:23:29Z September 7 before the AR-165 tree.

AR-165 review reproduced duplicate JSON identity/error keys selecting fallback,
and malformed object/non-finite success data selecting native review. Strict
bounded parsing and array-of-objects success shape repair these cases without
changing permitted paths, action pins or the aggregate. Focus 62, full workflow
235 and fresh named spine 1085/three existing skips pass. ADR-0228 explicitly
reconciles only 8/9 to claim-conditional hosted measurement and the legacy
exemption; no savings or hosted-success claim. All nine current isolated checks
satisfy at 9effff3f in the first review. PR #716 merged 520a10e3 at 10:58:51Z
September 7 before the separate AR-166 tree.

AR-166's correlation/privacy implementation remains relevant. Its read-only
owner-control criterion contradicts ADR-0117, and the provider-secret selector
still incorrectly disables valid choices. The one-line repair passes 189 UI
cases/current coverage floors, 235 backend/owner cases and the fresh named spine
1085/three existing skips. ADR-0229 explicitly reconciles only criterion 1;
the bounded complete prompt already belongs to AR-298. Browser proof and all
six isolated verdicts are now satisfied at 4a244776. The selector passed 18 real
source-served browser checks after a fixture-endpoint correction. A second
criterion-2 gap, null HTTP error JSON losing status/request ID through TypeError,
is repaired with a null-safe lookup and 401/403/503 regression. Latest UI 190
passes; fresh named spine 1085/three skips, 66.99s; asset checks three pass.
Final browser passes 20 exact-source checks at 1280/375, including terminal
null-401 notices with safe IDs; no POSTs. All six criteria satisfy after one
existing-implementation citation recheck; first verdicts remain at bc28bf66.
AR-166 is done; PR #717 merged c6252499 at 11:36:32Z September 7 before AR-168.

AR-168's generic manifest repair is present. Fresh 308 packaging tests pass,
one native-Windows case deselected. Clean 6363a788 produces a Linux pair that
passes independent verification and strict Twine; its source manifest has
2,256 unique rows with exact membership/newline policy. Retain the unchanged
five criteria/states: same-candidate native Windows/Linux source equality
remains owner evidence under AR-160/ADR-0219. No code, acceptance or count change.
PR #718 merged 790a01d7 at 11:49:53Z September 7; AR-169 is already retired.
AR-170 repairs three reproduced correlation gaps: present null identity,
fabricated exact-lookup pagination and uncorrelated worker validation. UI 193,
fresh spine 1085/three existing skips and four asset/packaging checks pass.
Initial source browser has 16 desktop passes then an incorrect-notice-expectation
timeout, preserved at 90654955. Corrected exact-source browser passes 34 checks
across 1280/375 pixels and zero POSTs. ADR-0230 explicitly reconciles only 6/7/9;
originals remain. First review is preserved at 662eb947. Final candidate
91273e41 satisfies 1/2/4/5/6/7/8; 3/9 retain full-call-site and raw-gate-receipt
evidence gaps. Publish the tested repair with AR-170 in_progress and no count
change. Two-pass limit is reached; PR #719 merged 29e76943 at 12:18:00Z
September 7 before the separate AR-171 tree.

AR-171's existing lifecycle reason/hash redaction is confirmed. A new eight-value
DOM regression strengthens inert presence rendering; no runtime change.
Store/HTTP 199, UI 194/current floors and fresh spine 1085/three existing skips
pass. Raw transcripts are retained. Only stale criterion 6 is reconciled under
ADR-0105, original wording preserved. All six current criteria satisfy in the
first isolated review at 8a8db2ae; AR-171 is done. PR #720 merged a846c88f at
12:32:58Z September 7 before the separate AR-172 tree.

AR-172's existing snapshot/paging implementation is confirmed with ten new
state-preservation regressions. Store/HTTP/activation 278, UI 204/current floors
and fresh spine 1085/three existing skips pass. Only obsolete criterion 7 is
reconciled under ADR-0105. All seven criteria satisfy at dec1bc51; first verdicts
remain at 4c5acdcf before the single criterion-6 call-site citation recheck.
No production change or candidate retry. AR-172 is done; PR #721 merged
47d40fec at 13:11:01Z September 7 before the separate AR-173 tree.

AR-173's existing trace attachment is confirmed and its missing direct HTTP
regression added. Two actual social explanations plus invalid/disabled guards
prove exact response/log digest binding, bounded metadata and no durable
diagnostic turns. Full focused 195, UI 204/current floors and fresh spine
1085/three existing skips pass. ADR-0231 initially reconciled 1/4/5; first review
at 941b9025 exposed criterion 2's remaining raw-trace/digest wording error.
ADR-0232 explicitly supersedes it, preserving originals. All five criteria
satisfy at 594bc4d3 in the second/final review. No production changes or third
review; AR-173 is accepted locally. The owner paused at 13:38 UTC September 7
before publication; clean local checkpoint 1f16f948 preserves it. At 20:14 UTC
the owner explicitly resumed until 9 p.m. Eastern (September 8 at 01:00 UTC).
AR-173 merged through PR #722 at 7ad0d33e on September 7 at 20:18:19Z;
main was clean and fast-forwarded before the owned AR-174 tree and d43dc923 ledger.
Finish at a clean checkpoint by the owner cutoff.

AR-174's existing shortcut passes 235 focused workflow tests/five Windows-named
deselections, all 18 Bash syntax checks, release hygiene, offline workflow
security, UI 204/current floors and a fresh spine 1085/three existing skips.
No source change. The old timing blocker missed August 31 PR #380's successful
five-runner docs-only run: exact API/Git proof measures 366 raw runner-seconds.
This is historical timing, not present billing health or measured savings.
First review is preserved at 5d20ec28: 2/3/4/6/8 satisfy, 1/5 need isolated
workflow/matrix citations, and 7 lacks billing-repair proof despite valid raw
timing. ADR-0233 explicitly separates the timing requirement from account
administration, with original wording retained; 8 still follows ADR-0105.
No runtime change. All eight criteria satisfy at 5a003a05 in the second/final
review; AR-174 is done with first verdicts preserved and no third review.
PR #723 merged 57a70139 at 20:41:36Z September 7; main was clean and
fast-forwarded before the owned AR-175 tree and merge ledger 7f403ab7.

AR-175 reproduces a real remaining request-ID loss on invalid control schema
despite the legacy fallback already being absent. Eight new cases fail before
the API-boundary repair; all 20 now pass, including cancellation/lifecycle races.
UI 224/current floors, four asset/floor tests and fresh spine 1085/three existing
skips pass. Assets shrink 74 bytes to 386965 under the unchanged 378-KiB ceiling.
Private installed-wheel Chromium proof now passes 21 views and 36 faults across
both refresh paths and three widths, including actual 404/network failures and
schema/JSON corruption. Thirty server response headers match sent IDs; six
network faults retain sent IDs without responses. No legacy GETs or POSTs;
all ten served-resource hashes match checked source. All six criteria satisfy
at 328c5634; only 6 needed bounded line citations after the first packet omitted
its browser excerpt. First verdicts remain at 8ed3c516; no third review.
No native Windows or AR-170 completion claim. A separate fresh current-profile
Codex canary actually ran but failed parent-spawn, response and header evidence;
its missing-credential/transport observations are retained in the live audit.

AR-175 merged through PR #724 at 891f0c32, 21:21:39Z September 7. AR-176's
seven repaired stale cases and strict namespace doubles merged through PR #725
at d2125438, 22:12:58Z. Its final focused package passes 525/one skip/64 Windows
deselections and fresh spine 1085/three skips, but two inventory criteria remain
unaccepted after two review passes. It stays in_progress.

AR-177 retires only its superseded mandatory manual-run/release checklist under
ADR-0234/AR-186. Manual-only CI, four shards, 97 percent and all six compatibility
sessions remain intact; 222 focused contracts pass. The sole retained manual
hosted run failed whitespace validation, not accepted as green or billing proof.
Original checkbox states remain unchanged. Current branch count: 40 actual open
trackers plus 78 unfinished legacy records, 118 total; main remains 119 until
AR-177 merges. No duplicate tracker, exhaustive dispatch or false acceptance.

AR-177 merged PR #726/cbe82aaf at 22:32:47Z September 7. AR-178 remains
relevant deferred post-production research, explicitly non-blocking under
ADR-0102. Its six scenario definitions and strict validator are not six
matched blind-graded application results; all original states remain.
Owner-requested fanout separately established a real install-warning defect:
AR-407/#727 scopes residual drift to the requested hosts while retaining global
status. Filing adds one mapped issue, making 119 = 41 mapped + 78 legacy.
The live audit corrects the earlier AR-271 warning inference: Codex disk/cache
is current, the unfiltered warning is OpenClaw-only, and this running parent
separately retains older hook definitions and lacks its credential variable.

AR-407's actual fix now satisfies all three criteria at dcd58720. Focused158
passes/one Windows deselection, independent review35passes, fresh spine1085/
three skips and UI224 pass. Exact live-pointer helper check preserves allfive
pointer files/metadata; restrictive-umask portable build passes independent
verification/Twine and fresh installed MCP/dashboard/all-host generated smoke
(eight/zero/zero,5.09s). No native-turn claim. Done branch count returns to
118 (40 mapped/78 legacy); normal PR/merge and #727 closure precede AR-180.
The unchanged public-roster fixture belongs to AR-176. Windows stays excluded;
the oldest-first ledger and capsule preserve all holds. Ordinary-session
unverified Agency/header behavior remains a separate unfinished concern.

AR-189 publication preparation now supplies a real private ZCode owner-CLI
install/plan/refuse/apply/no-op proof without replacing authority, bindings,
locks, replanning or retention. ADR-0117 supersedes only the old presence
ceremony; all original criteria remain in the receipt and native Windows
companion/handle-rename/PowerShell obligations remain open. Updated-source
focused 127/two Windows skips, named spine 1,085/three skips, UI 224 and
repository lint/format pass. No production code or owner integration changes,
acceptance verdict or backlog-count reduction. AR-185/PR736 merged00fc1aef
at23:55:01Z; AR-408/PR737 mergedbfe21d66 at23:59:35Z and #732 is CLOSED,
all read back. AR189/PR738 merged f408b6f2 at00:06:15Z September 8;
AR190/PR740 merged d39ec14d with criterion3's remaining evidence gap preserved.
AR409 source merged PR739/4db6be16; installed/live delivery is separate.
Integrated AR189 focused rerun:127/two skips5.50s.

AR-191's records-only checkpoint retires the obsolete July V2 activation-grant
checklist under ADR-0236, superseded by current AR-255 staffing authority.
Its exact aliases, arguments, exit-code reporting and existing-Store guards
remain implemented; 23 fresh offline checks pass. All original checkbox states
are preserved. AR-180's restricted one-card exec proof is not the removed grant
graph or its broader TUI/Desktop/multi-card/child-only acceptance. Parent
published order45 in PR741, merged a8c2ca54 at00:33:11Z September8; normal main
integration preserves all frozen acceptance candidates. No tracker action or
fresh global count is claimed.

AR-194's source-only cross-version inspection fix remains implemented. Fresh
launcher/service-core/service tests pass116 with42 name-filtered deselections
in2.75s. Installed owner CLI status is read-only and reports a current, owned,
active, reachable Linux systemd service with no repair needed; four inspection
modules match source. ADR-0117 removes only the obsolete AR-196 ceremony
dependency, with reciprocity; all original five criterion states remain.
Native Windows stale-task/runtime repair and post-repair reachability stay
open. Queue order47 is reserved after AR-190/191/192; this is a branch-only
checkpoint, not another completion or a claim of native Windows proof.

The owner requires oldest-first sequential delivery: one record, one PR,
merge, then the next, without routine approval stops. Windows stays excluded.
The [oldest-first ledger](AR-404-oldest-first-reconciliation-20260905.md) is the
current ordering/disposition record. AR-115 was retired under ADR-0222 in
PR #690, merged at d9ea419b; tracker #127 closed NOT_PLANNED at 23:47:12Z,
read back. Its surviving live obligation is explicitly owned by AR-119/AR-125.
Fresh counts are 41 open trackers plus 99 legacy records (140 unfinished).
AR-119 remains a relevant incomplete umbrella; its record reconciliation merged
in PR #691 at 8b8b594e without changing any matrix cell, candidate, founding
vision or acceptance criterion. Its tracker #132 stays open. AR-120's source
review now separates implemented contracts/typed relationships/snapshots from
missing enrichment-review, discoverability and scheduled artifact-refresh work.
219 focused tests pass; PR #692 merged at bc392228 and #133 stays open with a
bounded remaining plan. AR-125 likewise retains its real matched-selection/
value and five-host live obligations; 33 evaluator regressions pass, not a live
study. PR #693 merged at 79930464; #138 is read back OPEN. AR-127's shape fix is
present, while its retry/unavailable/full-suite checklist contradicts later
policies. Retire it under ADR-0223 with current ZCode responsibility in AR-135.
Broader checks expose the same three legacy assertions already recorded in
August; AR-176 explicitly owns their repair (133 pass/three failures, not green).
PR #694 merged at 66282312 and #151 closed NOT_PLANNED at 00:23:39Z on
September 6 UTC (September 5 local), read back. Fresh counts: 40 actual open
trackers plus 99 legacy records (139 unfinished). AR-129's shared environment
builder exists; 64 non-Windows tests pass with 12 Windows-named cases deselected.
It retains its explicit Windows/installed evidence hold for the owner; PR #695
merged at d38e9d13. AR-130's positive trust cache is also already removed:
19 current trust-regression/file-integrity tests pass. Its broader non-Windows
run has 40 pass/two confirmed stale fixtures/39 Windows-named cases deselected;
AR-176 owns those fixtures. Retain native Windows and current hook-budget proof,
without presenting old batching timings as current evidence. AR-131 follows
after the disposition merges. No platform acceptance is fabricated.
The earlier AR-349-first plan below
is historical. A requested Codex-only hook refresh returned exit 1 with trust
unverified and a projection mismatch; it is not live completion evidence.

### Previous published checkpoint

AR-348 is accepted and locally done under ADR-0221: both original criteria
satisfied against c9b678a5, 413 focused passes/one skip, 1075 fast-spine passes/
three skips, 138 UI passes, routing pass, and 184/184 protected mutation kills
with source unchanged. PR #687 merged at 0309f251; tracker #406 closed at
22:20:23Z on 2026-09-05 and read-back confirms CLOSED. Fresh enumeration:
42 actual open issues; local unfinished: 141 (42 mapped plus 99 legacy).
That exact immutable revision is installed. All 45 new hiring regressions pass
against installed package bytes, and all eight deterministic smoke checks pass.
Codex files are refreshed but attended trust remains; the running OpenClaw
gateway is untouched. Claude/Hermes/ZCode registered/enabled, not live-proven.
Strict=false warnings and inference-owned provider choices are unchanged.
AR-349's rejected-hire persistence is the next separate implementation package;
AR-298 remains implemented pending isolated verification. Windows is excluded.

### Earlier published checkpoint

PR #683 is merged at cb7dca77: AR-148/149/323 done and AR-139 retired.
PR #684 is merged at 853de310: the AR-406/152 package implements ADR-0220's production-wide coverage
scope, preserving every product module and all 95/86/93 floors. Actual configured
local command: 138 UI passes, coverage 96.92/86.62/95.71. Local/hosted scope
regressions first fail, then the complete workflow-contract package passes 163
tests. Existing listener code and UI behavioral tests are unchanged. Both
acceptance records now have seven satisfied isolated criteria. AR-406 and
AR-152 are done on main. Tracker #682 was closed as completed at 21:35:56 UTC
on 2026-09-05 and its state was read back. Fresh tracker enumeration confirms
43 open issues; local unfinished count is 142 (43 mapped plus 99 legacy).
The first immediately-after-close REST enumeration briefly still returned 44;
the subsequent issue listing and REST enumeration agree on 43. Never substitute
the sum of these two distinct queues for a count of demonstrated defects.

That checkpoint selected AR-348's actual resolved-provider independence boundary,
including legacy routing, harness overrides, fallback chains and safety repair.
Its proposed single call to the declared-profile helper is not an implementation
specification: that helper skips unresolved legacy routes, while production
already compares actual provider chains for warning recording. Keep the current
strict=false contract and inference-owned staffing choices. AR-349 follows as
a separate rejected-hire persistence package. Windows work remains excluded.

### Prior checkpoint history

Owner clarification: work sequentially, close verified completed records,
assess agent-written tickets against the current product rather than accepting
their proposed designs, and leave Windows-specific work to the owner's machine.
The starting 147 count was 43 open trackers plus 104 unfinished pre-tracker
local records, not 147 demonstrated defects. The count reconciliation records
the exact join. AR-149 is already implemented and now has current real HTTP
verification; all four isolated criteria are satisfied and the record is done.
The first absent 2/3 verdicts remain in f2e41b89; the targeted second check
followed missing ContextVar/Store source citations, not criterion changes.
AR-139 is retired:
AR-295 and 3023f0557 superseded its old ceiling with audited required UI;
current 386,366-byte assets pass the strict 378 KiB guard. No guard is changed.
AR-152's listener soak passes,
but the separate current UI function-coverage gate fails (91.12 versus 93
percent), recorded as AR-406/#682. Filing it adds one tracked issue; retiring
AR-139 and completing AR-149 remove two legacy items (44 tracked plus 102
unfinished legacy at that checkpoint). No corresponding external trackers
exist for those two.

AR-148's signature repair is also present. Its wider validation uncovered the
already-tracked AR-323 stale schema-literal defect: three native-child ledger
cases and seven migration/credential tests expected 46 while schema is 49.
The test-only correction removes copied current-version literals, preserves
historical input versions and all behavioral assertions, and passes the complete
401-test focused package. Fresh named production spine: 1030 passed, three
existing skips (63.73s). AR-148/323 now have eight satisfied isolated criteria
and are done; no new tracker was created for this existing issue family.
First-batch split: 44 actual open trackers plus 100 unfinished legacy records
(144 local unfinished). Three old records completed; one obsolete requirement
retired; AR-406 remains a separate current finding.

Final first-batch verification: fresh routing passes; 138 UI cases pass;
development-venv conformance passes its baseline and kills all 182 mutations
with source unchanged. The first installed-interpreter attempt had no pytest
and ran no mutations; that invocation mistake is retained in the capsule.
AR-406's then-next bounded package corrects a measurement-scope error: the mixed
aggregate includes fixtures, while all seven production modules already meet
unchanged 95/86/93 floors. It will not manufacture callback tests for the score.

A stale-hook warning prompted `agency install --agent codex` from the existing
installed immutable runtime. Codex files refreshed; exit 1 honestly retains
activation-required/unverified hook trust. A fresh attended local Codex terminal
must grant hook trust; no trust bypass or repeated unattended retry occurred.

Phase: implementing. The owner asked to push and continue after the first
semantic record cleanup. That cleanup is on main through PR #676/#677 at
3ed51069. Two bounded defect packages follow it:

- AR-405 is done and merged through PR #678 at 78e501b7; tracker #675 is closed.
  Its test-only correction turns 91 pass/two fail into 100 pass/one native
  Windows skip, without changing production identity semantics. Three isolated
  criteria are satisfied; portable real and synthetic assertions remain active.
- AR-271 is done for its bounded contract outcome; PR #679 merged at 5434836e.
  Install and uninstall now share the exact bounded stopped-state classifier.
  Regression-first seven fail/fifteen pass becomes a 248-pass focused suite
  with two native Windows skips. Owner denial, execution-identity drift and
  live/unknown state after approval and before commit remain blocking.
  Three isolated criteria are satisfied; fast spine 1030 pass/three skips,
  UI 138, docs/acceptance/tracker tests 104, routing and protected conformance
  baseline plus 182 mutation kills pass. Exact merged-main non-editable install
  and all eight deterministic smoke checks pass, covering five host contracts.
  Native refresh remains partial: Codex needs attended hook trust and OpenClaw
  is live. Claude/Hermes/ZCode registered/enabled, but no current-build live
  session is claimed. The installer restarted its dashboard and repaired
  fourteen Claude package permissions under recorded consent; no OpenClaw
  stop/restart/uninstall or credential change occurred.

Prior delivery accounting: 146 unfinished baseline records plus AR-404 (147 then-current
unfinished records). The frozen inventory started with 155, the four accepted
AR-400..403 fixes left 151, and four obsolete policies AR-132/167/169/267 left
147. AR-271 removes one more baseline item; AR-405 was filed outside that
baseline and has since closed. The first semantic review and historical
checkpoint counts remain in the linked disposition record.

AR-160 retains current paired no-helper release artifact proof under ADR-0219.
AR-285 remains in_progress with three satisfied and two absent criteria:
trusted-runner wiring citations and a successful changed-precondition dry-run
receipt. Its real historical installs do not fill both evidence gaps. Do not
conflate its receipt-specific acceptance with AR-271's new bounded contract.

Earlier lane A has twelve satisfied isolated verdicts for AR-400..403, merged
through PR #669 at 1de05aea. AR-397/398/399 tracker debt is reconciled at
#654/#670/#671. That immutable runtime's deterministic five-host smoke and
one Claude native-child pass remain scoped to that build; Codex trust,
OpenClaw restart consent and Hermes/ZCode ordinary-session proof remain visible.

The review still does not support mass closure. AR-348 permits same-provider
creator/reviewer hiring despite strict_independence=true in a current offline
production-path replay; AR-349 still returns repair exhaustion without a durable
rejected case. AR-350 needs an explicit authority decision. AR-337's literal
all-supported-host wording disagrees with its four-host battery, and AR-351's
domain-axis proposal conflicts with descriptive-domain semantics. These remain
bounded packages, not assumptions that old checkboxes or inherited p0 labels
are authoritative.

## Approach

1. **Finish this review's delivery (lane A).** Persist exact installed evidence,
   obtain isolated acceptance verdicts for AR-400/401/402/403, merge records,
   close only accepted trackers. Keep platform/operator exits visible.
2. **Reconcile known record debt.** Bind AR-398 to #670 and AR-399 to #671,
   verify existing candidate-bound verdicts and close #654/#670/#671.
   The owner's 2026-09-05 backlog-cleanup request authorizes this bookkeeping;
   it does not authorize altering historical receipts or relaxing criteria.
3. **Security/hiring invariants first (lane B).** Start with AR-348 strict
   independence, AR-349 rejected-hire persistence, AR-350 risk hints versus
   binding verdicts, and AR-351 explicit-empty contracts. Reproduce the current
   boundary before changing it; AR-402/ADR-0217 changed domain semantics, so
   AR-351's domain proposal must be reconciled, not implemented blindly.
4. **Prove staffing quality and speed (lane C).** Use AR-253 as the performance
   owner, AR-370/374 for representative recall/eligibility, and AR-393 for gap
   accounting. Add a small fixed corpus of ordinary and true-gap tasks across
   native parent/child entry points; report end-to-end p50/p95, stage timings,
   calls/input counts, selected-role relevance, valid gap accounts and hiring
   outcomes. Compare cold/warm fresh processes and retain failed trials.
   Keep strict critics, audits and authority gates enabled. One recall pair
   cannot close this lane.
5. **Native completion (lane D).** Check exact installed identity, fresh process,
   trust and credential availability before spending live inference. AR-359's
   code is implemented but its specific operator-policy rewrite needs the exact
   approved text; AR-365/366/367/368/369/371 need their own host-visible evidence.
   Do not infer live success from deterministic adapters.
6. **Release and UI outcomes (lanes E/F).** Reconcile obsolete exhaustive-test
   requirements with current governance through explicit record changes, never
   by inventing a pass. Group remaining issues by their actual dependency and
   visible outcome; Windows/macOS evidence must come from those platforms.
7. **For every package:** cite current source/test evidence per criterion;
   implement missing behavior in an owned worktree; focused tests, at most two
   review passes, named fast spine, demo, isolated acceptance, PR merge and
   exact ledger. Only then update canonical and remote state. Duplicates or
   superseded proposals require a documented rationale and reciprocal links.

## Dependencies

The current review closes first. Native trust, service interruption, missing
approved operator text, platform availability and publication remain explicit
operator decisions. The current owner-requested cleanup reconciles obsolete
criteria through cited successor decisions; ADR-0219 retires only the removed
helper's signing obligations. Broad cleanup does not waive current proof gates.
No exhaustive workflow dispatch or unattended restart is implied.

## Acceptance

- [ ] Every unfinished item in the baseline inventory has a reviewed disposition: verified completion, a linked superseding/duplicate rationale, or a bounded remaining delivery package with explicit evidence and blockers.
- [ ] The current review findings and known AR-397/398/399 tracker debt have merged records, valid acceptance and strict tracker parity.
- [ ] Remaining packages are implemented and their applicable acceptance is satisfied before closure; no code, live-proof or operator gate is silently waived.
- [ ] The final inventory and canonical/remote statuses agree, with no unaccounted unfinished baseline item.

## Next bounded package

AR189/190/191 are published. Continue parent-coordinated serial AR192 and
AR194 packages; merge current main normally, preserving frozen acceptance
candidates and live identities. Root final delivery begins publication by00:52Z.
The September 7 continuation ends at 9 p.m. Eastern (September 8, 01:00 UTC);
leave a clean durable checkpoint. Windows-only work stays with the owner.
The older AR-152/298/348-first ordering above is historical and does not override
the owner's oldest-first loop. Keep genuine live/operator and fixture gaps
visible, exclude Windows execution, and do not close the full backlog until
every baseline record has a reviewed disposition and remaining acceptance is met.
