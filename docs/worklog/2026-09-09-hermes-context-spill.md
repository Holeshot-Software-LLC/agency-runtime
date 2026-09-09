---
title: "Hermes native hook spill repair"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [hermes, context, reliability]
related:
  - docs/roadmap/issue-AR-426-preserve-hermes-hook-specialist-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0244-deliver-large-hermes-card-sets-through-native-tools.md
supersedes: []
superseded_by: null
type: worklog
commit: ab924385dc8b1e7f0b2c218c2bebab55cb52b3db
short: ab924385
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/824
date: 2026-09-09
related_issues:
  - docs/roadmap/issue-AR-427-preserve-complete-inferred-specialist-team.md
  - docs/roadmap/issue-AR-428-avoid-test-results-units-without-test-results.md
  - docs/roadmap/issue-AR-426-preserve-hermes-hook-specialist-context.md
---

# Hermes native hook spill repair

## Approach

Owned worktree starts at clean synchronized c6c3e7b5. AR-426/#823 separates native
input-context spilling from AR-418 output truncation. Recipe17 defers large Hermes
card loads to a local native tool, preserves exact selected versions and caps the
whole returned JSON below the native tool-spill floor before recording a load.
The final hook envelope stays below10,000characters. Small inline cards and the
shared staffing/critic routes remain unchanged. No native spill or output budgets
are raised. No old terminal receipt is reopened.

## Evidence and challenges

The exact native messages535347/535352 contain12,991/16,585character spill pointers,
not the selected full cards or response contract. Retained JSON binds native
message/session identity, saved-context digest, Store failure and terminal records.
The old-source regression emits15,578characters and wrongly records four loads
before retrieval; its bounded-hook assertion fails. The candidate returns full
exact cards through the generated tool with native correlation.

A new cross-session regression found an exception before the shared active-turn
check; the bridge now rejects correlation before taking the snapshot. Registration
tests needed their exact expected tool set updated. All failures remain in the
validation artifact. A mistyped nonexistent test filename ran no tests and is not
verification. Source Python could not inspect an installed worker projection;
the installed interpreter's read-only inspection succeeds8/8trusted.

## Five-host receipt boundary

Fresh parent Codex MCP process2200222 executes projection6db15efbecbe and responds;
classifier6 is recorded. All615installed package files match the prior wheel.
The handoff trace01a086f4 has classifier5, subject/reranker contract rejections,
critic_wrong_neighbor_selection and no finalization event. No raw failed routing
selection is persisted; the critic cannot be judged erroneous from these receipts.
Claude review and OpenClaw follow-up retain wrong-neighbor vetoes; Hermes review
retains missing independent assurance. Zcode first responses place Bash permission
explanations before their headers. Later corrected output cannot repair the valid
first terminal rejection. Hermes default checkout7cd91114 is unchanged; upstream
PR106490 remains open at30f421ecce. AR-418 original output cap remains unknown.

## Verification

Candidate context/terminal tests75passed; wider focused121passed/6skipped. Wider focused, required fast validation,
canonical build and fresh installed native demonstration follow this checkpoint.
No exhaustive or Windows workflow. AR-423 corrected packet still awaits explicit
owner authorization for a third isolated pass. No all-host reliability claim.

## Follow-ups

Finish the bounded AR-426 validation/install/demo/isolated acceptance package,
merge through a PR and record exact implementation and merge worklogs. Preserve
AR-404/418/423 and remaining Zcode/staffing failures until their own gates pass.

## Installed demo checkpoint

PR824 is draft. Sourceab924385/artifactaee01dc6: required production1151passed/3skipped,
UI224passed, routing/Ruff/format/docs/strict tracker417pass. Focused75context and
121wider/6skip pass. Frozen conformance188/188killed,0invalid/0survived, source
unchanged. Canonical build, Twine, independent artifact validation and installed
smoke pass;616files exactly match wheeldd6e13969f3d78e060945b949236290ffc6a77d021fdfc0c0c901d000cc6f59f.
The shared-clone build hit the bounded Git-output limit; a private clone of the
same immutable commit built successfully with no source or limit changes.
Only Hermes native projection refreshed; other four native projections remain
as previously verified. No native budget/settings/permission changes. Three
unchanged Hermes manifest requests will each run once under360s, preserving
all failures. The full-card native gate and isolated acceptance remain pending.

## First native phase and bounded refinement

Tool-only candidateaee01dc6 native phase returns95.801s/69.346s/99.422s, no timeouts.
Review finalizes with matching headers but omits both pending cards. Follow-up
omits cards and fails the first header; multi-step fails the critic with
critic_wrong_neighbor_selection_code_reviewer. No case satisfies all native gates.
The exact frame is no longer spilled, and no omitted card is counted loaded.
No failed turn is reopened. This evidence motivates a source delivery refinement,
not an unchanged-condition retry: use Hermes's documented ordered callback list
and per-callback spill application to deliver full cards before model execution.
Recipe18 candidate adds at most16card callbacks plus a current snapshot. Each
card uses the existing exact selected-version native bridge, with no new inference,
manual identity choice or budget/permission change. Native source excerpts and
hashes are preserved in AR-426-native-fragment-contract-20260909.json.

Refined callback/context/terminal focused suite131passed; Ruff and format pass.
Revised production, conformance and native proof follow the source checkpoint.

## Callback candidate demo checkpoint

Sourcefaf5645a/artifact22f24edd, recipe18: focused131pass, production1151pass/3skip,
UI224pass, routing/Ruff/format/metadata/docs pass. Frozen conformance188/188killed,
0invalid/0survived, source unchanged. Canonical build, Twine, independent artifact
validation and installed smoke pass. All616files match wheel73cf18d6e49156fd736a62eed6de582b9d4d23f705fda67d4436f5c86f26479f.
Only Hermes projection refreshed. The callback candidate will run the unchanged
three native requests once each under360s. Initial native failures remain retained;
AR-404/418/423/426 remain open before native and isolated proof.

## Callback native phase

The second fixed phase exercised recipe 18 once per case and passed 0/3 full
acceptance gates. Ordinary review failed recruiter coverage and confidence;
follow-up received `critic_wrong_neighbor_selection`; multi-step timed out at
the planner after 60,071 ms. All have zero finalization events. The native
callback delivery path therefore remains unproven, despite passing source and
installed checks. Exact receipts are in
`AR-426-hermes-native-after-fragments-20260909.json`.

One fresh multi-step attempt is bounded to 360 seconds after the provider
timeout; there is no retry loop or manual staffing. AR-426 remains open and
PR 824 remains draft pending native and isolated acceptance evidence.

## Final bounded native attempt

The single fresh attempt after the planner timeout ran 91.605 seconds, session
20260909_130400_c24d85, trace
20260909_130400_c24d85:f1369f31-b3e1-43f1-845b-8e3fabde18a1:4e6a81af.
The planner and recruiter applied; reranker contract rejection and independent
critic_wrong_neighbor_selection remain recorded. No finalization event exists.
The native user context contains the contract without a spill pointer, but
staffing failed before any selected-card callback path. This does not establish
full-card delivery. No further native attempt is scheduled.

AR-426 is blocked by shared staffing; PR 824 remains draft and unmerged. The
builder record cites exact source evidence for criteria 1/2 and explicitly absent
native acceptance for criterion 3. AR-404/418/423 remain open; AR-423's third
isolated pass still requires the pending explicit owner authorization.

## Isolated evidence review

First AR-426 pass: criterion 1 absent because native pointer paths were replaced
with placeholders, criterion 2 satisfied, criterion 3 explicitly absent. The
whole first record is retained. The corrected packet includes exact native
head/tail output and historical pointers, with content hashes and missing-marker
comparisons. One second default pass follows; no third pass is authorized.

## Blocked package checkpoint

Second isolated AR-426 pass: criterion 1 remains absent because the verifier
requires preserved missing context itself in addition to native pointer/head/tail
text; criterion 2 is satisfied; criterion 3 is explicitly absent. Both passes
remain recorded. The two exact saved native context files are now copied into
repository evidence with a SHA-256 manifest for a future corrected packet. The
saved files include a terminal newline beyond each native-reported hook length.
No third isolated pass is run or authorized; the current verdicts are unchanged.

Package exits blocked, not done. PR 824 stays draft/unmerged. No issue closes.
Native acceptance is blocked by shared staffing, and failed content-free receipts
cannot establish that a critic veto was erroneous. Next bounded implementation
must diagnose that boundary before choosing a repair. AR-423's third pass remains
separately pending. Main stays clean at c6c3e7b5; this owned branch retains all
substantive/ledger checkpoints. Required source checks pass; final docs/tracker
parity follows. No exhaustive or Windows workflow.

A final policy-availability invocation initially lacked PYTHONPATH and raised
ModuleNotFoundError before checking; the same check passed with the source path
and project interpreter. Packet preparation rejected an out-of-range line 36
before any verifier call; corrected range 1-35 passed the dry-run checks.

Final metadata (1371 Markdown files), policy availability, exact worklog, docs
with required trackers, strict tracker parity (417 items; 2 historical PR-tracked
items skipped) and diff checks pass. Main remains clean at c6c3e7b5; the owned
branch is preserved as draft PR 824 with no merge or issue closure.

## Authorized continuation and bounded critic capture

Owner's 2026-09-09 "go for it" authorizes continued reliability repairs and one
additional isolated pass for each corrected AR-423/426 packet. AR-423 uses its
own worktree. Before choosing a staffing repair, one fresh Hermes multi-step
diagnostic captures the actual inference proposal and public critic response
through the previously established loopback observer pattern. The observer
forwards request/response bytes unchanged, forwards credentials without logging
headers, and captures only the exact supplied-code request. Synthetic tests
pass all three boundaries. The call is capped at 360 seconds and never loops;
the owner config is restored in finally. No trust or staffing validator changes.

## Complete-team delivery finding and repair

The authorized AR-423 pass satisfied criteria 1/3 but left criterion 2 absent on
independent assurance. Read-only Store comparison found a concrete High defect:
five specialists were selected, including a separate security reviewer, while
four immutable prompt references were persisted. AR-427/#825 owns the legacy
hydration cap repair. Recipe 19 requests complete-team hydration under the
existing sixteen-reference and host-context limits. Missing or overflowing teams
fail before any load recording; default legacy helper callers retain their cap.

Corrected regressions fail on old source in all five host paths and both native
retrieval paths (7 failed for the omitted fifth worker). The first fixture was
invalid because it put five workers in one unit; that failure is retained and is
not causal evidence. Valid candidate checks: 66 passed / 1 skipped focused,
production 1151 passed / 3 skipped, UI 224 passed. Frozen conformance and a fresh
installed native complete-team demonstration follow this checkpoint.

The one Hermes critic diagnostic ran 103.375 seconds, captured one exact packet,
and restored owner configuration byte-for-byte with no observer errors. The
critic veto remains failed. Its plan invented static test-result analysis and
selected a role requiring completed results despite no execution. AR-428/#826
records that separate planning defect; no speculative critic override or planner
repair is bundled with the bounded hydration change.

## Recipe 19 installed checkpoint

Source `176adc19` and ledger `20c49e0d` preserve the complete selected team.
Frozen conformance passed 188/188 under private umask 077 after the retained
permissive-umask fixture failure. Canonical distribution, installed smoke and
616-file identity checks pass. OpenClaw normal stop/refresh/start completed;
the immediate RPC startup probe failed, and the subsequent read-only probe is
healthy. No observer remains. Eight refreshed Codex hooks are modified; owner
trust review and fresh process are pending. PR 827 retained Claude evidence and
its absent criterion 2; no issue closure or whole-team acceptance is claimed.

## Fresh complete-team native checkpoint

One unchanged large-context request ran once each in fresh Hermes and Claude
processes with 360-second limits. Hermes session `20260909_143551_e08888`
passed in 114.863s: native message 535391 contains all five inferred immutable
cards and the response contract without a spill pointer; first authoritative
response hash is `6546ecb6525a7f1237f47e519b7971574e9d7424862bf50e23ee364f9a980968`.
Claude session `0a59da24-79ca-4bc5-afa2-b4f4e32ba5eb` failed both planner
contracts in 118.255s; first reply missed correctness/security review, second
reported semantic invalidity. No unchanged retry or acceptance claim.

AR-426's owner-authorized third isolated pass and AR-427's first pass now have
exact native cards and terminal proof. The old AR-426 second record is retained.
Hermes checkout remains `7cd91114`; upstream PR106490 still open at `30f421ecce`.
Zcode's first failed outputs still contain permission prose before the headers;
later corrected responses cannot replace their terminal receipts.

## Isolated scope acceptance and fresh Codex

AR-426 third pass returned satisfied for all criteria: `bb4cf179`, `73ca814f`,
`eaba9409`. AR-427 first pass returned satisfied: `d32ea9de`, `7cd12f81`,
`653edb20`. Exact digests and reasons remain in their acceptance records. Those
two scopes are done; AR-404, AR-418, AR-423 and AR-428 remain open.

The owner completed Codex's refreshed trust review: eight trusted, zero modified.
Fresh Codex PID 2749577 spawned runtime PID 2749856 and UserPromptSubmit
PID 2750290 on published projection `37c1bf7d5eb0`. The parent PID 2200222
remains stale at `6db15efbecbe`; no process was silently replaced. Fresh Codex
session `01a0877b-45dd-7b01-b99d-92c03587393f` passed in 103.434s with all
five selected cards and response hash `72f3a83528f0165e820684d23f3cd1b3394d2ae1b30c9805a4da06e81acc85e0`.

## Merge checkpoint

PR 824 merged at `e81f8e00d5d511e2c605192ff9c5a461aebe0cb2` with exact
subject `fix(runtime): merge PR824 complete native specialist delivery`.
The immediately following ledger records that commit. AR-426/#823 and AR-427/#825
closed automatically from the reviewed PR body after all criteria satisfied.
AR-404, AR-418, AR-423 and AR-428 remain open. Implementation and acceptance
worktrees are historical and merged; next substantive work uses a new owned tree.
