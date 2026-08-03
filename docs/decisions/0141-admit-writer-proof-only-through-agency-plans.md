---
title: "Admit writer proof only through Agency plans"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, canary, product, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/decisions/0140-use-codex-stable-multi-agent-feature.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/evals/product_host.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0140-use-codex-stable-multi-agent-feature.md
superseded_by: null
id: ADR-0141
type: decision
deciders: [maintainers]
---

# ADR-0141: Admit writer proof only through Agency plans

## Context

ADR-0140 hypothesized that forcing `multi_agent_v2` caused a generic
Agency-disabled parent to skip `spawn_agent`. A new retained control using
stable `multi_agent` disproves that hypothesis: it also records zero spawns,
zero follow-ups, one completed wait with zero receivers, and zero unexpected
items. Its parent then falsely reports that a child hit a read-only workspace,
even though no child existed and the backend passed `workspace-write`.

That generic parent is not the README product path. Exact Agency product trial
`ar223-eb8e077-readme-01` already proves the installed global guidance and
accepted inference plan cause nine V2 spawns, nine follow-ups, eighteen waits,
and nine completed workers. Its remaining failure occurs inside writer task
realization after successful Agency scheduling. Separately, direct app child
`ar223-direct-native-child-01` writes and reads back exact bytes, proving current
Codex child workspace-write capability.

The generic controls removed the two authorities that make the real path
representative: an accepted Agency delegation plan and the installed global
delegation request. Treating their parent discretion as an admission gate
redirected work away from the already-proven product scheduler.

## Decision

1. Retain the current `multi_agent_v2` host feature for the established
   two-turn `spawn_agent` / `followup_task` product contract. ADR-0140's stable-
   feature replacement is superseded without producing a build.
2. A writer execution sentinel is product-admissible only when it starts from
   one accepted inference-authored Agency plan row, loads that row's selected
   specialist, follows the installed global delegation request, and uses the
   same activation and self-contained execution protocol as the product host.
3. Agency-disabled generic parent controls remain diagnostic observations.
   They cannot prove or disprove Agency scheduling and cannot trigger feature,
   inference, header, dashboard, or execution-envelope changes.
4. Preserve the direct native child result as independent workspace-capability
   evidence. Preserve the consumed product trial's nine spawns as scheduler
   evidence. The only next live question is whether the new self-contained
   follow-up makes one accepted Agency writer child create exact bytes.
5. Do not run another full product trial until that one-row installed Agency
   sentinel passes with one spawn, one follow-up, two waits, one loaded
   specialist, one completed worker, exact file proof, and zero corrections.

## Consequences

- The next evaluation exercises the README mechanism rather than a generic
  Codex behavior that Agency does not promise.
- Existing inference authority, global guidance, child lifecycle, and evidence
  correlation are reused instead of reconstructed in another control harness.
- A passing native child alone is not called Agency success; a green Agency
  lifecycle alone is not called artifact success. The one-row sentinel must
  prove both in the same run.
- The stable-feature detour is preserved as rejected evidence rather than
  silently erased or carried into a build.

## Alternatives

- **Keep changing feature flags from generic controls.** Rejected because both
  stable and V2 controls fail identically while the real Agency V2 scheduler
  already proves nine launches.
- **Run another full product trial immediately.** Rejected because one writer
  row can test the repaired execution edge faster and without spending the
  product evidence slot.
- **Count the direct app child as Agency proof.** Rejected because it lacks an
  inferred plan, selected specialist, Agency lifecycle, header, and correction
  evidence.
- **Let the parent write after a child omission.** Rejected because that would
  hide the exact product defect.
