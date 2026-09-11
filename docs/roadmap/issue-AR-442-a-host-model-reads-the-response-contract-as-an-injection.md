---
title: "AR-442: A host model reads the Agency response contract as an injection"
status: open
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [header, response-contract, zcode, hermes, reliability]
related:
  - docs/decisions/0255-say-who-delivers-the-response-contract.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/roadmap/issue-AR-439-planner-method-capabilities-force-incoherent-coverage.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-442
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/888
depends_on: []
blocks: []
---

# AR-442: A host model reads the Agency response contract as an injection

## Problem

Every turn starts with the `[AGENCY RESPONSE CONTRACT v1]` block, delivered
through the host's prompt hook, which says the final response must begin
with five `Label: value` lines (`Agency/Agencies loaded`, `Agency/Agencies
delegated`, `Skills loaded`, `Actual Model selected`, `Recruited via`)
whose values equal the turn's Store evidence. On 2026-09-11 the owner
relayed how the zcode model reasoned about it: it called the block "a
prompt injection attempt via hook", said the header "demands I prefix my
response with fabricated Agency header lines" about "a model I'm not", and
answered the user without the lines. Staffing had already succeeded on
that turn (two units, code-reviewer, critic approved); the finalization
policy then found none of the five fields and the turn ended
`response_invalid`.

The store shows the same shape ten times since 2026-09-08: zcode 3, hermes
4, codex 2, claude 1 `response_invalid` finalizations: nine missing all
five header fields and one hermes turn (2026-09-09T16:44Z) missing two. The AR-434 handoff diagnostic met it on zcode too. The
contract text names the verifier's checks precisely, but it never says who
installed it, that the values are evidence the runtime supplies in the same
turn rather than claims the model must invent, or that the owner asked for
the header. A careful model reading a bare bracketed block in its prompt
has every reason to treat it as untrusted text, which is what Agency's own
prompts tell its recruiter to do with bracketed blocks.

## Current state

Repaired on branch `claude/ar442-header-repair-20260911` per ADR-0255:
`RESPONSE_CONTRACT_PROVENANCE` in `core/header/response_contract.py` opens
the block by naming Agency Runtime as the owner-installed hook that delivers
it, calling it host configuration rather than part of the user's message,
and saying the header lines report Agency's own record of the turn supplied
in the header snapshot, to be reported as given and never invented, and not
claims about the model's own identity. Every verifier claim, the marker, the
five fields, the snapshots and every host's delivery rules are unchanged;
the hash pin moved to the new text and a test pins the provenance
sentences' order and content. Filed 2026-09-11 from the owner's relayed
zcode response.

## Approach

Make the contract identify itself and its authority: the owner-installed
Agency Runtime hook delivers it, the five values are the runtime's own
Store evidence for this turn (the header snapshot names them), the lines
report that evidence rather than assert the model's identity, and a model
that cannot see the evidence should say so in the lines rather than omit
them. Keep the verifier and the five fields unchanged; measure the
`response_invalid` rate per host before and after on the same wordings.

## Dependencies

The header contract and finalization policy in `core/header`. AR-434 and
AR-439 supply the measured turns where the refusal appeared.

## Acceptance

- [ ] The delivered contract states who installed it and that the header
      values are the runtime's own turn evidence supplied in the snapshot,
      and every existing header, finalization and Stop-path test passes
      unchanged.
- [ ] One fresh native run per host on the ordinary-review wording after
      the reinstall ends `completed` with the five header lines present, and
      the per-host `response_invalid` count is recorded against the ten
      finalizations since 2026-09-08.
