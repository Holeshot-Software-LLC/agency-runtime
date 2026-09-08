---
title: "Bind structured reranking to the offered candidate membership"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [staffing, reranker, reliability]
related:
  - docs/roadmap/issue-AR-420-bind-reranker-candidate-membership.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
supersedes: []
superseded_by: null
type: worklog
commit: 5ff8e85c725ea669ba935970bc07511abbefc57b
short: 5ff8e85c
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/803
related_issues:
  - docs/roadmap/issue-AR-420-bind-reranker-candidate-membership.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Bind structured reranking to the offered candidate membership

## Purpose

The owner correctly rejected isolated successes as general reliability proof.
The latest native turn failed again. Preserve that failure and repair a measured
cause without weakening the independent critic or staffing contract.

## Approach

An owned branch starts from synchronized b69c4926. One private standalone probe
observed existing provider calls without changing their contents or configuration.
The optional reranker returned 16 candidates for a unit offered 15 and five for
a unit offered two, including candidates from different units. The unchanged
validator rejected it. The complete standalone staffing nevertheless accepted;
that does not reproduce or adjudicate the earlier native critic veto.

One replay used the exact reranker prompt and model with a per-unit schema:
unit identity enum, candidate enum, exact candidate count and unique items. It
passed in 15.280 seconds versus the captured rejection's 25.561 seconds. Every
candidate order remains possible; the existing parser still checks unit order,
identity, membership and uniqueness. No model or timeout changes, retries,
selection, critic or native reranker changes. This refines the existing ADR-0171
permutation contract rather than creating a new staffing policy.

## Challenges encountered

Historical failed receipts retain bounded reasons but not the proposal needed
to judge a wrong-neighbor veto. The subject classifier also rejects an empty
answer despite asking for one when uncertain; that is separately observed in
source, not established as the latest native response. The native critic remains
unadjudicated. Planner/recruiter shape and coverage failures remain unresolved.

The isolated verifier initially made no calls: Claude2.1.265 package and bin parents
had reverted from755to775 at22:24:43–44UTC, and the normal executable gate refused their namespace.
Both owner-owned directories were restored to755; the gate then resolved normally.
The process responsible for the permission recurrence is not established.
Two record-format preflights were corrected before any verifier call (empty result
table and explicit line-bound citations); no verdict was fabricated.

The first schema probe failed at import before making a provider call; its
module path was corrected. The original-source integration test fails because
the provider still receives a broad schema, then passes on the candidate. The
assertion occurs inside the optional-recall boundary, so its failure becomes a
failed recall attempt and the test observes that status.

## Verification

Focused 112 passed, including all permitted two-candidate permutations and
negative membership cases. Original-source integration regression failed as
expected. Named fast spine: 1151 passed, three skipped (72.81s); UI224 passed.
Focused expanded suite164 passed; Ruff781 files, docs1344, metadata, policy
availability, routing and tracker411 pass. Canonical private-clone build,
independent distribution verification and strict Twine pass. Immutable installed
source3fe3d7ba has all614package files equal to its verified wheel, SHA256
1b1e8cb40fd0bbc5af4cb60ceb9dd82ab27fb53084d0ed1ce9e0927cf09535b1.
Native Codex trace01a0831f-1a40-7a12-a079-3386a3b439d3 completed in41.514s
(staffing28.148s), with every staffing stage applied, exact full card in native
context, truthful five headers and authoritative finalization9a0df117-341a-490f-af7d-6eb0a23a7d6d.
Visible-response hash275f342c32095feede701491e437d2db3da280d7799c352dd1adfbae19f3921f
matches Store. No trust bypass or model override. Source identity is independently
verified installed bytes; native context exposes no published projection hash.
See evidence/AR-420-native-codex-20260908.json. Frozen-source conformance passes188/188 with zero survived/invalid and
source_unchanged=true. No exhaustive corpus, coverage or Windows matrix dispatch. The first conformance
launcher selected a Python lacking pytest; rerun uses the existing test venv.
The first policy-availability invocation lacked PYTHONPATH; corrected check passes.
The repository evidence contains offered sets and observed responses, no headers,
credentials or raw owner configuration. Timing is a single replay, not a benchmark.

## Follow-ups

AR-420 completed its three isolated acceptance criteria against86c99a36,
verifier runsac570ab4,066b15e0,376408aa. PR803 closes only this membership
defect; it does not establish general reliability. AR-404 keeps
broader staffing reliability unresolved and retains all Hermes/OpenClaw/Claude/
Zcode gates. Prior host successes do not prove this new candidate. Existing
pending operator choices remain pending; no observer or upstream publication
approval is inferred from this repair request.

PR803 merged as `263a0ec3` with exact subject
`fix(staffing): merge PR803 bounded reranker membership`. AR-420/#802 is closed
after isolated acceptance; AR-404/#672, AR-418/#796 and AR-419/#797 remain open.
The merge and recovery records retain all unresolved gates and failed receipts.

PR804 merged as `e36fc883` with exact subject `docs(staffing): merge PR804 AR420 recovery checkpoint`.

Final recheck after PR805: Claude's executable gate is failing again. Package
and executable ctimes advanced to22:38:08UTC, package/bin parents returned775.
The earlier22:24:43UTC replacement has the same pattern. Two Claude processes
from September1 use a deleted installation, which does not establish that they
performed the replacements. No active terminal was stopped. Owner clarification
on concurrent installers is pending; further chmod retries were not performed.
AR-420's source/native evidence and isolated verdicts remain valid observations;
current Claude availability is an explicit separate AR-404 blocker.

[PR806](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/806) merged as `ad8b05de`
with exact subject `docs(hosts): merge PR806 Claude recurrence evidence`. Current Claude gate remains failing.
