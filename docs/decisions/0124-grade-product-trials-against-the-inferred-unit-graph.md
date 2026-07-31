---
title: "Grade product trials against the inferred unit graph"
status: accepted
category: decisions
created: 2026-07-31
updated: 2026-07-31
tags: [evaluation, product, delegation, codex, evidence, specialists]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0124
type: decision
deciders: [maintainers]
---

# ADR-0124: Grade product trials against the inferred unit graph

## Context

The installed Codex activation canary intentionally proves one fixed
`code-reviewer` child. A README-shaped product request instead produced eight
inferred work units and nine selected specialists. The product harness passed
that multi-unit plan into the one-child canary grader, whose persisted-rollout
parser required exactly one spawn and one wait. Product-host tests mocked the
proof result, so the incompatible contracts remained green until the live run.

The product run also used about 100 seconds even though inference alone consumed
66.6 seconds. That left no credible budget for eight native workers, product
tests, documentation, finalization, and independent validation. Allowing the
parent to merge units or perform their work would make a passing artifact build
compatible with the generalist behavior Agency exists to prevent.

## Decision

Keep the activation canary and product trial as distinct evidence contracts.
The activation canary remains a fixed one-spawn, one-wait proof of installation
and hook behavior. A Codex product trial instead projects a bounded persisted
topology of one through sixteen native children and one through sixty-four
waits.

For every exact persisted unit-agent plan row, product proof requires one
correlated delegation, one native-hook activation grant and consumption, one
specialist load, one completed worker run, one exact persisted Codex spawn, one
hook-injected child prompt delivery, and one successful child completion. The
spawn must belong to the exact parent session and use the deterministic native
task label for the delivered work-unit ID. Selected dependency or companion
specialists remain selection evidence; execution cardinality follows the
persisted primary unit rows.

The parent may use only the native spawn and wait primitives during product
execution. It must dispatch every persisted row exactly once and may synthesize
the final response from completed child results, but it may not merge, omit, or
perform a planned specialist unit through its own tools. An undispatchable row
is declined explicitly and makes that product trial fail; it never authorizes a
generalist substitute.

Persist only content-free collaboration identities, counts, task labels, prompt
delivery hashes, and lifecycle states. Child prompts, tool arguments, tool
outputs, and final messages never enter the product report. A successful trial
also requires one accepted first-pass finalization, correction count zero, the
exact workspace-write proof, and independent artifact validation.

Use 600 seconds as the minimum complete-product deadline and retain 1,800
seconds as the CLI default. The minimum is a guard against accidentally running
a multi-worker build with a canary-sized timeout; it is not a latency target.

## Consequences

- A multi-specialist product plan is no longer rejected merely for exceeding
  the activation canary's one-child topology.
- A parent-built product cannot pass by launching nominal specialist children
  after doing the repository work itself.
- Every passing product report maps inferred work units to exact delegated
  specialists and native child lifecycles without retaining private content.
- Product trials take longer than activation canaries and remain limited to one
  attempt per exact installed build.
- Declines, missing children, extra parent tools, header corrections, and
  incomplete workspace-write evidence remain explicit failed trials.

## Alternatives

- **Reuse the activation canary grader.** Rejected because a fixed one-child
  installation proof cannot grade an inference-owned multi-unit product plan.
- **Grade only the final artifacts.** Rejected because a generalist parent could
  build them while specialist execution remained fictional.
- **Let the parent merge or omit inferred rows.** Rejected because it breaks the
  exact staffing evidence and can silently move specialist work back to the
  parent.
- **Require one wait per child.** Rejected because child rollouts prove each
  completion directly; a bounded final wait sequence may observe several
  concurrent children without weakening their individual evidence.
