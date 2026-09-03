---
title: "AR-370: Staffing asks the wrong question, so operational requests retrieve nothing"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-03
tags: [routing, staffing, retrieval, recruiter]
related:
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-370
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/518
depends_on: []
blocks: []
---

# AR-370: Staffing asks the wrong question, so operational requests retrieve nothing

## Problem

The operator asked codex `install this: https://zcode.z.ai/en` and the turn ran
steward-only. The receipt (trace `01a0621f`, 2026-09-02 12:38:33Z) reads
`substantive_specialist_unavailable` with
`["no_safe_sufficient_team", "recruiter_abstained"]`.

The recruiter was right to abstain. It was handed three irrelevant cards. The
turn was lost in retrieval, not judgement, and the roster was never the
problem: `devops-automator` and `developer-tooling-engineer` are both
governed, approved and enabled.

Measured against the shipped 265-agent roster, same underlying need:

| query | top candidates |
|---|---|
| `install this: https://zcode.z.ai/en` (the literal turn) | ai-generated-code-security-auditor 0.193, ai-citation-strategist 0.141, ai-engineer 0.132 — **3 candidates, none relevant** |
| `install the zcode CLI on linux from this url` | **developer-tooling-engineer 0.204**, terminal-integration-specialist 0.160 |
| `set up and install developer tooling on linux` | **developer-tooling-engineer 0.312**, developer-advocate 0.210 |

Retrieval is healthy. The question is impoverished: the subject of "install
**this**" is a URL that contributes only the noise tokens `zcode`, `z`, `ai`,
`en`, and the words that would actually match a card — CLI, tool, linux,
package — are never stated by the user and never inferred.

`core/selector/domain_expansion.py` is the layer meant to close that gap, but
it is a hand-curated table of about 25 nouns, nearly all specific to this
operator's own stack (`openclaw`, `hermes`, `litellm`, `systemd`,
`telegram`). The most common operational verbs have no entries at all:

| query | raw | with operational-verb context |
|---|---|---|
| `install this: <url>` | ai-generated-code-security-auditor 0.193 | it-service-manager 0.285, developer-tooling-engineer 0.250 |
| `deploy this service` | it-service-manager 0.303 | it-service-manager 0.410, developer-tooling-engineer 0.296 |
| `configure the gateway` | **zero candidates** | it-service-manager 0.320, developer-tooling-engineer 0.282 |
| `upgrade the runtime` | webassembly-engineer 0.140 | it-service-manager 0.315, developer-tooling-engineer 0.280 |

A plain `configure the gateway` retrieving nothing at all is the clearest
statement of the defect.

## Current state

Every host shows staffing failures with different codes in the same minutes
(claude `selection_confidence_too_low` and `staffing_critic_rejected`, codex
`recruiter_abstained`, openclaw `staffing_critic_rejected`, hermes
`inference_invalid`), and AR-353 measured 69% fail-open over 24 h. AR-336
diagnosed the recruiter stage. This issue says the stage before it is feeding
the recruiter a candidate set that no judgement could rescue.

## Live corroboration (2026-09-03, 30-prompt smoke)

Measured on the Linux box with the runtime installed from `b1f030f2`, running
thirty diverse prompts through `agency route --json` and `agency explain`:

- **Operational requests score 0.0 across the entire roster.** "Install ripgrep
  on this machine" returns a top candidate with `score: 0.0`; so do "Restart the
  dashboard service and confirm it is reachable", "Summarize what this
  repository does", "Write a runbook for a p95 latency alert" and "Choose
  between Postgres and DynamoDB".
- **The zero-score result is not empty — it is alphabetical.** With no signal,
  `route` returns `3d-scene-developer, accessibility-auditor,
  account-strategist`: the first three slugs in the roster, presented as a
  ranked answer. `3d-scene-developer` appeared in the top three of **20 of the
  30 prompts** and was top-1 for **7**.
- The scorer is healthy when the vocabulary matches: a Python CLI request scores
  `python-application-engineer` at 24.0 and a release-verification request
  scores `cross-platform-release-verifier` at 14.0.

The degenerate fallback is worth treating as its own defect alongside the
retrieval gap: returning the alphabetical head of the roster with no
zero-signal marker is worse than returning nothing, because the caller cannot
distinguish it from a real ranking.

See [AR-374](issue-AR-374-host-capability-vocabulary-gap.md) for the
eligibility half of the same smoke run.

## Approach

Owner direction (2026-09-02, after reviewing the measurements above): do not
solve this with keywords. The expansion table is the wrong architecture and
`_DOMAIN_EXPANSIONS` is already product debt — it ships one operator's
vocabulary (`openclaw`, `hermes`, `litellm`, `nexus`, `mentor`, `systemd`) to
every installation, and no user should have to phrase a request in card
vocabulary to get staffed. Inference is why this system exists; the fix is to
use it one stage earlier, not to grow a lexicon.

The measurement tables above are therefore diagnostic, not a proposal. They
establish that retrieval responds correctly once the query states the work —
which is exactly what an inference step can produce and a lookup table cannot.

### The mechanism already exists; it runs one turn too late

Traced 2026-09-02. Agency already derives a typed work statement and already
feeds it to retrieval -- just never in time to help the turn that produced it.

- `workforce_subject_hints_from_plan` (`core/turn_routing_context.py:123`)
  extracts typed identifiers from a verified workforce plan: `domains`,
  `languages`, `frameworks`, `capability_ids` (from the plan's
  `required_capabilities`) and `platforms`. Identifiers only -- no prose, no
  keywords, nothing stack-specific.
- `core/selector/pipeline.py:470-486` appends exactly those hints to the
  retrieval query before `expand_query(affirmative_intent(refined))`.

So the pipeline is already built to retrieve on a typed statement of the
work rather than the user's words. The defect is ordering: on a fresh turn
retrieval runs *before* the planner, so the query is the raw message, and the
plan's typed subject only enriches the *following* turn's retrieval. A first
turn -- which is every turn the operator noticed -- never benefits.

That reframes the work. It is not "add an inference step and a vocabulary";
it is "use the typed subject we already compute, early enough to matter". The
options differ in cost, and the choice is real:

- **Re-retrieve after planning.** No new inference call: plan first on the
  bounded index, derive hints, retrieve again. Costs one extra retrieval,
  which is cheap and local.
- **A short classification pass before retrieval.** One small inference call
  that emits only the typed fields. Costs latency on every turn.
- **Retrieve twice only when the first attempt is empty or weak.** Pays
  nothing on turns that already route well, and pays once on the turns that
  are currently lost.

The third is the cheapest defensible default and is the one this issue
proposes, with the first as its fallback shape.

1. **Inference forms the retrieval query.** Today retrieval runs on the user's
   literal text. It should run on a work statement the planner derives from
   the turn: the action, the artifact, the platform, the domain. "install
   this: <url>" becomes something like "install a CLI tool on linux from a
   downloaded distribution" — stated by the model that read the turn, not
   matched from a table. Retrieval quality then rides on inference, which is
   the intended architecture and is stack-neutral by construction.
2. **Resolve the reference before retrieving.** A request whose subject is a
   bare deictic ("this", "that", "it") or a bare URL has no retrievable
   subject. The work statement must resolve it — from the turn's own context,
   or from the URL itself — and the routing receipt must record what it
   resolved it to, so a wrong resolution is visible rather than silent.
3. **Distinguish the three ways a turn goes unstaffed.** The operator
   currently cannot tell them apart, which is why this read as a recruiter
   defect for weeks. Each needs its own reason code in the receipt:
   `request_underspecified` (no retrievable subject — nothing to rank),
   `no_relevant_candidate` (retrieval ran and found nothing above the floor),
   and the existing `no_safe_sufficient_team` (a real candidate set the
   recruiter judged unsafe or insufficient). Only the third is a recruiter
   verdict.

Retiring `_DOMAIN_EXPANSIONS` belongs to step 1: once the query states the
work, a hand-curated synonym table has nothing left to add, and keeping it
would keep shipping one stack's nouns to everyone.

## Dependencies

- AR-336 owns recruiter qualification; this is the retrieval stage feeding it.

## Acceptance

- [ ] Retrieval runs on an inference-derived work statement, not the user's
      literal text; `configure the gateway` and `install this: <url>` both
      retrieve a relevant specialist without the user supplying vocabulary.
- [ ] The typed subject hints the planner already produces reach the turn
      that produced them, not only the next one.
- [ ] `_DOMAIN_EXPANSIONS` is retired, so no installation ships another
      operator's stack vocabulary.
- [ ] A request whose subject is a bare reference resolves that reference
      before retrieval, with the resolution recorded in the routing receipt.
- [ ] An underspecified request is reported as underspecified, distinctly
      from an abstention over a real candidate set.
- [ ] The routing eval carries a case per operational verb, so the table
      cannot silently regress.
