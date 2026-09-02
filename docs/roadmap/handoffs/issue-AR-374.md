---
title: "AR-374 host-capability eligibility handoff"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [handoff, workforce, eligibility, staffing]
related:
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-374
branch: main
evidence_commit: 430e8832edf919572d3c6d732dd0de91d4cc18df
minimum_ledger_commit: 430e8832edf919572d3c6d732dd0de91d4cc18df
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/540
---

# AR-374 host-capability eligibility handoff

Start-here capsule for a fresh session. The subject is one question: why can
Agency not staff an ordinary request on this installation, now that every
earlier blocker in the chain is fixed?

## checkpoint

Main is green on both strict gates and deployed on this box. The staffing
chain was chased end to end on 2026-09-02 and four distinct defects were
found and fixed in sequence; this is the fifth and last one standing.

What the chain looked like, in the order it failed:

1. **Model names.** `~/.agency-runtime/agency.yaml` pointed at
   `gpt5.6-luna-medium`; litellm serves `gpt-5.6-luna-medium`. The planner
   never ran, so every turn was steward-only. Repointed to the purpose-built
   `task-agency-*-v2` routes (backup: `agency.yaml.bak-ar370-20260902-102611`).
   **This is operator config, not code, and it is not in git.**
2. **AR-373 (fixed, merged).** `typed_staffing_requirements` shows the
   recruiter `artifact:plan`, `domain:platform`; the nomination validator
   required hyphens only, so entire nominations were discarded as
   `provider_response_contract_invalid` -- 475 times in 24 h. Widened the
   evidence charset only; the shared identifier schema is untouched.
3. **AR-374 (this issue, open).** With the contract failure gone the
   recruiter reaches a real judgement and abstains, because the candidates it
   wants are ineligible on tools.

After 1 and 2, the same request now behaves like this:

    planner            applied   structured_response_applied
    recall_embedding   applied   dense_recall_applied
    recall_reranker    applied   structured_response_applied
    recruiter          applied   structured_response_applied   <- was: rejected
    staffing           abstained no_safe_sufficient_team

## completed-evidence

The measurement that defines this issue, taken against the shipped
291-worker index:

- `_NATIVE_HOST_CAPABILITIES` grants every execution host the same nine
  capabilities: `code-execution`, `native-delegation`,
  `package-management`, `repository-read`, `repository-write`,
  `runtime-evidence`, `shell-execution`, `source-control`,
  `test-execution`.
- The roster demands **246 distinct tool classes**.
- **219 of 291 workers (75%) are permanently ineligible**; 72 are eligible.
- Top blockers: `browser-interaction` 55, `web-research` 43,
  `analytics-reader` 27, `database-access` 19.

The planner is not the problem and should not be re-litigated. On
`install this: https://zcode.z.ai/en` it produced: *"Install the software
available from the provided Zcode website on the Linux host and verify that
the installation works"*, decomposed into discovery / operation /
verification, all `linux`, with sane typed domains and capabilities. It
resolves the pronoun and the URL correctly.

AR-370's original premise -- that lexical retrieval was losing the turn --
is **wrong and the issue records the correction**: `semantic_retrieve` and
`_DOMAIN_EXPANSIONS` belong to the legacy selector branch, which the
workforce path never uses. Do not restart there.

## exact-blocker

`agent_tools_missing`. Establish which of AR-374's three hypotheses holds --
the roster over-declares, the hosts under-declare, or the vocabulary is
mis-scaled -- before changing anything. They need opposite fixes.

## same-task-continuity

Reproduce in about 70 seconds, no host needed:

```bash
set -a; . /home/holeshot/.config/ai-secrets/common.env; set +a   # LITELLM_API_KEY
V=/home/holeshot/.local/share/agency-runtime/venvs/0abe4a77c87af87cf0d2789df77d40d4a6f80a44
$V/bin/python - <<'PY'
from agency_runtime.core.config import load_config
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.workforce.inference import plan_and_staff_workforce
from agency_runtime.core.workforce.staffing_verifier import StaffingContext
from agency_runtime.core.workspace_stacks import detect_workspace_stacks
cfg = load_config(); snap = workforce_index_snapshot(Store())
ctx = StaffingContext("codex", "linux",
    frozenset({"native-delegation","repository-read","shell-execution"}),
    snap.generation, None, detected_stacks=detect_workspace_stacks())
out = plan_and_staff_workforce("install this: https://zcode.z.ai/en", snap,
    config=cfg, context=ctx, turn_routing_context={})
print(out.status, out.abstention_codes)
for a in out.attempts:
    print(a.stage, a.status, a.reason_code, a.validation_detail[:200])
PY
```

Widen the `frozenset` to include `package-management`, `ci-runner`,
`infrastructure-tooling`, `test-execution`, `build-toolchain` and the
recruiter's nomination is accepted -- that contrast is the whole issue.

Traps worth knowing: a bare harness without the key in the environment
reports `workforce_provider_unavailable` and looks like a code fault;
`configured_workforce_providers(cfg, stage=...)` is a legacy accessor and
does not report what the real path uses -- read `out.attempts[*].requested_model`
instead. Never run `python -c` importing `agency_runtime` with the cwd
inside the checkout; the working tree shadows the venv.

## next-bounded-work-package

1. Answer the three hypotheses with evidence: sample the blocked cards and
   judge whether each declared tool class is genuinely required; check what
   each host could prove if detection existed.
2. Whichever way it falls, add the drift guard AR-374's last acceptance box
   asks for, so the two vocabularies cannot separate silently again.
3. Then re-run the reproduction above and, if it staffs, take one live
   ordinary turn per host as the receipt.

## verification

Done, for this handoff's subject, means:

1. The three hypotheses in AR-374 are each confirmed or rejected against
   measured evidence, and the answer is recorded in the issue.
2. The structurally-unstaffable share is stated per host with the tool
   classes responsible, not just the aggregate 219/291 measured here.
3. Whatever the fix, a regression test pins that the capabilities a host
   proves and the tool classes the roster demands cannot drift apart
   silently again.
4. Every change proves the local gates: focused tests, the named fast Python
   spine under `-W error`, ruff check and format, both docs gates, the
   worklog dance, and the routing plus decision-conformance evals if a
   routing or policy surface changed.
5. An ordinary install request staffs a specialist on this installation with
   a live receipt, or the reason it correctly should not is recorded.

## constraints

- Never commit to `main`; branch in a worktree, PR, merge. GitHub Actions is
  off -- prove gates locally: ruff from
  `~/.cache/agency-runtime-ar281-trusted-venv/bin/`, then
  `python3 -m pytest $(WORKFLOW_CONTRACTS + PRODUCTION_SPINE)` with the system
  `python3` (the trusted venv is not an OS-protected interpreter and the
  spine refuses it), plus the mutation-snippet check.
- Ledger dance on every substantive commit; new docs carry `tracker_url`.
- Findings go in repo docs, not the reply. One question per turn. Rule 8.
- `agency.yaml` is operator configuration: do not rewrite model routes
  without the owner's word.
