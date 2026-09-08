---
title: "AR-414 staffing and failure-header checkpoint"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, staffing, headers]
related:
  - docs/worklog/2026-09-08-installed-qualified-veto-verification.md
  - docs/worklog/2026-09-08-captured-native-critic-veto.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/worklog/2026-09-08-native-staffing-receipts.md
  - docs/worklog/2026-09-08-recruiter-fallback-recovery.md
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/worklog/2026-09-08-negated-request-scope.md
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/worklog/2026-09-08-failed-headers-and-planner.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-414
branch: codex/ar416-installed-verification-20260908
evidence_commit: 0bc2f89526d8949d26699b49233c0a4307616205
minimum_ledger_commit: caab485176d63c3c0062c022e55866d8733f19e7
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/773
---

# AR-414 staffing and failure-header checkpoint

## Checkpoint

Installed-verification package waiting_for_operator. Verified8629e2ed wheel is
installed; all614package files match. Fresh wheel/sdist smoke and installed
captured-verdict replay pass; rejection is preserved with cause/omission marker.
AR-417 removes an unpackaged test-input dependency; extracted regression8pass.
Codex plugin0.1.0+codex.823aab6fbe85 registered/enabled, restart required. Fresh
hooks/list reports8modified/0trusted. Owner asked to review /hooks in a fresh TUI;
no bypass or native attempt. Initial verifier launch was refused by namespace
trust; same-version private Claude2.1.263 now passes transport checks. Isolated
acceptance returned4/4satisfied for AR-416 and3/3for AR-417; those scoped fixes
are complete. AR-414/415 remain open; no fresh native proof is claimed.

Earlier PR788 checkpoint: native handoff captured and source diagnostic fix verified.
Two exact native packets expose experiment-tracker assigned to non-experiment
handoff review. The critic veto is supported by that mismatch; its named
alternative is not verified as suitable. AR-416 retains a qualified veto's
standard cause plus an explicit omitted-detail marker. Owner config restored
byte-for-byte. Installed runtime and hook trust unchanged. Earlier ordinary
native review has accepted staffing and exact-response Stop-hook acceptance.

## Completed evidence

Header repair merged PR774/905d37b8; planner instructions PR775/975ce7b4.
Actual SQLite/MCP diagnostic renders truthful failed headers without accepting
the failed run. Earlier normal native session01a081a6-c4bf-7ee3-916a-5dff92d0b43b
delivered all five failure-header fields and exposed AR-415's negated-scope bug.
AR-415 repair merged PR779/d0bb4127, evidence PR780/21a8a39e, ledgercea0020b.
Installed c1ef8566 wheel74988840e7f2e01aebd1db45ccef56372cfe07a1c87b7ce515b6df19577590bc;
all614package files matched. Historical native evidence is not new-artifact proof.

Recruiter failure isolated: same captured real53,782-character packet returns
200 on MiniMax,404/model_not_found on the GPT-5.5 fallback. Owner configuration
had no content-fallback route and strict budget5 could starve fallback/critic.
GPT-5.6-sol candidate timed out60s and was not adopted. GLM candidate passed
the actual nomination accumulator and staffing verifier. See worklog for IDs.

Two existing recruiter fallback deployments now use openai/glm-5-turbo, existing
ZAI credential reference and low reasoning through extra_body. Stored mode is
chat, base_model glm-5-turbo; failing intermediate /responses mismatch corrected.
Original MiniMax primary, critic and unrelated gateway deployments unchanged.
Agency adds only recruiter content-fallback profile/mapping and strict budget8.
Budget covers subject1, planner2, recruiter2, fallback2, critic1; bounds unchanged.
Unrelated owner configuration compared equal after excluding these additions.

Explicit fault demo: inject two primary empty objects; actual fallback first
returns non-JSON15.282s, repair accepted18.783s, actual critic approved3.171s.
Accepted37.282s including two synthetic faults and three simulated prior calls;
all8funded budget units used, no hidden retry, no validator changes.

Fresh unmodified installed pipeline: {} then units:string rejected with exact
recruiter_response_shape_invalid; content fallback12.509s and critic2.396s pass.
Accepted96.503s: subject2.963, planner6.413, embedding38.258, reranker8.880,
primary3.639+21.166seconds. Naturally reproduced failure recovered, not just a retry.
Embedding latency is recorded, not bundled into this recruiter repair.

## Exact blocker

Historical receipt ba132c4d and fresh trace01a0820a still lack their proposals.
New traces01a0821b-af73-70b0-b3bd-4ffd84b98bc9 and
01a0821d-2379-7dc2-a360-eb3bedbac25b capture an identical handoff packet and valid
wrong-neighbor-selection-documentation-evidence-researcher veto. Both failed;
only staffing_critic_rejected survived receipt projection. AR-416 fixes this
loss without changing staffing or critic approval. Critic named an alternative
whose full contract it did not see; that alternative has narrow API-verification
scope and is not endorsed. Details and hashes live in the captured-veto worklog.
No operator trust/restart gate remains for the previously demonstrated process.

## Same-task continuity

Read the installed-qualified-veto worklog first, then native receipts and recruiter
recovery for configuration and
reversal limits. The resumed clean baseline was mained9d5aa9; current delivery
branch is named above. Keep unrelated worktrees and Windows items untouched.

## Next bounded work package

After owner hook review, verify actual trust and a fresh native turn. Complete
the remaining AR-414/415 acceptance gates. The repair is installed; qualify
actual native diagnostic behavior before claiming current-artifact native proof. Keep AR-414/415 open until their
isolated acceptance gates have evidence. Never retry merely for approval or
manually select specialists. No broad staffing-policy repair is justified here.

## Verification

Current captured-response/critic/receipt/inference124pass; fast production
1151pass/3skip; UI224pass; Ruff779files and docs1334files pass. Routing and
tracker408items match before the pending AR-416/417 tracker closure. Frozen-source conformance188/188killed,
source_unchanged=true. No new installed/native diagnostic claim.
Source replay preserves terminal failure and renders the retained cause.
The remaining evidence below predates this source change.

Current focused189pass, production1151pass/3skip, UI224pass; Ruff/docs/routing
and strict tracker pass. Current frozen-source conformance188/188pass,
source_unchanged=true, after resolving runner interpreter/umask setup failures.
The following paragraph describes the prior recovery checkpoint.


Focused inference/configuration/installer336pass including12fallback regressions.
Named fast production spine1151pass/3skip; dashboard224pass. Metadata/docs1325
and Ruff778files pass. Routing and strict tracker406items pass. The first
conformance run was invalidated by a test edit; frozen-source repeat passes:
188mutations killed,0survived/invalid, source_unchanged=true. Corrected focused
336pass. Installed614file identity and six scope boundaries rechecked.
No exhaustive suite, Windows matrix, new wheel, host reinstall or trust bypass.

## Constraints

No manual specialist choice, weaker validator, false acceptance, credential
replacement, cross-provider nomination merge, OpenClaw restart or backlog wave.
Preserve failed-run immutability and correlation. Owner config backup exists;
reverse only owned fields after concurrent-change checks. Gateway PATCH ignores
ordinary null fields: do not claim a null PATCH clears the new ZAI parameters.
