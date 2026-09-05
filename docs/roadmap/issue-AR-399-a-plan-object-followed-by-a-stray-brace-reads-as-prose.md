---
title: "AR-399: A complete plan object followed by one stray closing brace reads as prose and costs the turn"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, planner, inference, transport, receipts, reliability]
related:
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/handoffs/issue-AR-383.md
  - docs/decisions/0212-ask-again-when-a-complete-reply-is-not-json.md
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/preflight_failure.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-399
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-399: A complete plan object followed by one stray closing brace reads as prose and costs the turn

## Problem

The planner alias answers some prompts with a complete, valid plan object and
then one more `}`: `...,"depends_on":[]}]} }` or `...]}}\n`. `_parse_model_text`
(`agency_runtime/core/structured_provider.py`) tried the whole text, then the
span from the first `{` to the *last* `}`; the stray brace is the last one, so
both attempts failed, the transport reported `provider_model_text_not_json`,
and the AR-396 second ask drew the same shape. The turn ended
`workforce_provider_unavailable` / `inference_unavailable` with no plan, on a
reply whose plan was complete.

## Current state

Captured 2026-09-05 through the real `UserPromptSubmit` hook against a store
copy with `capture_full.py` keeping full replies (session `3a994fdc`,
`payloads-notif1` and `payloads-notif2`): two notification-shaped prompts,
four planner replies, every one a valid object plus a single trailing `}`
(`json.loads` fails with "Extra data" at the last character; content lengths
492 to 525, `finish_reason stop`, 230 to 321 completion tokens). The same
failure shape was the most common live failure in the window after the
`c42fb0a5` install: 10 of 14 receipts carried `inference_unavailable` with two
planner attempts each reading `provider_model_text_not_json` at 5.6 to 8.5 s,
`actual_model` empty. The trigger seen so far is a system-notification text
arriving as the user message; the prompts include `response_format` with the
plan JSON schema, so this is the model closing one brace too many rather than
answering in prose.

## Fix (2026-09-05)

`_parse_model_text_with_repair` keeps both existing attempts and adds one: when
the text starts with an object, `json.JSONDecoder.raw_decode` reads the first
complete object and the rest is accepted only if it consists of closing
brackets, fence ticks or whitespace. The object is re-read through the bounded
JSON loader so the size, depth and node limits still apply. The repair is
named: `StructuredProviderResult.model_text_repair` carries
`model_text_trailing_data_trimmed`, the applied attempt records it as a
validation reason code, and the receipt projection admits that runtime-owned
code for every stage, so a rescued reply is distinguishable from a clean one
on the receipt. Any other trailing text is still not JSON, and prose is still
prose.

## Approach

Parser-side tolerance for the one observed shape, recorded on the attempt;
no prompt change. A prompt-side guard cannot make the model stop emitting the
brace, and the second ask already proved that asking again draws the same
reply.

## Dependencies

- AR-396 added the second ask this shape defeats; ADR-0212 stands.

## Acceptance

- [ ] A reply that is one complete object followed only by closing brackets or
      whitespace is applied on the first ask, and the attempt carries
      `model_text_trailing_data_trimmed`.
- [ ] A reply with any other trailing text, or no object at all, is still
      reported `provider_model_text_not_json`.
- [ ] The repair code survives receipt projection for every stage, and a
      clean reply carries no repair code.
- [ ] Replaying the four captured replies through the parser yields four plan
      objects.
