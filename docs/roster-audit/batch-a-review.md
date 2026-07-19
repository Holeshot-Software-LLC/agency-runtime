---
title: "Roster semantic safety audit - batch A"
status: active
category: governance
created: 2026-07-17
updated: 2026-07-17
tags:
  - roster
  - security
  - audit
related:
  - docs/roster-audit/batch-a.json
supersedes: []
superseded_by: null
---

# Roster semantic safety audit - batch A

## Result

This batch semantically reviewed the complete prompt body of **59 source agents** at
upstream revision `459dce837db3bdfdc4763d3fefd1fd854e73c8f1`. The machine-readable record contains exactly
one entry per source file and does not copy prompt bodies.

- Approved under the bounded runtime contract: **59**
- Quarantined: **0**
- Direct-context safe after projection: **12**
- Isolated-context only: **47**
- Authority projection: advise 8, modify 11, plan 16, review 24

"Approved" does not approve each raw directive. It means the useful specialty can
be retained when Agency projects only the recorded capabilities, anti-capabilities,
authority, evidence contract, host support, and context mode. Raw prompt claims of
memory, tool access, external authority, or production readiness remain inactive.

## Scope

| Division | Reviewed agents |
|---|---:|
| academic | 6 |
| design | 9 |
| finance | 5 |
| healthcare | 3 |
| product | 5 |
| project-management | 7 |
| sales | 9 |
| support | 6 |
| testing | 9 |
| **Total** | **59** |

The authoritative upstream repository inventory at this revision contains 263 agent
definition Markdown files across 17 divisions. This file is one declared 59-agent
audit batch; that benchmark is intentionally separate from any manifest importer's
current traversal or candidate count.

## Safety and quality findings

| Finding class | Audit disposition |
|---|---|
| Persistent persona memory | 57 records explicitly claim or depend on durable memory. The projection treats each invocation as turn-scoped unless a host supplies an authorized memory mechanism. |
| Tools and external systems | Browser, shell, file, CRM, Jira, cloud, finance, healthcare, research, and test systems are never implied by the persona. LiteLLM remains an inference router and is not recorded as an execution host. |
| High-stakes authority | Finance, tax, legal, clinical, government, employment, procurement, investment, and customer decisions are projected to advice, planning, or review with qualified-human gates. |
| Destructive or mutating examples | Infrastructure deletion, payments, filings, API mutation, load testing, messaging, production flags, account changes, and external submissions require exact target authorization, rollback, and evidence. |
| Manipulation and privacy | Several sales, behavioral, and gamification prompts include pressure, profiling, surveillance, scarcity, or outreach patterns. The projection requires lawful data provenance, consent, opt-out, and non-manipulative alternatives. |
| Biased evaluation defaults | Evidence Collector and Reality Checker prescribe default failure or defect quotas. The projection requires evidence neutrality and permits a verified zero-finding result. |
| Stale or hard-coded implementation assumptions | Seven records are Linux-only because their stated workflows hard-code POSIX commands or paths. Laravel, Jira, framework, path, metric, and tool-version assumptions must defer to the actual repository and host. |
| Illustrative code | Embedded code samples were treated as examples, not trusted production implementations. Findings identify unsafe DOM injection, destructive shell commands, deprecated APIs, incomplete methods, arithmetic edge cases, and unvalidated ML or statistical claims. |

No source in this batch required quarantine because every useful specialty could be
expressed without retaining its unsafe authority. A future source must be quarantined
when prompt-priority escalation, credential exfiltration, unavoidable destructive
behavior, or an invalid body cannot be removed by a bounded projection.

## Portability projection

- **13** tool-free records support Codex, Claude, OpenClaw, and Hermes.
- **46** records require a tool-capable host and support
  Codex, Claude, OpenClaw, and Hermes only.
- **7** records are Linux-only as written because they prescribe
  POSIX-specific execution. The other **52** are
  semantically portable across Windows and Linux when the declared host tools exist.

Host support is a compatibility claim, not evidence that any host or tool is
installed. Runtime discovery and per-turn tool receipts remain authoritative.

## Conflict and composition notes

The records mark direct conflicts where co-loading can create competing governing
instructions: brand governance versus whimsy, product ownership versus sprint
ownership, delivery shepherding versus a stack-specific senior project manager,
studio operations versus workflow optimization, and overlapping release-verdict
roles. Dependency links are reserved for concrete review needs such as accessibility;
persona instructions that say to load other agents do not self-activate them.

## Validation

Generation fails closed unless all of the following hold:

- exactly 59 source files and 59 records;
- exact source-path set equality and unique ingress-derived slugs;
- all required fields and only those fields;
- valid authority, context, status, host, and platform enums;
- exact SHA-256 match between every record and its full source bytes;
- revision identity `459dce837db3bdfdc4763d3fefd1fd854e73c8f1` and audit revision `1` on every record;
- all conflict and dependency references resolve within the batch;
- no direct-safe record has mutating or approval authority or requires tools; and
- LiteLLM is absent from execution-host compatibility.
