---
title: "AR-321: Select a reliable free LiteLLM child judge"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-27
tags: [bug, workforce, child-judge, litellm, local-models, reliability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
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
blocks: [AR-297]
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
- The owner requires all Agency inference on this system to resolve through
  authenticated LiteLLM aliases and requires the child judge to remain free.
  Tracker creation remains prohibited by the active task.

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
- [ ] Repeated initial and repair selector probes choose `code-reviewer` from
      the exact 59-card universe without fallback, truncation, or direct access.
- [ ] The stable child-judge alias is updated through LiteLLM, remains healthy,
      and the exact Agency config still passes all route and schema checks.
- [ ] A fresh no-bypass Codex production-container install proves accepted v6
      delivery, consumption, header, finalization, Store correlation, and
      current-profile attestation through the promoted alias.
- [ ] Temporary aliases are removed after retained evidence is complete.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
