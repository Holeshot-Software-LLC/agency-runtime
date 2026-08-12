---
title: "AR-119 rule and host evidence matrix"
status: active
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [vision, acceptance, evidence, hosts, parity]
related:
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
supersedes:
  - docs/roadmap/AR-119-acceptance-evidence.md
superseded_by: null
type: roadmap
ar119_authority: completion-evidence
vision_block_sha256: 8d81be4301ea76b3820b792f54842916321a9557b4a13fce58d6688abe962e50
candidate_commit: b79a4138fd34e4f2e8abc01c5622d359e190e1dc
evidence_cutoff: 2026-08-12
---

# AR-119 rule and host evidence matrix

This is the sole current completion projection for the
[founding nine-rule vision](AR-119-founding-vision.md). It is deliberately
conservative: implementation or simulation evidence does not become installed
or live proof, an unavailable host stays `unproven`, and a Store row or model
claim never substitutes for the proof authority named below.

`candidate_commit` is the exact source-evaluation baseline. `State` is derived
from the four layer columns: any current negative layer makes the cell
`negative`, all four proven layers make it `proven`, and every other combination
is `unproven`. An installed or live result counts only when its host artifact is
bound to that exact candidate. Earlier artifacts remain visible as prior-
candidate context but cannot make a current installed/live layer green or red.
Although the schema reserves `not-applicable`, none of the nine rules is
optional on a supported host.

Because this document is first introduced by a later commit, its recorded
candidate intentionally names the last clean ancestor evaluated by this
package. The package commit and its ledger are governance evidence only and do
not change runtime source; the next runtime package must advance the candidate
field and re-evaluate every affected layer.

## Canonical matrix

| Rule | Host | State | Implementation | Simulation | Installed | Live | Proof authority | Artifact | Observed | Source | Limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | claude | negative | negative | unproven | unproven | unproven | Inference receipt joined to exact delivered card hashes | hooks.py deterministic pre_narrow and compatibility path | 2026-08-12 | `agency_runtime/adapters/hooks.py:990-1019,1116-1142` | Prior-candidate cards were delivered, but exact-candidate simulation/installed/live proof is absent and current source can alter inference choice |
| R1 | codex | negative | negative | unproven | unproven | unproven | Inference receipt joined to exact delivered card hashes | hooks.py deterministic pre_narrow and compatibility path | 2026-08-12 | `agency_runtime/adapters/hooks.py:990-1019,1116-1142` | Delivery is also negative, so no current simulation or installed card-hash join exists |
| R1 | zcode | negative | negative | unproven | unproven | unproven | Inference receipt joined to exact delivered card hashes | hooks.py deterministic pre_narrow and compatibility path | 2026-08-12 | `agency_runtime/adapters/hooks.py:990-1019,1116-1142` | Host is not installed and no current simulation proves inference-only choice |
| R1 | hermes | unproven | unproven | unproven | unproven | unproven | Inference receipt joined to exact delivered card hashes | none | unobserved | `docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md` | No current host-specific selection proof |
| R1 | openclaw | unproven | unproven | unproven | unproven | unproven | Inference receipt joined to exact delivered card hashes | none | unobserved | `docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md` | No current host-specific selection proof |
| R2 | claude | unproven | unproven | unproven | unproven | unproven | Native primary-caller artifact containing selected cards before first caller speech | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | Child artifacts do not prove that the existing parent conversation received its cards |
| R2 | codex | unproven | unproven | unproven | unproven | unproven | Native primary-caller artifact containing selected cards before first caller speech | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | Child simulation does not prove primary-caller delivery through the real encrypted channel |
| R2 | zcode | unproven | unproven | unproven | unproven | unproven | Native primary-caller artifact containing selected cards before first caller speech | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No exact-candidate primary-caller artifact |
| R2 | hermes | unproven | unproven | unproven | unproven | unproven | Native host artifact containing cards before first caller speech | none | unobserved | `docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md` | Host path remains unmeasured |
| R2 | openclaw | unproven | unproven | unproven | unproven | unproven | Native host artifact containing cards before first caller speech | none | unobserved | `docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md` | Host path remains unmeasured |
| R3 | claude | unproven | unproven | unproven | unproven | unproven | Native primary-caller artifact with multiple compatible card hashes before first caller speech | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | Prior multi-card child artifacts prove Rule 4, not multi-card delivery into the parent caller |
| R3 | codex | unproven | unproven | unproven | unproven | unproven | Native primary-caller artifact with multiple compatible card hashes before first caller speech | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | Fake child simulation does not prove multi-card primary-caller delivery |
| R3 | zcode | unproven | unproven | unproven | unproven | unproven | Native primary-caller artifact with multiple compatible card hashes before first caller speech | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No exact-candidate multi-card primary-caller artifact |
| R3 | hermes | unproven | unproven | unproven | unproven | unproven | Native host artifact with multiple compatible card hashes before speech | none | unobserved | `docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md` | Multi-card behavior is unmeasured |
| R3 | openclaw | unproven | unproven | unproven | unproven | unproven | Native host artifact with multiple compatible card hashes before speech | none | unobserved | `docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md` | Multi-card behavior is unmeasured |
| R4 | claude | unproven | unproven | unproven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | prior-candidate children ad68a49ad2297ebd2 a9c6ab358c1e5ebc6 a41e5c325024bb208 | 2026-08-11 | `docs/roadmap/issue-AR-119-inference-first-workforce.md#historical-execution-record-superseded` | Three prior-candidate live proofs exist, but they do not establish exact-candidate implementation or simulation layers |
| R4 | codex | negative | negative | unproven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | prior-candidate GUI child 019ff1e9-defe-77c2-8bd1-9d503f1670b6 and TUI child 019ff250-6243-7261-a7bd-366714f530ad | 2026-08-11 | `docs/roadmap/issue-AR-119-inference-first-workforce.md#historical-execution-record-superseded` | Current source cannot use encrypted context; prior-candidate live negatives do not bind this candidate or prove a current simulation layer |
| R4 | zcode | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | `test_a_host_initiated_child_is_handed_cards_plural[zcode]` | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:287-310` | Simulation exists but no exact-candidate native child artifact |
| R4 | hermes | unproven | unproven | unproven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | none | unobserved | `docs/roadmap/issue-AR-119-inference-first-workforce.md#historical-acceptance-record-superseded` | Host is unavailable on the evidence machine |
| R4 | openclaw | unproven | unproven | unproven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | none | unobserved | `docs/roadmap/issue-AR-119-inference-first-workforce.md#historical-acceptance-record-superseded` | Host is unavailable on the evidence machine |
| R5 | claude | unproven | unproven | unproven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | prior-candidate parent 91e03ac9-c1ec-40f1-b8a8-eaf6dc853c65 to child a9c6ab358c1e5ebc6 | 2026-08-11 | `docs/roadmap/issue-AR-119-inference-first-workforce.md#historical-execution-record-superseded` | Prior native-origin context cannot establish a current universal source-absence or simulation gate |
| R5 | codex | unproven | unproven | unproven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | prior-candidate parent 019ff1e8-e0fe-7fe0-b8ba-57de219228c6 to child 019ff1e9-defe-77c2-8bd1-9d503f1670b6 | 2026-08-11 | `docs/roadmap/issue-AR-119-inference-first-workforce.md#historical-execution-record-superseded` | Prior native-origin context cannot establish a current universal source-absence or simulation gate |
| R5 | zcode | unproven | unproven | unproven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | none | unobserved | `docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md` | No current native-origin artifact or absence verifier |
| R5 | hermes | unproven | unproven | unproven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | none | unobserved | `docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md` | No current native-origin artifact or absence verifier |
| R5 | openclaw | unproven | unproven | unproven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | none | unobserved | `docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md` | No current native-origin artifact or absence verifier |
| R6 | claude | unproven | proven | unproven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | host-neutral contractor contract test only | 2026-08-12 | `docs/roadmap/AR-119-acceptance-evidence.md#ar-122-governed-contractor-hiring-and-workforce-lifecycle` | Implementation is present, but no Claude-scoped simulation or installed same-turn artifact exists |
| R6 | codex | unproven | proven | unproven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | host-neutral contractor contract test only | 2026-08-12 | `docs/roadmap/AR-119-acceptance-evidence.md#ar-122-governed-contractor-hiring-and-workforce-lifecycle` | Implementation is present, but no Codex-scoped simulation or installed same-turn artifact exists |
| R6 | zcode | unproven | proven | unproven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | host-neutral contractor contract test only | 2026-08-12 | `docs/roadmap/AR-119-acceptance-evidence.md#ar-122-governed-contractor-hiring-and-workforce-lifecycle` | Implementation is present, but no ZCode-scoped simulation or installed same-turn artifact exists |
| R6 | hermes | unproven | proven | unproven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | host-neutral contractor contract test only | 2026-08-12 | `docs/roadmap/AR-119-acceptance-evidence.md#ar-122-governed-contractor-hiring-and-workforce-lifecycle` | Implementation is present, but no Hermes-scoped simulation or installed same-turn artifact exists |
| R6 | openclaw | unproven | proven | unproven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | host-neutral contractor contract test only | 2026-08-12 | `docs/roadmap/AR-119-acceptance-evidence.md#ar-122-governed-contractor-hiring-and-workforce-lifecycle` | Implementation is present, but no OpenClaw-scoped simulation or installed same-turn artifact exists |
| R7 | claude | unproven | unproven | unproven | unproven | unproven | Same identity observed in one turn and absent from the next turn | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No current two-turn non-carryover artifact |
| R7 | codex | unproven | unproven | unproven | unproven | unproven | Same identity observed in one turn and absent from the next turn | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No current two-turn non-carryover artifact |
| R7 | zcode | unproven | unproven | unproven | unproven | unproven | Same identity observed in one turn and absent from the next turn | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No current two-turn non-carryover artifact |
| R7 | hermes | unproven | unproven | unproven | unproven | unproven | Same identity observed in one turn and absent from the next turn | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No current two-turn non-carryover artifact |
| R7 | openclaw | unproven | unproven | unproven | unproven | unproven | Same identity observed in one turn and absent from the next turn | none | unobserved | `docs/roadmap/AR-119-founding-vision.md` | No current two-turn non-carryover artifact |
| R8 | claude | unproven | proven | unproven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | no Claude-scoped prompt-preflight simulation | 2026-08-12 | `agency_runtime/adapters/hooks.py:932-951` | Implementation fails open, but the cited prompt-preflight test covers only Codex and ZCode and no native publication proof exists |
| R8 | codex | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[codex]` | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` | Contract output cannot prove native host publication |
| R8 | zcode | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[zcode]` | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` | No live host publication artifact |
| R8 | hermes | negative | negative | unproven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | bridge exception path replaces output with block response | 2026-08-12 | `agency_runtime/adapters/hermes/bridge.py:269-318` | Current source withholds when Agency is unavailable; no separate simulation proof is claimed |
| R8 | openclaw | negative | negative | unproven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | bridge failure cancels host output | 2026-08-12 | `agency_runtime/adapters/openclaw/node_bridge.py:790-903` | Current source withholds when Agency is unavailable; no separate simulation proof is claimed |
| R9 | claude | negative | negative | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate b79a4138 | 2026-08-12 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Current Rule-1 source is negative and exact-candidate simulation/installed/live parity is unproven |
| R9 | codex | negative | negative | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate b79a4138 | 2026-08-12 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Current Rule-1 and Rule-4 source are negative; simulation/installed/live parity is unproven |
| R9 | zcode | negative | negative | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate b79a4138 | 2026-08-12 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Missing simulation and live evidence prevents parity |
| R9 | hermes | negative | negative | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate b79a4138 | 2026-08-12 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Rule 8 source is negative and simulation/live evidence is incomplete |
| R9 | openclaw | negative | negative | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate b79a4138 | 2026-08-12 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Rule 8 source is negative and simulation/live evidence is incomplete |

## Layer evidence

Each `proven` or `negative` R1-R8 layer above has one scope-bound record below.
R9 has no direct evidence: the verifier derives it from R1-R8. A source anchor
is resolved against `candidate_commit`; a row-wide narrative citation cannot
satisfy a layer.

| Rule | Host | Layer | State | Authority kind | Artifact | Observed | Source |
|---|---|---|---|---|---|---|---|
| R1 | claude | Implementation | negative | source | deterministic pre-narrow and compatibility selection branch | 2026-08-12 | `agency_runtime/adapters/hooks.py:990-1019` |
| R1 | codex | Implementation | negative | source | deterministic pre-narrow and compatibility selection branch | 2026-08-12 | `agency_runtime/adapters/hooks.py:990-1019` |
| R1 | zcode | Implementation | negative | source | deterministic pre-narrow and compatibility selection branch | 2026-08-12 | `agency_runtime/adapters/hooks.py:990-1019` |
| R4 | codex | Implementation | negative | source | current JIT task-channel implementation lacks an integrity-bound Codex context carrier | 2026-08-12 | `agency_runtime/adapters/hooks.py:957-1072` |
| R4 | zcode | Implementation | proven | source | host-started child JIT multi-card delivery implementation | 2026-08-12 | `agency_runtime/adapters/hooks.py:932-1072` |
| R4 | zcode | Simulation | proven | test | `test_a_host_initiated_child_is_handed_cards_plural[zcode]` | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:287-310` |
| R6 | claude | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | codex | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | zcode | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | hermes | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | openclaw | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R8 | claude | Implementation | proven | source | fail-open unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:932-951` |
| R8 | codex | Implementation | proven | source | fail-open unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:932-951` |
| R8 | zcode | Implementation | proven | source | fail-open unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:932-951` |
| R8 | codex | Simulation | proven | test | unavailable preflight publishes the host prompt | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` |
| R8 | zcode | Simulation | proven | test | unavailable preflight publishes the host prompt | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` |
| R8 | hermes | Implementation | negative | source | bridge exception replaces output with a blocking response | 2026-08-12 | `agency_runtime/adapters/hermes/bridge.py:269-318` |
| R8 | openclaw | Implementation | negative | source | bridge failure cancels host output | 2026-08-12 | `agency_runtime/adapters/openclaw/node_bridge.py:790-903` |

## Cross-cutting completion gates

- **Inference authority:** negative until AR-255 removes deterministic JIT
  selection and joins the exact inference decision to delivered card hashes.
- **Automatic contractor promotion:** implementation and simulation exist, but
  installed and live proof is unproven on all five hosts. AR-252 remains P0 and
  blocks AR-119.
- **Latency:** negative against the unchanged 15,000 ms cold gate. The latest
  200-decision baseline reports computed p50 88.3 s and p95 195.9 s; AR-253
  owns an exact-candidate remeasurement and repair.
- **Matched value:** unproven. AR-125 must produce a valid blinded Agency-on/off
  corpus; malformed and timed-out arms are invalid rather than losses.

## Update contract

Change a cell only from evidence that satisfies its named authority. Record an
exact candidate identity, source or host artifact, observation date, and known
limitation. A host becoming unavailable cannot improve a cell, and no cell may
be marked `not-applicable` while the host remains supported. Any semantic
change to the founding rules requires owner confirmation and a new canonical
vision digest before this matrix can be updated.
