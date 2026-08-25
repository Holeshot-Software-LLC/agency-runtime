---
title: "AR-266: Recall the complete workforce with dense hybrid retrieval"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-08-25
tags: [workforce, routing, embeddings, retrieval, inference]
related:
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-266
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320
depends_on: []
blocks: [AR-286, AR-287]
---

# AR-266: Recall the complete workforce with dense hybrid retrieval

## Problem

The active workforce recruiter does not inspect the complete governed roster.
For each inferred work unit, deterministic typed recall orders candidates by
coverage breadth and stable identity, then truncates the detail-card universe
to 24. The inference recruiter may select only from those cards. This protects
the recruiter from a roughly 273-card prompt, but a capable specialist outside
the first 24 is invisible and may be misreported as a workforce gap.

The defect is general classification and retrieval, not the literal phrase
`what's next?`. AR-265 now supplies a transcript-free subject for contextual
turns; workforce recall must use that current-turn subject to find relevant
specialists before inference decides the final staffing plan.

## Current state

- The local implementation keeps the ordered 24-card typed lane and searches
  every enabled approved contract through positive-only lexical and learned
  dense recall before the recruiter call.
- `workforce.dense_recall_mode` supports `off`, `shadow`, and `additive`.
  Learned recall activates only when both explicit capability-correct embedding
  and reranker routes exist; neither route inherits a default model.
- Cold turns batch the complete card catalog with current work-unit queries;
  warm turns embed only the queries against a two-entry exact-identity cache.
- The reranker must return every offered discovery exactly once. Additive mode
  can then expand the recruiter universe beyond 24, while shadow mode records
  evidence without changing cards or consuming the authoritative staffing
  budget.
- Missing exact actual-model identity, invalid vectors, provider failure,
  dimension/model drift, unsafe projections, or an invalid reranker all fail to
  the unchanged typed lane. No vectors or query text are persisted.
- Focused and production-spine verification is green. Forced four-host smokes
  and one native Hermes turn applied the live local embedding and reranker
  providers. The broader cross-provider quality and full shadow-value matrix
  remain open.
- Local shadow preparation found that a provider's valid 4,096-dimension
  default can exceed the unchanged aggregate scalar bound for the complete
  roster. AR-286 owns a provider-native bounded-dimension request; no client-side
  slicing or safety-bound increase is permitted.
- Tracker [#320](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320)
  is linked, and [PR #321](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/321)
  merged the shadow-default implementation to `main` as `042b5ed9`. The issue
  remains in progress until the live shadow-value gate is proven; the merge
  does not recommend additive production activation.

## Approach

Preserve the existing 24-card typed result as a guaranteed lane, not the
complete recruiter universe. Build a positive-only, versioned search document
for every enabled audited contract and combine typed recall, exact lexical
matches, learned dense similarity, and bounded hard-negative evidence through
deterministic reciprocal-rank fusion. The union is additive: no hybrid score
may remove or reorder the baseline typed IDs. Bound the expanded detail-card
document by serialized bytes and a defensive row ceiling rather than treating
24 as the total candidate ceiling.

Create a query per inferred work unit from the current request, typed unit
fields, and AR-265's closed transcript-free subject hints. Do not include raw
prior messages, specialist slugs, trace identifiers, or historical prose. Run
query retrieval on every routed turn. Rebuild roster vectors only when the
roster fingerprint, contract-card hash, projection version, embedding model
revision, dimensions, or normalization identity changes.

Require explicit `workforce.recall.embedding` and
`workforce.recall.reranker` inference routes. The embedding profile must use
`capability_class = "embeddings"`, while the reranker uses `text`; missing
routes disable learned recall rather than falling through to a default model.
An embedding profile may request a bounded provider-native projection through
`dimensions`: zero omits the field, while a nonzero value is accepted only for
embedding-capable Ollama, OpenAI-compatible, and LiteLLM profiles. The returned
dimension must match exactly and participates in catalog identity; rejection,
stripping, or mismatch preserves typed-only recall without slicing vectors.
The recall reranker must return every offered discovery exactly once and may
only order them. The existing `workforce.recruiter` remains the sole staffing
selector. Support `off`, `shadow`, and `additive` modes. Shadow is the safe
default while evaluation evidence is accumulated and uses an independent
two-call evidence budget that cannot consume planner, recruiter, repair, or
critic capacity.

Use an exact in-process cosine scan at current roster scale and a bounded
process cache. Do not reuse or grandfather legacy `agent_embeddings` rows.
Reject stale, partial, zero, non-finite, or mixed-dimension vectors and fall
back explicitly to byte-equivalent typed-only behavior. Record source ranks,
universe count and digest, projection/model identity, latency, cache state,
and failure category without retaining raw vectors or query text.

Pass the expanded cards to the existing recruiter and unchanged staffing
verifier. Dense or lexical evidence is recall evidence only: it cannot select,
exclude, authorize hiring, grant mutation authority, or override exact
eligibility constraints.

## Verification evidence

- Implementation commit `51c7a8ec` contains the bounded hybrid-recall slice.
- 144 focused hybrid-recall, inference-profile, and workforce-inference tests
  pass, including recovery beyond the typed 24, invalid-reranker fallback,
  context-specialized queries, exact-model cache failure, and shadow budget
  non-interference.
- Configuration/profile and receipt projections pass 77 and 68 focused tests;
  routing, selection, and hiring regressions pass 147 tests with one skip.
- The named fast Python production spine passes 806 tests with 20 skips; all
  134 dashboard tests pass; full-repository Ruff check and format-check pass.
- Routing evaluation passes every threshold, including 1.0 required recall,
  0.0 forbidden rate, and all 263/1,000/10,000-agent scale gates.
- Decision conformance passes its baseline and kills all 151 curated mutations
  with zero survivors; source integrity remains unchanged.
- Two independent High findings were repaired and re-reviewed GO: shadow uses
  an independent evidence budget, and absent actual-model identity cannot seed
  or reuse the cache.
- Tracker [#320](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320)
  carries the remaining live shadow gate, and
  [PR #321](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/321)
  merged the safe shadow-default implementation at `042b5ed9` after every
  automatic quality, CodeQL, dependency, Windows portability, performance, and
  unsigned-distribution gate passed without override.
- The full `tests/test_configuration.py` file retains one inherited mainline
  mismatch: it expects the default workforce mode `fast`, while fetched
  `origin/main` config declares `strict`. All AR-266 configuration tests pass.
- Local AR-286 configuration on 2026-08-25 keeps dense recall in `shadow` and
  routes its two optional stages directly to Ollama: embeddings use
  `qwen3-embedding:latest` at an exact 1,024 dimensions and reranking uses
  `qwen3-14b-abliterated:latest` under the closed response schema. The existing
  OpenClaw and Hermes parent-workforce defaults remain
  `linux-task-agency-router` / `task-agency-router` through LiteLLM.
- One forced, bounded AR-266 integration smoke per host label (`codex`,
  `claude`, `hermes`, and `openclaw`) produced applied embedding and reranker
  attempts, 16 novel candidates, and no provider fallback. Codex and Claude
  were evaluator-only; no native host, OAuth, or canary was invoked.
- A versioned `agency eval shadow-recall` promotion gate now fixes four
  identity-free vocabulary-gap targets across those same four host contexts.
  Its focused evaluator, CLI, parser, shadow-isolation, and gate contracts pass
  106 tests. Live provider execution remains the next gate; no result has been
  observed or threshold changed while defining the matrix.
- Native OpenClaw trace `8e6033b2-6ab6-4e1d-ac3b-dca792e8eb2d` produced a real
  Agency header after exact-alias parent inference and both local recall stages
  applied. Routing decision `8b52dd59-fb6a-4326-a655-04d57267382e` loaded
  `gis-analyst` and `codebase-onboarding-engineer`; the OpenClaw receipt kept
  native `task-general` with no fallback. Because this CLI turn has no outbound
  `message_sent` receipt or finalization row, its Store run remains active and
  is native retrieval/header proof, not terminal or external-channel delivery.
- The preceding OpenClaw attempt was rejected before allocation because the
  CLI's implicit `main` agent no longer exists; the distinct successful turn
  explicitly targeted the configured default agent `nexus`. No OpenClaw
  configuration was changed. Hermes shutdown also returned exit 1 after
  honoring SIGTERM; that failed stop receipt is preserved, and the refreshed
  service subsequently started normally.
- Two distinct fresh Hermes CLI turns preserve the next native-host boundary.
  The first lacked the gateway's credential environment indirection and made
  no provider attempt. The second securely reused that populated indirection
  but exposed an 80-second generated bridge and Store lease against a
  120-second harness profile; finalization correctly blocked the unverified
  draft. AR-287 now budgets the parent, recall, hiring, and lease paths from
  static host-scoped profiles. Agency alone was reinstalled into Hermes with a
  595-second hook, without changing Hermes native config. A third fresh trace
  crossed the old timeout and recorded successful exact-alias workforce,
  embedding, and reranker receipts. Its operator-only eight-iteration CLI cap
  then forced a no-tool summary before `agency.finalize`; finalization correctly
  rejected the stale header. That failed attempt is preserved, and a changed
  native turn remains pending behind AR-288: the generated plugin instructs the
  model to call `agency.finalize` but exposes no Hermes native finalizer tool.
- AR-288 then registered Hermes-native `agency_finalize` without changing
  Hermes config. Fresh session `20260825_112803_2eae8e` completed with exact
  terminal response hash
  `91c4a26d30097a6bf18e55dfb792d7c6e1532fe6ba61bca723596b847470daa4`.
  Its Store trace applied the harness-scoped LiteLLM alias
  `task-agency-router`, local 1,024-dimension `qwen3-embedding:latest`, and
  local `qwen3-14b-abliterated:latest`; Hermes native execution stayed on
  `task-general`. This is bounded live-provider evidence, not the complete
  shadow-value matrix or an additive-production recommendation.

## Dependencies

- AR-265 and ADR-0163 provide bounded current-turn subject context without
  replaying the session transcript.
- AR-286 provides bounded provider-native dimensions without changing AR-266's
  per-vector or aggregate safety limits.
- AR-287 binds generated host and Store-lease timeouts to the complete bounded
  host-scoped inference path before Hermes native proof resumes.
- ADR-0083 governs capability-indexed bounded recall.
- ADR-0118 keeps substantive staffing inference-owned.
- ADR-0121 forbids promoting deterministic recall metrics to selection proof.

## Acceptance

- [x] Versioned positive-only card documents exclude prompts, instructions,
      negative fields, audit findings, prior transcript, and raw vectors.
- [x] Index evidence binds the complete roster count and digest, recruiter
      fingerprint, card hashes, projection version, exact actual-model
      revision, dimensions, and normalization identity.
- [x] Every current-turn work unit receives a context-specialized query; a
      `what's next?` turn in two subjects produces distinct safe queries.
- [x] The complete enabled roster is searched while all baseline typed IDs and
      their order are retained in additive mode.
- [x] Expanded cards are byte-bounded and validated against the exact snapshot
      universe before recruiter inference.
- [x] Separately configured embedding and recall-reranker models supply learned
      vectors and bounded ordering; the existing configurable recruiter remains
      the sole staffing selection authority.
- [x] Missing, timed-out, malformed, stale, or mismatched embeddings preserve
      typed-only staffing and record explicit unavailable evidence.
- [x] Dense evidence alone cannot create a semantic gap, hire a contractor,
      select an ineligible worker, or bypass the unchanged staffing verifier.
- [ ] Shadow evaluation proves 100-percent baseline retention, no category
      recall regression, zero forbidden/ineligible/disabled activation, zero
      stale-index reuse, and at least one predeclared recovered vocabulary gap.
- [x] Warm turns do not re-embed the roster, use at most one batched query
      embedding request and one bounded recall-reranker request, without
      consuming the authoritative staffing call budget.
- [x] Focused tests, the named fast production spine, routing and decision
      conformance evaluations, documentation gates, and `git diff --check`
      pass before handoff.
- [x] A same-repository tracker issue titled `[AR-266]` with label
      `epic:workforce` is linked as
      [#320](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320).
