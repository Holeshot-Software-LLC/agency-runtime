---
title: "AR-404 oldest-first backlog reconciliation"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [backlog, evidence, supersession, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-404 oldest-first backlog reconciliation

## Resumed checkpoint

On September 6 the owner explicitly resumed at AR-131. Restore the oldest-first
one-record/PR/merge loop; Windows work remains with the owner. AR-131's current
MCP/CLI contract review found and repaired a public identifier-admission gap.
All six isolated criteria satisfy at 973acdb9 on September 7; first verdicts
remain preserved at 6a139e23. PR #698 merged at ac1ce173. AR-135's current source
and generated smoke pass, but native parent/child/Stop evidence still needs an
attended ZCode call; its retention merged in PR #699 at e2f7a5f2. AR-138 is done:
browser review found and repaired accessibility/desktop clipping defects, and
the first isolated review exposed a stale-error race (preserved at 25b9a67a).
The repair passes 30 new late-error cases, all 172 UI tests and all 21 rebuilt-wheel
browser checks. All six second-pass criteria satisfy at 2ecde1a5; PR #700 merged
at 1ada216c. AR-140's implementation and all 39 local Linux routing/performance
gates pass, with 202 focused tests. Retain its isolated supported-runner evidence
hold, including the owner's Windows arm. PR #701 merged at 7afa4b4d. AR-145 is
retired under ADR-0224: the working repairs pass 41 focused instrumented tests,
the mandatory exhaustive-release checklist is superseded, and AR-176 retains
actual fixture/requested aggregate diagnostic work. PR #702 merged at cd061668.
AR-147 is Windows-only and remains with the owner. AR-150 is accepted at ae71761f:
four direct inverse-order tests supplement the existing shared refresh epoch.
First review's evidence gap remains at 4e820ff4; all four second-pass criteria
satisfy. UI 176 and server 180 pass, with same-byte installed-wheel evidence.
PR #703 merged at 460f319b. AR-151's direct host contract passes 13 scenarios;
its full-dashboard criterion exposed nine unchanged-main fixture failures.
Their bounded repair passes 274 dashboard tests and the named spine; no product
change. ADR-0225 explicitly reconciles the old blanket duplicate criterion with
per-host authority; first verdicts remain at f954d1e9. All four second-pass
criteria satisfy at 791820bb; AR-151 is done, PR #704 merged at 5a12f357.
AR-153 confirms existing worker-filter-before-limit and bounded evidence:
focused six, workforce lifecycle 25 and UI 176 pass. ADR-0105 reconciles only
its obsolete full-corpus criterion; all four isolated criteria satisfy at ea577285.
AR-153 is done; PR #705 merged at 8b36ea28. AR-154's initial-page repair also
exists. Twelve new direct state-preservation cases, 13 cursor/activity/observation
cases and all 188 UI tests pass. All four original isolated criteria satisfy
at e1c3069c; AR-154 is done, PR #706 merged at 434175f0. AR-155 confirms existing
200-row/1 MiB metadata-only hiring pages and explicit exact-case evidence loading.
Four focused Store/HTTP cases, 25 workforce tests and 188 UI tests pass. Only its
stale fifth gate is reconciled under ADR-0105. All five criteria satisfy at
6ed24943; initial criterion-3 unavailability is preserved at a3e00bd5, and its
single unchanged-candidate retry passes. AR-155 is done; PR #707 merged at 729e7dc4.
AR-156 retains its hosted/Windows proof but repairs real local false success when
Node is unavailable and the stale documented UI command. Three comments recover
the unchanged asset budget without executable changes. Fast workflow 165 pass,
spine 1085/three skips and UI 188 pass. Its exact rebuilt wheel passes 21 loaded
browser checks; PR #708 merged at 6b4650b3. AR-157 and AR-158's existing behavior
and strengthened tests are accepted through PR #709 (ea6864b1) and PR #710
(b2ea5946). AR-159 remains open: current main is unprotected with no rulesets or
current check contexts. Local aggregate/security contracts pass 104 tests;
hosted enforcement awaits explicit owner approval and current check evidence.

Previous pause: the owner asked to conserve credits and publish AR-130 through
[PR #696](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/696),
merged at f38720c7 with exact ledger delivered by PR #697 at c1c5d9d9. That pause
is now lifted; its historical instruction did not authorize background work.

## Owner-directed order

The owner requested: oldest first, one record at a time, PR, merge, then the
next; do not stop for routine approval. Windows work remains with the owner.
This replaces the earlier AR-349-first queue. Read-only investigation of the
current session's missing staffing credential/header evidence is set aside
until its relevant backlog package; no credential, trust or service change is
authorized merely by a record's age.

Order unfinished canonical records by original creation date, with stable AR
number breaking same-day ties. Each gets one explicit disposition: accepted
complete, superseded/irrelevant retirement, real bounded implementation, or
retained with its exact unresolved dependency/operator/platform evidence.
An umbrella whose children remain open cannot be completed just to move down
the list. Retain it and continue to the oldest actionable record. Do not
create 99 duplicate tracker issues or assume those records mean 99 defects.

At e5662d91 the queue is 141 unfinished records: 42 mapped plus 99 exempt
pre-tracker records. The legacy population was 104 before four verified
completions (AR-148/149/152/323) and one retirement (AR-139). Historical
snapshots remain intact; a retired mapped record changes the mapped count,
not the 99 legacy count.

## Sequential dispositions

| Order | Record | Disposition and evidence | Publication |
|---|---|---|---|
| 1 | AR-115 | Retire as superseded, not accepted. ADR-0222 replaces ADR-0078's heuristic staffing/six-field header with existing inference-only/canonical-five-field authorities. Original unchecked live gates retained; AR-119 explicitly absorbs the surviving outcome and AR-125 retains evaluation. Focused routing/header/credential/records: 183 passed (19.11s); fast spine: 1075 passed/three skips (68.74s). No runtime or live-state change in the retirement. | [PR #690](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/690) merged at d9ea419b; #127 closed NOT_PLANNED at 2026-09-05T23:47:12Z, read back. |
| 2 | AR-119 | Retain in_progress: relevant nine-rule/five-host umbrella with incomplete exact-candidate live evidence, AR-252 promotion, AR-253 dispatch/latency, AR-255/281 child proof, and AR-125 value/evaluation. Matrix still has three proven and 42 unproven cells at its August 18 candidate, not September certification. Reconcile stale current-state/capsule and R1 narrative; preserve all matrix rows, candidate, founding vision, criteria and failure history. | [PR #691](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/691) merged at 8b8b594e; [disposition comment](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132#issuecomment-5555649869); #132 intentionally remains open. |
| 3 | AR-120 | Retain open, partially implemented: normalized contracts, typed relationships, atomic snapshots and quarantine authority exist (219 focused tests pass, 15.34s). Independent enrichment-review evidence, owner-approved discoverability baseline, and proposed contract/confusion/evaluation refresh remain real gaps. Weekly cadence is intentional; do not restore nightly spending or automatic activation. Original acceptance unchanged; bounded remaining plan recorded. | [PR #692](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/692) merged at bc392228; #133 read back OPEN. |
| 4 | AR-125 | Retain open: configured/held-out matched selection, paired outcome lift and five-host live evidence remain unproven. Evaluation machinery exists (33 focused regressions pass, 2.68s); it is not the study result. Label checked old-candidate Windows/Linux evidence as historical. One-shot application work already belongs to deferred AR-178 under ADR-0102; do not restore it as a gate. Six original acceptance states unchanged. | [PR #693](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/693) merged at 79930464; #138 read back OPEN. |
| 5 | AR-127 | Retire obsolete checklist under ADR-0223, not accepted. The shape fix exists at both rejection sites; ADR-0089 stays accepted. Current first-pass/replay, Rule-8 availability, and bounded verification supersede the old retry/unavailable/full-suite assumptions. AR-135 owns current ZCode integration. Broader check: 133 pass/three known legacy failures, explicitly owned by AR-176; no runtime/test change or new live claim. | [PR #694](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/694) merged at 66282312; #151 closed NOT_PLANNED at 2026-09-06T00:23:39Z, read back. |
| 6 | AR-129 | Shared least-privilege environment implementation exists. Non-Windows environment/discovery/namespace tests: 64 pass, 12 Windows-named cases deselected (0.43s). Retain the explicit native Windows/installed evidence hold for the owner, not a code-rebuild task. Original acceptance unchanged; no duplicate pre-tracker issue created. | [PR #695](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/695) merged at d38e9d13; legacy record remains open. |
| 7 | AR-130 | Positive trust cache is already removed; Store connections revalidate. Current regression/file-integrity package: 19 pass (0.23s). Broader non-Windows run: 40 pass/two confirmed stale fixtures/39 Windows-named cases deselected (0.84s); AR-176 owns the wrong ACL-double boundary and obsolete 0644 expectation. Retain native Windows and current hook-budget evidence, not a trust-repair rewrite. Historical latency and original criteria preserved. | Published in [PR #696](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/696); legacy record remains open. Exact publication receipt belongs to the worklog. |
| 8 | AR-131 | Done: original MCP repair verified and remaining public identifier aliasing repaired. Six isolated criteria satisfy at 973acdb9; first verdicts preserved at 6a139e23. New public cases 13 pass; MCP/CLI 126/five skips; spine 1085/three skips; UI 138; routing pass; conformance 184/184 killed, source unchanged. Unchanged fallback fixture fails on main and belongs to AR-176, not hidden as green. | [PR #698](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/698) merged at ac1ce173. Legacy count 99 → 98; actual open trackers remain 40. |
| 9 | AR-135 | Retain open: installer/rendering/correlation implementations exist. 16 installer/header, 13 selected hook/Stop and four child-adapter/delivery/profile cases pass. Generated ZCode smoke passes 4/4, including isolated SessionStart process, config preservation/idempotency/toggles. Installed inspection is enabled-runtime-unverified, no executable or canary; current native Agent/record-zero/full-Stop proof needs an attended call. Correct only the fixture docstring that called stubbed routing live proof. | [PR #699](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/699) merged at e2f7a5f2. No production, user-profile, acceptance, matrix or count change. |
| 10 | AR-138 | Done: original refresh/mobile repairs verified; remaining accessibility/clipping and stale-error races repaired at d7231df3/cd35aa2c. First failed review preserved at 25b9a67a. All six isolated criteria satisfy at 2ecde1a5. Dashboard Python 180 pass; repeated named spine 1085/three skips; UI 172 and current coverage floors pass; rebuilt wheel passes 21 loaded-view checks at 1280/1024/375 px. | [PR #700](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/700) merged at 1ada216c. Legacy count 98 → 97; actual open trackers remain 40. |
| 11 | AR-140 | Retain open: optimization, cache safety and explicit budgets are implemented. All 39 current local Linux gates pass: narrowing/cache p95 1.081/0.201 ms; CLI version median 16.989 ms; all retrieval tiers pass with the unchanged result hash. Focused tests 135 + 67 pass. ADR-0121 governs candidate recall/synthetic cache evidence, not real staffing; AR-253 owns end-to-end staffing latency. Original isolated supported-runner gate remains, with Windows for the owner. | [PR #701](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/701) merged at 7afa4b4d; no code/threshold/acceptance or count change. |
| 12 | AR-145 | Retire duplicate mandatory coverage checklist under ADR-0224, not accepted. Existing observation/ownership/synthetic-performance repairs and authority tests pass 41 focused cases under branch instrumentation (12.08s). No aggregate percentage is claimed. ADR-0105 already made exhaustive delivery gates optional; AR-176 explicitly owns remaining fixtures/requested aggregate gaps with the unchanged 97-percent floor. AR-156 owns observed release-checklist UI command drift. | [PR #702](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/702) merged at cd061668; legacy count 97 → 96, actual open trackers remain 40. |
| 13 | AR-150 | Done: existing epoch/cancellation verified with four new direct inverse-order cases, both scope directions and response orders. First missing-evidence review preserved at 4e820ff4; all four second-pass criteria satisfy at ae71761f. UI 176 passes 95/86/93 floors; server/auth/transaction 180 pass. Unchanged product bytes bind the 21-case wheel receipt; no runtime change. | [PR #703](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/703) merged at 460f319b. Legacy count 96 → 95; actual open trackers remain 40. |
| 14 | AR-151 | Done: existing host rejection verified by 13 direct UI-to-POST cases. Nine stale dashboard fixtures repaired; full six-module suite 274 pass, UI 176/current floors pass, named spine 1085/three skips. ADR-0225 explicitly revises only the old blanket duplicate criterion; original wording and first contradicted verdict remain at f954d1e9. All four second-pass criteria satisfy at 791820bb. No runtime change. | [PR #704](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/704) merged at 5a12f357. Legacy count 95 → 94; actual open trackers remain 40. |
| 15 | AR-153 | Done: hiring filter precedes limit; lineage/evidence pages have exact totals/truncation and one read snapshot. HTTP detail is capped at 200 rows/collection and 2 MiB. Fresh targeted six, full workforce lifecycle 25 and UI 176 pass; byte-identical dashboard/spine receipts reused. ADR-0105 explicitly reconciles only the obsolete full-corpus criterion. All four isolated criteria satisfy at ea577285. No code/test change. | [PR #705](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/705) merged at 8b36ea28. Legacy count 94 → 93; actual open trackers remain 40. |
| 16 | AR-154 | Done: existing initial-page admission is fail-closed. Twelve new full/control refresh cases directly retain last-good data/revisions for missing first cursor/revision in roster, snapshots and reviews. Focused cursor/activity/observation 13 pass; UI 188 pass current production floors. Python/source receipt reuse is explicit. All four original criteria satisfy at e1c3069c; no runtime or criterion change. | [PR #706](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/706) merged at 434175f0. Legacy count 93 → 92; actual open trackers remain 40. |
| 17 | AR-155 | Done: collection SQL omits every evidence document, Store/HTTP cap 200 rows at 1 MiB, exact lookup retains all five documents, and explicit UI inspection rejects stale responses. Fresh focused four, workforce 25 and UI 188 pass; Python/source receipts are reused. ADR-0105 reconciles only the obsolete fifth gate. All five criteria satisfy at 6ed24943; initial criterion-3 unavailability is preserved at a3e00bd5 and its sole unchanged-candidate retry passes. | [PR #707](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/707) merged at 729e7dc4. Legacy count 92 → 91; actual open trackers remain 40. |
| 18 | AR-156 | Retain open; existing bounded workflow/local runner verified. Missing-Node false success repaired before any gate execution, local/hosted/documented UI argv pinned to unchanged floors, and branch/push guidance reconciled. Comment-only compaction restores 387,058 bytes below the unchanged 387,072 ceiling. Workflow 165 pass/five Windows-named deselections; spine 1085/three skips; UI 188 pass. Four Windows-profile assumptions fail on Linux unchanged main and remain owner work. | Clean dccb4e85 wheel passes 21 private/offline loaded browser checks and all three polling/fault-recovery interactions; receipts/screenshots retained. [PR #708](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/708) merged at 6b4650b3; no acceptance or count change. |
| 19 | AR-157 | Done: existing quiet public/disconnect handling confirmed. Two primary tests now verify actual content-free degraded observations. Two stale HTTP fixtures repaired at current catalog/finalization seams. Full four-module package 104 pass/three existing skips, targeted transport 100 percent. Runtime bytes unchanged; current spine/UI/wheel reuse explicit. Only obsolete criterion 6 reconciled under ADR-0105. | All six isolated criteria satisfy at a35657e1. [PR #709](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/709) merged at ea6864b1; legacy count 91 → 90, actual open trackers remain 40. |
| 20 | AR-158 | Done: existing MCP/HTTP exact selectors verified. Hook observation proof restored on the current three-host R8 failure test; no retired denial restored. Store slow/busy fixtures inject matching unrelated events, busy selection requires exact request ID, and privacy checks cover all envelopes. Focused 13 pass, ten five-case repeats all pass, complete five-module package 135/five skips. Runtime unchanged; scoped spine/UI/wheel reuse. Only criterion 7 reconciled under ADR-0105. | All seven criteria satisfy at 95085a30 after one citation-only recheck; first review preserved at 809354be, six accepted checks unchanged. [PR #710](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/710) merged at b2ea5946; legacy count 90 → 89, actual open trackers remain 40. |
| 21 | AR-159 | Retain open: September 7 main unprotected, no rulesets including parents, no current check runs/status contexts. Source aggregate/security contracts pass 104 focused cases. Latest listed CI/CodeQL are August 31/cancelled; historical billing cause is not freshly established. All seven original criteria remain; owner approval, current check/app identities and bypass/readback proof required. | [PR #711](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/711) merged b499e7fb. No hosted settings or count change: 40 actual trackers plus 89 unfinished legacy records. |
| 22 | AR-160 | Retain in_progress under ADR-0219: no removed helper restored, original five current criteria unchanged. Fresh 258 focused cases pass/one native-Windows deselection; canonical Linux pair from clean f1c7d0b0 passes independent portable verification and strict Twine. Fresh separate wheel/source installs each pass packaged MCP/dashboard/config/roster/selection, CLI, pip check and eight deterministic smoke checks including five generated host bundles. | [PR #712](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/712) merged f18b5acf. Windows producer, paired-source/shared-payload/release-set proof and applicable live host/publication authority remain explicit. No count change or native-host claim. |
| 23 | AR-162 | Existing topology verified; actual HTTP-200/no-body false availability repaired with bounded strict JSON classification. One request, exact analyzers, unavailable evidence, permissions, events and aggregate remain. Focus 65, full non-Windows workflow 210 and named spine 1085/three existing skips pass. Current public API availability is not a hosted pass. ADR-0226 reconciles claim-conditional measurement (8) and the existing legacy tracker exemption (9); first verdicts are preserved at c456b6bd. Exact pre-change/current event projections now compare identical. | All nine criteria satisfy at d30b8ae0 in the second and final review; AR-162 done. [PR #713](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/713) merged a01abe81 at 09:53:40Z September 7 before AR-163. Hosted enforcement stays with AR-159; no licensing/settings/dispatch changes. |
| 24 | AR-163 | Existing implementation remains relevant and present. Fresh 167 complete remediation/API-projection and 188 DOM cases pass without failures/skips. Signed historical evidence cannot suppress current ineligible candidates; original events reopen without churn; dashboard revision/prefix continuity and disjoint labels remain. No code or test changes. | All eight original criteria satisfy at fd551fd4 in the first review; AR-163 done. Legacy exemption applies; 40 mapped plus 87 legacy = 127 unfinished. No native-host claim. [PR #714](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/714) merged 6d1ca01f at 10:04:47Z September 7 before AR-164. |
| 25 | AR-164 | Existing ancestor PATH boundary remains relevant and implemented. Fresh 38 discovery, 129 current launch and 24 surviving Git/process cases pass; Windows limits explicit. ADR-0227 reconciles only deleted execution-backend names in criterion 5, preserving original wording and all other criteria. No code/test changes. | All seven current criteria satisfy at 2a7c20c5 in the second review; first absence verdict preserved at 6ac3b1aa before exact Git proof. AR-164 done; [PR #715](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/715) merged ba6e55cb at 10:23:29Z September 7 before AR-165. Retired worker dispatchers stay removed; native Windows and AR-187 attended activation remain separate. |
| 26 | AR-165 | Real malformed-input gap repaired: strict duplicate-free bounded UTF-8 JSON and array success shape. Four reproduced false classifications now fail closed. Focus 62, full non-Windows workflow 235, fresh spine 1085/three existing skips pass. Both permitted paths and action pins unchanged. ADR-0228 explicitly reconciles only measurement/tracker criteria 8/9, preserving originals. | All nine current criteria satisfy at 9effff3f in the first review; AR-165 done; [PR #716](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/716) merged 520a10e3 at 10:58:51Z September 7 before AR-166. Current public API access is not hosted success or a savings claim. Counts: 40 mapped plus 85 legacy = 125. |
| 27 | AR-166 | Existing correlation/privacy remains. Stale read-only criterion conflicts with ADR-0117; provider selector still disables all valid choices. One-line repair plus direct selection/redaction/invalid-list/recovery tests; UI 189/current floors, backend/owner 235, fresh spine 1085/three skips pass. ADR-0229 explicitly reconciles only criterion 1. | Browser checkpoint and six isolated verdicts pending. Counts unchanged: 40 mapped plus 85 legacy = 125. No backend/broker authority change or AR-298 completion claim. |

After the merged AR-115 retirement, fresh enumeration confirms 41 open trackers
and 140 unfinished local records (41 mapped plus 99 legacy) before AR-127.
After merged AR-127 retirement, fresh enumeration is **40 open trackers** and
139 unfinished local records (40 mapped plus 99 legacy). Retained AR-129 leaves
both counts unchanged, as does retained AR-130. Accepted AR-131 now reduces the
local queue to **138** (40 mapped plus **98 legacy**) without a tracker closure.
Retained AR-135 leaves those counts unchanged. Accepted AR-138 reduces the local
queue to **137** (40 mapped plus **97 legacy**), without a tracker closure.
Retained AR-140 changes neither count; it is not a new unfixed Linux hot-path bug.
Retired AR-145 reduces the queue to **136** (40 mapped plus **96 legacy**),
without claiming its original aggregate coverage criteria passed.
Accepted AR-150 reduces the queue to **135** (40 mapped plus **95 legacy**),
without creating or closing an unrelated tracker.
Accepted AR-151 reduces the queue to **134** (40 mapped plus **94 legacy**),
with ADR-0225's requirement reconciliation and first verdict preserved.
Accepted AR-153 reduces the queue to **133** (40 mapped plus **93 legacy**),
under ADR-0105's already-established bounded verification policy.
Accepted AR-154 reduces the queue to **132** (40 mapped plus **92 legacy**),
with all four original criteria unchanged and independently satisfied.
Accepted AR-155 reduces the queue to **131** (40 mapped plus **91 legacy**),
with ADR-0105's fifth-gate reconciliation explicitly recorded.
Accepted AR-157 reduces the queue to **130** (40 mapped plus **90 legacy**);
its first five criteria are unchanged and criterion 6 follows ADR-0105.
Accepted AR-158 reduces the queue to **129** (40 mapped plus **89 legacy**);
all seven criteria satisfy after one command-citation recheck, not a code retry.
Accepted AR-162 reduces the queue to **128** (40 mapped plus **88 legacy**);
all nine current criteria satisfy, with original criteria 8/9 and first verdicts
preserved before explicit requirement reconciliation.
Accepted AR-163 reduces the queue to **127** (40 mapped plus **87 legacy**);
all eight original criteria satisfy in the first isolated review, without any
runtime/test change or requirement reconciliation.
Accepted AR-164 reduces the queue to **126** (40 mapped plus **86 legacy**);
only obsolete criterion 5 terminology changed; the missing Git output and first
verdict are preserved. All seven current criteria satisfy without code changes.
Accepted AR-165 reduces the queue to **125** (40 mapped plus **85 legacy**);
all nine current criteria satisfy in the first review after the parser repair.
Windows-specific work remains with the owner.
This is record reconciliation, not completion of retained implementation or
platform-evidence work.

Publication correction: GitHub interpreted the negated closing phrase in
PR #691's original body as a closure directive and closed #132 at 23:59:38Z.
Strict parity caught this during AR-120 review. The body was corrected, #132
reopened, and OPEN state plus the 41-issue count read back. It never represented
an acceptance verdict. Retained-item PRs use references without closing syntax.

The Codex-only hook refresh requested during AR-119 review returned exit 1
with activation required, unverified trust and a reported projection mismatch;
it did not supply live evidence or change any backlog disposition.
