---
title: "AR-280 current Hermes purpose authority inspection"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [hermes, lifecycle, security, performance]
related:
  - docs/roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md
  - docs/roadmap/acceptance/evidence/AR-280-native-purpose-boundary-20260908.md
  - docs/roadmap/handoffs/issue-AR-280.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 8ce0461f359f361384c8677e17705a42be7a730c
short: 8ce0461f
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/751
related_issues:
  - docs/roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md
---

# Worklog detail: Retain Hermes purpose authority boundary

Substantive commit: `8ce0461f359f361384c8677e17705a42be7a730c`, exact
subject `test(hermes): retain AR-280 native purpose authority boundary`.
The immediately following worklog-only commit records that source/receipt
checkpoint; capsule metadata retains the inherited clean source/ledger floor.

## Purpose

Identify a safe way to prevent redundant Hermes internal staffing without
skipping a real user request. Retain the actual missing prerequisite instead
of treating old agent diagnoses as current caller attribution.

## Approach

Read the complete AR-280 issue and governing turn-origin decision; trace the
generated plugin, bridge and actual installed editable Hermes source. Record
content-free source hashes and the exact current native hook schema. Add 21
focused adversarial payload cases without executing them. No runtime bypass
is implemented. Canonical criteria and historical evidence remain intact.

## Challenges encountered

Current title generation is already outside preflight; native background
review remains a plausible duplicate caller, but no fresh caller attribution
was collected. Its private memory-write origin does not establish a supported
turn-bound purpose authority. Looking for sample records in the new worktree
also found paths absent from its earlier base; no missing record was invented.

## Decisions and alternatives

Apply existing ADR-0064; no new policy is adopted. Reject prompt heuristics,
payload flags, same-session parent tests and private agent introspection.
Combining unrelated relay and memory-provenance ContextVars would silently
create a new authority contract. Native host edits require a separate scope.

## Verification

Only source, targeted Ruff lint/format and diff checks. The new 21 regressions
are written but not run. No pytest, CI, acceptance, model or native call and
no owner profile/configuration/Store mutation. No success or completion claim.
Ruff lint passed, one test file was already formatted, and diff check was
clean. Metadata and static documentation validation passed for 1,275 Markdown
files. The inspected native source remained clean after inspection.

## Follow-ups

Obtain a supported session/turn-bound native purpose authority, then implement
and verify the bounded skip under AR-280. Tracker authorization remains
pending. Parent coordinates integration/publication; no PR was opened here.

Integration `77391f21` preserves the published installed-delivery and twenty-record triage checkpoint, including all incoming faithful worklog rows. No runtime mutation or new verification is implied.
