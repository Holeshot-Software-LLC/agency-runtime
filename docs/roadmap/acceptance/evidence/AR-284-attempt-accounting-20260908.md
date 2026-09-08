---
title: "AR-284 provider attempt accounting source checkpoint"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [evidence, receipts, inference, compatibility]
related:
  - docs/roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md
  - docs/decisions/0238-separate-provider-fallback-accounting-from-stage-order.md
  - tests/test_provider_attempt_accounting.py
  - tests/test_store_preflight_coverage_final.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-284 provider attempt accounting source checkpoint

## Proven source defect and bounded repair

Inspection began at main `e790c4d4`, after AR-411. Three current writers used
`enumerate(...)` to populate `model_receipts.attempted_fallbacks`: atomic ready
in `store/preflight.py`, direct workforce in `selector/pipeline.py`, and
pending hiring commit in `store/preflight.py`. Existing Store regression even
expected 0/1 for an unstamped flattened list. This is source evidence of the
bug, not an executed expected-red result.

Both structured workforce and hiring producer loops now own one ephemeral
provider-chain accounting object. Their configured slot, transport dispatch
fact and prior actually invoked entry count are stamped separately. Every
semantic repair of one entry retains its fallback count. A complete structured
answer remains a real call even if its contract is rejected. Named failures
use the transport's explicit dispatch fact; legacy bare None stays unknown.
Unknown earlier entries keep later counts unknown instead of becoming zero.

The bounded shared projector admits only metadata version 1, a closed stage,
exact integer/boolean/null types and consistent bounded values. Invalid or
absent metadata is omitted without losing the rest of the receipt. New durable
attempt lists preserve independent one-based ordinal and stage. Existing JSON
without the new metadata remains an exact projection fixed point.

All three wrapper writers take only the projected count or None. Generic
wrapper ingress preserves explicit None, using the existing nullable SQL
column. Omitted defaults, non-wrapper normalization and authoritative LiteLLM
callback behavior are unchanged. Store read paths return raw row dictionaries
and preserve SQL NULL. No schema change, old-row update, provider order, retry
limit, budget, model authority, profile or staffing policy is changed.

## Regressions written, not run

The focused cases cover three independent single-profile stages; repeated
semantic repairs followed by a real fallback; dispatched failure versus
pre-request refusal versus unknown transport result; propagation of unknown
prior entries; malformed and over-bound metadata; closed stage vocabulary;
legacy/new projection fixed points; actual hiring chain stamps; all three
writers; atomic ready replay; explicit NULL through Store reopen; historical
integers remaining unchanged; and unchanged omitted-default/host/callback
normalization. Existing hand-built legacy expectations now require None
instead of an invented flattened count.

The provider calls in those cases are local deterministic stubs, but **the
cases themselves were not executed**. No pytest, CI, model-backed review,
native canary, install, owner database mutation or acceptance verdict occurred.
Targeted Ruff lint/format and diff inspection were the only source checks.
An initial Ruff pass corrected two import-order findings; later lint passed.
No red/green test result or live performance saving is claimed.

Ruff's final source check reported `All checks passed!`, and its formatting
check reported `12 files already formatted`; `git diff --check` was clean.
The first static documentation pass found two record-maintenance obligations:
remove newly mapped AR-284 from pre-tracker history and index inherited merge
e790c4d4. Both were corrected without a runtime change. Metadata validation
checked 1,279 Markdown documents.

The parent's first bounded read-only source pass found no scoped Critical or
High issue in the runtime delta. It also confirmed the failed-preflight
projection reuses the model-attempt projector, so the same bounded metadata
survives that path. This is source review, not acceptance or executed testing.

## Frozen source blob set

These SHA256 values freeze the reviewed source and written regressions; none
is an installed artifact or executed verification result.

| Repository file | SHA256 |
|---|---|
| `agency_runtime/core/receipts/attempt_accounting.py` | `902a569021bae9ea9823629c7e641373acaff9c5c10a8ed7b137faa95465a92e` |
| `agency_runtime/core/receipts/ingress.py` | `2566f439e4b7c2d524049f84ed676c61b47e5b4e69210329cff468d7d40ac0de` |
| `agency_runtime/core/store/evidence.py` | `b31670d59830fece865fc9023a1a941b26f378c4e5ab33aafa0885b2fbd915ad` |
| `agency_runtime/core/store/preflight.py` | `f3e84ab2a49294c8a459034e6b0a880262500860d0b3ac3d6cce8a67e5b61970` |
| `agency_runtime/core/selector/receipt_projection.py` | `1696fea1cfa92807b59c0370a91cfcacb41d009517d328a3f5ea8e39c93afcf3` |
| `agency_runtime/core/selector/pipeline.py` | `0afa117675bf865da17d4c66d77f46924f4044c01d2a70711dbbf40f28f8ed82` |
| `agency_runtime/core/workforce/inference.py` | `e4906f1a4055c02dcb9b469c61a1de114ecc924d84ded3781e1a6bb24c71e5bc` |
| `agency_runtime/core/workforce/hiring.py` | `9567d6fac6a7da8b673fe686bbf35f78547c6d8a7dbd403fa918932d5bdc7868` |
| `agency_runtime/core/workforce/routing_projection.py` | `88f14e27ef9ff1162f7b94e2f2593df7d690665f7096f10a2986156d9e765ea5` |
| `tests/test_provider_attempt_accounting.py` | `555dae0b1e7b337f1f758f3271455ba3dcc2cf887ab830c458057be3b64a11c6` |
| `tests/test_store_preflight_coverage_final.py` | `4d9eb58fa37df8a568c09318846529be08aa903cae7c2a33b04e53f094bb7fa8` |
| `tests/test_workforce_inference.py` | `281bd4c5d8faed897932a182f0506b9cc5e096b220bf352309f2ef442a1031d7` |

## Historical and remaining scope

Historical SQL wrapper integers lacking versioned companion metadata remain
ambiguous; they must not be relabeled as actual fallback counts. A null count
is unknown, not zero. Uninstrumented legacy producers remain unknown rather
than acquiring inferred counts. This bounded change covers the actual
workforce/hiring chain loops feeding the three identified writers, not every
transport's internal retry or router behavior.

AR-281–283 were inspected first in oldest-ID order: the current native-child
host profile resolution, OpenClaw completion-send path and post-message-sent
terminalization source are already present, consistent with their historical
implemented/live-delivery records. That source check was not a new acceptance
verdict or fresh live proof, and no manufactured implementation was added.
AR-284 was selected because its ordinal writer defect is still explicit.

Tracker #754 was explicitly authorized and created; original pending-tracker
acceptance wording remains historical provenance. All six original criteria
remain unchecked. Next: scoped independent source review, then normal PR
publication as in_progress. Run the written focused checks only when the owner
authorizes test execution; do not generate a provider failure merely to obtain
a fresh receipt.
