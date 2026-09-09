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

The second fixed phase exercised recipe 18 once per case and failed 0/3 full
acceptance gates. Ordinary review failed recruiter coverage and confidence;
follow-up received `critic_wrong_neighbor_selection`; multi-step timed out at
the planner after 60,071 ms. All have zero finalization events. The native
callback delivery path therefore remains unproven, despite passing source and
installed checks. Exact receipts are in
`AR-426-hermes-native-after-fragments-20260909.json`.

One fresh multi-step attempt is bounded to 360 seconds after the provider
timeout; there is no retry loop or manual staffing. AR-426 remains open and
PR 824 remains draft pending native and isolated acceptance evidence.
