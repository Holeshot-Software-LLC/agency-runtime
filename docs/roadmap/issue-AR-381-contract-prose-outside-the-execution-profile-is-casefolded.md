---
title: "AR-381: Contract prose outside the execution profile is still casefolded, so a v3 card says python source and clis"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, card-quality, defect]
related:
  - docs/roadmap/issue-AR-380-execution-profile-prose-is-casefolded.md
  - docs/roadmap/issue-AR-379-hire-schema-has-no-home-for-domain-procedure.md
  - docs/decisions/0196-carry-governed-method-and-an-output-exemplar-in-the-contractor-card.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-381
priority: p2
tracker_url: null
depends_on: []
blocks: []
---

# AR-381: Contract prose outside the execution profile is still casefolded, so a v3 card says python source and clis

## Problem

AR-380 stopped casefolding the five **execution-profile** prose arrays from
schema v3. It deliberately left `_items()` casefolding for everything else,
on the ground that the remaining lists are identifiers whose normalized casing
is load-bearing.

That ground holds for `capabilities`, `lifecycle_phases`, `platforms`, `hosts`
and `tools`. It does not hold for the other **prose** fields that share the
same guard and render straight into the compiled card:

`outcomes_owned`, `artifacts_produced`, `requirements`,
`evidence_requirements`, `anti_capabilities`, `forbidden_scenarios`,
`preferred_scenarios`, `avoided_scenarios`.

## Current state

Compiled live from the packaged `python-application-engineer` card at v3, after
AR-379 and AR-380 landed:

```
Capabilities and owned outcomes
- maintainable production python behavior      <- Python
- portable python packaging                    <- Python
- async python design                          <- Python

Expected artifacts
- python source                                <- Python
- python package configuration                 <- Python

Role boundaries
- act outside production python applications, services, and clis   <- CLIs
```

So the same corruption AR-380 fixed for `working_principles` still reaches
every other prose section of the very cards ADR-0196 set out to improve. A
card that now carries a precisely-cased decision procedure sits directly above
a bullet reading `python source`.

`evidence_requirements` is the sharpest case: it renders in the *same* section
as `verification_steps`, which now keeps its case, so one section mixes cased
and lowercased bullets. `_merged()` was added to keep that from double-
rendering a duplicate pair, but it cannot fix how the surviving line reads.

## Approach

Decide per field, not wholesale. For each of the eight fields above, establish
whether any matcher, allowlist, dedup or persistence key compares its value,
and preserve case only where nothing does. `capabilities` is the cautionary
example: it reads as prose but is matched against
`unit.required_capabilities`, so it must keep casefolding.

Gate the change on a schema version exactly as AR-380 did, so already-minted
workers keep replaying the render they were minted under.

## Dependencies

- Should land as one further version bump rather than piecemeal, because each
  change moves `prompt_hash` for every newly minted card.

## Acceptance

- [ ] Every prose field that no matcher compares keeps its authored case end
      to end, proven by test.
- [ ] Every field that is matched, deduped or persisted still casefolds,
      proven by test naming the consumer that requires it.
- [ ] A packaged card renders no lowercased proper noun in any section.
- [ ] Contracts minted under earlier versions replay byte-identically.
