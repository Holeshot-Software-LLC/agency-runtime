---
title: "Exact installed uv-plan evidence for AR-190"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-08
tags: [updates, uv, evidence, isolation]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
supersedes: []
superseded_by: null
type: worklog
commit: d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f
short: d1a9260c
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
---

# Worklog detail: docs(roadmap): capture exact installed uv-plan evidence for AR-190

## Purpose

Supply the previously missing real installed uv-tool plan evidence for the
existing AR-190 implementation, without changing the owner's installation.

## Approach

Build and independently verify a portable wheel from clean detached
`c64ce3ce54c6e51280292298b5e3600611cb72fc` under `umask 077`. In an existing
exact local Docker image, let verified uv 0.11.8 create its legitimate default
tool installation and receipt. Invoke that installed Agency entrypoint to
resolve the same exact immutable SHA, without executing either printed command.
Preserve exact raw JSON and readable portable evidence. The later record-only
candidate has identical runtime, scripts, tests and packaging configuration;
the receipt does not claim its additional documentation was live-executed.

## Challenges encountered

An earlier bubblewrap capability probe failed at uid-map setup; no install
or plan ran there. The separately authorized local-container route succeeded.
The first container used an older exact artifact, so a fresh same-SHA artifact
was built and the bounded plan repeated. Both successes and the original
failure are retained. The pre-existing c64ce3ce merge-ledger omission was
resolved by fast-forwarding its already-created `d28ccc23` ledger commit.

## Decisions and alternatives

Apply existing ADR-0107's planning/application separation. Do not relabel the
owner's non-uv AR-348 venv, synthesize a uv receipt, install uv into the owner
environment, override tool target directories or execute an upgrade. No new
authority or architectural decision was introduced.

## Verification

Canonical builder, strict Twine and independent portable verifier exit zero.
The actual installed plan selects `uv-tool` with no pip installed; 669 compared
prefix files, the uv receipt and Agency entrypoint are unchanged after the
plan. Both disposable containers are removed and owner wrapper/input hashes
are unchanged. Focused update/CLI tests: 67 passed in 0.83 seconds. Targeted
Ruff, documentation, metadata, policy-availability, worklog and diff checks
pass at the evidence checkpoint. Isolated acceptance is not yet claimed.

## Follow-ups

Freeze the AR-190 builder at this committed evidence candidate and run the five
isolated verifiers. Parent serializes PR publication and merging; no owner
upgrade or native host activation is part of this plan-only completion.

## First isolated verification checkpoint

Commit `a6efa01b` faithfully records four `satisfied` verdicts and one `absent`
verdict from the first default all-five run. Criterion 5 rejected the link from
live-tested c64ce3ce to later documentation candidate d1a9260c because the
source-equivalence statement could not be verified inside its snapshot. No
product failure or issue completion is inferred from that result. The exact
first reasons and digests remain in that commit's acceptance record.

The owner subsequently requested one bounded changed-evidence response: build
and install exact d1a9260c, produce its same-SHA uv plan, rerun focused checks,
and clarify final product-source identity without requiring a receipt commit
to include its own future execution. A new receipt candidate changes every
criterion digest, so the second and final review must run all five; it cannot
reuse the first four verdicts under a different candidate SHA. No third review
is authorized by this bounded package.

## Exact d1a9260c response

Commit `eac2d6a2` retains the original criterion verbatim and distinguishes
exact tested product source from the later commit carrying its receipt. A
fresh clean detached d1a9260c wheel, independently verified and genuinely
installed by uv, generated a same-SHA plan at 2026-09-08T00:00:19Z. Installed
planner SHA-256 values match the detached source; the full path-scoped source
diff is empty, and 669 prefix files plus receipt/entrypoint remain unchanged.
Fresh focused tests and Ruff pass; record gates pass for 1,241 documents.

The branch was pushed only to let official GitHub resolution see that exact
commit; no PR or owner install occurred. The new evidence candidate requires
all five isolated verdicts to be regenerated. This changes evidence semantics,
not installer safety, ownership or mutation authority; existing ADR-0107 and
the acceptance lifecycle still govern.

## Refused verifier admission

Commit `7a387063` preserves the failed Claude admission before the second
actual review. Its package directory had again become group-writable; the
production resolver explicitly refused it as untrusted. The runner exited 2
and recorded no verdict for any criterion. Actor identity is unproved, and
the worker did not enter a chmod/retry loop. The owner instead selected the
supported Codex verifier against the unchanged eac2d6a2 receipt candidate.
Read-only checks found Codex CLI 0.153.4 installed, authenticated and usable;
no owner configuration or credentials were changed.
