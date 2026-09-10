---
title: "AR-433: Name the neighbour a wrong-neighbour veto points at"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, critic, staffing, receipts, reliability]
related:
  - docs/decisions/0246-make-a-wrong-neighbour-veto-name-its-neighbour.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/evidence/AR-433-critic-veto-population-20260910.json
  - docs/roadmap/evidence/AR-433-live-diagnostic-20260910.json
  - docs/roadmap/evidence/AR-433-install-liveness-20260910.json
  - docs/roadmap/issue-AR-435-install-into-the-openclaw-version-the-host-runs.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-433
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/847
depends_on: []
blocks: []
---

# AR-433: Name the neighbour a wrong-neighbour veto points at

## Problem

The owner reported that recruitment "happens every OTHER call, like it works,
then it doesnt". In Codex session `01a08b2d-acd5-70f3-b4a9-2d5b97b26556` the
four turns went staffed, vetoed, staffed, vetoed. Read against the immutable
receipts, the two vetoes are terminal strict-critic verdicts on operational
requests ("merge everything to remote main and pause", "create a handoff")
and the two staffed turns are substantive engineering requests; the sequence
is content, not periodicity, and the earlier stage rejections in the vetoed
turns (subject, planner, reranker, recruiter) also occur in staffed turns.

The base rate is the defect. Since 2026-09-08 the strict critic vetoed 30
nontrivial turns across all five hosts (15 of 53 terminal Codex outcomes): 26
named `wrong-neighbor-selection`, two named another ground, and two named no
ground at all. Only two of the 26 can say which card the critic preferred,
each by a name folded into the code itself (AR-416), because
`CRITIC_RESPONSE_SCHEMA` carries codes alone; ADR-0205's "a wrong-neighbour
veto must point at a card in that unit's eligible neighbourhood" is a sentence
in the prompt with nothing in the contract to hold it to. The ground is
unfalsifiable at the boundary where the runtime already knows both identities
it would need to check. This repair addresses that one ground; the observed
session's second veto was a different ground whose cause is AR-434.

## Current state

Repair implemented on branch `claude/ar433-alternating-recruitment-20260910`
per ADR-0246: the critic schema gains an optional bounded `wrong_neighbors`
pointer array; a `wrong-neighbor-selection` code (bare or qualified) without a pointer, or with a pointer the runtime cannot
verify against the neighbourhood it supplied, is a critic contract failure
with one bounded repair; the runtime itself never approves. This does change
outcomes: a critic that cannot ground its claim is asked again for the verdict
the team warrants and may then approve, where before its bare code was a
terminal veto. A verified pointer rides the applied critic attempt into both
durable receipts as a `validation_failures` row naming the unit, the selected
worker and the preferred card. Focused regressions cover the schema, contract,
each verification check, the charset, the wire form, both receipts, the
captured AR-414 reply, and the repair guidance for every other critic failure.

One bounded fresh diagnostic ran each exact vetoed request once per mode
against the live gateway and roster (single samples, planner and recruiter
stochastic). Under the pointer contract both requests reached the critic and
were approved on its first reply with no repair re-ask; under main the merge
request was vetoed again with a bare `wrong-neighbor-selection` naming no card
and the handoff request was approved. The two merge-case critics judged
different recruiter teams, so that pair says nothing about the contract's
effect on a given team; no live run has yet produced a verified pointer, so
the new receipt row is stage-proven only. Details, including the discarded
first attempt whose unproven capability receipt made every contract
ineligible, are in
[AR-433-live-diagnostic-20260910.json](evidence/AR-433-live-diagnostic-20260910.json).
The acceptance record and isolated verdicts remain pending after merge.

Installed and live on 2026-09-10: the a354e9a5 wheel and then the 83994e2b
wheel (AR-435) were installed into the shared runtime venv and projected to all
five hosts; every launcher pointer, projection and the dashboard service unit
are on runtime digest `c2d5c60e`, and the launcher trees match the venv byte
for byte. Fresh native turns on the ordinary-review request, observed on the
critic route with the owner config restored byte-exact, show the pointer
contract in the live critic prompt on claude, hermes, zcode and openclaw after
the second install (and on the first three after the first). Hermes and zcode
staffed teams; claude (twice) and openclaw were vetoed on
`missing-lifecycle-assurance-the-plan-calls-for`, a ground this issue does not
touch, so that veto is a new observation, not a regression of this repair.
Codex re-enters `activation-required` after every digest change and needs the
owner's Trust screen before a fresh Codex turn can prove anything. Details in
[AR-433-install-liveness-20260910.json](evidence/AR-433-install-liveness-20260910.json).

Population evidence is in
[AR-433-critic-veto-population-20260910.json](evidence/AR-433-critic-veto-population-20260910.json).
Historical critic packets were not retained, so whether any historical veto
named a real neighbour is unknowable; this issue does not claim they were
wrong, only that they were unaccountable.

The second veto in the observed session also shows a separate deterministic
defect: the plan validator read "create a handoff ... where the code is" as a
code mutation and demanded implementation and test units, after which the
critic vetoed the repaired plan for lacking the lifecycle assurance those
units imply. That is filed as AR-434 and not repaired here.

## Approach

Make the wrong-neighbour claim structurally accountable without touching the
gate itself: the critic still only vetoes, still reasons independently, and a
veto that names a real eligible better-fitting card still kills the turn. The
runtime adds no selection, ranking or approval; it checks two identities
against facts it computed for the same document (ADR-0205) and refuses a claim
that fails the check exactly as it refuses any other malformed critic reply
(AR-304). Retain the verified pointer in the existing per-unit
`validation_failures` projection so a veto is diagnosable from the receipts.

## Dependencies

ADR-0205 supplies the per-unit `eligible_neighbourhood` the pointer is checked
against. ADR-0200 and AR-416 govern how the critic's codes reach the receipts
and are unchanged. AR-434 is the separate plan-policy defect the same session
exposed.

## Acceptance

- [ ] The critic contract, system prompt and response schema require a
      `wrong_neighbors` pointer beside any `wrong-neighbor-selection` code,
      and the runtime verifies each pointer against the unit's eligible
      neighbourhood, refusing an unnamed or unverifiable claim as a critic
      contract failure with one bounded repair rather than a veto.
- [ ] A verified pointer reaches both the routing receipt and the
      preflight-failure receipt on the applied critic attempt as a
      content-free per-unit row naming the selected worker and the preferred
      card, and re-projects to itself.
- [ ] One bounded fresh diagnostic runs the two exact vetoed requests once each
      against the live gateway with the repaired contract and records the
      critic's verdict and any pointer it returns, with the named fast checks
      passing and the population evidence retained; no manual selection,
      acceptance, failed-receipt reopening or repeated sampling.
