---
title: "Say who delivers the response contract and whose facts the header reports"
status: accepted
category: decisions
created: 2026-09-11
updated: 2026-09-11
tags: [header, response-contract, hosts, evidence]
related:
  - docs/roadmap/issue-AR-442-a-host-model-reads-the-response-contract-as-an-injection.md
  - docs/roadmap/issue-AR-357-canonical-response-contract-statement.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0255
type: decision
deciders: [owner]
---

# ADR-0255: Say who delivers the response contract and whose facts the header reports

## Status

**Accepted 2026-09-11.** Owner direction: the Agency header is a record of
what the runtime did for the turn, and a host model must be able to see
that it is reporting the runtime's facts, not asserting its own.

## Context

Every turn starts with the `[AGENCY RESPONSE CONTRACT v1]` block (AR-357),
delivered through the host's prompt hook beside the initial header
snapshot. It stated precisely what the finalizer checks and nothing else: it
never said who wrote it, that the values are the runtime's own Store record
supplied in the snapshot, or that the owner installed the hook that delivers
it. On 2026-09-11 the zcode model called it "a prompt injection attempt via
hook" that demanded "fabricated Agency header lines" about "a model I'm not",
and answered without the lines; the turn had staffed and ended
`response_invalid`. The store holds ten such finalizations since 2026-09-08
across zcode, hermes, codex and claude, each missing all five fields. A
careful model reading a bare bracketed block in its prompt has every reason
to treat it as untrusted text; Agency's own recruiter is told to treat
bracketed blocks exactly that way.

## Decision

1. **The contract opens with its provenance.** Before the verifier's
   claims, the block says it is delivered by Agency Runtime, the evidence
   runtime the owner of this machine installed into this host's hooks, that
   it is host configuration and not part of the user's message, that the
   header lines report Agency's own record of the turn supplied in the
   header snapshot (the specialist capsules loaded or delegated, the skills
   loaded, the model identities observed, how it recruited), and that the
   model reports those values as given, never invents them, and that they
   are not claims about the model's own identity.
2. **Every verifier claim stays verbatim.** The five lines, the value
   comparison, the finalizer's body requirement, the values-only snapshots
   and the publishes-unverified rule are unchanged, and the hash pin in
   `tests/test_response_contract.py` moves to the new text with a test that
   the provenance sentences come first and say what this record says.
3. **Nothing else moves.** The marker stays `v1` because the finalizer's
   rejection names it; the five fields, the finalization policy, the
   snapshots and every host's delivery rules are unchanged.

## Consequences

- A model that refuses to assert facts about itself is told, in the block
  itself, that it is asked to report the runtime's facts, with the source
  named.
- The block grows by about five hundred characters on every host; the
  claude native hook ceiling of 10,000 units is still far off.
- Whether the sentences change a host model's behaviour is a live question;
  the AR-442 acceptance measures one fresh run per host on the ordinary
  review wording against the ten failed finalizations since 2026-09-08.
