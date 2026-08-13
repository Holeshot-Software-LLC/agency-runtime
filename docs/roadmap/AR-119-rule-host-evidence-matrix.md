---
title: "AR-119 rule and host evidence matrix"
status: active
category: roadmap
created: 2026-08-12
updated: 2026-08-13
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
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
supersedes:
  - docs/roadmap/AR-119-acceptance-evidence.md
superseded_by: null
type: roadmap
ar119_authority: completion-evidence
vision_block_sha256: 8d81be4301ea76b3820b792f54842916321a9557b4a13fce58d6688abe962e50
candidate_commit: 967b0a2c7936ed34206a07905302be5967d2f685
evidence_cutoff: 2026-08-13
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

Candidate `967b0a2c` proves Rule 7 at source and simulation on the four hosts
that have adapter classes. The mechanism was already present and simply never
observed: closing a turn expires its cards, and the next turn is told which
expired, because a card appended to the caller's context cannot be retracted.
Observing it first required repairing the host-parity suite, which read the
operator's durable master switch and so reported evidence mismatches whenever
Agency was switched off; two of its four cases had been failing for that reason
alone and pass again now. ZCode is deliberately not claimed: it has no adapter
class, reaches Agency through the shared hooks boundary, and the suite sweeps
the generic adapter instead, so its Rule 7 simulation stays unproven rather than
assumed.

Candidate `e80cb40c` repairs the only two `negative` cells. Hermes and OpenClaw
previously withheld a completed turn whenever Agency itself could not run, which
Rule 8 forbids and which `THREAT_MODEL.md` already described as the opposite of
the intended contract. Both hosts now return the host's own output when Agency
is blind, while an evaluated negative still withholds, envelope integrity still
denies, and stale evidence still cannot terminalize a turn. It changes only the
two host bridges, the generated Hermes payload, and their tests, so every other
row's source anchor is unchanged from `211563c7`. Its decision-conformance
evaluator exited zero with a baseline of 201,500 ms, 151/151 mutations killed,
zero survived or invalid, and `source_unchanged=true`; the curated mutation that
disables the evaluated-negative branch is still killed, so the blocking path
this repair deliberately preserved remains observable. No cell is `negative`.

Candidate `211563c7` retains AR-255 native-child inference authority, Claude's
in-lifetime collector, and the exact CLI `0.147.0` TUI/exec profiles. Its sealed
v3 Codex attestor adds a separate Desktop `0.147.0-alpha.6.6` profile chosen only
from exact transcript metadata. Desktop accepts root and 13 observed depth-one/
depth-two V2 child tuple families, rejects eight unobserved cross-products and
disabled guardians, and seals canonical ownership, both depth-two edges, direct
start/output evidence, copied history, files, profile, and currentness. All
external ancestry remains bounded to 64 MiB, and final validation still rolls
the route back transactionally. This is source and simulation evidence, not an
installed or live host artifact. Every Installed and Live layer therefore
remains unproven.

The current Sol/TUI spawn and all 65 observed Desktop calls omitted the explicit
empty marker and delivered encrypted content. The inherited CLI census remains
11/11. A content-safe probe of the new Desktop profile resolved all 52 authentic
V2 chains (47 depth one, 5 depth two), with a maximum 32,650,955 external bytes
and 2.765 seconds. Focused provenance/hook verification passed 288/288, the
focused-plus-anchor gate passed 289/289, and the named fast spine passed 673 with
6 skips. The scoped Desktop baseline passed and killed 20/20 mutations with
zero survived or invalid and `source_unchanged=true`; an independent run
reproduced those results and reported no finding at any severity. Codex R4
Implementation and Simulation are therefore proven. The expanded
decision-conformance evaluator first failed for `211563c7` with two survivors
that a masked identity test could not observe; after the AR-257 repair it exited
zero with a baseline passing in 200,798 ms, 151/151 mutations killed, zero
survived or invalid, and `source_unchanged=true`. The earlier 131/131 result
remains candidate-`45b21cdc` history. Its dashboard UI suite passed
134/134, routing passed every threshold, and Ruff lint/format passed. Exec depth-
two/deeper remains unsupported, and no Installed or Live layer advances.

## Canonical matrix

| Rule | Host | State | Implementation | Simulation | Installed | Live | Proof authority | Artifact | Observed | Source | Limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | claude | unproven | proven | proven | unproven | unproven | Inference receipt joined to exact delivered card hashes | complete-universe inference team and exact plaintext HookBridge forwarding | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` | Implementation and simulation preserve the exact inference team; no exact-candidate installed/live join exists |
| R1 | codex | unproven | proven | proven | unproven | unproven | Inference receipt joined to exact delivered card hashes | marked calls use the existing exact inference team; unmarked calls remain unstaffed | 2026-08-13 | `tests/test_codex_plaintext_hook.py` | Synthetic delivery proves inference authority, not installed/live host receipt |
| R1 | zcode | unproven | proven | proven | unproven | unproven | Inference receipt joined to exact delivered card hashes | exact inference team reaches the plaintext host boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` | No exact-candidate installed/live join exists |
| R1 | hermes | unproven | proven | proven | unproven | unproven | Inference receipt joined to exact delivered card hashes | shared native-child adapter forwards one exact inference result | 2026-08-12 | `tests/test_native_child_adapter_staffing.py:39-95` | Shared adapter simulation is not installed Hermes bridge or host proof |
| R1 | openclaw | unproven | proven | proven | unproven | unproven | Inference receipt joined to exact delivered card hashes | shared native-child adapter forwards one exact inference result | 2026-08-12 | `tests/test_native_child_adapter_staffing.py:39-95` | Shared adapter simulation is not installed OpenClaw bridge or host proof |
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
| R4 | claude | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | in-lifetime SafeClaude collector with real HookBridge lifecycle | 2026-08-12 | `tests/test_host_canary.py:805-1055` | Test-managed install and fake process runner are simulation only; prior-candidate live artifacts do not green this candidate |
| R4 | codex | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | reviewed sealed v3 exact CLI `0.147.0` and Desktop `0.147.0-alpha.6.6` profiles | 2026-08-13 | `agency_runtime/core/codex_spawn_provenance.py`, `tests/test_codex_spawn_provenance.py` | Source/simulation cover the CLI 11/11 TUI census and Desktop 52/52 V2 census; exec depth-two/deeper and exact-candidate host artifacts remain open |
| R4 | zcode | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | exact inference team reaches the ZCode child boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` | Simulation exists but no exact-candidate native child artifact |
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
| R7 | claude | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:213-283` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | codex | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:213-283` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | zcode | unproven | proven | unproven | unproven | unproven | Same identity observed in one turn and absent from the next turn | shared turn-scoped expiry only; no zcode-specific observation | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` | ZCode has no adapter class and is exercised through the shared hooks boundary, so the parity eval sweeps the generic adapter instead and never observes zcode |
| R7 | hermes | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:213-283` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | openclaw | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:213-283` | Deterministic eval evidence only; no installed or live host artifact |
| R8 | claude | unproven | proven | unproven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | no Claude-scoped prompt-preflight simulation | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` | Implementation fails open, but the cited prompt-preflight test covers only Codex and ZCode and no native publication proof exists |
| R8 | codex | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[codex]` | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` | Contract output cannot prove native host publication |
| R8 | zcode | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[zcode]` | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` | No live host publication artifact |
| R8 | hermes | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | Agency-blind paths return the host draft unchanged while an evaluated rejection still replaces it | 2026-08-13 | `agency_runtime/adapters/hermes/bridge.py:269-322` | Contract output cannot prove native host publication |
| R8 | openclaw | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | Agency-blind gates allow the turn while envelope integrity and evaluated negatives still deny | 2026-08-13 | `agency_runtime/adapters/openclaw/node_bridge.py:798-947` | Contract output cannot prove native host publication |
| R9 | claude | unproven | unproven | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate 211563c7 | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Rule-1 source and simulation are repaired, but multiple rules and every installed/live layer remain unproven |
| R9 | codex | unproven | unproven | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate 211563c7 | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Rule 4 source/simulation are proven, but other rules and installed/live parity remain unproven |
| R9 | zcode | unproven | unproven | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate 211563c7 | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Rule-1 source and simulation are repaired, but missing rule and live evidence prevents parity |
| R9 | hermes | unproven | unproven | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate e80cb40c | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | The Rule 8 negative is repaired, but most rules and every installed/live layer remain unproven |
| R9 | openclaw | unproven | unproven | unproven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | this matrix at candidate e80cb40c | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | The Rule 8 negative is repaired, but most rules and every installed/live layer remain unproven |

## Layer evidence

Each `proven` or `negative` R1-R8 layer above has one scope-bound record below.
R9 has no direct evidence: the verifier derives it from R1-R8. A source anchor
is resolved against `candidate_commit`; a row-wide narrative citation cannot
satisfy a layer.

| Rule | Host | Layer | State | Authority kind | Artifact | Observed | Source |
|---|---|---|---|---|---|---|---|
| R1 | claude | Implementation | proven | source | complete-universe inference selection with exact whole-team validation | 2026-08-12 | `agency_runtime/core/native_child_staffing.py:845-1000` |
| R1 | claude | Simulation | proven | test | exact inference team reaches the Claude plaintext child boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` |
| R1 | codex | Implementation | proven | source | only an exact host-marked call enters inference-owned staffing | 2026-08-13 | `agency_runtime/adapters/hooks.py:1258-1310` |
| R1 | codex | Simulation | proven | test | marked calls preserve staffing and unmarked calls remain unstaffed | 2026-08-13 | `tests/test_codex_plaintext_hook.py:94-338` |
| R1 | zcode | Implementation | proven | source | exact whole inference team reaches the plaintext child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:1088-1256` |
| R1 | zcode | Simulation | proven | test | exact inference team reaches the ZCode plaintext child boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` |
| R1 | hermes | Implementation | proven | source | shared native-child adapter uses only the inference service result | 2026-08-12 | `agency_runtime/adapters/base.py:779-852` |
| R1 | hermes | Simulation | proven | test | shared adapter preserves the exact Hermes inference result | 2026-08-12 | `tests/test_native_child_adapter_staffing.py:39-95` |
| R1 | openclaw | Implementation | proven | source | shared native-child adapter uses only the inference service result | 2026-08-12 | `agency_runtime/adapters/base.py:779-852` |
| R1 | openclaw | Simulation | proven | test | shared adapter preserves the exact OpenClaw inference result | 2026-08-12 | `tests/test_native_child_adapter_staffing.py:39-95` |
| R4 | claude | Implementation | proven | source | sealed in-lifetime collector binds one current host artifact to one invocation | 2026-08-12 | `agency_runtime/core/child_delivery_evidence.py:1484-1665` |
| R4 | claude | Simulation | proven | test | SafeClaude collects a real-shape HookBridge artifact before profile cleanup | 2026-08-12 | `tests/test_host_canary.py:805-1055` |
| R4 | codex | Implementation | proven | source | sealed v3 attestation preserves exact CLI profiles and adds the atomic 13-family Desktop profile with exact causal/output/currentness binding | 2026-08-13 | `agency_runtime/core/codex_spawn_provenance.py:245-3525` |
| R4 | codex | Simulation | proven | test | exact CLI and Desktop lineage, causal, profile, currentness, bound, and replay fixtures pass for every supported variant | 2026-08-13 | `tests/test_codex_spawn_provenance.py:776-1835` |
| R4 | zcode | Implementation | proven | source | host-started plaintext child receives the exact inference team | 2026-08-12 | `agency_runtime/adapters/hooks.py:1088-1256` |
| R4 | zcode | Simulation | proven | test | exact inference team reaches the ZCode child boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` |
| R6 | claude | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | codex | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | zcode | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | hermes | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | openclaw | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R8 | claude | Implementation | proven | source | fail-open unavailable prompt and unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` |
| R8 | codex | Implementation | proven | source | fail-open unavailable prompt and unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` |
| R8 | zcode | Implementation | proven | source | fail-open unavailable prompt and unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` |
| R8 | codex | Simulation | proven | test | unavailable preflight publishes the host prompt | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` |
| R8 | zcode | Simulation | proven | test | unavailable preflight publishes the host prompt | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` |
| R7 | claude | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | claude | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:31-57` |
| R7 | codex | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | codex | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:31-57` |
| R7 | zcode | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | hermes | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | hermes | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:31-57` |
| R7 | openclaw | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | openclaw | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:31-57` |
| R8 | hermes | Implementation | proven | source | an unavailable Agency path returns the host draft unchanged | 2026-08-13 | `agency_runtime/adapters/hermes/bridge.py:269-322` |
| R8 | hermes | Simulation | proven | test | a raising finalizer returns the draft unchanged and does not terminalize the turn | 2026-08-13 | `tests/test_completion_policy_boundary.py:241-273` |
| R8 | openclaw | Implementation | proven | source | blind soft control, correlation, evidence, decision, and commit paths allow the turn | 2026-08-13 | `agency_runtime/adapters/openclaw/node_bridge.py:798-947` |
| R8 | openclaw | Simulation | proven | test | unreadable evidence and unrecoverable correlation allow, while a broken envelope still denies | 2026-08-13 | `tests/test_owned_adapter_surface_coverage_final.py:805-888` |

## Cross-cutting completion gates

- **Inference authority:** implementation and simulation are proven on all five
  host adapters at `211563c7`; installed and live card-hash joins remain
  unproven everywhere.
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
