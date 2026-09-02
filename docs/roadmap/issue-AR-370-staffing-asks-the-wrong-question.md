---
title: "AR-370: Staffing asks the wrong question, so operational requests retrieve nothing"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
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

## Approach

Three layers, cheapest first, each independently measurable:

1. **Operational-verb expansion.** Give install, deploy, configure, upgrade,
   provision, migrate, restart, troubleshoot the same treatment `auth` and
   `systemd` already get. The table already exists; this is data, and the
   measurements above show it moves the right specialist from absent to
   top-two.
2. **Deixis and reference resolution.** "install **this**: <url>" should
   resolve its subject before retrieval — at minimum contribute the URL's
   host and path as subject tokens rather than tokenizing them as noise.
3. **An empty candidate set is its own signal.** Three cards at 0.193, or
   none at all, should report that the request was too underspecified to
   route, not hand the recruiter garbage and let it abstain with
   `no_safe_sufficient_team`. The operator currently cannot tell "I could not
   understand the request" from "no team is safe".

## Dependencies

- AR-336 owns recruiter qualification; this is the retrieval stage feeding it.

## Acceptance

- [ ] Operational-verb requests retrieve a relevant specialist in the top
      three; `configure the gateway` never returns an empty candidate set.
- [ ] A request whose subject is a bare reference resolves that reference
      before retrieval, with the resolution recorded in the routing receipt.
- [ ] An underspecified request is reported as underspecified, distinctly
      from an abstention over a real candidate set.
- [ ] The routing eval carries a case per operational verb, so the table
      cannot silently regress.
