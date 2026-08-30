---
title: "Roster semantic safety audit - marketing, paid media, and security"
status: active
category: governance
created: 2026-07-17
updated: 2026-07-22
tags:
  - roster
  - security
  - audit
related:
  - docs/roster-audit/batch-marketing-security.json
supersedes: []
superseded_by: null
---

# Roster semantic safety audit - marketing, paid media, and security

## Result

This batch semantically reviewed the complete prompt body of **55 official source
agents** at upstream revision
`459dce837db3bdfdc4763d3fefd1fd854e73c8f1`. The machine-readable record contains
exactly one entry per assigned source file and does not copy prompt bodies.

- Approved under the bounded runtime contract: **55**
- Quarantined executable contracts: **0**
- Direct-context safe after projection: **3**
- Isolated-context only: **52**, including the remediated ASO projection whose raw
  source remains immutable quarantine provenance
- Authority projection: advise 1, modify 6, plan 35, review 13

"Approved" does not approve each raw directive. It means the useful specialty can
be retained when Agency projects only the recorded capabilities, anti-capabilities,
authority, evidence contract, host support, and context mode. Raw prompt claims of
memory, tool access, external authority, production readiness, or permission remain
inactive.

Audit revision 2 also records `audit`, `coordination`, `governance`,
`investigation`, `operations`, and `risk-analysis` as controlled capabilities for
`incident-responder`. Those identifiers are grounded in its already reviewed
evidence integrity and chain-of-custody controls, crisis coordination,
evidence-triage, containment/recovery-planning, and post-incident-analysis outcomes.
They improve typed recruitment without granting live containment authority: the
contract remains plan-only, isolated, tool-bound, and subject to every recorded
anti-capability and approval gate.

`marketing/marketing-app-store-optimizer.md` contains U+0004 control characters at
byte offsets **6817** and **10647**, a C1 U+0080 control, and mojibake headings. The
exact original bytes and SHA-256
`1987be72f8fd43ca694f9145cb0dbe37eabc5b1f04439425d7b59185db9263c9` remain
immutable quarantine provenance and are never executable. Audit revision 2 approves
only a two-stage derivative: exact reviewed full-heading replacements must produce
SHA-256 `d802fee2d7677278562d2b7b8a355363c6bcaab1b8492f620ecf0e7ffd04a0cc`,
then an independent semantic rule projects the bounded read-only ASO contract. The
receipt binds both rule revisions, before/after hashes, edit offsets, and finding
dispositions. Unknown or ambiguous corruption, changed bytes, unresolved findings,
or a failed post-repair audit keeps the entry quarantined.

## Scope

| Division | Reviewed agents |
|---|---:|
| marketing | 36 |
| paid-media | 7 |
| security | 12 |
| **Total** | **55** |

The authoritative `divisions.json` inventory at this revision contains **263 source
definitions across 17 divisions**. Recursive enumeration is required because some
official divisions organize definitions in subdirectories. This file is the complete
assigned 55-agent batch, not a claim that the other official divisions belong here.

The manifest explicitly classifies `integrations/` as generated per-tool conversion
output and `strategy/` as playbooks and runbooks without source-agent identity. They
are `NON_DIVISION_DIRS`, as are `examples/` and `scripts/`, so none are projected as
roster agents. The generator validates that these directories are absent from the
official division manifest and that the official source total remains exactly 263.

## Safety and quality findings

| Finding class | Audit disposition |
|---|---|
| Persistent persona memory | Every record rejects the raw prompt's claimed durable memory. Each invocation is turn-scoped unless a host supplies a separately authorized memory mechanism. |
| External authority and tools | Web, browser, analytics, ad-platform, publishing, email, cloud, shell, scanner, monitoring, and research access are never implied by the persona. LiteLLM remains an inference router and is not recorded as an execution host. |
| Marketing manipulation and authenticity | Raw prompts include covert seeding, engagement bait, artificial urgency, raffle mechanics, pressure tactics, first-person voice, and automatic publishing. Projections require truthful attribution, non-manipulative alternatives, review gates, and no undisclosed or inauthentic engagement. |
| Privacy, consent, and localization | Email, private-domain, analytics, advertising, China-market, and cross-border roles can touch personal data, tracking, protected traits, tax, platform policy, and regulation. Contracts require lawful provenance, consent, minimization, opt-out, current sources, and qualified local review. |
| Paid-media spend and production mutation | Auditing and query analysis remain read-only. Creative, tracking, and configuration work is limited to authorized artifacts; campaign activation, budget changes, bidding, audience uploads, vendor commitments, and live tag deployment require separate owner approval. |
| Offensive security | The penetration-testing source contains actionable exploitation, credential, persistence, evasion, and social-engineering procedures. Its useful expertise is retained only for explicitly authorized defensive review and isolated reproduction with synthetic data, fixed scope, stop conditions, and no persistence or real-data access. |
| Incident, cloud, detection, and credential operations | Raw prompts include host isolation, account disablement, firewall and infrastructure changes, live SIEM deployment, adversary emulation, credential rotation or revocation, and history rewriting. The bounded contracts stop at evidence-backed review, planning, or authorized file changes; live control-plane actions remain outside authority. |
| High-stakes conclusions | Compliance certification, legal and regulatory interpretation, breach notification, public communication, attribution, risk acceptance, store-rule claims, and financial or tax conclusions require current primary sources and qualified accountable owners. |
| Illustrative or stale implementation assumptions | Embedded code, commands, metrics, platform behavior, standards, crawler claims, and hard-coded paths are evidence to review, not production-ready instructions. The Senior SecOps source's nonexistent internal policy reference is replaced by the actual repository policy and reproducible evidence. |
| Invalid source body | The App Store Optimizer raw body remains immutable, quarantined provenance. Only its exact hash-bound repaired derivative and separately reviewed governed projection can route. |

No other source required quarantine because each useful specialty could be expressed
without retaining unsafe authority. A future source must be quarantined when prompt-
priority escalation, credential exfiltration, unavoidable destructive behavior, or
an invalid body cannot be removed by a bounded projection.

## Portability projection

- **4** approved records have no unconditional hard tool prerequisite and support
  Codex, Claude, OpenClaw, and Hermes. Conditional evidence requirements still apply.
- **51** approved records require a tool-capable host and support Codex, Claude,
  OpenClaw, and Hermes only.
- **54** approved records are semantically portable across Windows and Linux when
  their declared host tools exist.
- **1** approved penetration-testing record is Linux-only as projected because its
  bounded isolated workflow still requires Linux security tooling.

Host support is a compatibility claim, not evidence that any host, model, platform,
or tool is installed. Runtime discovery and per-turn tool and model receipts remain
authoritative.

## Conflict and composition notes

Direct conflicts are reciprocal and intentionally narrow:

- Baidu SEO versus general SEO, where local-market evidence and regulatory context
  must not be overridden by generic search assumptions.
- Global podcast strategy versus the general podcast role, which would otherwise
  produce overlapping editorial governance.
- AI-generated code auditing, application security, and Senior SecOps, whose broad
  code-review mandates can issue competing severity and release judgments.
- Incident response versus penetration testing, because live containment and
  offensive test execution must never govern the same target context concurrently.

All conflict targets resolve to stable slugs in this batch. No source declares a
hard runtime dependency; raw instructions that mention other roles do not activate
or load them.

## Validation

Generation fails closed unless all of the following hold:

- the manifest-derived official inventory is exactly 263 sources across 17
  divisions, with non-division directories excluded;
- the assigned inventory is exactly 55 source files and 55 records: 36 marketing,
  7 paid-media, and 12 security;
- exact source-path set equality, deterministic path order, and unique stable slugs;
- all required fields and only those fields, in the canonical field order;
- valid authority, context, status, host, and platform enums;
- exact SHA-256 match between every record and its full source bytes;
- revision identity `459dce837db3bdfdc4763d3fefd1fd854e73c8f1`, batch audit revision `2`, and a current per-record audit revision;
- all conflict and dependency references resolve and all conflicts are reciprocal;
- no direct-safe record has tools, mutating authority, or approval authority;
- LiteLLM is absent from execution-host compatibility;
- no raw source body is executable;
- the App Store Optimizer remediation is exact-hash-bound, preserves the original
  offsets and bytes as quarantine evidence, and produces the reviewed intermediate
  and executable hashes; and
- any incomplete remediation receipt or failed post-repair audit remains unroutable.
