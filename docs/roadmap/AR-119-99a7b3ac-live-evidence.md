---
title: "AR-119 installed and live evidence at runtime 99a7b3ac"
status: active
category: roadmap
created: 2026-08-18
updated: 2026-08-18
tags: [roadmap, evidence, hosts, AR-119, AR-255]
related:
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-c77c67a4-live-evidence.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 installed and live evidence at runtime 99a7b3ac

Every claim below is bound to one runtime: merge `99a7b3ac` (PR #287, the
owner's small-unit policy), whose `agency_runtime/` tree equals every
later main tip through `f980f27e` (docs-only merges since; verified by an
empty `git diff 99a7b3ac origin/main -- agency_runtime/`) — installed on
2026-08-17 (before 21:00 UTC, per the runtime-state file) as runtime digest
`cc478bc88258210b24dfd8f990caa76b41b4585de72a68c45d4c040b74c7f5e5` for
claude, codex, and zcode (one digest, AR-258), store schema 47 == checkout
47 == launcher 47. PRs #288–#290 after the install are docs-only, so the
installed build equals main for the package tree. Store rows are
correlation only; each claim's origin authority is the host-authored
artifact (ADR-0156). Timestamps are UTC.

The measurement session for R1/R4/R5-Live is the loop session itself —
Claude Code session `f3066348-ca45-4318-9095-878a4a23c5c2`, a fresh
real-profile session started 2026-08-18 00:04, after the installs. Its
primary artifacts are the parent transcript
`~/.claude/projects/C--Workspaces-Holeshot-Software-agency-runtime/f3066348-ca45-4318-9095-878a4a23c5c2.jsonl`
and the child transcript
`…/f3066348-…/subagents/agent-a3b16809ebb7e199e.jsonl`, written by Claude
Code itself and retained where the host wrote them.

## R4 and R1 claude — RETRACTED 2026-08-18; an existence proof, not a proven cell

**Claimed at all four layers on 2026-08-18 and withdrawn the same day by
adversarial review.** The artifact is real and every binding verifies —
several more strongly than first claimed — but the inference from it to
`proven` does not survive.

### What the artifact does establish, verified to the byte

The child transcript
`~/.claude/projects/C--Workspaces-Holeshot-Software-agency-runtime/f3066348-…/subagents/agent-a3b16809ebb7e199e.jsonl`
record zero (`type=user`, `isSidechain=true`, 01:47:41.715Z, marker at
char 2022; first assistant record is index 5 at 01:47:44.369Z) carries an
`[AGENCY INFERENCE TEAM v6]` envelope whose bindings all hold:

- `launch_id` = `toolu_01NpSMbfcshZ8UgNYQ71Fvkm` = the parent transcript's
  tool_use record **and** the host's own `agent-….meta.json` `toolUseId` —
  two independent host files.
- `task_sha256 7ee6b9ce…` equals SHA-256 of the parent-recorded 2,020-char
  prompt, which contains **no** v6 marker — the envelope was appended
  host-side afterward, so the parent copy is a genuinely independent
  witness. It also equals `routing_decisions.query_hash`.
- The delivered 2,496-char card body is **byte-identical** to
  `agent_versions.content` for `codebase-onboarding-engineer`, and
  `sha256(body)` equals `agent_workers.current_hash` — a content checksum,
  not a matching identifier.
- `runtime_digest` = `candidate_digest` = installed `cc478bc88258…`, and
  the installed launcher tree versus this checkout's `agency_runtime/`
  compares **577 files, 0 added, 0 missing, 0 differing**.
- Delivered inside its 60 s validity window; store row `applied`,
  `native_child_inference`, trace `1b717647…`.

That is a sound **existence proof**: the JIT path delivered a fully bound,
pre-speech, exact-hash card to a harness-spawned child, once.

### Why it is not a proven cell

1. **Undisclosed base rate: one delivery in fourteen.** Since this runtime
   was installed, Claude Code wrote **14** harness-spawned child
   transcripts on this machine; exactly **one** carries a v6 envelope.
   Inside the measuring session itself, four children were spawned under
   identical conditions — one got a card, three record zeros carry no
   `[AGENCY` marker at all, and two show the `SubagentStart` hook firing
   and writing "this identity message supplies no card". Rule 4's text is
   "Harness-spawned children **must** also get cards." A limitation
   reading "single occurrence" implies measured-once; it was measured
   fourteen times and succeeded once. (Much of the shortfall is provider
   availability — 13 parent-stage routing failures in that session — and
   Rule 8 permits abstention, but **no receipt is bound to any of the
   three unstaffed child launches**, so their non-delivery is unexplained
   in the store rather than a documented abstention.)
2. **The promotion reversed this session's own recorded reading, with no
   decision written down.** The loop status document, from the same
   artifact the same night, said: no R4 matrix cell, "conservative reading
   of R4's authority keeps the cell untouched until a collector-verified
   proof exists". The matrix says a collector-minted proof "is the only
   thing that can satisfy Rule 4", and
   `native_child_delivery_verifications` still holds **zero rows**. The
   standard was not relaxed by decision; it was simply not applied. That
   is the exact failure mode this matrix has recorded three times.
3. **A stated corroboration was false.** The claim said `task_sha256`
   equals "the store's captured-assignment hash". The stored
   `captured_task` is **2,000 characters — a truncated prefix** (bounded
   by `MAX_CAPTURE_CHARS`), and its own SHA-256 is `66023421…`, not
   `7ee6b9ce…`. Only the `task_sha256` *column* matches, and that column
   was written by the same code path that built the envelope, so it is a
   self-assertion rather than a content check. The conclusion survives on
   the parent-transcript recompute alone; the sentence was wrong.
4. **Plurality.** The founding vision says children get cards, "plural",
   and the matrix's hermes/openclaw R4 rows demand "the exact **plural**
   ordered team". This artifact delivered exactly one card (`CARD 1/1`).
   A permissive reading is defensible, but applying a looser standard to
   claude than to other hosts is precisely the asymmetry Rule 9 exists to
   prevent.
5. **Installed is not independent of Live here.** Both are readings of one
   01:47:41Z launch; the only fact distinctly belonging to Installed is
   `runtime_digest` — a field of the same envelope. Counting one event as
   two proven layers doubles apparent evidence weight.

**R1 falls with it**: its Installed and Live claims rested on the same
single artifact ("the same envelope", "same artifact, same joins"), so
findings 1, 2 and 5 transfer unchanged.

**What would prove these cells:** a collector-minted host-artifact proof
(the first `native_child_delivery_verifications` row), or a measured
delivery *rate* across a series of harness-spawned children with a
receipt bound to every non-delivery — plus, for the strict reading, a
plural ordered team in one child.

## R5 claude installed — RETRACTED 2026-08-18

**Claimed and withdrawn the same day, by adversarial review, before it
reached the owner.** It asserted that `agency eval spawn-authority --json`
analyzed the installed launcher tree, 5/5 cases passing.

It cannot stand: the eval **emits no package path**. Its receipt is
`{suite, passed, passed_count, failed_count, cases}`, and module names are
relative to the package root, so they read identically for every tree. The
one number reported — `modules: 295` — is shared by the ar119 checkout,
the primary checkout, **and eight separate launcher trees**. The
distinguishing step (printing `agency_runtime.__file__` in-process) left
**no retained artifact**, on a machine where that exact confusion already
happened once this session.

Worse, it is not independent even in principle: this document also asserts
the checkout tree equals the installed tree, so an eval reading either
cannot distinguish them. **An installed layer whose evidence is provably
invariant to which tree it read is not an installed proof — it is the
Implementation layer re-run.**

What would prove it, and was available for free: run the eval *through the
installed launcher's own bootstrap*, which executes under `-I -S` so the
caller's CWD, user site, and PYTHONPATH are removed and only the private
package parent is restored — making the installed tree structurally
unavoidable rather than asserted — and retain the command line and stdout.
The same objection applies to the `c77c67a4`-era R5 Installed claim, which
rested on the same unretained assertion; it is prior-candidate context
now, but it inherits this defect and the owner should know.

## R5 claude live — RETRACTED 2026-08-18

**Withdrawn, and one sentence in it was factually false.**

The claim said "Agency started no process". Agency demonstrably *did*
start one inside that very turn: the child staffing decision
`native-child-3507ad14…` ran on provider **`codex-subscription`** with
`latency_ms 11850`, and `cli_transport` is declared process-capable
("inference provider call") by the spawn-authority eval itself. Agency
held an OS subprocess open for ~11.85 s ending 01:47:41.457Z — **1.4 s
before** the delegation row's `started_at` (01:47:42.866Z). Under Rule 5's
own tool/agent distinction that is permitted (Agency may start *tools*),
but the sentence must then read "started no **worker**". As written it
asserted a proposition its own store row falsifies.

The deeper defect: the authority is a conjunction — source separation
**plus** a native spawn-origin artifact — and a delegation row with a
parent `tool_use` is purely positive evidence. It proves the host started
something; it carries no information about absence. The negative half was
borrowed from the source layer, which the matrix's derivation rule does
not permit. `tests/test_spawn_origin_absence.py` shows what a real
measurement costs: four seams detector-patched for a whole turn, a
positive control proving the detector fires, and non-vacuity asserted from
the turn's own artifacts. This claim had none of that.

## R2 claude installed

A fresh real-profile `claude -p` session on the installed projection
(session `1eaa3a55-e7ad-4309-a61d-1a054aae3e55`, started 02:56:56Z from
the ar119 worktree) activated the delivery path end to end: the
UserPromptSubmit hook attached the `[AGENCY LOADED]` capsule as transcript
record 8 (02:58:49.750, persisted side file
`hook-3576769e-…-additionalContext.txt`, 18,748 bytes), and the store
gained the accepted routing decision (`949ced13`, 109.5 s, trace
`442b50db`) and four `specialists_loaded` rows written by the installed
runtime for that trace. Limitation: one turn, not a rate.

## R2 claude live

The same turn is a real live turn on the owner's profile: the capsule
carries the selected cards' entries with whole instruction bodies
(`Instructions:` appears four times in the side file) for
`codebase-onboarding-engineer`, `application-security-engineer`,
`secrets-credential-hygiene-engineer`, `code-reviewer`, attached before
the first assistant record (record 8 at 02:58:49.750 vs record 9 at
02:58:51.404). Store join: decision `accepted` with exactly those four
selected, four `specialists_loaded` rows on the same trace, zero
`delegation_events` for the session — no child existed that could have
received the cards instead. Selected and loaded sets are equal (4/4),
with no narrowing. Limitation: one turn.

## R3 claude installed

Same activation artifact as R2 installed: the installed projection
delivered a multi-card capsule — four compatible cards in one turn —
into the caller's turn, pre-speech. Limitation: one turn.

## R3 claude live

The R2 live artifact carries four compatible cards' whole instruction
bodies in one turn, each also present as a `specialists_loaded` row on the
same trace. Rule 3 asks for two or more; the turn delivered four, and the
selected set equals the loaded set. Limitation: one turn.

## R7 claude installed

The installed projection expired turn 1's cards at run close: all four
`specialists_loaded.expired_at` values equal the run's `ended_at`
(03:02:32.057455) exactly, and turn 2's capsule attachment opens the next
turn with the expiry notice. Limitation: one two-turn observation.

## R7 claude live

The resumed turn 2 of session `1eaa3a55` (run `bfb6c3a5`, 03:05:52Z)
received its capsule as record 56 (03:06:38.679, persisted side file
`hook-1b86c5a5-…-additionalContext.txt`), before turn 2's first assistant
record 57 (03:06:54.170). It states `[AGENCY SPECIALIST EXPIRY] … no
longer loaded: application-security-engineer, code-reviewer,
codebase-onboarding-engineer, secrets-credential-hygiene-engineer` —
every turn-1 card named, none re-delivered: turn 2's accepted decision
(`d05cd5d9`, 03:06:38) selected and loaded `ci-operations-advisor` and
`sre-site-reliability-engineer` instead. Same identity held in its own
turn, absent from the next, expiry stated. Limitation: the expiry notice
rides the next turn's capsule, so an empty-context turn would not carry
it.

## R6 claude installed and live — NOT CLAIMED; the ladder half holds, the use half fails

Both layers were claimed on 2026-08-18 and are **withdrawn the same day**
by adversarial review. What survives is worth keeping precisely, because
most of the ladder did hold.

**What is solid.** The installed projection ran the whole hiring ladder
organically inside a real turn of another project's session (conveyor
worktree session `b97eb5cb…`, 05:05:48Z) on the **exact installed
candidate** — that session's own hook command line names
`…/runtime-sha256-cc478bc88258…/site-packages/agency_runtime/_bootstrap.py`,
so candidate binding here is stronger than in most cells. Hiring case
`bfe8a9cb` carries gap, duplicate and contract evidence, three staged
model receipts (`hiring`/haiku, `hiring-critic`/sonnet,
`security_review`/sonnet, `inference_required: true`), and a real
**security review with `verdict: "safe"`, `same_provider_as_creator:
false`** — so the "independent critic receipt" clause of the authority is
genuinely satisfied, and an earlier worry that the dynamic path recorded
only an inline audit stanza was **wrong** (the audit block is a third,
separate thing: the compiled contract's own stanza). The worker was filed
`origin='agency'`, `employment_class='contractor'`. It is the **last row
in `agent_hiring_cases`** (31 rows, none after 05:05:48.439), so "reused
with zero further hiring cases" holds. Two distinct later turns exist and
are provably distinct: different UserPromptSubmit hook ids, different
resident-manager turn ids, different parentUuids, and two
`specialists_loaded` rows on **different traces** (`01605b15…` 05:05:48,
`a19437fb…` 06:29:49).

**Why the cell is nevertheless not claimed.** R6's authority ends with
**host-backed use**, and the host's own artifact contradicts it. Every
host-authored `Agency/Agencies loaded:` header in both windows reads
`agency-steward` with `Recruited via: none` and `Actual Model selected:
none observed` (records 2613 and 2621, verified directly). The only text
on the machine naming `deployment-readiness-reviewer` as loaded is an
`[AGENCY UPDATED HEADER SNAPSHOT]` injected by Agency's own PostToolUse
hook — Agency-authored, which ADR-0156 says can never originate the
claim. Both runs terminated **`response_invalid`**, and the reuse card's
entire lifetime was 10.6 s (`loaded_at 06:29:49.879` → `expired_at
06:30:00.521`, the run's end).

A second, smaller correction: the earlier write-up cited "capsule record
1948 … with its instruction body". That record is a `<persisted-output>`
2 KB preview in which the slug appears **only** in the routing-suggestion
line; the card body lives in the retained side file
`…/tool-results/hook-e18246fa-…-additionalContext.txt` (21,001 bytes).
Cite the side files, not the transcript records.

**What would prove R6 here:** one host turn whose own final header names
the minted contractor as loaded, on a run that does not terminate
`response_invalid`. Delivery is already evidenced; host-attested *use* is
the gap. Also worth the owner's eye: `critic_evidence["approved"]` is a
hardcoded literal rather than a read verdict, and
`critic_evidence["receipt"]` stores the security-review receipt rather
than the critic's — so quoting `approved: true` as a receipt is a
tautology. The real critic receipt survives only in `model_evidence`.

## Not moved at this candidate

- **R8 claude**: no clean "unstaffed turn proceeded" host publication
  artifact exists yet. The canary discards the disposable-profile parent
  transcript, so tonight's three preflight-failed runs (0/3 series,
  provider-killed) could not double as R8 artifacts; preserving a bounded
  parent-proof in the canary attestation is proposed as a morning decision
  (it is a new capture surface, which section 3 of the loop brief reserves
  to the owner).
- **codex / zcode / openclaw / hermes**: unchanged from candidate
  `f2f3ca88`; see the matrix and the owner-run verification packet.
