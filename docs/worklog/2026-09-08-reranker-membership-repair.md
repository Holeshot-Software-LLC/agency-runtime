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
Native evidence and frozen-source conformance are pending. The first conformance
launcher selected a Python lacking pytest; rerun uses the existing test venv.
The first policy-availability invocation lacked PYTHONPATH; corrected check passes.
The repository evidence contains offered sets and observed responses, no headers,
credentials or raw owner configuration. Timing is a single replay, not a benchmark.

## Follow-ups

AR-420 stays open for installed evidence and isolated acceptance. AR-404 keeps
broader staffing reliability unresolved and retains all Hermes/OpenClaw/Claude/
Zcode gates. Prior host successes do not prove this new candidate. Existing
pending operator choices remain pending; no observer or upstream publication
approval is inferred from this repair request.
