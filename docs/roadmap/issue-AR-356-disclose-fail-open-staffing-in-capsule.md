---
title: "AR-356: Disclose fail-open staffing honestly in the turn capsule"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [preflight, capsule, fail-open, honesty]
related:
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-355-working-agreements-resident-manager.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-356
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/426
depends_on: []
blocks: []
---

# AR-356: Disclose fail-open staffing honestly in the turn capsule

## Problem

When preflight fails open, the parent model sees nothing: the failure
receipt lands in the store and the turn runs Agency-blind with the
plain steward frame. The model has no way to know it is unstaffed, so
it can imply staffing it does not have, and the fail-open finalization
family (AR-344/AR-346) had room to grow precisely because the turn's
own context never said what happened. With the AR-353 intermittent
window still live, fail-open turns keep occurring.

## Current state

Before this change fail-open turns delivered the steward kernel and the
binding line only. The operator policy was *not* delivered either —
`render_operator_policy` ran only inside the staffed recipe builder
(`_result_from_recipe`), so the earlier claim that fail-open turns
carried the house rules was wrong; that is fixed here as part of the
same insertion point. The honest zero-specialist result
(`no_specialist_fail_open`) existed internally but nothing about it was
rendered into the capsule.

## Approach

On fail-open turns only, append one bounded line to the delivered
capsule, e.g. "Staffing failed this turn (`<reason class>`); you are
unstaffed, proceeding under the steward alone." Source the reason
class from the recorded preflight failure receipt; never include
provider internals. Zero cost on staffed turns.

Scope note (2026-09-01, owner-approved lift): the same honesty rule
extends to specialist tooling — a card's requested capability is not
proof its tools were available (cards already say "availability must be
proven before use"). When a loaded specialist's required tool is
absent, the turn should disclose the degradation rather than let the
model imply capability it lacks (principle stated independently in
ECC's gan-evaluator: report the degraded mode instead of silently
scoring the requested one).

## Implementation (2026-09-01)

- `agency_runtime/core/fail_open_disclosure.py` (new): the versioned,
  hash-pinned disclosure contract. `render_fail_open_disclosure` renders
  one bounded line (`MAX_FAIL_OPEN_DISCLOSURE_CHARS = 512`) whose reason
  class is the persisted `reason_code` (must be a member of
  `PREFLIGHT_FAILURE_REASONS`, else it collapses to `preflight_failed`)
  plus at most four allowlisted staffing codes (`staffing_critic_rejected`,
  `inference_invalid`, `selection_confidence_too_low`, ...). Provider
  detail (`routing_error`, `inference_failures`, attempt payloads) is
  never rendered. Wording v1, sha256
  `4324a6b2256fec064faa1c25757445a65c52210ce9db5080a9c82b2b67000f20`.
- `agency_runtime/core/preflight.py::_fail_open_preflight_result` now
  receives the config, the host delivery ceiling, and the diagnostics'
  reason codes, and builds the capsule as kernel + binding line, then the
  operator policy (previously dropped on fail-open), then the disclosure
  line — all through `_combine_context` under the same ceiling as staffed
  turns. The staffed builder (`preflight_recipe._result_from_recipe`) is
  untouched and never imports the module, so staffed capsules are
  byte-identical; the resident kernel hash and every stored recipe
  fingerprint are unchanged.
- Every host converges on that builder (claude/codex/zcode through
  `adapters/hooks.py` UserPromptSubmit, hermes through `bridge.py`,
  openclaw through `node_bridge.py`, MCP `agency_preflight`), so the
  line reaches all of them without per-host work; the per-host test
  exercises codex, claude, hermes, and openclaw adapters directly.
- Scope note (tool degradation): specialists selected by preflight are
  already filtered by host eligibility (`_tool_requirement_reason`
  rejects unproven required tools before selection), so the real hole was
  `agency_load_specialist`, which loaded any card by slug with no tool
  check. `Store.get_turn_proven_capabilities` (new, `core/store/preflight.py`)
  reads the turn's ready recipe and returns the capability list only when
  the persisted receipt status is verified (`native-contract-verified`,
  `native-installation-verified`, `explicit-tools-without-execution-host`);
  `server/mcp_tools.py::_load_specialist` compares the governed roster
  entry's `required_tools` against it and appends a bounded
  `[Agency tool degradation ...]` line to the returned card (also exposed
  as the `tool_degradation` field) when tools are missing or nothing was
  proven for the turn. Cards without required tools, fully proven cards,
  and stores without the readers render nothing. Wording pinned by
  `TOOL_DEGRADATION_HASH`.
- Tests: `tests/test_fail_open_disclosure.py` (22 tests) — contract pins
  and budget, allowlisted/deduplicated/bounded reason classes, per-host
  capsule delivery asserting the capsule ends with the exact line derived
  from the persisted receipt, operator policy ordered after Agency's
  frame and before the disclosure, the `workforce_inference_failed;
  staffing: staffing_critic_rejected, selection_confidence_too_low`
  shape with provider detail excluded, staffed turns without the marker
  (plus a source-level pin that the staffed builder never imports the
  module), the proven-capabilities store read from a ready recipe, and
  the load-time degradation cases.

## Dependencies

- None; complements AR-353's measurement.

## Acceptance

- [x] A fail-open turn's capsule states that staffing failed, with the
      bounded reason class, on every host — proven by
      `test_fail_open_capsule_discloses_the_staffing_failure_on_every_host`
      (codex, claude, hermes, openclaw adapters; zcode shares the
      claude/codex hook path) and
      `test_workforce_inference_failure_discloses_its_staffing_codes_without_detail`.
- [x] Staffed turns are byte-identical to today — proven by
      `test_staffed_turns_never_carry_the_disclosure` (marker absent on a
      staffed hermes capsule; `preflight_recipe.py` never imports the
      disclosure module) and by the unchanged kernel hash
      `62c94d87...` in `tests/test_resident_managers.py`.
- [x] The line is covered by regression tests and its wording is part
      of the recipe contract (hash-stable) —
      `test_disclosure_wording_is_a_versioned_hash_pinned_contract` pins
      version 1 and both template hashes;
      `test_worst_case_disclosure_stays_inside_its_budget_on_one_line`
      pins the bound.
