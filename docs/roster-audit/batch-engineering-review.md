---
title: "Roster semantic safety audit - engineering division"
status: active
category: governance
created: 2026-07-17
updated: 2026-07-22
tags:
  - roster
  - security
  - audit
  - engineering
related:
  - docs/roster-audit/batch-engineering.json
supersedes: []
superseded_by: null
---

# Roster semantic safety audit - engineering division

## Result

This batch semantically reviewed the complete prompt body of **54 engineering
source agents** at upstream revision `459dce837db3bdfdc4763d3fefd1fd854e73c8f1`. The review covered
**14,882 lines** and **786,326 source bytes**. The machine-readable
record contains exactly one entry per source file and does not copy prompt bodies.

- Approved under the bounded runtime contract: **54**
- Quarantined executable contracts: **0**
- Direct-context safe after projection: **2**
- Isolated-context only: **52**
- Authority projection: advise 1, modify 36, plan 13, review 4

"Approved" does not approve each raw directive or embedded example. It means the
useful specialty can be retained when Agency projects only the recorded routing
contract. Raw claims of memory, tool access, organizational authority, external
authority, legal or compliance certainty, and production readiness remain inactive.

Audit revision 2 also records `coordination`, `investigation`, `operations`, and
`risk-analysis` as controlled capabilities for `incident-response-commander`, and
retains its engineering identity and incident-response scope. Those identifiers
are grounded in its reviewed incident-triage, response-coordination, risk-bounded
recovery, and operational-planning outcomes. They do not authorize production
containment or communications: the contract remains plan-only, isolated,
tool-bound, and constrained by its anti-capabilities and approval requirements.

## Scope and method

| Division | Reviewed agents |
|---|---:|
| engineering | 54 |
| **Total** | **54** |

The authoritative upstream inventory at this revision contains 263 source agents
across 17 divisions. This is the complete engineering division: source-path
set equality is enforced, so additions, omissions, or duplicate ingress-derived slugs fail
generation. Every full prompt was read semantically; headings or front matter alone were
not treated as an audit.

Each record projects a compact routing contract: capability and anti-capability
boundaries, task fit, tools, host and platform compatibility, authority, context
mode, conflict edges, expected output, evidence, model requirements, exact source
revision, and SHA-256 over the full raw source bytes.

## Remediation decision

`engineering-mobile-app-builder.md` contains two literal U+0004 control bytes at
byte offsets **11070** and **14825**, a C1 U+0080 control, and multiple mojibake
heading prefixes. The original bytes and SHA-256
`1a3e043f806b0b7c071d58b2ee3ab3c58c8342e2727c1ca9e6e5175f86986caf` remain
immutable quarantine provenance and are never executable.

Audit revision 2 approves a two-stage derivative, not a silent source rewrite. An
exact source-hash-bound rule replaces only the reviewed full heading strings and must
produce SHA-256
`c67b433c23a8bc4f79c0e42917f10a3f4db03985eb4dd18ddc10fd57d487fbe9`.
A separate semantic rule then projects only the allowlisted mobile contract. The
receipt records both rule revisions, before/after hashes, byte offsets, and resolved
findings. Any changed source hash, missing match, extra occurrence, hash mismatch,
unresolved finding, or failed deterministic/inference/conflict gate remains
quarantined; unknown corruption is never guessed or generically stripped.

## Safety and quality findings

| Finding class | Audit disposition |
|---|---|
| Production and external authority | Network commits, database migrations, cloud changes, fleet OTA, mobile-store submissions, messages, deployments, incident containment, and CDN/cache changes are isolated and require exact target authorization, staged evidence, and rollback. |
| Money and regulated workflows | Drupal Commerce, payments/billing, WooCommerce, WeChat Pay, identity, email, voice, and accessibility roles are useful only behind sandbox, privacy, qualified-review, and human approval gates. No persona may move money, approve requests, determine tax or law, or confer compliance. |
| Credentials and sensitive data | Signing keys, payment secrets, identity tokens, email, query logs, transcripts, speaker embeddings, telemetry, billing data, and customer records must not enter prompts or logs without an authorized protected channel. |
| Unsafe illustrative code | Findings preserve concrete defects: model-generated `eval`, a JWT in a redirect query, incomplete payment retry and settlement logic, a Solidity narrowing conversion that breaks accounting, mismatched Wasm examples, malformed video commands, and incomplete realtime authorization and durability. |
| Unsupported guarantees | Exactly-once delivery, zero data loss, zero sandbox escapes, first-pass review rates, WER and diarization targets, uptime, payment success, and performance improvements require measured evidence rather than persona confidence. |
| Version and platform drift | Vendor APIs, model IDs, app-store rules, cloud prices, GaussDB variants, WeChat limits, CMS frameworks, browsers, codecs, payment standards, and runtime APIs must be verified for the exact target and date. |
| Hidden reasoning and orchestration | The prompt and multi-agent specialists cannot request hidden chain-of-thought, fabricate model or delegation receipts, self-activate hierarchies, or replace host-native scheduling. Observable evidence and bounded outputs are required. |
| Missing local artifacts | The senior-developer and OrgScript sources assume paths, persistent memory, specifications, or CLIs that may not exist. They must inspect the current repository and abstain when the governing artifact is absent. |

Two current official-source corrections were recorded. Revised Section 508 incorporates
WCAG 2.0 Level A and AA rather than making WCAG 2.1 a universal Section 508 baseline:
<https://www.access-board.gov/ict/>. Separately, an April 2026 interim final rule moved
the larger-entity ADA Title II web-rule date to April 26, 2027, so the raw specialist's
repeated April 24, 2026 deadline is stale:
<https://www.ada.gov/resources/web-rule-first-steps/>. These are technical routing
findings, not legal advice.

## Portability projection

- **2** tool-free, direct-safe records (`code-reviewer` and
  `software-architect`) support Codex, Claude, OpenClaw, and Hermes.
- **52** approved records require at least repository access or another declared
  hard prerequisite and support Codex,
  Claude, OpenClaw, and Hermes.
- All **54** bounded contracts are semantically portable across Windows and Linux
  when the declared tools exist. Host support is not evidence that a tool, runtime,
  credential, or native test target is installed; discovery and per-turn receipts remain
  authoritative.

## Conflict and composition decisions

The audit records 12 symmetric conflict pairs. These are not mere topical
overlaps: their raw directives can produce competing authority, scope, or governing
method when loaded into the same context.

- `code-reviewer ↔ codebase-onboarding-engineer`
- `codebase-onboarding-engineer ↔ technical-writer`
- `devops-automator ↔ sre-site-reliability-engineer`
- `drupal-shopping-cart-engineer ↔ payments-billing-engineer`
- `incident-response-commander ↔ it-service-manager`
- `incident-response-commander ↔ sre-site-reliability-engineer`
- `minimal-change-engineer ↔ senior-developer`
- `minimal-change-engineer ↔ software-architect`
- `payments-billing-engineer ↔ wordpress-shopping-cart-engineer`
- `rapid-prototyper ↔ senior-developer`
- `rapid-prototyper ↔ software-architect`
- `section-508-accessibility-specialist ↔ uswds-developer`

Examples include neutral onboarding versus prescriptive review or writing, minimal
change versus architecture, prototype shortcuts versus production craftsmanship,
incident command versus overlapping operations authority, and legal accessibility
scope versus a design-system prompt that conflates standards. Related specialists
without incompatible directives remain independently selectable; overlap alone is not
a conflict. Dependencies remain empty because no specialist should self-activate
another persona merely because its raw prompt names a collaboration pattern.

## Validation

Generation fails closed unless all of the following hold:

- pinned upstream HEAD is exactly `459dce837db3bdfdc4763d3fefd1fd854e73c8f1` and its checkout is clean;
- exactly 54 engineering source files and 54 records with exact path-set equality;
- unique front-matter-name-derived ingress slugs and an exact front-matter display name;
- all required fields and only those fields, with semantically non-empty routing arrays;
- valid authority, context, status, host, and platform enums;
- exact SHA-256 match between every record and its full raw source bytes;
- source revision `459dce837db3bdfdc4763d3fefd1fd854e73c8f1`, batch audit revision `2`, and a current per-record audit revision;
- all conflict and dependency references resolve, and every conflict edge is symmetric;
- no direct-safe record has mutating or approval authority or requires tools;
- LiteLLM is absent from execution-host compatibility; and
- every control-bearing original remains immutable quarantine provenance, while a
  remediated contract is packaged only when its exact two-stage receipt and all
  post-repair audit gates pass.
