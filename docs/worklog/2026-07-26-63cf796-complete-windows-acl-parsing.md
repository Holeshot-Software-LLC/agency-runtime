---
title: "Worklog: Parse complete Windows ACL descriptors"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [security, windows, acl, filesystem-trust]
related:
  - docs/roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
supersedes: []
superseded_by: null
type: worklog
commit: 63cf79673e64af4d715630e2c9be3ae786cdbc04
short: 63cf796
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md
---

# Worklog: Parse complete Windows ACL descriptors

## Purpose

Close a high-severity Windows filesystem-trust bypass in which flat ACE
extraction could omit a native-valid outer conditional full-control grant.

## Approach

Replaced regular-expression ACE extraction with a linear, quote-aware balanced
parser that consumes the complete DACL. The parser validates current SDK ACE
types, flags, GUIDs, conditional payload shape, NULs, nesting, and trailing
input. Conditional grants remain opaque and are classified by maximum stated
rights so the runtime never relies on evaluating a Windows condition.

## Challenges encountered

The malicious-looking descriptor was accepted and round-tripped by native
Windows APIs because quoted claim text may contain parentheses. The former
parser saw only the nested text and silently lost the enclosing foreign grant.
Security behavior therefore had to be tested at every shared classifier, not
only at the tokenizer.

## Decisions and alternatives

ADR-0039 and ADR-0055 continue to govern fail-closed ACL and executable
namespace trust. A more permissive partial parser and evaluation of conditional
expressions were rejected: incomplete parsing recreated the omission class,
while condition evaluation would incorrectly depend on a context the runtime
does not authoritatively possess.

## Verification

- Broad ACL, private-path, and executable-authority package: 402 passed, 6
  skipped.
- Focused local regression: 239 passed, 1 skipped.
- Ruff check and format check: passed.
- Documentation metadata, policy availability, worklog, and link validation:
  passed.
- Git diff check: passed.

## Follow-ups

The integrated Python release gates and hosted Windows security matrix remain
required by AR-147. Tracker creation remains pending explicit authorization.
