---
title: "Request automatic Codex delegation through managed global guidance"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [codex, agents, delegation, authority, inference, product]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
superseded_by: null
id: ADR-0138
type: decision
deciders: [maintainers]
---

# ADR-0138: Request automatic Codex delegation through managed global guidance

## Context

Exact installed merge `b2be077` passes autonomous Codex activation with one
inferred and loaded specialist, exact child execution, a closed exit-zero
worker, a valid first header, and zero corrections. Its governed product trial
`ar223-b2be077-readme-01` then accepts an eight-specialist inferred plan but
launches no child. The parent rollout contains zero spawns, follow-ups, waits,
specialist loads, or workers, and the evaluator reports
`codex_parent_spawn_missing`.

ADR-0126 put product scheduling instructions in evaluator-only Codex developer
context after an older host rejected hook context alone. Current Codex uses
native subagents when the user asks or applicable `AGENTS.md` or skill
instructions request delegation. `UserPromptSubmit.additionalContext` remains
developer context, so it can carry the inference-owned plan without becoming
the owner's durable delegation request.

A real control probe in Codex thread
`019fbff7-bb2a-7903-8a22-56bc908bc4e1` selected the installed Agency skill,
then emitted a parent `command_execution` to read `SKILL.md`; its final Agency
header still reported `Skills loaded: none`. Broadening that skill would make
ordinary product parents use a non-collaboration tool that the evaluator must
reject and would create an untraceable visible claim. Adding a sentence only to
the evaluator prompt would instead prove a harness-only path.

Agency installation is the owner's durable opt-in to automatic specialist
delegation. Codex loads global `AGENTS.md` guidance before work without a
parent-side skill read. That is the supported installed surface that can carry
the owner's request without changing any repository's governance.

Exact installed merge `8097e77` proves the global block is present and passes
the one-unit activation canary, but its 11-unit product plan again launches no
child. Current Codex defaults each command hook's model-visible
`additionalContext` to approximately 2,500 tokens and spills a larger value to
disk. Agency permits a bounded persistent-host context of up to 32,000
characters. The product parent may use only collaboration tools, so it cannot
recover an exact spilled plan from the emitted file path and correctly declines
delegation rather than guessing missing rows.

## Decision

Codex installation manages one bounded, marked Agency block in the active
global guidance file. A nonempty safe `AGENTS.override.md` is active when
present; otherwise installation uses `AGENTS.md`. Installation preserves all
owner content outside the markers, replaces its own block idempotently, rejects
malformed or unsafe files before mutation, and reports only path, status,
change, and digest evidence. Uninstall removes only the managed block from both
global files and preserves all other content.

The managed block explicitly requests Codex native subagent delegation only
when the current turn contains an accepted `[AGENCY DELEGATION PLAN]`. It
requires every accepted persisted row to be dispatched exactly once with the
plan's exact native task name, goal, activation and execution messages,
canonical child path, dependencies, and waits. The parent may only schedule,
wait, and consolidate recorded outcomes; it may not replace specialist work.

The block has no staffing authority. It cannot choose, name, replace, or invent
a specialist. Inference remains the only selector, and the persisted plan plus
installed hooks remain the only worker-identity authority. Without a current
accepted plan, the block requests no delegation and does not change ordinary
Codex behavior.

The isolated product profile projects the exact same canonical block through
the production renderer before Codex starts. It accepts no arbitrary guidance
text. Product prompts remain ordinary scenario requests, and the evaluator
does not inject a user-only delegation sentence.

The generated Codex `UserPromptSubmit` command handler sets
`additionalContextLimit` to `0`, the host-supported value that disables
spilling for that handler. Agency's existing 32,000-character context and
48,000-byte encoded-output ceilings remain authoritative, so this does not make
Agency context unbounded. Every other hook retains Codex's default spill
behavior. Bundle smoke validation rejects a Codex install that omits this
complete-plan delivery setting.

## Consequences

- Ordinary installed Codex turns and governed product trials use the same
  durable owner request for automatic delegation.
- Installing Agency is the durable opt-in; users do not append "use subagents"
  to each substantive request.
- Repository `AGENTS.md` files remain untouched; only the Codex global profile
  receives the marked block.
- Multi-unit plans remain inline and exact at the parent inference boundary;
  the parent never needs a file-read tool to recover routing authority.
- Native-only or failed-inference turns contain no accepted plan, so the block
  cannot manufacture a worker or specialist claim.
- Installer, uninstall, isolated-profile, and decision-conformance checks fail
  if this exact installed request or its inference boundary disappears.

## Alternatives

- **Broaden the installed Agency skill.** Rejected because the real probe adds
  a parent shell read, remains untraceable in the header, and violates the
  product parent's collaboration-only boundary.
- **Prefix only product-evaluation prompts with a delegation request.**
  Rejected because it would prove a special harness path rather than installed
  README behavior.
- **Keep evaluator developer instructions as the only authority.** Rejected
  because the exact `b2be077` trial proves that current Codex launches no child.
- **Modify every repository's `AGENTS.md`.** Rejected because installation must
  not rewrite project governance or create clone-specific behavior.
- **Let the parent read Codex's spilled hook-output file.** Rejected because the
  parent is intentionally collaboration-only and the spill path is not part of
  the persisted exact-plan authority.
- **Let global guidance choose a default worker.** Rejected because inference
  owns every substantive staffing decision.
