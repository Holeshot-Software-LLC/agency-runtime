---
title: "Align Hermes and OpenClaw with the owner's shared staffing profiles"
status: accepted
category: decisions
created: 2026-09-09
updated: 2026-09-09
tags: [inference, configuration, native]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-09-shared-staffing-native-verification.md
  - docs/worklog/README.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
supersedes: []
superseded_by: null
id: ADR-0242
type: decision
deciders: [owner]
---

# ADR-0242: Align Hermes and OpenClaw with owner shared staffing

## Context

Hermes/OpenClaw host defaults shadow the owner's global per-stage profiles.
The previous fixed sample measured repeated 120-second staffing timeouts and
malformed replies. Codex, Claude and Zcode resolve separate planner, recruiter
and critic profiles. The owner explicitly authorized "use shared staffing".

## Decision

Remove only the Hermes/OpenClaw host overrides from the owner's configuration.
Both now inherit the existing global per-stage profiles, including the independent
critic. Preserve answering models, provider definitions, credentials, budgets,
other settings and inference-owned selection. Validate the exact semantic delta
and resolve all five hosts from a fresh configuration read before native trials.

Application evidence is committed at `a18e556c`; its exact ledger is `3624ddf5`.
The worklog registry and AR-404 traceability table record both scope and provenance.

## Consequences

The requested staffing profiles are aligned; actual provider replies still govern
observed model identity and acceptance. Costs may change. Configuration equality
does not establish equal speed or reliable staffing. Retain every prior failure
and run one fresh phase of the fixed native sample with unchanged case deadlines.
Normal native permission and hook-trust gates remain in force.

## Alternatives

Keeping the overrides preserves the measured slow/failing path. Changing answering
models does not address the identified staffing override. Weakening critic or
schema validation would turn rejected inference into fabricated success. None
is adopted. This is an owner configuration decision, not a new shipped default.
