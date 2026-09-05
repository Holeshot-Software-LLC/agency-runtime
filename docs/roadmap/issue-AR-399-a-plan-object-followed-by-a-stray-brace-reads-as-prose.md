---
title: "AR-399: A complete plan object followed by one stray closing brace reads as prose and costs the turn"
status: done
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, planner, inference, transport, receipts, reliability]
related:
  - docs/decisions/0215-accept-one-complete-object-with-a-trailing-bracket.md
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
failure shape accounts for five of the 14 receipts since the `c42fb0a5`
install: claude turns whose two planner attempts each read
`provider_model_text_not_json` at 5.6 to 8.5 s with `actual_model` empty.
Five more receipts in that window carry `inference_unavailable` from zcode with
no provider attempt at all, a different failure this change does not touch.
The trigger seen so far is a system-notification text
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
on the receipt. The first-to-last-brace span still runs first, so trailing
prose after a complete object is accepted as it always was; a stray bracket
followed by anything but brackets or whitespace, and a text with no object,
are still not JSON. Only the HTTP transport parses model text this way; the
CLI transport reads model text with the bounded loader directly and gets no
repair, so the same shape from a codex or claude CLI provider still costs the
turn (out of scope here). ADR-0215 records the contract change.

## Approach

Parser-side tolerance for the one observed shape, recorded on the attempt (ADR-0215);
no prompt change. A prompt-side guard cannot make the model stop emitting the
brace, and the second ask already proved that asking again draws the same
reply.

## Dependencies

- AR-396 added the second ask this shape defeats; ADR-0212 stands.

## Acceptance

- [x] A reply that is one complete object followed only by closing brackets or
      whitespace is applied on the first ask, and the attempt carries
      `model_text_trailing_data_trimmed`.
- [x] A reply in which a stray closing bracket is followed by anything but
      closing brackets or whitespace, and a reply with no object at all, are
      still reported `provider_model_text_not_json`, and a reply nested past the
      interpreter's recursion limit is refused the same way rather than raising.
- [x] The repair code survives receipt projection for every stage, and a
      clean reply carries no repair code.
- [x] Replaying the four captured replies through the parser yields four plan
      objects.
