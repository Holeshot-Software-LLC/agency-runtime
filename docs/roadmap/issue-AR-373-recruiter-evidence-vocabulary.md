---
title: "AR-373: The recruiter is rejected for citing the coverage vocabulary Agency teaches it"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-03
tags: [workforce, recruiter, inference, staffing]
related:
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
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

## Captured live, 2026-09-03

The widening is deployed (the installed runtime is byte-identical to `main`)
and it works: a repair attempt on the helix-install turn cited
`artifact:plan`, `authority:plan`, `domain:operations` as `positive_evidence`
and those rows passed. The live criterion below still fails, for three reasons
that were only visible once the exact request and reply were captured in
process rather than read back from the receipt. All three came from
`anthropic/MiniMax-M3`, which serves this route first; the one turn the
gateway handed to `chatgpt/gpt-5.5` returned clean hyphenated codes on every
row and was accepted.

1. **The same defect, one vocabulary over.** `typed_recall` shows the
   recruiter each candidate's `ineligibility_reasons`, in underscore form
   (`agent_authority_mismatch`, `agent_lifecycle_mismatch`). A recruiter that
   cites those back as `negative_evidence` is rejected
   `recruiter_candidate_negative_evidence_invalid`, because the charset admits
   `:` and `-` but not `_`. Seen on two of five captured turns; the same shape
   as the original filing.
2. **Forbidden rows without `positive_evidence`.** The provider does not
   enforce the JSON schema's `required` list, so a forbidden candidate arrives
   with `negative_evidence` only and fails
   `recruiter_candidate_row_shape_invalid`. Three units on one captured turn;
   7 of 48 rejected recruiter attempts in the smoke carry that diagnostic. An
   absent evidence array on a forbidden row carries no information the
   contract needs.
3. **Prose after a misleading retry.** When the first reply was truncated
   (AR-385) the generic feedback sent the retry through the ordinary system
   prompt, and the model answered with `"repository-read mapping"`,
   `"not_for: implementation rather than review"`. Two of five turns.

The counts that matter: of 48 rejected recruiter attempts in the smoke, 9
carry `invalid_candidate` and this issue owns them; 31 carry
`staff_without_safe_team` and belong to AR-384; 8 carry nothing and belong to
AR-385. The dominant staffing failure is not the evidence charset.

## Residue read in process, 2026-09-03, and its fix

Once ADR-0198 and ADR-0201 had cleared the verifier and the planner, four of
the eleven install wordings still died at the recruiter on reply shapes the
MiniMax deployment emits, captured in process on the ADR-0201 run:

| turn | what the deployment sent | how the runtime read it |
|---|---|---|
| 202 | a forbidden row without its empty `positive_evidence` array | `recruiter_candidate_row_shape_invalid` on three units, then the repair cited `agent_domain_mismatch` as negative evidence and lost to the underscore |
| 203 | the `units` array wrapped once more, `{"units": [{"units": [...]}]}` | no row named a unit: `missing_work_unit` on every unit without a diagnosis; the repair returned evidence as objects whose keys were the codes and lost to `recruiter_candidate_positive_evidence_invalid` |
| 204 | a repair reply of exactly `{}` | a bare error, so the attempt reached both receipts with no validation record (AR-385's third criterion) |
| 207 | a valid reply the verifier rejected on confidence | the attempt row was blank on both receipts; only the turn-level `staffing_reason_codes` named the verifier |

Fixed per [ADR-0202](../decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md):
a candidate row is read as the deployment sends it where no safety property
lives (a missing evidence array is empty, a string-keyed object is its keys,
identity and score stay mandatory, unknown fields stay refused, every bound
still applies); the evidence charset admits the underscore vocabulary Agency
shows beside the colon form this issue admitted; one wrapper is unwrapped;
a reply that is not a units object is recorded per unit as
`missing_work_unit` with the closed `recruiter_response_shape_invalid`
diagnosis and repaired; and the verifier's `unit=code` rows project onto the
attempt row of both receipts. Pinned from the captured rows in
`tests/test_recruiter_reply_residue.py`.

Live re-measurement, the same eleven wordings, strict mode, branch runtime
against the reconciled store copy (evidence in
`docs/roadmap/acceptance/evidence/AR-373-AR-385-residue-evidence-20260903.txt`):

| outcome | turns |
|---|---|
| completed with a staffed team, critic approved | 4 (204, 206, 207, 209); ADR-0201 run 3, AR-386 run 2 |
| a reply that was not a units object, recorded per unit with `recruiter_response_shape_invalid` and repaired | 1 (206, one proper row, one row without `unit_id`, nineteen text fragments; the turn completed) |
| rows missing their `score`, recorded as `recruiter_candidate_row_shape_invalid` and repaired | 1 (304; the repair was accepted by the verifier and vetoed by the critic) |
| the missing-array, evidence-object, wrapper and underscore shapes | 0 recurrences on fresh replies |
| a reply the transport could not read as JSON (`failed`, `provider_no_valid_response`) | 1 (201) |
| verifier confidence (`selection_confidence_too_low`) | 1 (202; its attempt rows were captured blank before the re-projection fix below) |
| strict critic `wrong-neighbor-selection` | 4 (203, 205, 208, 304); 205's team is the one the critic approved on the ADR-0201 run |
| recruiter gap, hiring ran, no hire | 1 (305) |

The replies were fresh, not gateway replays: no recruiter or planner response
carried a cache key and every plan differed from the ADR-0201 run's. One
finding came from the run itself: the verifier rows projected onto an attempt
when the receipt is written were dropped when it was read back, because the
list path admitted nomination codes only. The row projection now admits a
bare `unit=code` row from the verifier's closed vocabulary
(`STAFFING_VERIFIER_REASON_CODES`), and 202's captured detail round-trips
identically offline. What the recruiter deployment still does that the
runtime cannot read: omit a candidate's `score` (304) and return no JSON
object at all (201, and 304 on the previous run).

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
- [x] Live: an ordinary staffed turn on this installation. Met 2026-09-03 on
      the ADR-0201 runtime under strict mode: turns 205, 206 and 305 of the
      eleven install wordings completed with staffed teams and the critic's
      approval (`docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt`);
      the residue table above records what the recruiter deployment still
      sends and how ADR-0202 reads it.

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
