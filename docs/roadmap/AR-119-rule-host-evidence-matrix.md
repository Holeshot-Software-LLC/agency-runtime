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
candidate_commit: a25ec35007031cf352a19fc2d8d37f1f5bc55de1
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

Candidate `a25ec350` carries the same evidence as `be18a9b0` and advances the
baseline by two test-only commits, which retire assertions that the delegation
prune and the resident-manager kernel split had orphaned. No anchored file
moved, so every citation below resolves unchanged. Its decision-conformance
evaluator exited zero with a baseline passing in 218,955 ms, **151/151
mutations killed, zero survived and zero invalid**, and `source_unchanged=true`.

That run also settles a scare worth recording. An earlier attempt at this gate
reported `passed=false` with 84 killed, zero survived, and 67 `invalid_test_result`
entries carrying exit code 106 and empty `failed_nodes` -- a runner that could
not launch, not a mutation that escaped. The working tree it ran in lost its
`.venv/pyvenv.cfg` and its git worktree registration during that run. The cause
was a second job started against the same tree while the evaluator held it, not
the evaluator: run alone, it completed cleanly and left the tree intact. Do not
run anything against a tree while this evaluator is running against it; the
failure mode is a destroyed working tree, not a slow suite.

Candidate `967b0a2c` proves Rule 7 at source and simulation on the four hosts
that have adapter classes. The mechanism was already present and simply never
observed: closing a turn expires its cards, and the next turn is told which
expired, because a card appended to the caller's context cannot be retracted.
Observing it first required repairing the host-parity suite, which read the
operator's durable master switch and so reported evidence mismatches whenever
Agency was switched off; two of its four cases had been failing for that reason
alone and pass again now. ZCode was deliberately not claimed there: it has no
adapter class, reaches Agency through the shared hooks boundary, and the suite
swept the generic adapter instead, so its Rule 7 simulation stayed unproven
rather than assumed. Its decision-conformance evaluator exited zero with a
baseline of 211,811 ms, 151/151 mutations killed, zero survived or invalid, and
`source_unchanged=true`.

Candidate `be18a9b0` completes **simulation parity on all five supported
hosts**: every rule R1 through R8 is proven at that layer everywhere, so Rule 9
derives as proven in simulation for each of them. It closes the last three gaps,
and both gaps were the same kind -- a rule proven somewhere else and assumed
here.

Claude had no Rule 8 simulation: the fail-open prompt-preflight case is entirely
host-generic, yet it ran on Codex and ZCode only, so the host whose boundary
that code was written for was the one host it never ran on. Hermes and OpenClaw
had no Rule 4 simulation of their own: the existing evidence was a synthetic
adapter subclass calling `build_preflight_context` directly, which cannot speak
for the shipped plugin classes or for the bridges that actually receive a child
launch -- the same substitution the ZCode Rule 7 work had to undo. Both now
drive each bridge's real `handle()` entry with its real adapter and its own
payload key names, and assert the exact plural ordered team reaches the child,
bound to the host's own parent and launch identities, before the child model
runs. A third case pins the other half: a child the host cannot fully correlate
is left unstaffed rather than guessed at, so the suite cannot pass on a path
that staffs anything it is told about. The staffing service is stubbed at the
same boundary the Claude and ZCode Rule 4 rows stub it, so the claim is like for
like.

No cell is proven, and none can become proven from here. Rule 5 Implementation
and every Installed and Live layer on every host remain open, and those need a
host artifact bound to this exact candidate rather than any further source work.

Candidate `d4b64c35` proves Rule 5 in simulation on all five hosts, which is
what first completed that layer on codex and zcode.

Rule 5's negative half is an absence, so it is measured rather than read off the
source. Every seam Agency has for creating a process -- the owned-process policy
and `subprocess` itself, so a path around the policy would still be seen -- is
replaced with a detector for the duration of a whole turn, on a request that
openly asks to be split up and handed out. Nothing reaches a detector. A
positive control proves the detectors fire, so a clean run means Agency started
nothing rather than that the guard was never wired, and non-vacuity is the
turn's own evidence: the request is planned, staffed, and dealt a card, so the
absence holds at full depth. The positive half is covered too -- when the host
makes its own delegation and reports it afterwards, Agency records it and still
starts nothing.

The Implementation layer is deliberately left unproven, and the reason is worth
recording so it is not rediscovered. A static call-graph absence proof does not
hold as the row's proof authority describes it: the turn-path import closure
legitimately contains sixteen process-capable modules, because Agency's own
inference reaches CLI providers through the same hardened bounded-process
primitive the installer, the host canary, and the hook-trust inspector use.
Proving Rule 5 at source therefore needs a formulation that separates starting
an agent from running a tool, not a reachability sweep for `subprocess`.

Candidate `75663ed0` proves Rule 6 in simulation on all five hosts. The hiring
ladder itself was never in doubt and already had thorough host-neutral coverage;
what it lacked was any evidence of running inside a turn on a host boundary,
which is what Rule 9 asks of every rule. Each case now drives the host's own
entry point with a request the roster cannot cover and follows the whole ladder:
inference proves the gap, an independent critic and a security review pass on it,
the contractor is filed under `origin='agency'` in the contractor lane, and it is
dealt into the very turn whose gap created it. A second turn then finds it
already in the pool and hires nobody, because "file it in the pool for next
time" is the half of the rule a single-turn assertion cannot reach. Two seams
were required and are worth recording: `hire_contractor_for_gap` binds the real
invoker as a default argument at import time, so patching the inference module
alone leaves hiring calling a live provider and failing as a silent abstention,
and `workforce.provider` must be configured or hiring declines the same quiet
way. Installed and Live still require a native same-turn hiring artifact.

Candidate `42c1354b` gives Rules 2 and 3 their first evidence of any kind. The
product's central claim -- "load into the caller, don't spawn", and more than
one card when the job needs them -- held ten `unproven` cells and no artifact,
though nothing was missing from the runtime: preflight already builds the
capsule and every host already hands it to the caller's own turn. What was
missing was anyone watching it happen. Each case now follows the real path an
ordinary user turn takes on that host -- the `UserPromptSubmit` boundary for
claude, codex, and zcode, the request-scoped adapter entry point for hermes and
openclaw -- with only the choice stubbed, since inference alone chooses. The
cards are real roster specialists and their instruction bodies are read back out
of the Store, so a passing test cannot merely agree with itself. Rule 3 needed
its own two-unit stub: one work unit takes exactly one specialist, so a second
card exists only when the turn holds a second unit of work. Both rules are
therefore proven at Implementation and Simulation on all five hosts. The
Installed and Live layers are untouched and still require a native
primary-caller artifact.

Candidate `cb6808fe` closes that gap without inventing a zcode adapter. The
construction the hooks boundary performs for a host without its own adapter
class — build the Claude adapter, rebind the host identity so runtime control
reads the zcode row and every receipt is attributed to zcode — is now a single
named function that both the boundary and the parity sweep call, so the sweep
observes the same object zcode really runs on and cannot drift from it. All
three adapter cases sweep six entries instead of five, and the sweep now checks
the host it built against the host it claims: a builder that quietly returned a
neighbour fails rather than reporting parity that was never observed. Rule 7 is
therefore proven at source and simulation on all five supported hosts, and
`generic` remains what it always was — a stand-in for any host with no
dedicated adapter, not a sixth product host. This is deterministic evaluation
evidence; no Installed or Live layer moves.

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
| R2 | claude | unproven | proven | proven | unproven | unproven | Native primary-caller artifact containing selected cards before first caller speech | the chosen card's own instruction body reaches the caller's turn, the turn records it, and no child exists that could have received it instead | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R2 | codex | unproven | proven | proven | unproven | unproven | Native primary-caller artifact containing selected cards before first caller speech | the chosen card's own instruction body reaches the caller's turn, the turn records it, and no child exists that could have received it instead | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R2 | zcode | unproven | proven | proven | unproven | unproven | Native primary-caller artifact containing selected cards before first caller speech | the chosen card's own instruction body reaches the caller's turn, the turn records it, and no child exists that could have received it instead | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R2 | hermes | unproven | proven | proven | unproven | unproven | Native host artifact containing cards before first caller speech | the chosen card's own instruction body reaches the caller's turn, the turn records it, and no child exists that could have received it instead | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R2 | openclaw | unproven | proven | proven | unproven | unproven | Native host artifact containing cards before first caller speech | the chosen card's own instruction body reaches the caller's turn, the turn records it, and no child exists that could have received it instead | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R3 | claude | unproven | proven | proven | unproven | unproven | Native primary-caller artifact with multiple compatible card hashes before first caller speech | two units of work in one turn each keep their own card, and both instruction bodies arrive whole in the caller's turn | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R3 | codex | unproven | proven | proven | unproven | unproven | Native primary-caller artifact with multiple compatible card hashes before first caller speech | two units of work in one turn each keep their own card, and both instruction bodies arrive whole in the caller's turn | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R3 | zcode | unproven | proven | proven | unproven | unproven | Native primary-caller artifact with multiple compatible card hashes before first caller speech | two units of work in one turn each keep their own card, and both instruction bodies arrive whole in the caller's turn | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R3 | hermes | unproven | proven | proven | unproven | unproven | Native host artifact with multiple compatible card hashes before speech | two units of work in one turn each keep their own card, and both instruction bodies arrive whole in the caller's turn | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R3 | openclaw | unproven | proven | proven | unproven | unproven | Native host artifact with multiple compatible card hashes before speech | two units of work in one turn each keep their own card, and both instruction bodies arrive whole in the caller's turn | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` | Deterministic delivery evidence with inference stubbed; no installed or live host artifact |
| R4 | claude | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | in-lifetime SafeClaude collector with real HookBridge lifecycle | 2026-08-12 | `tests/test_host_canary.py:805-1055` | Test-managed install and fake process runner are simulation only; prior-candidate live artifacts do not green this candidate |
| R4 | codex | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | reviewed sealed v3 exact CLI `0.147.0` and Desktop `0.147.0-alpha.6.6` profiles | 2026-08-13 | `agency_runtime/core/codex_spawn_provenance.py`, `tests/test_codex_spawn_provenance.py` | Source/simulation cover the CLI 11/11 TUI census and Desktop 52/52 V2 census; exec depth-two/deeper and exact-candidate host artifacts remain open |
| R4 | zcode | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | exact inference team reaches the ZCode child boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` | Simulation exists but no exact-candidate native child artifact |
| R4 | hermes | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | the exact plural ordered team reaches a host-spawned child through each bridge's real handle() entry with its real adapter, bound to the host's own parent and launch identities; a child the host cannot fully correlate is left unstaffed | 2026-08-13 | `tests/test_native_child_host_boundary_staffing.py:119-217` | Host-boundary simulation with the staffing service stubbed at the same boundary the Claude and ZCode Rule 4 rows stub it; the host is unavailable on the evidence machine, so no installed or live native child artifact exists |
| R4 | openclaw | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | the exact plural ordered team reaches a host-spawned child through each bridge's real handle() entry with its real adapter, bound to the host's own parent and launch identities; a child the host cannot fully correlate is left unstaffed | 2026-08-13 | `tests/test_native_child_host_boundary_staffing.py:119-217` | Host-boundary simulation with the staffing service stubbed at the same boundary the Claude and ZCode Rule 4 rows stub it; the host is unavailable on the evidence machine, so no installed or live native child artifact exists |
| R5 | claude | unproven | unproven | proven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | a whole turn on a request that asks to be split up starts no process at any seam, while being planned, staffed, and dealt a card; a positive control proves the detector fires; and the host's own delegation is recorded without Agency starting it | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` | Simulation only. A static call-graph absence proof does not hold as written: the turn-path import closure legitimately contains 16 process-capable modules, because inference reaches CLI providers through the same bounded-process primitive the installer and canary use. The Implementation layer needs a formulation that separates starting an agent from running a tool, and no native spawn-origin artifact is bound to this candidate |
| R5 | codex | unproven | unproven | proven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | a whole turn on a request that asks to be split up starts no process at any seam, while being planned, staffed, and dealt a card; a positive control proves the detector fires; and the host's own delegation is recorded without Agency starting it | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` | Simulation only. A static call-graph absence proof does not hold as written: the turn-path import closure legitimately contains 16 process-capable modules, because inference reaches CLI providers through the same bounded-process primitive the installer and canary use. The Implementation layer needs a formulation that separates starting an agent from running a tool, and no native spawn-origin artifact is bound to this candidate |
| R5 | zcode | unproven | unproven | proven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | a whole turn on a request that asks to be split up starts no process at any seam, while being planned, staffed, and dealt a card; a positive control proves the detector fires; and the host's own delegation is recorded without Agency starting it | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` | Simulation only. A static call-graph absence proof does not hold as written: the turn-path import closure legitimately contains 16 process-capable modules, because inference reaches CLI providers through the same bounded-process primitive the installer and canary use. The Implementation layer needs a formulation that separates starting an agent from running a tool, and no native spawn-origin artifact is bound to this candidate |
| R5 | hermes | unproven | unproven | proven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | a whole turn on a request that asks to be split up starts no process at any seam, while being planned, staffed, and dealt a card; a positive control proves the detector fires; and the host's own delegation is recorded without Agency starting it | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` | Simulation only. A static call-graph absence proof does not hold as written: the turn-path import closure legitimately contains 16 process-capable modules, because inference reaches CLI providers through the same bounded-process primitive the installer and canary use. The Implementation layer needs a formulation that separates starting an agent from running a tool, and no native spawn-origin artifact is bound to this candidate |
| R5 | openclaw | unproven | unproven | proven | unproven | unproven | Source call-graph absence proof plus native spawn-origin artifact | a whole turn on a request that asks to be split up starts no process at any seam, while being planned, staffed, and dealt a card; a positive control proves the detector fires; and the host's own delegation is recorded without Agency starting it | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` | Simulation only. A static call-graph absence proof does not hold as written: the turn-path import closure legitimately contains 16 process-capable modules, because inference reaches CLI providers through the same bounded-process primitive the installer and canary use. The Implementation layer needs a formulation that separates starting an agent from running a tool, and no native spawn-origin artifact is bound to this candidate |
| R6 | claude | unproven | proven | proven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | one uncovered turn proves the gap, passes an independent critic and a security review, files the contractor under origin=agency, and is dealt the new card in that same turn; the next turn reuses it and hires nobody | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-333` | Deterministic ladder evidence with inference stubbed; no installed or live host artifact |
| R6 | codex | unproven | proven | proven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | one uncovered turn proves the gap, passes an independent critic and a security review, files the contractor under origin=agency, and is dealt the new card in that same turn; the next turn reuses it and hires nobody | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-333` | Deterministic ladder evidence with inference stubbed; no installed or live host artifact |
| R6 | zcode | unproven | proven | proven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | one uncovered turn proves the gap, passes an independent critic and a security review, files the contractor under origin=agency, and is dealt the new card in that same turn; the next turn reuses it and hires nobody | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-333` | Deterministic ladder evidence with inference stubbed; no installed or live host artifact |
| R6 | hermes | unproven | proven | proven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | one uncovered turn proves the gap, passes an independent critic and a security review, files the contractor under origin=agency, and is dealt the new card in that same turn; the next turn reuses it and hires nobody | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-333` | Deterministic ladder evidence with inference stubbed; no installed or live host artifact |
| R6 | openclaw | unproven | proven | proven | unproven | unproven | Inference hiring receipt independent critic receipt immutable identity and host-backed use | one uncovered turn proves the gap, passes an independent critic and a security review, files the contractor under origin=agency, and is dealt the new card in that same turn; the next turn reuses it and hires nobody | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-333` | Deterministic ladder evidence with inference stubbed; no installed or live host artifact |
| R7 | claude | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:231-293` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | codex | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:231-293` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | zcode | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case on the adapter the hooks boundary itself builds for zcode: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:231-293` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | hermes | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:231-293` | Deterministic eval evidence only; no installed or live host artifact |
| R7 | openclaw | unproven | proven | proven | unproven | unproven | Same identity observed in one turn and absent from the next turn | two-turn parity case: the card is held in its own turn, absent from the next, and its expiry is stated there | 2026-08-13 | `agency_runtime/core/evals/host_parity.py:231-293` | Deterministic eval evidence only; no installed or live host artifact |
| R8 | claude | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[claude]`: a bridge fault publishes the prompt, loudly, without costing the turn | 2026-08-13 | `tests/test_host_hooks.py:2345-2406` | No live host publication artifact |
| R8 | codex | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[codex]` | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` | Contract output cannot prove native host publication |
| R8 | zcode | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | `test_hook_boundary_publishes_prompt_when_preflight_integrity_fails[zcode]` | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` | No live host publication artifact |
| R8 | hermes | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | Agency-blind paths return the host draft unchanged while an evaluated rejection still replaces it | 2026-08-13 | `agency_runtime/adapters/hermes/bridge.py:269-322` | Contract output cannot prove native host publication |
| R8 | openclaw | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | Agency-blind gates allow the turn while envelope integrity and evaluated negatives still deny | 2026-08-13 | `agency_runtime/adapters/openclaw/node_bridge.py:798-947` | Contract output cannot prove native host publication |
| R9 | claude | unproven | unproven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the simulation layer on claude | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Simulation parity is complete for this host, but Rule 5 Implementation and every Installed and Live layer remain unproven, so parity itself is not proven |
| R9 | codex | unproven | unproven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the simulation layer on codex | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Simulation parity is complete for this host, but Rule 5 Implementation and every Installed and Live layer remain unproven, so parity itself is not proven |
| R9 | zcode | unproven | unproven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the simulation layer on zcode | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Simulation parity is complete for this host, but Rule 5 Implementation and every Installed and Live layer remain unproven, so parity itself is not proven |
| R9 | hermes | unproven | unproven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the simulation layer on hermes | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Simulation parity is complete for this host, but Rule 5 Implementation and every Installed and Live layer remain unproven, so parity itself is not proven |
| R9 | openclaw | unproven | unproven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the simulation layer on openclaw | 2026-08-13 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Simulation parity is complete for this host, but Rule 5 Implementation and every Installed and Live layer remain unproven, so parity itself is not proven |

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
| R8 | claude | Simulation | proven | test | a bridge fault publishes the prompt without costing the turn | 2026-08-13 | `tests/test_host_hooks.py:2345-2406` |
| R4 | hermes | Implementation | proven | source | the shared native-child boundary forwards one exact inference team to a host-started child | 2026-08-13 | `agency_runtime/adapters/base.py:832-884` |
| R4 | hermes | Simulation | proven | test | the exact plural team reaches a host-spawned child at that host's real bridge entry | 2026-08-13 | `tests/test_native_child_host_boundary_staffing.py:119-217` |
| R4 | openclaw | Implementation | proven | source | the shared native-child boundary forwards one exact inference team to a host-started child | 2026-08-13 | `agency_runtime/adapters/base.py:832-884` |
| R4 | openclaw | Simulation | proven | test | the exact plural team reaches a host-spawned child at that host's real bridge entry | 2026-08-13 | `tests/test_native_child_host_boundary_staffing.py:119-217` |
| R5 | claude | Simulation | proven | test | a complete turn starts no process at any seam, and the host's own delegation is recorded rather than started | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` |
| R5 | codex | Simulation | proven | test | a complete turn starts no process at any seam, and the host's own delegation is recorded rather than started | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` |
| R5 | zcode | Simulation | proven | test | a complete turn starts no process at any seam, and the host's own delegation is recorded rather than started | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` |
| R5 | hermes | Simulation | proven | test | a complete turn starts no process at any seam, and the host's own delegation is recorded rather than started | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` |
| R5 | openclaw | Simulation | proven | test | a complete turn starts no process at any seam, and the host's own delegation is recorded rather than started | 2026-08-13 | `tests/test_spawn_origin_absence.py:144-228` |
| R6 | claude | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | codex | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | zcode | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | hermes | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | openclaw | Implementation | proven | source | inference gap hiring, critic audit, enablement, and activation path | 2026-08-12 | `agency_runtime/core/workforce/hiring.py:1863-1940` |
| R6 | claude | Simulation | proven | test | an uncovered turn mints, interviews, and files a contractor, deals it that same turn, and the next turn reuses it without hiring again | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-363` |
| R6 | codex | Simulation | proven | test | an uncovered turn mints, interviews, and files a contractor, deals it that same turn, and the next turn reuses it without hiring again | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-363` |
| R6 | zcode | Simulation | proven | test | an uncovered turn mints, interviews, and files a contractor, deals it that same turn, and the next turn reuses it without hiring again | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-363` |
| R6 | hermes | Simulation | proven | test | an uncovered turn mints, interviews, and files a contractor, deals it that same turn, and the next turn reuses it without hiring again | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-363` |
| R6 | openclaw | Simulation | proven | test | an uncovered turn mints, interviews, and files a contractor, deals it that same turn, and the next turn reuses it without hiring again | 2026-08-13 | `tests/test_contractor_minting_host_parity.py:297-363` |
| R8 | claude | Implementation | proven | source | fail-open unavailable prompt and unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` |
| R8 | codex | Implementation | proven | source | fail-open unavailable prompt and unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` |
| R8 | zcode | Implementation | proven | source | fail-open unavailable prompt and unstaffed-child boundary | 2026-08-12 | `agency_runtime/adapters/hooks.py:257-293` |
| R8 | codex | Simulation | proven | test | unavailable preflight publishes the host prompt | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` |
| R8 | zcode | Simulation | proven | test | unavailable preflight publishes the host prompt | 2026-08-12 | `tests/test_host_hooks.py:2377-2428` |
| R2 | claude | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hooks.py:1728-1782` |
| R2 | claude | Simulation | proven | test | the caller's own turn context carries the chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` |
| R2 | codex | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hooks.py:1728-1782` |
| R2 | codex | Simulation | proven | test | the caller's own turn context carries the chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` |
| R2 | zcode | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hooks.py:1728-1782` |
| R2 | zcode | Simulation | proven | test | the caller's own turn context carries the chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` |
| R2 | hermes | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hermes/plugin.py:77-88` |
| R2 | hermes | Simulation | proven | test | the caller's own turn context carries the chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` |
| R2 | openclaw | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/openclaw/plugin.py:29-37` |
| R2 | openclaw | Simulation | proven | test | the caller's own turn context carries the chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:189-213` |
| R3 | claude | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hooks.py:1728-1782` |
| R3 | claude | Simulation | proven | test | the caller's own turn context carries every chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` |
| R3 | codex | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hooks.py:1728-1782` |
| R3 | codex | Simulation | proven | test | the caller's own turn context carries every chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` |
| R3 | zcode | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hooks.py:1728-1782` |
| R3 | zcode | Simulation | proven | test | the caller's own turn context carries every chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` |
| R3 | hermes | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/hermes/plugin.py:77-88` |
| R3 | hermes | Simulation | proven | test | the caller's own turn context carries every chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` |
| R3 | openclaw | Implementation | proven | source | the host hands preflight's context to the caller's own turn | 2026-08-13 | `agency_runtime/adapters/openclaw/plugin.py:29-37` |
| R3 | openclaw | Simulation | proven | test | the caller's own turn context carries every chosen card whole | 2026-08-13 | `tests/test_parent_caller_card_delivery.py:215-236` |
| R7 | claude | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | claude | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:34-51` |
| R7 | codex | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | codex | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:34-51` |
| R7 | zcode | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | zcode | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated, on the adapter the hooks boundary builds for zcode | 2026-08-13 | `tests/test_host_parity_eval.py:54-73` |
| R7 | hermes | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | hermes | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:34-51` |
| R7 | openclaw | Implementation | proven | source | closing a turn expires its cards and the next turn is told which expired | 2026-08-13 | `agency_runtime/core/store/evidence.py:1298-1340` |
| R7 | openclaw | Simulation | proven | test | a card held in one turn is absent from the next and its expiry is stated | 2026-08-13 | `tests/test_host_parity_eval.py:34-51` |
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
