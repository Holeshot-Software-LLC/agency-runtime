---
title: "AR-373: The recruiter is rejected for citing the coverage vocabulary Agency teaches it"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, recruiter, inference, staffing]
related:
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-373
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/537
depends_on: []
blocks: []
---

# AR-373: The recruiter is rejected for citing the coverage vocabulary Agency teaches it

## Problem

`typed_staffing_requirements` (`core/workforce/staffing_verifier.py:417-422`)
builds the coverage evidence the recruiter is shown, in the axis form:

    artifact:{artifact_kind}  lifecycle:{phase}  domain:{item}
    stack:{item}              capability:{item}  authority:{authority}

`_valid_nomination_evidence` then required `[a-z0-9][a-z0-9-]{0,127}` --
hyphens only, no colon. A recruiter that cited those exact tokens back as its
`positive_evidence` had **every** candidate row discarded as
`recruiter_candidate_positive_evidence_invalid`, which surfaces as
`provider_response_contract_invalid` and fails the turn open.

Agency showed the model a vocabulary and then refused it for using it.

Measured live on this installation, 2026-09-02, request
`install this: https://zcode.z.ai/en`:

- the planner produced a good three-unit plan (discovery / operation /
  verification, all `linux`);
- the recruiter nominated `devops-automator` **required at 0.85**, plus
  `sre-site-reliability-engineer` and `operations-manager`;
- every row was thrown away, e.g.
  `positive_evidence: ["artifact:plan","authority:plan","capability:operations","capability:planning","domain:platform","lifecycle:planning"]`.

`provider_response_contract_invalid` was counted **475 times in 24 hours**
on this box (AR-353 measurement), so this is the dominant staffing failure,
not an edge case.

## Current state

The evidence strings have **no downstream consumers**. Traced across the
package: `inference.py` uses them only as reason-code names, prompt text,
schema and validator; `staffing_verifier._semantic_forbidden` deliberately
stopped reading `negative_evidence` and derives from `row.forbidden`;
`preflight_failure` lists only the reason-code names; the remaining two
references are an eval's own schema and a chaos fixture. After validation the
parse loop keeps `agent_id`, `score` and `classification` and discards the
evidence. Nothing in `core/store`, `core/selector` or `core/header`
references them, so they never reach a receipt, projection, store or header.

They are a discipline device: they make the model justify each nomination,
and are then dropped.

## Approach

Accept the vocabulary Agency teaches. Widen only the nomination evidence
charset to admit `:`, keeping every bound that carries a safety property:
at most 16 items, unique, 1..128 characters, lowercase, no whitespace and no
control characters. The shared `_IDENTIFIER_ARRAY` is **not** widened -- it
backs `domains`, `platforms`, `depends_on` and other typed identifiers that
are matched against contracts -- so nomination evidence gets its own
`_EVIDENCE_ARRAY` schema.

The alternative, changing the coverage tokens to hyphens, would touch strings
the verifier consumes for coverage matching. That is real blast radius for no
gain.

## Dependencies

- AR-336 owns recruiter qualification; this removes one concrete blocker
  under it.

## Acceptance

- [x] A recruiter citing the axis vocabulary Agency shows it is accepted.
      Evidence: `_EVIDENCE_ARRAY`, the widened `_valid_nomination_evidence`,
      and `tests/test_recruiter_evidence_vocabulary.py` built from the real
      captured rows.
- [x] Whatever `typed_staffing_requirements` emits validates, derived from
      the real builder so the two cannot drift apart again. Evidence:
      `test_the_vocabulary_agency_shows_is_the_vocabulary_it_accepts`.
- [x] Every safety bound survives, and typed identifier fields are not
      widened. Evidence: `test_every_safety_bound_survives` and
      `test_typed_identifier_fields_are_not_widened`.
- [ ] Live: an ordinary staffed turn on this installation. The recruiter now
      returns `structured_response_applied` on the first attempt with
      `decision_source: inferred` instead of a discarded nomination, and then
      makes its own judgement; the remaining abstention is AR-336's subject,
      not a contract failure.

## Found alongside

- **Model configuration was pointing at names litellm does not serve**
  (`gpt5.6-luna-medium` versus `gpt-5.6-luna-medium`), so the planner never
  ran and every turn was steward-only. Repointed to the purpose-built
  `task-agency-*-v2` routes.
- **`agent_tools_missing` gates install work.** The install specialists
  require tools a host must prove: `cross-platform-installer-engineer` needs
  `package-management`; `devops-automator` needs `ci-runner` and
  `infrastructure-tooling`; `developer-tooling-engineer` needs
  `cross-platform-test-host`. If no host proves these, no install specialist
  can ever be staffed. Worth its own issue.
- `test_live_workforce_eval_canonicalizes_tool_aliases` had been failing on
  main since `380d72e6` made `native-delegation` a baseline capability;
  repaired here.
