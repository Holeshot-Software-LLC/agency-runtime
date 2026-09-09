---
title: "Preserve Claude selected cards across native hook limits"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [claude, context, native, exact-delivery]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
supersedes: []
superseded_by: null
type: worklog
commit: cd86e40a994bd7d6fad8699047140a8e369718a0
short: cd86e40a
date: 2026-09-09
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/814
related_issues:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
---

# Preserve Claude selected cards across native hook limits

## Purpose

Four accepted selected cards become a native persisted-output pointer, leaving
full model-facing context unproved. The caller prohibits file reads. The shared
bridge also trims the final card's trailing whitespace.

## Approach

Recipe 16 preserves the selection and moves oversized Claude card bodies to the
existing MCP retrieval surface. Each request resolves the selected version/hash
on the exact active session/trace. Pending selection is not recorded as loading.
The hook frame reserves room for headers and the bridge guards the complete
10,000-UTF-16-unit envelope. Joining segments preserves trailing card bytes.

## Challenges encountered

The first fixture accidentally gave four workers the same primary unit; that
invalid fixture failed before delivery. Corrected bindings expose the native
limit and final-card trim. The original-source negative control asserts its
old recipe 15 and source paths, then fails at 15,076 units versus 10,000.
The first production spine finds one direct non-Claude MCP regression: consulting
a full completion snapshot on a recipe-less legacy turn raises prematurely.
Restricting versioned snapshot lookup to Claude preserves the existing behavior.
Failed logs remain local; final results are recorded below as they complete.

## Decisions and alternatives

ADR-0241 records supported versioned tool delivery and honest pending loads.
No model route, answering configuration, trust hash, critic, staffing authority
or finalization policy changes. No file-read workaround and no manual specialists.

## Verification

Twelve new regression cases pass, including immutable-version refresh, missing
version, cross-session, unselected and terminal rejection, exact inline bytes,
UTF-16 measurement and failed oversized envelopes without accepted finalization.
Targeted MCP plus new cases: 72 passed. Initial production spine: 1 failed,
1150 passed, 3 skipped; the targeted follow-up passes after the fix. Ruff check
and formatting pass (784 files). Final named spine: 1151 passed, 3 skipped in 70.30s. Expanded focused checks:
166 passed, 6 skipped in 70.05s. UI: 224 passed.
No fresh native candidate evidence or isolated acceptance yet.

## Follow-ups

Finish required checks and a fresh-source conformance run, build a verified
artifact, refresh Claude normally, and test the fixed requests with full native
MCP response evidence. Keep AR-423/424 open until isolated gates pass. AR-404
still includes Hermes, OpenClaw, Codex and Zcode; its pending operator choices
and failures remain in the umbrella capsule.

## Verified artifact and live checkpoint

Source cd86e40a and ledger/artifact source 0cd4f289 are on draft PR814. Canonical
build and independent distribution verification pass. Wheel SHA256
3cea5770b896f788b790675db8dda8ea1321638e899bb57633198ab7266c211e
matches all 615 installed package files; a fresh isolated interpreter reports
recipe 16. Packaged MCP, roster, configuration, dashboard and asset smoke passes.
Normal Claude/Zcode refresh completes; gateway stop/start exits zero and RPC is
healthy. No answering/staffing configuration or trust hashes changed.

The fixed Claude three-case sample runs once in phase after_context_delivery,
with the original requests, normal permissions, 360-second case deadline and
retained failure output. Source conformance is running in parallel with private
umask 077. New native full-card/terminal evidence is not claimed before collection.
The third AR-423 criterion names observable regression/native evidence; the separate
repository-mandated isolated procedure remains required, avoiding a circular demand
that the verifier find its own verdict before issuing it.

## First native sample retained

Claude review 68.932s completes with full selected card, all five headers and
accepted hash (session 68924d99-0e43-4336-aea3-9c522cbe6150, trace
466affa6-154a-4966-8fce-22d4b60dd930). Same-session follow-up 51.823s has the selected
card and correct function but omits all headers: terminal response_invalid, trace
52f38ef1-e52c-49db-8324-3f405a1f4a80. Native Bash verification was denied; no tests
executed. Multi-step 75.196s fails staffing with critic_wrong_neighbor_selection,
trace 78c65d99-bcef-4e93-9f83-0d24592c3924. These are retained failures.

Both staffed cases selected one card and used the inline path, so this fixed
sample does not prove the new MCP path. A separately frozen one-attempt download
path correctness/security review is the next native surface probe; it names no
specialists and leaves selection to inference. Its result cannot replace any
fixed-sample failure. Fresh-source conformance now passes 188/188, no survivors
or invalid mutations, source unchanged. AR-424 isolated builder is next.

## Large-context native permission boundary

The separately frozen probe completes in 219.959s, session
cecefbf5-1f0c-486b-8ee6-abc750958ed7, trace
9341a1b3-0b7a-484e-a091-ade99e3f7157. Inference selects four cards totaling
11,604 UTF-16 units. Recipe 16 emits a 4,741-unit native hook with no persisted
pointer. Claude requests all four exact correlated cards; native permissions
deny each agency_load_specialist call. No loaded row or full native card exists.
The header truthfully contains only agency-steward and all five values match Store.
Native agency_finalize permission is also denied, but the normal Stop hook centrally
accepts the exact truthful final response. Central acceptance is not card proof.

AR-423 enters waiting_for_operator for normal native MCP permission; no tool
permission or trust override was applied. The owner has been asked to approve
agency_load_specialist in an attended Claude session. Preserve this failed card
gate and do not repeat the probe until the permission condition changes.
The fixed sample's header-invalid follow-up and staffing-failed multi-step remain.

## AR-424 isolated evidence refinement

Initial isolated criteria 1 and 2 are satisfied (e5e1a845, 287ec303). Criterion 3
is absent (f25218ff): the verifier could not establish the link from source
cd86e40a checks to candidate e76c1477 and lacked an explicit AR-424 shared-host
check in its packet. The original verdict is retained. A new dedicated evidence
file records the exact production and tests tree identities, an empty source
diff, and a fresh run of the named real Zcode bridge whitespace regression.
The criterion and acceptance procedure remain unchanged; a second isolated pass
will judge the strengthened packet. No broad tests are repeated because source
and tests are unchanged. One initial builder schema check rejected bare file
paths before any model call; corrected paths were used for the first pass.
