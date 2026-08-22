---
title: "Worklog detail: Gate OpenClaw provider calls on Agency preflight"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, inference, preflight, safety]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
supersedes: []
superseded_by: null
type: worklog
commit: a0ff74d4e9b4cfe85b2b4fc30b595556e5331708
short: a0ff74d4
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
---

# Worklog detail: Gate OpenClaw provider calls on Agency preflight

## Purpose

Prevent OpenClaw from starting its native provider after Agency workforce
preflight has failed, while improving strict planner repair without inspecting
or specializing for the model behind a LiteLLM alias.

## Approach

Moved the exact Agency preflight call into OpenClaw's fail-closed
`before_agent_run` input gate. A successful, bounded context is cached by exact
session and run for one later prompt injection; missing or failed preflight
blocks before model execution. The cache is count- and TTL-bounded and cleared
on disable or finalization.

The planner schema now binds capability identifiers to Agency's current
workforce ontology. Two stable parser failures receive closed repair codes and
bounded corrective guidance. The existing single repair attempt, strict local
validation, provider budget, zero protected fallback, and alias opacity remain.

## Challenges encountered

The retained live failure showed that OpenClaw 2026.7.1 ignores errors from the
prompt-build hook and proceeds to its native provider. The failed turn made 58
tool calls before a 300-second timeout. An Agency-only diagnostic isolated two
strict provider-output violations without another host-model run. The first
documentation check also exposed two missing reciprocal issue dependencies;
both records were corrected before commit.

## Decisions and alternatives

The installed host's prompt-bearing input gate was used instead of weakening
preflight, allowing native fallback, changing OpenClaw configuration, changing
the LiteLLM alias, or adding model-specific behavior. Provider-backed preflight
runs once; prompt construction only consumes its exact cached result.

## Verification

Expected-red: 3 failures. Focused planner/OpenClaw slice: 154 passed. Affected
installer/adapter slice: 65 passed with 131 deselected. Named production spine:
828 passed, 3 skipped. Documentation metadata/policy/worklog/docs checks, full
ruff check/format, 134 UI tests, routing evaluation, and diff checks passed.
Decision conformance retains the previously recorded trusted-Python fixture
limitation and was not retried unchanged.

## Follow-ups

Reinstall Agency only into stopped OpenClaw from this checkpoint. Run an
Agency-only inference check before one genuinely new native turn, then record
Store/header/finalization evidence. Tracker creation remains separately
unauthorized under AR-275 and AR-276.
