---
title: "Giving the child the parent's evaluation pattern"
status: draft
category: roadmap
created: 2026-08-16
updated: 2026-08-17
tags: [roadmap, staffing, native-child, inference, AR-255, AR-119, decision-needed]
related:
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-119-planner-scope-finding.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - agency_runtime/core/native_child_staffing.py
  - agency_runtime/core/selector/judge_protocol.py
supersedes: []
superseded_by: null
type: reference
issue_id: AR-255
---

# Giving the child the parent's evaluation pattern

Ten child staffing decisions, ten declines, zero staffed, with `code-reviewer`
offered every time and assignments from 541 to 2,408 characters. The parent
staffs the same specialist for the same turn. The difference is machinery, not
task — see AR-255, "The child is not evaluated the way the parent is".

This document proposes the change and states what must **not** be copied.

## Parity means the decision discipline, not the cost

The parent takes **119–124 seconds**: plan, recruit, verify, repair, recruit
again. The child takes **5.4–8.1 seconds**. Copying the parent wholesale would
put roughly two minutes in front of every `Agent` spawn.

That is not an acceptable trade and the capsule constraint says so directly:
keep the cold control fixed, and do not trade authority, safety, or evidence for
latency — which cuts both ways. AR-253 already treats the recruiter overrun as a
defect. Importing it into the child would multiply it by the number of children
a turn spawns; one observed run spawned **six**.

## What must not be copied: job two

`AR-119-planner-scope-finding.md` records three staffing failures caused by the
planner's *second* job — decomposing work and attaching hard requirements that
become eligibility gates. Invented domains defeated every ranking once already.

So the child must not receive a full planner. Any characterisation it gains has
to be **advisory** — used to annotate candidates and inform the judge, never to
reject one. Deterministic code may still filter hard-ineligible workers, as
ADR-0118 permits; it may not acquire a new synthesised reason to exclude.

## Three parts, cheapest first

### P1 — Tell the judge the filtering already happened (no extra inference)

The child's judge is handed 66 cards with no indication that the universe was
already narrowed to workers proven executable on this host. It is asked to worry
about "tools, hosts, or platform constraints" that were resolved before the
prompt was built. A candidate set that looks unvetted invites caution, and
caution has a one-word escape in the same sentence.

Scope this to `candidate_scope="complete"`, which is the child path and the
staffing eval, so the ordinary retrieved-scope selector is untouched.

Cost: none. Risk: prompt-behaviour change, so it needs a fixture test.

### P2 — One funded repair before an abstention is final

Today: one call, empty list, abstain. The parent's own successful runs took
**two** recruiter attempts; the second is the one that staffed.

Proposed: on an empty selection, make exactly one more call that asks the judge
to test its own abstention against the concrete set — not to pick something.
The distinction matters and must survive review: a repair that says "choose one"
converts honest abstentions into forced selections and would violate the rule
that inference alone chooses. A repair that says "confirm no candidate's declared
capabilities cover this work" leaves the answer with the model.

Record the outcome under a distinct reason so the two are separable in evidence:
`native_child_no_specialist_needed` for a first-pass abstention that survived
repair, and a new code for one that did not need repair, or vice versa — the
exact split to be settled when implementing, but they must not collapse into one
code, or the next measurement cannot tell whether the repair did anything.

**Settled at implementation (2026-08-16):**
`native_child_abstention_confirmed` means the funded repair ran and the judge
reaffirmed its empty answer against the concrete set;
`native_child_no_specialist_needed` (legacy) now means the first-pass abstention
stood because the repair could not produce a valid answer — an exception,
unavailable or invalid status, a non-list selection, or a repair selection whose
receipt did not carry exactly one applied provider response. A repair that
corrects the abstention adopts the repair call wholesale: its receipt is the one
applied provider response the decision binds, routing state is re-verified after
the extra call, and the selection passes the same validation a first-pass
selection would. **Known limitation, recorded deliberately:** a staffed decision
does not say whether the repair produced it — sealing both calls' receipts would
break the exactly-one-applied-attempt invariant, and writing a second diagnostic
row per abstention would distort decisions-to-declines rates. Conversion is
therefore measured in aggregate: the pre-P2 baseline series (0 staffed / 10) is
the control, and any post-P2 staffed child alongside `_confirmed` rows proves
the repair path executes. Falsification: if post-P2 series shows staffed
children but zero `native_child_abstention_confirmed` rows ever appear, the
first-pass judge started selecting on its own and the repair claim is
unsupported.

Cost: +5–8 s **on declines only**; successful staffing is unaffected. Given
10/10 declines today, that is currently every child, which is the point.

### P3 — A lightweight typed characterisation

The parent's judge is asked to cover named axes; the child's is asked an open
question about a block of text. A single small intent step could emit artifact
kind, lifecycle phase and capabilities as **descriptors only**, used to annotate
the shortlist.

Cost: +1 call (~3–5 s) on **every** child, including ones that would have
staffed. This is the only part with an unconditional latency cost, and it is the
part closest to job two, so it should ship last and only if P1 and P2 leave
declines unexplained.

## Recommendation

**P1 and P2 now; P3 held.** P1 is free and removes a plausible cause. P2 is the
change that most directly mirrors what actually works for the parent, and it
costs nothing on the path that succeeds. P3 buys the least per second spent and
carries the failure mode this project has already been burned by three times.

## Falsification

If P1 and P2 ship and the child still declines across a comparable series, then
the judge is declining on the merits and the fault is upstream — in what the
parent chooses to delegate, not in how the child evaluates it. At that point the
owner-gated `observability.capture_content` question becomes the only remaining
instrument, because the child's actual assignment would be the last unexamined
input.

If instead the child staffs, `native_child_delivery_verifications` gets its first
row ever and Rule 4 reaches Installed/Live on one host.

## Settled 2026-08-17: the capture answered it, and the judge was right

The falsification clause fired and the instrument confirmed it with content.
P1 and P2 shipped, a post-P2 series still declined 3/3, and the first
capture-enabled canary run (build `512f41fd5859`, 14:08–14:11Z, decisions
`7600e896` through `6917026c`) persisted all seven child assignments beside
their declines. What they show:

- **Six of seven children were mechanical errands** — verbatim shape: "Run
  exactly these PowerShell commands … paste the raw combined output verbatim.
  No commentary." Declining these is *correct* judgment under Rule 8: no card
  among 70 improves paste-this-output, and silence beats a wrong card. The
  long decline streak was largely the judge being right about errands.
- **The one review-shaped child arrived pre-staffed in prose.** The parent
  wrapped the canary's work unit in its own preamble — "You are acting as an
  independent code reviewer (authority: review only…)" — before delegating.
  The judge declined a card that would duplicate a role the parent had
  already embedded in the assignment text.
- The P2 repair transport confirmed 5 of 7 declines this run
  (`native_child_abstention_confirmed`), so the repair path is healthy; the
  earlier legacy-only draws were transport noise, not a pattern.

**Consequence: the measurement instrument was self-defeating, not the
runtime.** `CANARY_PROMPT` (shared with the codex activation contract in
`activation_canary_contract.py`) tells the parent to delegate one code-review
unit — and the parent model's natural delegation habit adds a role preamble
and environment-inspection errand children around it, so the judge never sees
a child with a staffable gap.

### Instrument fix (implemented 2026-08-17)

Change the agency-mode canary parent prompt to remove both confounds:

~~~text
Treat this as exactly one indivisible code-review work unit. Delegate that
complete work unit to exactly one sub-agent, and spawn no other sub-agents
this turn — no environment inspection first. Hand the sub-agent the work
unit text below EXACTLY as written: do not add a role, a persona, a "you are
acting as…" preamble, or review instructions of your own; your runtime
staffs sub-agents with any expertise they need. Work unit:
{CANARY_WORK_UNIT}
~~~

Acceptance for the fixed instrument: one canary run whose single child
decision carries the captured assignment equal to the work unit text (no
role preamble), judged over the complete universe. Falsification: if the
judge still declines that assignment, the embedded-role hypothesis is
refuted — the decline would then be on the unit's own merits and the next
question is whether a one-paragraph review brief is simply below the judge's
threshold for dealing a card. Note the codex activation contract pins the
exact prompt text (`_CODEX_ACTIVATION_CANARY_TASK` regex), so the codex-side
recognizer must move in the same commit.

**Status:** shipped 2026-08-17, hardened past this draft by adversarial
review before merge. Three confirmed findings strengthened the wording in
`CODEX_ACTIVATION_CANARY_PROMPT`: the prompt now demands *exclusivity*
("exactly the work unit text below, nothing before it and nothing after
it"), not just fidelity, because appending framing around a verbatim copy
satisfies the draft's letter while failing the equal-text acceptance; it
excludes the live-composed "Canary nonce" line from the work unit; and it
bans environment inspection before *or after* delegating. The recognizer
regex derives from the constant (prompt and codex recognizer move together
by construction), a golden test pins the full prompt text so a mid-prompt
insertion cannot pass, and `_explicit_indivisible_unit_request` is asserted
to fire on the exact prompt. The acceptance run above has not happened yet —
it needs the next installed build and one measured claude canary.

### The product question this raises for the owner

The canary parent's habit is probably not unusual: **organic parents may
routinely pre-staff their children in prose.** If so, the judge declining
duplicated roles is correct product behavior, and Rule 4's "children must
also get cards" is satisfiable only where parents delegate plainly. Whether
Agency should treat an embedded-role assignment as already-staffed (and say
so in evidence) rather than as a decline is an owner-level reading of the
vision, not an engineering default.
