---
title: "Authorize OpenClaw native skill reads from inventory"
status: accepted
category: decisions
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, skills, evidence, security]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/roadmap/issue-AR-275-record-openclaw-native-skill-reads.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/plugin.py
  - tests/test_openclaw_adapter.py
  - tests/test_security_turn_boundaries.py
  - docs/worklog/2026-08-22-7fcd828d-record-authorized-openclaw-skill-reads.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0167
type: decision
deciders: [maintainers]
---

# ADR-0167: Authorize OpenClaw native skill reads from inventory

## Context

OpenClaw `2026.7.1-2` loads a bundled native skill by reading its `SKILL.md`
through the host's supported `read` tool. It does not emit Agency's canonical
`skill_view` tool event. Treating every successful file read, a path suffix, or
model prose as a skill load would allow unrelated content to manufacture a
Store row and the corresponding five-line-header claim. Requiring the absent
generic tool would instead leave genuine native skill use unobservable.

OpenClaw exposes `skills info <skill> --json` as its native inventory and
eligibility authority. That receipt identifies the skill key, name, exact file
path and base directory, visibility, eligibility, and disable or block state.
Agency can therefore normalize the host-specific event without weakening the
existing Store or finalization authority boundary.

## Decision

The generated OpenClaw bridge retains only the bounded native `path` argument
needed to evaluate a completed `read` event. Before any inventory subprocess,
the adapter requires an absolute, NUL-free path of bounded length whose final
component is exactly `SKILL.md`, contains no `.` or `..` component, and yields a
bounded skill key.

Agency then invokes fixed-argument `openclaw skills info <skill> --json` through
the owned bounded native-command helper and an OpenClaw-only least-privilege
environment. A read becomes canonical `skill_view` evidence only when the
bounded receipt exactly matches the candidate key, name, file path, and base
directory; `eligible` and `modelVisible` are exactly true; and disabled,
allowlist-blocked, agent-filter-blocked, and platform-incompatible states are
exactly false.

Malformed, oversized, ambiguous, mismatched, ineligible, blocked, disabled, or
failed receipts produce no skill evidence. The canonical adapter's existing
tool-failure detection remains the final gate, and the Store-backed first-pass
header remains authoritative. No positive authorization is cached across
turns.

## Consequences

- A genuine native OpenClaw skill read can produce the same canonical Store and
  header evidence as a supported `skill_view` event.
- Arbitrary reads and model claims cannot become skill evidence merely because
  a path resembles a skill file.
- Native inventory availability is required at the observation boundary; an
  unavailable or changing inventory fails closed for that event.
- The repair is host-specific. Other harness adapters and their established
  skill contracts remain unchanged.
- The decision proves parent-turn skill observation only; it does not prove
  native-child card delivery or move an AR-119 Rule-4 matrix cell.

## Alternatives

- Accept every successful `read` ending in `SKILL.md`. Rejected because suffix
  matching does not establish inventory ownership, eligibility, or visibility.
- Trust the assistant's statement that it loaded a skill. Rejected because
  model prose is not an evidence authority.
- Require OpenClaw to emit the absent generic `skill_view` tool. Rejected
  because the audited native contract provides `read` plus an authoritative
  inventory surface.
- Scan directories or cache a prior positive inventory result. Rejected because
  both approaches can diverge from the host's effective per-turn state.
- Relax Store, finalization, filesystem, or executable trust checks. Rejected
  because the compatibility gap is event normalization, not a reason to weaken
  an existing safety boundary.

## Provenance

Commit `7fcd828d` implemented the bounded inventory authorization and canonical
event normalization. The linked worklog detail retains its regression-first
evidence and exact verification receipts.
