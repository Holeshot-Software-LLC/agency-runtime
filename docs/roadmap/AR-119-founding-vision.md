---
title: "AR-119 founding nine-rule vision"
status: active
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [vision, workforce, inference, native-child, hosts, contractors]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
supersedes: []
superseded_by: null
type: roadmap
ar119_authority: vision-wording
canonical_block_sha256: 8d81be4301ea76b3820b792f54842916321a9557b4a13fce58d6688abe962e50
---

# AR-119 founding nine-rule vision

This is the repository-local rendering of the owner-confirmed founding vision.
The rules were confirmed on 2026-08-07 and Rule 8 was sharpened on 2026-08-11.
It was imported on 2026-08-12 so recovery and completion no longer depend on a
session-local memory file. Repository-external identifiers are neutralized;
the confirmed rule semantics are preserved.

## Provenance

- Source label: `agency-runtime-founding-vision`
- Source modified: `2026-08-11T13:35:49.972Z`
- Source document SHA-256:
  `41f69274f3796126f11ea0c7b46bff9e2065bf960ab269076dde36f8ce1ec10e`
- Repository canonical block: UTF-8 with LF line endings, from the canonical
  card-metaphor heading up to but excluding the differentiator heading
- Repository canonical-block SHA-256: the machine-checked
  `canonical_block_sha256` front-matter field

The source digest identifies the owner-confirmed source used for this import.
The repository block is authoritative here and neutralizes only personal and
repository-external identifiers. Any semantic rule change requires a new owner
confirmation and updated provenance.

## Canonical card metaphor

Agency reads what was just asked, pulls the right card(s) from a ~280-card
cabinet of specialist prompts, and hands them to whoever is about to do the work
— the generalist, or any sub-agent the harness spun up on its own. The specialist
operates *inside the existing conversation*; nobody is hired and sent to a side
room.

## The nine rules

1. **Selection is inference-based, never manual.** This is the project's
   contribution over the inspiration project (~230 agents, 100% direct-load but
   manually chosen).
2. **Load into the caller, don't spawn.** The specialist works in the parent
   conversation.
3. **Multiple cards allowed** when the job needs them and they don't conflict.
4. **Harness-spawned children must also get cards** — plural. A sub-agent Claude
   Code spun up on its own initiative should be handed a specialist, not told to
   go call preflight itself.
5. **Agency never decides to spawn.** Spawning is the native harness's call,
   always. Agency's job is to staff whoever exists.
6. **No card found → create one (a "contractor"), interview it for safety, file
   it in the pool** for next time.
7. **Temporary, per turn.** "Vampire an employee for a turn and spit him out."
   The card returns to the cabinet at turn end; it does not stay with the
   generalist.
8. **If it can't help, get out of the way.** Silence beats a wrong card; a wrong
   card beats nothing only never. It complements and never blocks.

   **Sharpened 2026-08-11, after the rule kept being read as absolute:**
   the operative line is **"Agency never withholds a turn because Agency is
   *unavailable*."** Agency failing to *check* something is not a finding about
   the response. But a verifier that actually **evaluated and rejected** is
   Agency working, and it still blocks — if a definite negative may never
   withhold, the evidence contract is advisory and the verification spine is
   decoration. Two deliberate blocking paths therefore remain and are **not**
   drift: the verifier's definite negative, and the malformed-`Stop` boundary
   (an unreadable envelope means Agency cannot tell it even owns that Stop, so
   failing open would make the contract bypassable by sending a malformed
   payload). Anything else that withholds a turn is a bug. Audit it with
   `agency evidence rejections`, which partitions closed runs into withheld vs
   Agency-was-blind.
9. **HOST PARITY (confirmed 2026-08-07).** The functionality must run **the same on
   codex, claude, openclaw, hermes, and zcode.** A capability that exists on one
   host and not another is incomplete, not a trade-off. This is why the product
   is "across harnesses" — parity *is* the claim. Do not ask whether a behavior
   should be ported to another host; the answer is always yes. Build
   host-agnostic paths by default and treat per-host branches as a smell to
   justify.

## Differentiator

The product is a **DYNAMIC specialist system — for the main agent AND for the
harness's own sub-agents. Nobody has that.** Existing work is either
hard-coded pipelines (orchestrator→dev→QA→review) or manual specialist
selection. Dynamic + covering harness-spawned children is the novel claim. If a
document describes mechanism without stating this, the document has failed.

**Selection comes from INTENT, not keywords.** Picking an agent must follow what
the user actually means, not which words they used. Rule 1 says selection is
inference-based; this says *why*. A deterministic layer that reads the raw
request and changes what gets staffed is a violation even when the inference
call still happens.

## Owner clarifications in force

The 2026-08-12 mitigation direction fixes these interpretations for the open
completion work:

- Codex remains supported and must satisfy Rule 4; its opaque context channel is
  an engineering blocker, not an exception to Rule 9.
- Inference is the only specialist or contractor chooser. Deterministic code may
  recall, enforce hard eligibility and safety, validate, budget, and correlate;
  it may not make or erase the staffing decision.
- Only an artifact authored by the native host can originate a Rule-4 delivery
  claim, as governed by ADR-0156.
- Improve staffing latency without weakening the 15,000 ms cold control,
  inference authority, or evidence authority.
- Automatic contractor promotion is part of the AR-119 critical path, governed
  by ADR-0157.
