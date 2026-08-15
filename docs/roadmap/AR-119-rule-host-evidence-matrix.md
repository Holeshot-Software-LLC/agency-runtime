---
title: "AR-119 rule and host evidence matrix"
status: active
category: roadmap
created: 2026-08-12
updated: 2026-08-14
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
candidate_commit: 9e29aabe70b4977669e79fdbc62f21daf17f6ea8
evidence_cutoff: 2026-08-14
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

Candidate `9e29aabe` advances `2f0758d9` by building the host-free half of the
automatic-promotion gate, described below. It moves no rule cell: the gate is
cross-cutting, and its evidence is source and simulation only. A later
same-candidate change makes the Rule 4 collector name the stage that refused it;
that moves no cell either, but it is what turned two silent canary failures into
the two located blockers recorded under R4 claude below.

Candidate `2f0758d9` advanced `e216670a` by repairing a platform parity gap that
sat underneath the Rule 4 host-artifact proof, described below, and by putting
every cited test file into CI for the first time.

Candidate `e216670a` advanced `a9d84a27` by proving Rule 5 at the source, which
closed the last ten Implementation slots and took both the Implementation and
Simulation layers to 45/45. The reasoning is recorded under R5 below.

Candidate `a9d84a27` advanced `9724820e` by one test-only repair, described
below under R4 claude. `tests/test_host_canary.py` appears nowhere in the
curated mutation set, so `9724820e`'s decision-conformance result carries
forward to this candidate unchanged.

Candidate `9724820e` advanced `a25ec350` by two repairs that a Windows-only
workstation could not have found, and one of them was a real defect this matrix
was already claiming did not exist.

The R8 openclaw row asserted that "envelope integrity and evaluated negatives
still deny" while the code no longer did either. `_exact_outbound_terminal_state`
filters on the presented digest, so it answers `""` both when a trace has no
terminal at all and when it holds one that committed a *different* response.
The Rule 8 fail-open in `e80cb40c` read that single answer as Agency being
blind, and the policy call on a closed turn returns `None`, which now allows.
The result was that a completed turn re-presented with a tampered outbound
payload was delivered, and a trace terminalized as `response_invalid` became
deliverable by simply sending different text: the exact-digest binding could be
bypassed by failing to satisfy it. Both cases pass on `origin/main` and failed
here, so the branch introduced them. `e0d88ee4` separates the two answers by
asking the store for the trace's terminal without a digest filter -- a readable
terminal that disagrees is a verdict, not a fault -- and an unreadable, silent,
or agreeing store still falls through to the fail-open path, so Rule 8 keeps its
intent. This is the failure mode the R8 rows are most exposed to: the layer was
read from source, and a source read cannot see a property the code has lost.
Neither case is in the curated mutation set, so CI was green across both.

`25bdec39` is test-only and platform-driven. Five codex spawn-provenance
mutations expressed file substitution as `unlink()` followed by rewriting the
same bytes, which is an identity no-op on Linux: freeing an inode returns it to
the allocator, which hands the same number back to the next create in that
directory, so `st_dev`, `st_ino` and `st_size` all match and the `(dev, ino)`
seal reads the substitute as current. NTFS does not recycle file IDs that
eagerly, so the mutations only ever bit on Windows. Substituting by rename
guarantees a distinct inode everywhere and is the shape a real replacement
takes. CI reported one of the five because the conformance baseline runs under
`-x`; the other four were measured directly on Linux.

**Rule 4 Live on claude is blocked in two independent places, and this
workstation can produce a readable host artifact.** That last point was an open
question and is now settled by measurement rather than inference.

`claude -p` under an isolated `CLAUDE_CONFIG_DIR` spawns sub-agents and writes
one transcript each at
`projects/<slug>/<session>/subagents/agent-<child>.jsonl` — exactly the shape
`_canonical_host_artifact_shape` accepts, with record zero carrying
`type=user`, `isSidechain=true`, `message.role=user`, `agentId`, `sessionId`,
and `timestamp`. Observed twice on 2026-08-14: once from a bare probe, once
from a live canary that produced four of them. **Artifact production is not the
gate.** (A probe artifact written into an ordinary scratch directory is still
refused: `assert_storage_parent_chain` passes and `storage_parent_is_trusted`
fails. That is the ACL guard doing its job, and the canary's private lease
satisfies it by construction.)

**RETRACTED, and the real cause is a schema bump made the same afternoon.**
This section previously blamed the disposable canary profile, then blamed
`claude -p` for running no hooks. Both are wrong. `-p` runs hooks fine — a
trivial hook supplied through `--settings` fired on all five of `SessionStart`,
`UserPromptSubmit`, `PreToolUse`, `SubagentStart` and `Stop` — and the profile
was never the variable either.

Wrapping Agency's own hook command in a logging shim produced the answer on the
first run, identically on every event:

~~~text
RuntimeError: Agency Runtime database schema is newer than this runtime (46 > 45)
agency hook claude: RuntimeError; host operation continues
~~~

The live store is at schema **46**, this checkout is at **46**, and the pinned
launcher every hook actually executes
(`runtime-sha256-3925824a…`) is at **45**. `Store.__init__` refuses a store
newer than its runtime, the hook boundary catches it and fails open, and the
host proceeds with no card. The `Stop` event fails *closed* instead, returning
`{"continue": false}` with "could not verify or persist the turn-scoped
evidence contract" — the same block that interrupted the operator's own session
on this machine.

**The evidence store stops dead at `2026-08-14T23:15:24Z`** — the newest row in
`runs`, `routing_decisions`, `preflight_failure_receipts` and
`specialists_loaded` all share that boundary. AR-252 raised `SCHEMA_VERSION`
from 45 to 46, and running checkout-local CLI commands (`agency host-canary`,
`agency eval …`) against the real `~/.agency-runtime/agency.db` migrated it past
what the installed launcher accepts.

**So every zero-marker observation below was measuring that break**, including
both canary runs and all nine host probes. None of them says anything about
`-p`, about profile configuration, or about card delivery. This is
[the two-sources-of-truth shape](#) exactly: one schema fact, a checkout and an
installed launcher reading different copies of it.

`agency doctor` reported `db_schema: Schema version: 46` with a green tick
throughout, because it only checked that a version row existed. It now compares
the stored version against the running runtime's `SCHEMA_VERSION` and fails
loudly when the store is ahead, which is the one condition that silently
disables every hook on the machine.

**Repaired the same evening under explicit owner authorization.**
`agency install --all` republished the runtime from this checkout: all three
hosts re-registered, and Claude and ZCode now run
`runtime-sha256-f0ff261120e2` at SCHEMA_VERSION 46. That launcher's own code
opens the live store without raising, a replayed `SessionStart` payload returns
exit 0 with silent stderr where every event previously printed
`RuntimeError; host operation continues`, and `doctor` reports schema 46
truthfully rather than incidentally. Codex hook trust is unverified against the
new digest and needs the owner's interactive TUI pass; it was not bypassed.

**The first canary on the repaired runtime records again, and fails somewhere
else entirely.** `counts` reads `runs: 1, preflight_failures: 1` where every
earlier run today read all zeros — the hook now opens the store, creates its run
row, attempts routing, and writes its own receipt. That receipt says
`workforce_inference_failed` / `inference_invalid`: the planner applied on
haiku, and the recruiter was rejected twice on sonnet with
`provider_response_contract_invalid`, with `eligibility_reason_codes` empty. So
the canary now dies at the **known nondeterministic recruiter stage** already
recorded above, not at a broken runtime, and
`host_child_collection_reason: delivery_marker_absent` is the honest
consequence: nothing was staffed, so no envelope could reach the child.

**Rule 4 Live for claude is exactly as unproven as it was this morning.** What
changed is only that the machine can record, and that its remaining failure is
one this matrix already names.

The original (wrong) reasoning follows, kept because the measurements are real
and the elimination sequence is worth not repeating.

The 2026-08-14 run at `f4039746` produced four well-formed child transcripts and
**not one carried any Agency marker** — not a partial or mixed-version envelope,
the literal `[AGENCY` absent from every launch text — alongside `routing: 0` at
the canary's own query hash, `runs: 0`, `specialists: 0`, all five header lines
missing, and `isolated_plugin` = `{load_requested: true, registered: null,
enabled: null}`. Six flag and profile combinations were then tested against a
fresh home: `--setting-sources=` (the canary's own), default sources, and
`--setting-sources=user`, each with `--plugin-dir`; then a home carrying
`enabledPlugins` and `extraKnownMarketplaces`, once without `--plugin-dir` and
once with; then one carrying the real profile's `installed_plugins.json` and
`known_marketplaces.json`. All six produced zero markers, which ruled out the
flag and ruled out enablement but still left the isolated profile itself as the
suspect.

Running `claude -p` against the *real* profile — the same `~/.claude` whose
hooks fire for an interactive session, plugin installed and enabled in
`settings.json`, no `CLAUDE_CONFIG_DIR` override — produced a sub-agent child
with **no Agency marker, no AGENCY text anywhere in the parent transcript, and
zero Agency rows of any kind**: `runs: 0`, `routing: 0`,
`preflight_failure_receipts: 0`. Repeated with every inherited `CLAUDE_CODE_*`
variable stripped — `CLAUDE_CODE_CHILD_SESSION` among them, a fair confound for
measurements taken from inside a Claude Code session — with the same result.
Nine runs, two profiles, zero markers.

That was read as "the hook never ran", and the reading was wrong: zero rows is
also what a hook that runs and fails open produces, and Agency fails open by
design. **Absence of Agency evidence cannot distinguish a hook that never
started from one that started and refused** — which is precisely why the next
probe used a hook with an observable side effect, and why the one after that
wrapped Agency's own command instead of inferring from its silence.

**The lesson, since it is the second time in one day the same shape bit:** an
unrun hook and a fail-open hook are indistinguishable from the outside. Prove
which one you have before theorising about why.

One measurement from that sequence survives the retraction, because it is a
census rather than an inference. Of 63 child artifacts under
`~/.claude/projects`, 9 carry a delivery marker: 3 v5 JIT (newest
`2026-08-11T19:33Z`) and 7 v1 exact-activation (newest `2026-08-07T14:30Z`), all
correlated. **`v6` count is zero — no inference-team envelope has ever been
written on this machine** — and `_evidence` treats v5 as
`legacy_delivery_non_authoritative`, which can never verify.
`native_child_delivery_verifications` holds zero rows, ever.

What that does *not* establish is why. The installed launcher contains the v6
renderer and `staff_native_child` is its only writer, so the honest reading is
that no native child has been staffed under the v6 runtime here yet — and every
attempt to produce one on 2026-08-14 ran into the schema break above. One child
spawned from a working runtime settles it, and that is the next measurement,
not a conclusion to draw now.

**The collector now names the stage that refused.** It previously returned a
bare `None` for eighteen distinct conditions, which is why the two runs below
cost a day. `HostChildCollection` carries a closed reason vocabulary, the
canary record carries `host_child_collection_reason`, and the Rule 4 failure
line quotes it — two further live runs the same afternoon both report
`verified host-authored Claude child card delivery was not proven
(delivery_marker_absent)`, beside the pre-existing
`canary profile plugin registration and enablement were not proven` that
corroborates the first blocker. Three of those reasons were written directly
from what the live runs hit, and are held by `tests/test_child_delivery_evidence.py`:
`multiple_child_artifacts` (the collector requires exactly one artifact and one
run fanned out to four — the gate is unchanged, but a fan-out no longer reads
the same as a host that spawned nothing), `delivery_marker_absent`, and
`legacy_delivery_not_authoritative`.

Two live isolated-profile canary runs were executed on 2026-08-14 at
`bcfbe664`. Neither produced an attestation, and the canary correctly persisted
none.

The first run failed earlier, at routing: the planner applied and the recruiter
was rejected twice, so nothing was staffed and no child existed to collect. The
second run passed that stage -- `routing: 3` at the canary's own query hash, the
expected `code-reviewer` both loaded and selected, `routed_specialists` =
`application-security-engineer, code-reviewer`, and one correlated trace. **The
recruiter stage is therefore nondeterministic across otherwise identical runs,
which is itself a finding: a single failed canary is not evidence that the path
is broken** -- and the 2026-08-14 run at `f4039746`, with `routing: 0`, is the
opposite draw of the same coin.

**Read the canary's counts with care; two of the fields quoted above are not
canary-scoped.** `evidence_summary` filters `routing` by the canary's exact
query hash and `loaded_specialists` by those traces, so those are the canary's
own. `counts.specialists` is unfiltered and `counts.runs` is filtered only by
host and status, so on a workstation whose own interactive Claude session writes
to the same store, both can absorb activity that was never the canary's.
`specialists: 6` and `runs: 2` are therefore upper bounds, not measurements.
`preflight_failures: 0` is worse than ambiguous: it is equally what a clean
preflight and an unrun hook produce, and the `f4039746` run has both that zero
and no Agency activity at all.

The second run then stopped on the delivery proof. Its delegation row reads
`backend=delegate_task`, `native_run_id=claude-agent:ad903e971f817b43f`,
`status=completed`, `error=ok` -- with `retrieved_specialist_slug` empty and
`activation_receipt_id` unset, and `native_child_delivery_verifications` holds
zero rows. (`executed_worker_kind=generic-worker` is *not* an anomaly: the schema
constrains that column to exactly that value for a host-spawned native child.)

The break is upstream of the collector. `retrieved_specialist_slug` is written
only when a delegation activation receipt is consumed and attached, and **no
activation receipt was minted for this child at all** -- the newest row in
`delegation_activation_receipts` predates the canary by a week. So the host
spawned the child and Agency recorded the delegation, but native-child staffing
never engaged, and no card was dealt. No card means no host-written artifact
carrying card hashes, which is the only thing that can satisfy Rule 4.

**A correction, recorded because the wrong reading is the tempting one.** The
delegation columns suggest an outage: 127 of 174 native spawns carry a specialist
slug before `2026-08-07T14:31Z`, and 0 of 8 after, with the last consumed
activation receipt at `2026-08-07T14:36:19Z`. That reading is wrong.

`cd56471d` ("staff harness-spawned children just in time", `2026-08-07T16:04`)
retired exactly that accounting, deliberately and in its own words: the v5 JIT
envelope "carries no work_unit_id and no activation_token; there is nothing to
bind them to", and the child is "staffed but not accounted -- the load is
recorded for audit, but no delegation row is written, so the parent turn gains no
obligation to finalize against". `b222414b` then deleted the one-use activation
grant organ outright.

So `retrieved_specialist_slug` and `activation_receipt_id` are **expected to be
empty** on a JIT-staffed child, and their emptiness is not evidence that no card
was dealt. The capsule already forbids reconstructing "grant" and
"consumed-receipt" transport; that ban applies to reading them as evidence too.

What the failed canary actually shows is narrower and still open: no
collector-minted host-artifact proof was produced for the child, which is what
`_claude_host_child_delivery_failures` requires and the only thing that can
satisfy Rule 4. Whether the JIT path delivered cards is answerable **only** from
the host's own artifact, never from an Agency row -- which is ADR-0156's whole
point. R4 claude Live therefore remains `unproven` on collector evidence, with
no supported claim about a staffing outage.

**AR-252's promotion policy had no evidence it could ever receive.** The
three-success, seven-day policy has shipped since `f85074fe`, and this matrix
recorded it as having implementation and simulation. What it counted was
distinct work units carrying consumed activation receipts -- identities the
host-spawned, just-in-time architecture retired -- so no amount of successful
live work could reach the threshold. The gate read as a missing *live* proof
when the path itself did not exist.

The counted evidence is now an acceptance manifest built only from artifacts a
host wrote: a producer child's delivery proof carrying the contractor's exact
card and the produced artifact digest, a distinct inference-selected verifier
child's own proof, and that verifier's accepted verdict bound to the same
digest. Distinctness counts produced artifacts rather than recorded rows,
because two verdicts on one artifact are one piece of accepted work; the replay
identity is separate, so re-presenting the same evidence resolves to the first
event rather than adding a second success. Missing, ambiguous, Agency-only,
shared-identity, rejected, and replayed submissions each report one bounded
reason and write nothing.

Two paths were closed rather than left looking retired. The generic outcome
recorder now refuses both the retired verifier-receipt keys and any hand-written
acceptance manifest, so the only writer of countable promotion evidence is the
host-artifact path. And the dashboard's readiness projection stopped
reconstructing a stand-in for evidence it had just stripped: the manifest is
identities and digests with no retained content, so the summary carries the real
one and the parity assertion between the two paths now means something.

This is source and simulation only, and the gap is the point. Nothing yet
collects a real envelope -- every producer and verifier proof in the evidence is
constructed by the test. The runtime can now accept an outcome that no host has
yet offered it, which is precisely the remaining AR-252 work.

**Rule 4's host-artifact proof did not hold on Linux, and the matrix could not
see it.** `storage_file_is_trusted` required a foreign artifact to carry no
group or other bits at all -- mode `0600` -- while hosts write their transcripts
at `0644`. Every caller of that guard reads a file another program wrote: a
Claude sub-agent transcript, a Codex rollout, a host wiring file. On Windows a
different branch accepted the same artifact, so one artifact was trusted there
and refused on Linux, and the host-artifact half of Rule 4 was unobtainable on
Linux for any host with a normal umask.

`2f0758d9` keeps ownership, the private parent chain, single link count,
regular-file and symlink rejection, and the `(dev, ino)` seal, and drops only
the demand that group and other be unable to *read* the host's own transcript --
a confidentiality property of data Agency does not own, which the guard's own
docstring never claimed. Group- and other-writable files are still refused, and
the rejection cases are now pinned by a test in CI's spine.

This is the third time this exact shape has appeared: a layer marked `proven`
from a source read, where the property the row asserts is not the property the
code has. It was found by the matrix-evidence CI step added in the same
candidate, on that step's first run, and it could not have been found on a
Windows-only workstation. The R4 claude and codex Implementation rows remain
`proven`, but they were reading `proven` throughout a period when the artifact
they depend on was refused on Linux.

**R4 claude Simulation is proven again at this candidate, and the cause of its
one-day regression is worth keeping.** The failure was in the test, not the
runtime. `staff_native_child` always calls the judge with
`candidate_scope="complete"`, and the complete-universe path never scores
lexical retrieval, so it hard-sets `top_score` to `0.0`; `e8b60f64` sealed that
into the native-child success-route readback as `top_score != 0.0` and added
the killing case in `test_native_child_duplicate_launch.py`, but left this
canary's fake judge returning an impossible `0.99`. From then on the
transactional readback rejected the route, `record_routing_decision` raised,
staffing returned `native_child_routing_decision_unavailable`, and
`HookBridge.handle` answered `{}` — which the canary surfaced only as "safe host
invocation failed before evidence could be evaluated". `a9d84a27` makes the stub
report the zero score the real judge does.

Two things about that hid it for a day. The canary's `except Exception` around
the backend call replaces the real traceback with one fixed sentence, so a
precise store-level rejection reached the reader as an unattributed invocation
failure. And `tests/test_host_canary.py` is in neither the curated mutation set
nor CI's fast-spine allowlist, so nothing ran the sole R4 claude Simulation
evidence between the seal landing and this measurement. The first hypothesis —
that a stale installed projection caused it — was disproven: it failed
identically after the AR-258 reconciliation and on Linux. Simulation parity is
45/45 again.

The decision-conformance gate behind this candidate was proven by the
repository's own Linux CI rather than by a workstation run, which is the
stronger evidence here precisely because both repairs were invisible to Windows.
Its quality job passed in 7m33s at `9724820e`. Two failures remain outside the gate and are not this
branch's: `test_routing_receipt_header.py` loses two cases that are already
recorded in the `bd38e34c` baseline, and `test_owned_adapter_surface_coverage_final.py`
loses three that fail identically on `origin/main`. None is in the curated
mutation set, and none falls inside a cited range.

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

**The Implementation layer is proven at `e216670a`, on the formulation this row
spent two candidates asking for.** The withdrawn one was a reachability sweep,
and it could never have worked: Agency's own inference reaches CLI providers
through the same hardened bounded-process primitive the installer, the host
canary, and the hook-trust inspector use, so the turn-path closure legitimately
contains process-capable modules and counting them measures nothing.

The distinction Rule 5 actually draws is between a tool and an agent. A tool is
started, returns a value, and is gone. An agent is a worker: it gets an
identity, a lifecycle, and a unit of the user's work. Agency may start tools;
only the host may start agents. `agency eval spawn-authority` therefore proves a
separation rather than an absence — the modules that can start a process and the
modules that can bring a worker into Agency's records are disjoint, measured at
this candidate as 21 and 5 with an overlap of zero; worker origin is confined to
the four host boundaries plus the one store table that persists what a host
reported; and every process-capable module carries a declared tool purpose, so a
new one fails the eval until somebody classifies it. Agency has no path by which
a process it starts becomes an agent.

Two details keep this from being decoration. The seam detector counts a
*reference*, not a call, because `cli_transport` never calls the primitive — it
passes it as a default argument and calls it through the injected name, which a
call-only detector misses entirely; over-approximating the process side only
strengthens the disjointness claim. And three of the eight cases inject a
violation into a copy of the shipped package and require the eval to fail, which
is the check this matrix learned to demand after a source-read layer stayed
green through the R8 openclaw regression.

The separation is host-neutral by construction, so all five hosts rest on the
same evidence rather than five independent measurements. That is a real
limitation of the row and is recorded as one.

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
| R4 | claude | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | the in-lifetime SafeClaude collector reads a host-written child artifact carrying the exact team envelope, and the proof asserts verified_delivery, pre_speech, and the exact decision id while the child loaded no specialist itself | 2026-08-14 | `tests/test_host_canary.py:805-1058` | Simulation with the judge stubbed and the host process faked; no installed or live Claude artifact is bound to this candidate |
| R4 | codex | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | reviewed sealed v3 exact CLI `0.147.0` and Desktop `0.147.0-alpha.6.6` profiles | 2026-08-13 | `agency_runtime/core/codex_spawn_provenance.py`, `tests/test_codex_spawn_provenance.py` | Source/simulation cover the CLI 11/11 TUI census and Desktop 52/52 V2 census; exec depth-two/deeper and exact-candidate host artifacts remain open |
| R4 | zcode | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | exact inference team reaches the ZCode child boundary | 2026-08-12 | `tests/test_jit_staffing_host_parity.py:162-208` | Simulation exists but no exact-candidate native child artifact |
| R4 | hermes | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | the exact plural ordered team reaches a host-spawned child through each bridge's real handle() entry with its real adapter, bound to the host's own parent and launch identities; a child the host cannot fully correlate is left unstaffed | 2026-08-13 | `tests/test_native_child_host_boundary_staffing.py:119-217` | Host-boundary simulation with the staffing service stubbed at the same boundary the Claude and ZCode Rule 4 rows stub it; the host is unavailable on the evidence machine, so no installed or live native child artifact exists |
| R4 | openclaw | unproven | proven | proven | unproven | unproven | Correlated native child artifact with exact card hashes before first speech | the exact plural ordered team reaches a host-spawned child through each bridge's real handle() entry with its real adapter, bound to the host's own parent and launch identities; a child the host cannot fully correlate is left unstaffed | 2026-08-13 | `tests/test_native_child_host_boundary_staffing.py:119-217` | Host-boundary simulation with the staffing service stubbed at the same boundary the Claude and ZCode Rule 4 rows stub it; the host is unavailable on the evidence machine, so no installed or live native child artifact exists |
| R5 | claude | unproven | proven | proven | unproven | unproven | Source separation of process origin from worker origin plus native spawn-origin artifact | the modules that can start a process and the modules that can create a worker are disjoint, and worker origin is confined to the host boundaries; a whole turn on a request that asks to be split up then starts no process at any seam while being planned, staffed, and dealt a card, and the host's own delegation is recorded without Agency starting it | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` | Source and simulation only. The separation is host-neutral by construction, so it is the same evidence on every host rather than five independent measurements, and no native spawn-origin artifact is bound to this candidate |
| R5 | codex | unproven | proven | proven | unproven | unproven | Source separation of process origin from worker origin plus native spawn-origin artifact | the modules that can start a process and the modules that can create a worker are disjoint, and worker origin is confined to the host boundaries; a whole turn on a request that asks to be split up then starts no process at any seam while being planned, staffed, and dealt a card, and the host's own delegation is recorded without Agency starting it | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` | Source and simulation only. The separation is host-neutral by construction, so it is the same evidence on every host rather than five independent measurements, and no native spawn-origin artifact is bound to this candidate |
| R5 | zcode | unproven | proven | proven | unproven | unproven | Source separation of process origin from worker origin plus native spawn-origin artifact | the modules that can start a process and the modules that can create a worker are disjoint, and worker origin is confined to the host boundaries; a whole turn on a request that asks to be split up then starts no process at any seam while being planned, staffed, and dealt a card, and the host's own delegation is recorded without Agency starting it | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` | Source and simulation only. The separation is host-neutral by construction, so it is the same evidence on every host rather than five independent measurements, and no native spawn-origin artifact is bound to this candidate |
| R5 | hermes | unproven | proven | proven | unproven | unproven | Source separation of process origin from worker origin plus native spawn-origin artifact | the modules that can start a process and the modules that can create a worker are disjoint, and worker origin is confined to the host boundaries; a whole turn on a request that asks to be split up then starts no process at any seam while being planned, staffed, and dealt a card, and the host's own delegation is recorded without Agency starting it | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` | Source and simulation only. The separation is host-neutral by construction, so it is the same evidence on every host rather than five independent measurements, and no native spawn-origin artifact is bound to this candidate |
| R5 | openclaw | unproven | proven | proven | unproven | unproven | Source separation of process origin from worker origin plus native spawn-origin artifact | the modules that can start a process and the modules that can create a worker are disjoint, and worker origin is confined to the host boundaries; a whole turn on a request that asks to be split up then starts no process at any seam while being planned, staffed, and dealt a card, and the host's own delegation is recorded without Agency starting it | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` | Source and simulation only. The separation is host-neutral by construction, so it is the same evidence on every host rather than five independent measurements, and no native spawn-origin artifact is bound to this candidate |
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
| R8 | openclaw | unproven | proven | proven | unproven | unproven | Native host publication artifact showing an unstaffed turn proceeded | Agency-blind gates allow the turn while envelope integrity and evaluated negatives still deny | 2026-08-14 | `agency_runtime/adapters/openclaw/node_bridge.py:769-1000` | Contract output cannot prove native host publication |
| R9 | claude | unproven | proven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the implementation and simulation layers on claude | 2026-08-14 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Implementation and simulation parity are both complete for this host, but every Installed and Live layer remains unproven, so parity itself is not proven |
| R9 | codex | unproven | proven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the implementation and simulation layers on codex | 2026-08-14 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Implementation and simulation parity are both complete for this host, but every Installed and Live layer remains unproven, so parity itself is not proven |
| R9 | zcode | unproven | proven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the implementation and simulation layers on zcode | 2026-08-14 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Implementation and simulation parity are both complete for this host, but every Installed and Live layer remains unproven, so parity itself is not proven |
| R9 | hermes | unproven | proven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the implementation and simulation layers on hermes | 2026-08-14 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Implementation and simulation parity are both complete for this host, but every Installed and Live layer remains unproven, so parity itself is not proven |
| R9 | openclaw | unproven | proven | proven | unproven | unproven | Aggregate of every R1 through R8 cell under one exact candidate identity | every rule R1 through R8 is proven at the implementation and simulation layers on openclaw | 2026-08-14 | `docs/roadmap/AR-119-rule-host-evidence-matrix.md` | Implementation and simulation parity are both complete for this host, but every Installed and Live layer remains unproven, so parity itself is not proven |

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
| R4 | claude | Implementation | proven | source | sealed in-lifetime collector binds one current host artifact to one invocation, and names the stage that refused when it cannot | 2026-08-14 | `agency_runtime/core/child_delivery_evidence.py:1548-1792` |
| R4 | claude | Simulation | proven | test | the host artifact carrying the exact team envelope is collected inside the disposable profile's lifetime and proves verified pre-speech delivery of the exact decision | 2026-08-14 | `tests/test_host_canary.py:805-1058` |
| R4 | codex | Implementation | proven | source | sealed v3 attestation preserves exact CLI profiles and adds the atomic 13-family Desktop profile with exact causal/output/currentness binding | 2026-08-13 | `agency_runtime/core/codex_spawn_provenance.py:245-3525` |
| R4 | codex | Simulation | proven | test | exact CLI and Desktop lineage, causal, profile, currentness, bound, and replay fixtures pass for every supported variant | 2026-08-14 | `tests/test_codex_spawn_provenance.py:800-1855` |
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
| R8 | openclaw | Implementation | proven | source | blind soft control, correlation, evidence, decision, and commit paths allow the turn, while a terminal that disagrees with the presented digest still denies | 2026-08-14 | `agency_runtime/adapters/openclaw/node_bridge.py:769-1000` |
| R8 | openclaw | Simulation | proven | test | unreadable evidence and unrecoverable correlation allow, while a tampered payload on a completed turn and any delivery on a terminalized trace are still replaced | 2026-08-14 | `tests/test_adapter_parity.py:1593-1681` |
| R5 | claude | Implementation | proven | source | starting a process and creating a worker are disjoint capabilities, worker origin is confined to the host boundaries, and every process-capable module declares a tool purpose | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` |
| R5 | codex | Implementation | proven | source | starting a process and creating a worker are disjoint capabilities, worker origin is confined to the host boundaries, and every process-capable module declares a tool purpose | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` |
| R5 | zcode | Implementation | proven | source | starting a process and creating a worker are disjoint capabilities, worker origin is confined to the host boundaries, and every process-capable module declares a tool purpose | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` |
| R5 | hermes | Implementation | proven | source | starting a process and creating a worker are disjoint capabilities, worker origin is confined to the host boundaries, and every process-capable module declares a tool purpose | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` |
| R5 | openclaw | Implementation | proven | source | starting a process and creating a worker are disjoint capabilities, worker origin is confined to the host boundaries, and every process-capable module declares a tool purpose | 2026-08-14 | `agency_runtime/core/evals/spawn_authority.py:48-318` |

## Cross-cutting completion gates

- **Inference authority:** implementation and simulation are proven on all five
  host adapters at `211563c7`; installed and live card-hash joins remain
  unproven everywhere.
- **Automatic contractor promotion:** the rule that decides what may count, the
  recorder that applies it, and the readiness migration are proven at the source
  and in simulation (`agency_runtime/core/workforce/acceptance.py`,
  `tests/test_accepted_outcomes.py`). No host has produced an envelope: every
  producer and verifier proof in that evidence is constructed by the test, so
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
