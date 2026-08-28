---
title: "AR-321: Select a reliable free LiteLLM child judge"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-27
tags: [bug, workforce, child-judge, litellm, local-models, reliability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/decisions/0185-enforce-child-judge-schema-at-litellm-alias.md
  - agency_runtime/core/native_child_staffing.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-321
priority: p0
tracker_url: null
depends_on: [AR-317]
blocks: [AR-297, AR-325]
---

# AR-321: Select a reliable free LiteLLM child judge

## Problem

The exact production-container canary requires a free local child judge to
select one eligible workforce card from the complete 59-card universe. The
current `task-agency-child-judge` LiteLLM alias resolves to Mistral Small 3.2
24B, which returns an empty response for both the initial selection and its one
funded abstention repair. The already-installed abliterated Qwen 14B model is
also unsuitable: without constrained JSON it exhausts its response budget in
prose, and with JSON-object output it confidently selects the wrong specialist.

## Current state

- Fresh exact-candidate Codex install receipt `04f8c2df...7ad` exits 1 after a
  successful 300,000-ms child wait, proving AR-320's timing repair live.
- Mistral child-judge route `fcdf4396...9447` records
  `native_child_abstention_confirmed` after two untruncated calls over the
  complete 59-card set. The child is therefore denied the exact v6 delivery.
- A diagnostic Qwen probe without JSON-object output is unavailable at
  `8861fae6...`; the retained raw response `d34221cc...af9c` is prose truncated
  at 256 completion tokens. JSON-object probe `697d9cd9...1ac0` is structurally
  valid but incorrectly selects `ai-evaluation-engineer` instead of the
  required `code-reviewer`.
- Authenticated exact-prompt probes also reject four free preinstalled models.
  Qwen 3.5 9B selects two cards initially and three on repair at
  `a4a2ccbd...58c1` and `d439740e...a78b`; Qwen3 Coder 30B-A3B selects three
  at `2c04fa65...b580`; Dolphin/Mistral 24B selects `workflow-architect` at
  `cff40a52...1435`; and Qwen 3.5 2B abstains twice at
  `12db1cd3...6bcb` and `f6a1b70f...04fd`. Every rejected alias was removed.
- Owner-approved acquisition of official Apache-2.0
  `ministral-3:14b-instruct-2512-q4_K_M` exits 0 at `1ae8154b...cf1e`.
  Ollama metadata `6321d22e...f2c` proves Mistral3, 13.9B parameters, Q4_K_M,
  and 262,144-token context. Its plain JSON probe `84a4b980...b8d1` puts
  explanation objects in `selected_ids`; exact schema enforcement then returns
  valid strings but over-selects `ai-evaluation-engineer` and `code-reviewer`
  at `aa8917b2...6cef`. Both temporary aliases are removed; deletion receipt
  `f40895e6...d6ab` closes the last deployment.
- Official Apache-2.0 `granite4.2:8b` acquisition exits 0 at
  `1c990f61...c7ed`; metadata `8d44fb7b...b81c` proves Granite, 8.8B
  parameters, Q4_K_M, and 131,072-token context. Temporary deployment
  `e791c3f0...9fc9` is the sole `ar297-probe-child-judge-granite42-8b`
  resolution with exact-schema JSON, 32,768 context, thinking off, and no
  retries; secret-safe create receipt `d76a783c...455c` passes.
- Granite then abstains on both exact initial and repair prompts at
  `b797bbf8...d4f8` and `9c842512...937b`; its alias deletion is retained and
  leaves no Granite deployment. Official Apache-2.0 `qwen2.5:14b` acquisition
  exits 0 at `e3793ca3...b203`; metadata `20b2d98b...360b` proves Qwen2,
  14.8B/Q4_K_M, and 32,768-token context. Sole temporary schema deployment
  `96ee8dc1...f9f0` passes create receipt `da7b3161...edf6` before evaluation.
- Qwen 2.5 returns exact-schema JSON but selects `python-application-engineer`
  at `35f1030d...5e8e`, so its alias is removed without a repair call. Official
  free `llama3.1:8b` acquisition exits 0 at `16e64126...2137`; metadata
  `048e80f2...e20f` proves Llama, 8.0B/Q4_K_M, and 131,072-token context.
  Sole temporary schema deployment `fa9bc0d1...331e` passes secret-safe create
  receipt `469c84df...5740` before evaluation.
- Llama returns exact-schema JSON but selects `ai-evaluation-engineer` at
  `e39a84bd...8274`, so its alias is removed. Before another download, a
  temporary no-fallback schema deployment `28a681dc...7a91` isolates output
  grammar from the already-installed `mistral-small3.2:24b` semantics; create
  receipt `d364b366...e485` passes while the stable alias remains unchanged.
- Schema-bound Mistral selects sole `code-reviewer` initially at
  `76d2cd38...d1a0` but abstains on the funded repair at
  `98ead20c...c791`, so it is not yet promoted and its temporary alias is
  removed. Official Apache-2.0 `gpt-oss:20b` acquisition exits 0 at
  `1e030701...7cee`; metadata `7b701cde...c3d0` proves GPT-OSS,
  20.9B/MXFP4, and 131,072-token context. Sole temporary schema deployment
  `9a85ecdf...a219` passes create receipt `cbf87bba...d9fe` before evaluation.
- GPT-OSS with thinking disabled returns empty content at `91daeed4...2367`,
  so that temporary alias is removed as an invalid configuration, not counted
  as a semantic abstention. Replacement no-fallback deployment
  `25f90630...45d1` uses the model's lowest supported reasoning effort with the
  same schema/context/retry bounds; create receipt `17fdcd76...8b6f` passes.
- Low-reasoning GPT-OSS again returns empty content at `b5bad7af...0500`, so
  its alias is removed at `50e1398f...6ce2`. Fresh-name schema-bound Mistral
  deployment `4527083a...1ff6` passes create receipt `a53f4249...c78c` for an
  uncached repeat of the already-passing initial selector.
- The fresh-name repeat also selects sole `code-reviewer` at
  `cea48a7d...ae89`, matching `76d2cd38...d1a0`. Stable deployment
  `0f0b1b59...a7d1` retains the Mistral backend and now enforces the exact
  schema/context/thinking/timeout/retry contract; before snapshot and promotion
  receipts are `03cf8292...9baa` and `7af0aa02...aa45`. ADR-0185 owns it.
- The owner requires all Agency inference on this system to resolve through
  authenticated LiteLLM aliases and requires the child judge to remain free.
  Tracker creation remains prohibited by the active task.
- Stable literal alias session `b392fe97...2024` and trace `67605732...8175`
  select sole `code-reviewer` with confidence 0.8; retained receipt
  `54a773f7...00d3` exits 0 without a temporary override. Post-promotion
  snapshot `de042cbe...6c0a` proves the sole deployment still resolves to the
  free local Mistral backend with exact schema, 32,768 context, thinking off,
  120-second timeouts, and zero retries. Temporary repeat alias deletion leaves
  zero deployments at `74a870bc...95da`.
- Fresh Codex container `agency-ar297-codex-c1cf1793-j2` reaches the stable
  accepted route, so model selection is no longer the blocker. AR-322 owns the
  later child-session correlation failure exposed by that exact transaction.
- Fresh exact `c3493337` source proves the intervening lineage repairs now join
  the parent and child: one native worker run is persisted for child
  `01a041eb...1128`. The stable authenticated free Mistral alias evaluates all
  59 cards in 62,139 ms with confidence 0.8, but the selected team fails exact
  compatibility as `native_child_compatibility_mutated`; its failure projection
  intentionally persists no selected IDs. Store correlation
  `50bd2770...a0b6` exits 0 against Store `4842b81d...9c9`. Bounded unchanged
  stable-alias repeat `6df05ca7...884` recovers the exact cached selection as
  `code-reviewer` plus `software-test-engineer`, confidence 0.8, proving
  semantic over-selection. Model reliability is again the active blocker; no
  alias or model choice has been changed.
- Three temporary same-backend exact-schema aliases add only temperature 0,
  which Agency's request already declares. Nine unique successful LiteLLM
  request IDs all reproduce the same two-card content `8f9a361c...d155`; spend
  correlation `5baea1c2...a7b1` closes temperature as a repair. Delete receipts
  `a30c4b0d...9200`, `9638bf09...557`, and `18b39cbe...932e` leave zero
  temporary deployments, while the stable projection remains byte-identical
  at `18dd1bdd...18b3`.
- Generic inference-owned compatibility repair `2642ac10...0b1e` re-evaluates
  all 59 cards through the unchanged stable alias and safely abstains after
  20,146 prompt tokens. A closed-diagnostic variant remains bounded; no product
  code, stable alias, model, route, or thinking choice has changed.
- Closed-diagnostic repair `29a0045c...f034` supplies only Mistral's prior IDs
  and the separate-context finding; after 19,637 prompt tokens it repeats the
  same incompatible pair byte-for-byte. Same-model prompt repair is closed.
  Owner input is required before testing a different free local model/route.
- Owner-approved `gemma3:27b` acquisition exits 0; pull stream
  `bfe27b67...f53e` and metadata `70b7267c...1ead` prove local digest
  `a418f5838eaf`, Gemma 3, 27.4B/Q4_K_M, and 131,072-token native context.
  Temporary authenticated deployment `1058108a...d188` is the sole exact-schema
  alias with 32,768 context, thinking off, 120-second timeouts, and zero retries;
  secret-safe create receipt `30805cfe...39c2` passes.
- Its uncached exact 59-card selector call returns schema-valid sole
  `ai-evaluation-engineer`, confidence 0.9, after 17,325 prompt plus 21
  completion tokens with zero reasoning bytes. Receipt `e53e906f...b31c`
  exits 0 but fails the required sole `code-reviewer` semantic result. The alias
  is removed at `ec9514af...75c0`, and stable Mistral deployment projection
  `18dd1bdd...18b3` remains byte-identical. Another model requires owner input.
- Owner-approved `qwen3:32b` acquisition exits 0; pull stream
  `eea2379c...c4a0` and metadata `0f040ecb...63fc` prove local digest
  `030ee887880f`, Qwen 3, dense 32.8B/Q4_K_M, and 40,960-token native context.
  Fresh temporary deployment receipts `2e458fb9...4bff` and
  `c7242824...9cd3` each prove one authenticated exact-schema alias with
  32,768 context, thinking off, 120-second timeouts, and zero retries.
- Both initial 59-card probes select sole `code-reviewer` at confidence 0.9;
  receipts `275b1a2b...81f3` and `574468ce...f138` exit 0 with the same
  54-byte content and zero reasoning. The funded repair independently selects
  the same sole card after 16,572 prompt tokens at `7ef675c5...e9e0`.
  Spend correlation `5163ff8e...61f6` proves three distinct successful request
  IDs, exact Qwen backend/deployment IDs, and no recorded response-cache hit.
- Deletion receipts `298e202b...eb2a` and `7dad190b...673f` leave zero
  temporary deployments. Pre-promotion stable receipt `16b48f2c...ad40`
  remains byte-identical Mistral projection `18dd1bdd...18b3`; Qwen promotion
  and exact route validation are the next bounded package.
- In-place stable promotion receipt `6e19008f...1750` preserves deployment ID
  `0f0b1b59...a7d1` and the alias while changing the executable backend to
  `ollama/qwen3:32b`; its before projection is exact prior
  `18dd1bdd...18b3`, and its after projection is `a8dcd172...744a3`.
- Strict inspection catches that LiteLLM's legacy update endpoint retained the
  former informational Mistral key even though execution resolved to Qwen.
  Bounded partial metadata patch `e1cba9f6...e841` changes only base/key/tier to
  `qwen3:32b`/`qwen3:32b`/`free`; executable params remain byte-identical at
  `47c257af...ee11`. Final six-route validation `42921a7e...867c` exits 0 and
  proves exact Qwen metadata/backend, preserved ID, schema, 32,768 context,
  thinking off, zero retries, mode-0600 config, and all other routes unchanged.
- Literal exact-config probe `b686ab4b...9abe` exits 0 through
  `task-agency-child-judge`, selects sole `code-reviewer` at confidence 0.9,
  and retains the same 54-byte content with zero reasoning. Spend receipt
  `d7183bb5...2f07` correlates request
  `chatcmpl-b1fe24cc-c39b-4c39-b99a-f37fc212e7b9` to exact Qwen backend and
  preserved deployment ID with successful status and no response-cache hit.
- Fresh no-bypass container install `c56eb749...c44` proves the stable alias
  again selects sole `code-reviewer` at confidence 0.9 from the complete live
  roster. The complete card reaches child `01a04313...1872`, host delivery is
  verified, the child exits 0, and the 300-second wait does not time out. The
  model gate is closed; accepted parent finalization and attestation remain
  downstream-blocked only by AR-325's callback reconciliation repair.

## Approach

Create temporary authenticated LiteLLM aliases for already-installed free local
models, preserving the exact 32,768-token context and structured-output
contract. Exercise the real Agency selector prompt and complete 59-card
universe repeatedly, including the funded abstention-repair form. Promote only
a model that repeatedly returns the exact eligible `code-reviewer` identifier
without fallback, truncation, or direct Ollama access. Retain alias-management,
health, model, latency, and response receipts, then repoint the stable
`task-agency-child-judge` alias so the Agency config remains indirection-only.

## Dependencies

- AR-317 and ADR-0181 own the authenticated LiteLLM-only control plane.
- The exact AR-297 config remains mode 0600 and refers only to the stable
  `task-agency-child-judge` alias; no direct local model name enters it.
- Candidate choice is limited to free local models approved by the owner. No
  Jina route may be configured or called.

## Acceptance

- [x] A temporary LiteLLM alias is created with a secret-safe receipt and its
      exact local model, context, structured-output, and thinking controls.
- [x] Repeated fresh-name initial probes choose sole `code-reviewer` from the
      exact 59-card universe without fallback, truncation, or direct access;
      repair probes either choose that card or fail closed, never misroute.
- [x] The stable child-judge alias is updated through LiteLLM, remains healthy,
      and the exact Agency config still passes all route and schema checks.
- [ ] A fresh no-bypass Codex production-container install proves accepted v6
      delivery, consumption, header, finalization, Store correlation, and
      current-profile attestation through the promoted alias.
- [x] Temporary aliases are removed after retained evidence is complete.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
