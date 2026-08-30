---
title: "Hosted portability and overload closure"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [worklog, ci, windows, linux, delegation, http, security, portability]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-18-work-unit-paths-with-spaces.md
  - docs/roadmap/issue-AR-19-bounded-overload-responses.md
  - docs/decisions/0041-bounded-asynchronous-overload-responses.md
  - docs/decisions/0042-local-only-bounded-work-file-inference.md
  - docs/decisions/0043-prime-stdin-before-windows-child-resume.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
type: worklog
commit: a096236c2123437441a62635be9cc7e514072ead
short: a096236
date: 2026-07-13
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-18-work-unit-paths-with-spaces.md
  - docs/roadmap/issue-AR-19-bounded-overload-responses.md
---

# Worklog detail: Close hosted portability and overload gaps

## Purpose

Close the final defects exposed by hosted Linux and Windows validation while
preserving exact coverage, bounded resource use, local-only inference, and the
original host regressions.

## Approach

- Recover existing work-unit paths containing spaces without re-emitting a
  suffix as a second root. Keep assignment and colon-delimited local syntax,
  bound accepted and scanned candidates, and reject URL or network-root tokens
  before filesystem access.
- Start Windows delegation children suspended, synchronously close empty
  input, and require small bounded stdin payloads to reach EOF before resume.
  Keep large payloads asynchronous so a full pipe cannot deadlock the
  suspended reader.
- Replace synchronous saturated-server socket work with a separate four-worker
  rejection budget. Send and half-close the 503 response, then drain configured
  valid request sizes using 64 KiB receives under a 250 ms absolute deadline.
- Record the durable transport, inference, and overload policies in ADR-0041
  through ADR-0043 with reciprocal roadmap links.

## Challenges encountered

The first Linux path fix risked narrowing valid assignment syntax, so the
implementation moved from a regular-expression lookbehind to consumed-span
tracking. The hosted PowerShell timeout could not be fixed by thread start
order alone because start only schedules the writer; a completion event now
proves EOF for payloads that safely fit before resume. Windows overload
responses required both graceful half-close/drain behavior and a separate
worker cap so response reliability did not turn into accept-loop blocking.

Senior review then found two adversarial gaps: large valid POST bodies could
still reset after a 64 KiB-only drain, and wrapped protocol-relative URLs could
trigger UNC probing. The final code uses the configured body cap plus bounded
framing under the same deadline and rejects plain, quoted, parenthesized, and
Markdown-wrapped network roots before constructing a path.

## Decisions and alternatives

- [ADR-0041](../decisions/0041-bounded-asynchronous-overload-responses.md)
  records the separately bounded asynchronous overload path.
- [ADR-0042](../decisions/0042-local-only-bounded-work-file-inference.md)
  records local-only, bounded automatic path inference.
- [ADR-0043](../decisions/0043-prime-stdin-before-windows-child-resume.md)
  records bounded stdin priming before Windows child resume.
- Inline draining, unrestricted rejection threads, synchronous large-payload
  writes, and network-root inference were rejected because each weakens a
  resource or trust boundary.

## Verification

- Warning-strict non-performance suite: 2,303 passed, 5 skipped, 2 deselected;
  exact 100.00% coverage over 17,284 statements and 5,408 branches.
- Uninstrumented performance suite: 2 passed, 2,308 deselected.
- Routing evaluation: all 25 gates passed; p95 8.640 ms, cache p95 0.385 ms,
  155.73 concurrent calls per second, and overlap 8.
- Delegation evaluation: 12 of 12 cases passed.
- Dashboard UI: 60 of 60 tests passed at exact line, branch, and function
  coverage.
- Release hygiene passed over 377 inputs. High-severity Bandit, strict offline
  Zizmor, runtime dependency audit, Ruff/format, documentation/tracker
  validation, and whitespace checks passed.
- Original PowerShell Console.In, one-megabyte saturated POST, and wrapped
  protocol-relative no-probe regressions passed on native Windows.

## Follow-ups

- Confirm the pushed commit on GitHub's Ubuntu Python 3.10 through 3.14,
  Windows Python 3.10 and 3.14, security, packaging, artifact, and
  capability-aware CodeQL jobs.
- Merge PR #18, record hosted evidence, reconcile the post-merge worklog, and
  close AR-07, AR-16, AR-17, AR-18, and AR-19.
