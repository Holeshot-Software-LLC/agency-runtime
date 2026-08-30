---
title: "AR-265: Separate contextual inquiry from execution authority"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [routing, classification, workforce, safety]
related:
  - docs/roadmap/issue-AR-85-state-aware-turn-classification.md
  - docs/roadmap/handoffs/issue-AR-265.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-265
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317
depends_on: [AR-85]
blocks: []
---

# AR-265: Separate contextual inquiry from execution authority

## Problem

The turn classifier conflates two independent facts: a contextual question may
request no repository mutation while still benefiting from fresh specialist
expertise. Status and next-step forms such as `what's next?` currently become a
`conversation` with selection, rerouting, and execution decisions all false.
The selector therefore abstains deterministically, calls no provider, and
loads only the resident steward even when the surrounding task has materially
complex work.

Fresh rerouting alone is insufficient: the planner otherwise receives only the
literal short message and has no subject from the active session with which to
specialize its plan or workforce selection. Reusing retained prompt text would
solve the referent by crossing a new privacy and provider-egress boundary.

Simply restoring the former executable route is unsafe. Before the
conversation bypass was added, the workforce planner could infer
`workspace_write` units from these questions even though the user requested no
change. The correction must enable expertise without manufacturing execution,
delegation, or mutation authority.

## Current state

- The reproduced route records `turn_kind=conversation`,
  `selection_required=false`, `inference_attempted=false`, and an explicit
  deterministic abstention for contextual work inquiries.
- The status-query work-unit detector correctly declines parallel delegation;
  that separate topology decision does not justify suppressing specialist
  selection.
- Active-state classification handles revisions, pending interactions,
  continuation controls, acknowledgements, and greetings, but the contextual
  inquiry class previously fell through to the no-selection conversation path.
- A completed advisory turn could become the latest Store row and hide an
  older abandoned or otherwise unfinished turn from the following inquiry.
- Classifier v4 has no valid tuple for selection and fresh rerouting without an
  execution decision.
- Durable state identifies the prior trace and lifecycle but previously carried
  no bounded semantic subject into planner or recruiter inference.
- The five-field response header is rendered from routing evidence after
  preflight; it is a receipt, not the event that triggers routing.
- GitHub tracker [#317](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317)
  is open with the required `epic:routing` label.
- Pull request [#318](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/318)
  passed its automatic checks and merged without admin override as
  `90b852bdaa2ee1b9d02f61dff9f561a5c165bac4` on 2026-08-24.
- A Codex-only exact-main install published adapter
  `0.1.0+codex.0b797ab9d097`, preserved the other hosts, and passed the
  deterministic Codex smoke contract `4/4` with all eight hooks verified.
  Activation still correctly requires a fresh host process.
- A fresh Codex CLI process then proved the two-turn contextual route. The
  exact second prompt `what's next?` persisted classifier v5
  `turn_kind=conversation`, the decision tuple `(true, true, false)`, a guarded
  same-session context source, exactly one read-only analysis unit, specialist
  loads for `code-reviewer` and `software-architect`, zero delegations, and an
  accepted completed finalization.
- The attempted Codex Desktop task is negative lifecycle evidence, not an
  AR-265 classification result: that already-running process reported the old
  projection, its first turn failed preflight, and its second turn persisted
  `turn_kind=new_intent`. A full Desktop restart and completely new task remain
  required before claiming Desktop-installed proof.

## Approach

Implement classifier v5 without adding a seventh turn kind. Treat bounded
status, progress, recommendation, and prospective next-step inquiries as
advisory conversations or correlated continuations with
`selection_required=true`, `reroute_required=true`, and
`execution_decision_required=false`. Keep pure social conversation and exact
runtime controls on their existing bypasses. Keep object-bearing requests to
change, fix, or implement work on the executable new-intent or revision path.
Use a bounded structural grammar rather than a finite phrase list: every
advisory token belongs to a closed vocabulary, while explicit imperatives,
second-person action requests, and embedded mutation obligations take the
executable path. Common subjectless plan, options, priority, suggestion, and
status idioms are covered across current, active, and unavailable state.

Make the third boolean operational. An advisory workforce route may plan at
most one `analysis` unit, which deterministically compiles to `advise`
authority and `read_only` mutation scope. Validate the projected descriptor,
binding, loaded assignments, and non-delegated work unit; clear the selection
and fail safely if any executable or write-scoped authority appears. Tell the
host explicitly that the specialist context is a read-only parent assessment,
not mutation or native-child authorization.

Preserve unfinished context across completed advisory rows with a bounded
Store lookup. Missing, stale, or corrupt state still forces fresh selection,
but a surface-proven advisory inquiry never gains write authority from that
uncertainty.

Project a transcript-free subject capsule from the exact preceding substantive
row in the same session and host. The capsule contains source identity,
governed specialist-card hints, bounded unit descriptors, and closed domain,
language, framework, capability, and platform identifiers. It excludes prior
messages, request summaries, outcomes, resources, paths, risks, acceptance
prose, and final responses, regardless of the content-capture setting. Pass it
to planner and recruiter as separate untrusted evidence, bind its digest into
cache identities and the current-turn receipt, and rerank historical
specialists against the current eligible roster rather than reusing them.

Advance the preflight recipe and context policy to v15. Carry a source guard
with the exact source sequence, evidence revision, recipe digest, context
digest, and roster generation; reselect and validate it inside the ready
transaction. A source race fails before publishing a stale route. Each external
turn refreshes classification and its routing receipt before the header is
rendered.

Validate the v1 context and source guard as exact-key schemas with exact
non-boolean integer versions. Turn kinds remain allowlisted, source lifecycle
labels use a bounded identifier compatible with legacy terminal Store rows,
and prose or unknown fields fail closed rather than being silently projected.

Retain inference-owned gap hiring for advisory turns so a real missing
assessment capability may found a specialist. Treat that as internal workforce
mutation only: the resulting advisory unit remains parent-only, load-delivered,
non-delegated, and read-only.

## Dependencies

- AR-85 and ADR-0064 own the six-kind state-aware classifier and its three
  independent decisions.
- Inference remains the sole specialist-selection authority; deterministic
  code constrains and validates advisory safety but does not choose a worker.
- ADR-0163 governs the subject capsule's retention, privacy, cache, and
  transaction boundaries.
- Existing workforce artifact compilation supplies the canonical
  `analysis -> advise -> read_only` mapping.

## Acceptance

- [x] Status, progress, recommendation, and prospective next-step inquiry
      variants require fresh specialist selection without an execution
      decision.
- [x] Active and pending-state inquiries remain correlated continuations and
      reroute fresh; missing state selects conservatively without write
      authority.
- [x] Concrete action-bearing requests remain executable new intent or
      revision.
- [x] Direct `do`, `proceed`, `work`, `go`, `tackle`, and `focus` requests stay
      executable even when they also contain advisory words such as `next` or
      `plan`.
- [x] Subjectless plan, options, priority, progress, recommendation, and
      suggestion shorthand remains read-only across current, active, and
      missing state.
- [x] Classifier v5 and persisted replay accept the advisory tuples while v4
      remains unchanged.
- [x] Advisory workforce planning is bounded to one read-only analysis unit,
      and a write-scoped projection is rejected and cleared.
- [x] Completed advisory rows do not mask older unfinished work.
- [x] The host context states the read-only, parent-only boundary explicitly.
- [x] Planner and recruiter receive a same-session typed subject separately
      from the current request; identical short messages in different subjects
      have distinct planner inputs and cache identities.
- [x] Prior transcript text and prose-bearing plan fields remain excluded even
      when observability content capture is enabled.
- [x] Context and guard projections reject unknown fields, prose lifecycle
      labels, invalid turn kinds, and boolean or floating-point schema
      versions while preserving bounded legacy terminal identifiers.
- [x] Recipe v15 persists the context source and receipt revision, and the ready
      transaction rejects a changed source or roster before publication.
- [x] The response header remains a current-turn receipt; every external turn
      refreshes classification before header rendering.
- [x] Advisory gap hiring remains available as internal staffing without
      granting child, workspace-write, or external-write authority.
- [x] Fail-open results preserve continuation/advisory classification, and
      legacy header explanation lines do not mask authorization questions.
- [x] Focused classifier, selector, Store, and workforce-inference tests pass:
      `268 passed` after independent-review repairs.
- [x] The named fast production spine passes: `806 passed, 20 skipped` in
      `135.02s`.
- [x] The curated decision-conformance evaluation passes with all `151`
      mutations killed, `0` surviving, `0` invalid, and source unchanged.
- [x] The dashboard UI gate passes `134/134`, and the routing evaluation passes
      all accuracy, latency, and scale gates.
- [x] Documentation metadata, policy availability, worklog parity, and
      aggregate documentation validation pass after the local substantive
      commit is recorded in the required ledger commit.
- [x] Same-repository tracker
      [#317](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317)
      has the exact `[AR-265]` title and `epic:routing` label.
- [x] Authorized pull request
      [#318](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/318)
      passes its final hosted checks and is merged without disturbing
      concurrent OpenClaw work.
- [x] Exact merged main is installed for Codex only, deterministic smoke passes,
      and a fresh Codex CLI process plus correlated Store evidence proves the
      contextual two-turn route without delegation or mutation authority.
- [ ] After a full Codex Desktop restart, a completely new task proves the same
      two-turn route on the Desktop host. The stale-process attempt is retained
      as negative lifecycle evidence and is not promoted to a pass.
