---
title: "Enforce the child-judge schema at the LiteLLM alias"
status: accepted
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [litellm, child-judge, structured-output, local-models, operations]
related:
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/selector/judge_protocol.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0185
type: decision
deciders: [maintainers]
---

# ADR-0185: Enforce the child-judge schema at the LiteLLM alias

## Context

AR-297's stable free child-judge alias used Mistral Small 3.2 24B with a
32,768-token context but no backend output grammar. Two complete 59-card calls
returned empty content. Seven alternative free local models either abstained,
mis-selected, over-selected, violated the documented JSON shape, or could not
return content inside the fixed selector budget.

The same Mistral backend with Ollama's exact JSON schema constraint selected
sole `code-reviewer` in two independent fresh-name calls. Its synthetic repair
probe returned an empty valid decision, which is fail-closed; the deterministic
initial call does not fund repair after it succeeds.

## Decision

Keep Agency's stable `task-agency-child-judge` alias and its free local
`mistral-small3.2:24b` backend. At the LiteLLM deployment, enforce the existing
selector response contract: an object with required numeric `confidence` and
an array of at most three string `selected_ids`, with no additional fields.
Keep `num_ctx=32768`, thinking disabled, a 120-second timeout, zero retries,
and no fallback. Do not place a backend model name in Agency configuration.

Treat repeated exact initial selection as the promotion criterion. A funded
repair may select the same valid card or abstain, but must never be converted
by deterministic code into a selection. Full production-container evidence
still decides whether this operating choice is sufficient.

## Consequences

The stable Agency config remains byte-identical and operators can change the
backend centrally. Output grammar prevents prose, object-valued slugs, and
malformed JSON without deciding which workers the model selects. An empty
repair remains an honest failed install rather than a false-positive route.

LiteLLM alias state is now part of the exact production contract and requires
secret-safe snapshots, one-deployment resolution, actual-model evidence, and
repeat probes after changes. Model metadata labels are descriptive; the local
backend plus zero token cost proves the judge remains free.

## Alternatives

Changing Agency's selector prompt or parser was rejected because the existing
contract is already explicit and valid. Forcing `code-reviewer`, filtering a
larger model-selected team, or constraining the schema to one item was rejected
because that would transfer staffing authority to deterministic operations.
Promoting GPT-OSS, Qwen, Granite, Llama, Dolphin, or Ministral was rejected by
their retained exact-prompt evidence.
