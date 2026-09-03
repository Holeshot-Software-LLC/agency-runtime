---
title: "AR-380: Execution-profile prose is casefolded, so a card cannot name a case-sensitive identifier"
status: done
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, card-quality, defect]
related:
  - docs/roadmap/issue-AR-379-hire-schema-has-no-home-for-domain-procedure.md
  - docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-380
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/564
depends_on: []
blocks: [AR-379]
---

# AR-380: Execution-profile prose is casefolded, so a card cannot name a case-sensitive identifier

## Problem

`_items()` (`agency_runtime/core/workforce/hiring_contract.py:431`) lowercases
every item it validates:

```python
result = tuple(_text(item, f"{label} item", maximum=160).casefold() for item in value)
```

That is correct for the identifier lists it also guards — `capabilities`,
`lifecycle_phases`, `platforms`, `hosts`, `tools` — where normalized casing is
load-bearing for matching, allowlist membership and dedup.

It is wrong for the five **prose** arrays of the execution profile, which all
route through `_execution_items` into `_items`: `inspect_before_acting`,
`working_principles`, `failure_modes_to_check`, `verification_steps` and
`stop_conditions`.

## Current state

Compiled live against the tree at `9de00006`:

```
input:    "Name zones in IANA form, for example America/Chicago, never an abbreviation."
          "Report as: 3:47 PM, Tuesday 4 March 2026, CST (UTC-6)."

rendered: - name zones in iana form, for example america/chicago, never an abbreviation.
          - report as: 3:47 pm, tuesday 4 march 2026, cst (utc-6).
```

`america/chicago` is not a valid IANA zone identifier. The same corruption
reaches any code identifier, class name, file path, environment variable,
acronym or proper noun that a specialist's method needs to name — which is
most of what makes method content specific rather than generic.

Found while deciding AR-379, which puts an ordered decision procedure in
`working_principles`. That decision cannot deliver while the field destroys
the identifiers a procedure has to cite.

## Approach

Fix `_execution_items` only; leave `_items` casefolding for the identifier
lists. Two comparisons inside the guard currently rely on the value already
being lowercase and must become case-insensitive while the stored value keeps
its case:

- membership in `_GENERIC_EXECUTION_GUIDANCE`, whose entries are lowercase;
- the uniqueness check, so two principles differing only in case stay a
  duplicate.

## Dependencies

- None to start, but it changes every rendered contractor prompt, so it moves
  `prompt_hash` and `template_hash`. It belongs inside the AR-379 contract
  version bump rather than landing on its own.

## Acceptance

- [x] An execution-profile item keeps the case it was authored with, end to
      end, from `parse_employment_contract` through the compiled prompt.
- [x] The identifier lists that share `_items` still casefold, proven by test.
- [x] The generic-guidance rejection and the uniqueness rejection both still
      fire on case-varied input.
