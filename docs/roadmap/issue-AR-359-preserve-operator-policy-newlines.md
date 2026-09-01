---
title: "AR-359: config set --stdin flattens operator_policy newlines"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [cli, config, operator-policy]
related:
  - docs/roadmap/issue-AR-355-working-agreements-resident-manager.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-359
priority: p3
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/429
depends_on: []
blocks: []
---

# AR-359: config set --stdin flattens operator_policy newlines

## Problem

`agency config set operator_policy --stdin` parses the piped text as a
YAML scalar, folding the operator's line breaks into spaces. Measured
2026-09-01 setting the owner's five working agreements: a five-line
numbered list was stored and injected as one long line. The
operator-policy module explicitly preserves `\n` because "line
structure is how it stays readable inside the injected block" —
the ingestion path defeats the design.

## Current state

Content survives (numbering keeps it parseable) but formatting the
owner wrote is lost; live capsules show the flattened form.

## Approach

Treat `--stdin` input for string-typed keys as a literal string, not a
YAML document (or wrap it as a YAML literal block before parsing).
Re-set the live installation's policy with its line breaks once fixed.

## Dependencies

- None.

## Acceptance

- [ ] `config set <string-key> --stdin` stores the piped bytes'
      line structure verbatim (modulo the module's own control-char
      normalization), covered by a regression test.
- [ ] This installation's operator policy is re-set with its five
      lines intact and verified in a live capsule.
