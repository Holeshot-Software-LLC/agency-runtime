---
title: "Worklog detail: configure bounded embedding dimensions"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags:
  - workforce
  - embeddings
  - configuration
related:
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 2bea0c764cccf05fddef55feef62ceedae489087
short: 2bea0c76
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
---

# Worklog detail: configure bounded embedding dimensions

## Purpose

Let an explicit embedding-capability inference profile request a provider-native
vector width that fits Agency's unchanged complete-roster scalar bound.

## Approach

Added an optional `dimensions` profile field with zero meaning provider default.
Nonzero values are bounded and limited to embedding profiles using Ollama,
OpenAI-compatible, or LiteLLM adapters. The value is forwarded only on embedding
requests, enforced exactly against returned vectors, and bound into provider and
catalog cache identity. Observed receipt dimensions retain their existing
meaning. Agency never slices or pads vectors.

## Challenges encountered

The installed local embedding model defaults to 4,096 dimensions, which is valid
per vector but exceeds the one-million-scalar bound at the current roster size.
The provider supports a native 1,024-dimension projection, so raising the bound
or truncating response vectors was unnecessary and unsafe.

The first cache-identity regression used a nonexistent test specialist and
entered recruiter repair, where the repair prompt is not a bare JSON document.
The corrected test uses an actual roster identity and passed without weakening
the parser or repair contract.

## Decisions and alternatives

Keep the existing aggregate bound and request the projection at the provider.
Treat an unsupported, stripped, or mismatched dimension as typed-only fallback.
Do not extend legacy text-provider chains or add a Store migration for this
profile setting.

## Verification

- Regression-first artifact: 12 expected failures, 7 passes, SHA-256
  `8e4fe65511b6eaad6d41d3aef49206b3f373f88467c1ae5b5e66dcab8184b54b`.
- Focused schema, transport, cache, fallback, receipt, hybrid-recall, and
  workforce tests: 167 passed with warnings treated as errors.
- Independent focused review: GO; no Critical, High, or Medium findings.
- Ruff 0.15.20 check and format check passed for package, tests, and scripts.
- Documentation metadata, policy availability, worklog, and repository
  documentation verification passed.
- `git diff --check` passed.

## Follow-ups

Install this exact clean runtime projection before adding `dimensions` to the
live Agency configuration, then collect local-provider and ordinary-host shadow
evidence. Tracker creation remains pending explicit authorization.
