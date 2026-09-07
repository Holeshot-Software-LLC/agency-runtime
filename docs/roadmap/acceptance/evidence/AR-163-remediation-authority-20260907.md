---
title: "AR-163 current remediation-authority evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [security, remediation, dashboard, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/acceptance/issue-AR-163.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-163 current remediation-authority evidence

## Scope and existing implementation

Reviewed after PR #713 merged a01abe81d75de988526e58acac6adfaddce1a18a;
clean merge ledger 4103d1b8a341c7ca3b3cb6ba69bcd3961ef187b4. Original implementation
f64ba1e remains present. No runtime, script or test changes are needed for this
bounded reconciliation. All eight original acceptance requirements are retained;
converting plain bullets to unchecked boxes is schema normalization, not a
change to their wording or a verdict. The record stays in progress until all
eight isolated checks have candidate-bound verdicts.

The security goal remains relevant: an immutable signature proves historical
evidence, not continued candidate eligibility. Current suppression/history
queries additionally require a current passing latest audit and policy/roster
basis for pending/approved quarantine, or the exact activated candidate version
and hash. Read-time reopening selects the original queue event. It creates no
replacement queue or resolution event and does not grant prompt execution.

## Fresh focused verification

From the owned clean checkout, with Python 3.12.3 and checkout-local imports:

```bash
PYTHONPATH=. python -m pytest tests/test_roster_remediation.py \
  tests/test_dashboard_operational.py -q -W error
node --test tests/dashboard_ui.test.mjs
```

Python: **167 passed in 14.39s**, no failures, skips or deselections.
Dashboard: **188 passed**, no failures, skips or cancellations, **197.292186 ms**.

The executed Store cases cover rejected-candidate reopening, exact signed-marker
replay remaining stale, modified-HMAC insertion refusal, audit-basis drift,
approval/activation refusal, unchanged queue/resolution event counts, and
duplicate/malformed raw resolution classification. Existing provenance,
dependency-loss, rollback and normal activation checks also execute.

The executed dashboard tests preserve expanded pages for matching revision and
prefix; invalidate formerly paged history on a reopening revision change; and
suppress defensive queue/history overlap. Rendered labels distinguish stale
signed resolutions from unvalidated raw records. The actual API projection test
checks that a private prompt sentinel is absent. Public queue/history mappings
remove internal underscore-prefixed source and authority fields; rendered cards
select explicit metadata rather than signing material or prompt bodies.

These are fresh local Store/API-projection and DOM workflow checks, not a
hosted service, native-host activation, screen-reader or Windows canary.

## Exact-byte broader receipts

```bash
git diff --exit-code fcdcd6eb -- agency_runtime tests scripts AGENTS.md pyproject.toml
git diff --exit-code dccb4e85 -- agency_runtime/dashboard
```

Both comparisons return zero. Reuse AR-162's exact unchanged named production
spine: **1085 passed, three existing skips, 68.09s**. The current two-module
focused package and UI were freshly rerun, not inferred from older receipts.
AR-156's same-byte loaded-browser receipt (ten matching assets, 21 checks)
remains broader context only; no new browser launch or installation is claimed.

No exhaustive corpus, four-shard coverage gate, six-interpreter matrix, hosted
dispatch, Windows work or trust bypass was performed. No requirement is added
for these optional diagnostics. This exempt pre-tracker record needs no
duplicate tracker creation. Strict local documentation/tracker parity remains
a publication check; the builder never assigns an acceptance verdict.
