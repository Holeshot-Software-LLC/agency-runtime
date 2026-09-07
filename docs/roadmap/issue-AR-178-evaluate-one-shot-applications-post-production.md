---
title: "AR-178: Evaluate complete one-shot applications after production launch"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [evaluation, applications, post-production, testing]
related:
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/AR-119-live-gates-runbook.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-178
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/153
depends_on: [AR-119]
blocks: []
---

# AR-178: Evaluate complete one-shot applications after production launch

## Problem

Specialist participation and matched selection evidence do not answer every
question about how Agency affects complete application delivery. Proving that
broader outcome requires a costly fixed corpus, blind grading, and matched
Agency-on/off execution after the runtime itself is production-ready.

## Current state

Product-evaluation validators exist, but no complete benchmark-valid six-
application corpus has been run. ADR-0102 makes this research explicitly
post-production and non-blocking for AR-119, AR-125, production GO, and release.

September 7 reconciliation at cbe82aaf retains this intentional research
backlog, not a missing runtime repair or superseded request. All six versioned
scenario definitions exist in core/evals/product_scenarios.py; the live-trial
validator in core/evals/product_one_shot.py requires completed execution,
runtime contract and validation, and explicitly disclaims comparative
superiority from one trial. Definitions and validators do not constitute six
matched blind-graded results. AR-119's live acceptance remains incomplete.
All six original acceptance states are preserved; tracker #153 remains open.

Next bounded package remains post-production: predeclare corpus/grading/budget,
then collect matched trials with exact activation evidence. No costly study
or new release gate is introduced by this reconciliation.

## Approach

After production launch, predeclare and version six applications: a Python CLI
or service; a TypeScript/Node application; a Python API with TypeScript
dashboard; a cross-platform installation/configuration flow; an authenticated
data-backed application; and an application with observability and failure
recovery. Match Agency-on/off arms by ask, host, model, configuration, workspace,
and grader. Blind-grade outcomes and retain exact Agency activation evidence.

## Dependencies

AR-119 must first establish the production runtime and its exact specialist-
participation contract. This issue blocks no production or release item.

## Acceptance

- [ ] The corpus, graders, thresholds, and budget are predeclared and versioned.
- [ ] All six matched Agency-on/off pairs run under the same controls.
- [ ] Blind grading covers install, startup, configuration, core workflows,
  recovery, security, tests, observability, documentation, and portability.
- [ ] Exact activation receipts are retained; malformed, timed-out, or missing-
  receipt arms remain invalid rather than losses.
- [ ] Evidence is published and every discovered defect is filed independently.
- [x] The evaluation is explicitly post-production and non-blocking.
