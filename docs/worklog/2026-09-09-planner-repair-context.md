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
