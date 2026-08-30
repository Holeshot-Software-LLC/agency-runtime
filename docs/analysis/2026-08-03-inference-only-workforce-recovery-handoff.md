---
title: "Inference-only workforce recovery handoff"
status: active
category: analysis
created: 2026-08-03
updated: 2026-08-03
tags: [handoff, inference, routing, workforce, codex, zcode]
related:
  - docs/roadmap/issue-AR-228-eliminate-deterministic-staffing-authority.md
  - docs/roadmap/issue-AR-227-expand-specialist-roster.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-225-align-product-scenario-with-independent-validator.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/analysis/2026-08-03-ar-203-readme-story-evidence.html
supersedes: []
superseded_by: null
---

# Inference-only workforce recovery handoff

## Executive verdict

Agency has proven that one exact inference-authored seven-specialist team can be
natively delegated by Codex and complete a real application. Agency has **not**
proven that ordinary product behavior is universally inference-owned. The
installed runtime still contains and reports deterministic staffing behavior,
and its current failure message can call working inference unavailable.

Do not restart from scratch. Preserve the valid native-delegation work, finish
the bounded AR-227 roster checkpoint, and then repair the inference-authority
contradiction as AR-228. Do not declare `EUREKA` again until AR-228's complete
negative and live-product gates pass.

## What PR #235 actually proved

Exact candidate `71faad8badc40a74b1b00ab01063cc5feb97800d` passed one controlled
product scenario:

- inference authored seven work units and selected seven specialists;
- Codex performed seven native delegations;
- seven workers completed with exit code zero;
- accepted finalization and workspace-write proof passed;
- workflow, invalid-ID recovery, project tests, and documentation passed;
- the authenticated dashboard displayed the seven completed delegations.

This evidence is real and must be retained. It proves the full mechanism can
work. It does not prove that every prompt reaches that mechanism or that no
deterministic selection path remains.

## Newly confirmed product defects

1. `tests/test_mandatory_inference.py` requires pure social turns such as
   `hello` to skip a configured provider and emit `inference_mode="deterministic"`.
2. `agency_runtime/core/workforce/fallback.py` still exports and executes
   `deterministic_plan_and_staff` and `deterministic_staff_plan`.
3. `agency_runtime/core/workforce/lifecycle_roles.py` and callers retain role
   anchors that can shape semantic ownership.
4. ADR-0118 says the deterministic offline floor is superseded, but production
   tests and code still preserve it.
5. `_PREFLIGHT_UNAVAILABLE` in `agency_runtime/adapters/hooks.py` always tells
   the operator to restore inference or staffing and forbids a generalist
   answer, even when inference was configured and successfully called.
6. Current persisted evidence shows successful planner and recruiter responses
   followed by `no_safe_sufficient_team` / `recruiter_abstained`, not provider
   unavailability.
7. The latest hiring evidence includes a false high-risk-medical classification
   on unrelated work, demonstrating why semantic risk cannot be inferred by
   deterministic word rules.
8. The evidence page's product-wide `EUREKA` statement overgeneralizes a
   scenario-scoped canary and must be narrowed until AR-228 closes.

## Settled target contract

Inference owns every semantic staffing decision:

1. Interpret the request and decide whether staffing is needed.
2. Describe the ideal specialist or team before matching the roster.
3. Query or inspect the complete roster without a deterministic request-based
   filter silently excluding candidates.
4. Select faithful existing specialists or declare and design a real gap hire.
5. Return an exact structured plan and evidence.

Deterministic code may only enforce closed, observable invariants:

- schema, bounds, hashes, identities, and persisted receipt correlation;
- duplicate, cycle, relationship, and budget constraints;
- actual host, platform, tool, sandbox, permission, and approval evidence;
- exact runtime-control parsing and historical receipt compatibility.

It may not decide semantic relevance, skip inference based on conversational
wording, promote a role anchor, infer a risk class from words, choose a worker,
or construct a fallback team.

No configured provider means no Agency selection: disclose it and let the
native host answer without claiming specialist activity. A configured provider
that fails or remains invalid after its bounded repair fails loudly and never
falls back to deterministic staffing. Inference may explicitly return that a
social turn needs no specialist.

## Current repository state

- Base: merged PR #235, merge commit
  `c01f178f4165180fbbe4865fb0775b4909e399c0`.
- Branch: `codex/ar-227-expand-specialist-roster`.
- AR-227 is uncommitted and unpushed.
- AR-227 adds six genuinely missing governed contractors, strengthens the
  existing backend-service contract, and expands the finite complete recruiter
  index envelope from 256 KiB to 288 KiB after measuring 263,700 bytes for 278
  workers.
- The six proposed near-neighbor roster overlays were removed because Agency's
  existing contracts already contained the useful boundaries and the additive
  selection phrases caused deterministic fallback drift.
- Focused AR-227 verification passed 75 tests before the index-envelope change.
- The named fast spine then passed 640 tests with 6 skips and failed 20 copies
  of the same 256 KiB index-capacity boundary.
- After the 288 KiB repair, the affected rerun reached 68 passes, 1 skip, and
  four failures: two stale exact counts and two selection-drift cases.
- Those four defects were patched; their exact rerun now passes 4/4.
- The complete named fast spine has **not** been rerun after the final patches.
- Documentation validation passed before AR-228 and this handoff were added; it
  must be rerun.
- User-owned untracked files must remain untouched:
  `docs/analysis/2026-07-25-deep-audit-findings.md` and `uv.lock`.

## Live installed-state evidence

Read-only diagnostics on 2026-08-03 reported:

- profile `yolo`;
- provider `codex-subscription`, transport `codex`, requested model
  `gpt-5.6-luna`;
- provider configured, OAuth-authenticated, and usable;
- latest successful model receipt resolved
  `codex-subscription/gpt-5.6-luna`;
- Codex and ZCode registered, with live loading still unproven from cold
  inventory;
- Codex hook trust reported unverified by cold status;
- active installed roster count 273, so the uncommitted AR-227 additions are
  not installed.

Do not interpret the blank legacy `judge.model` field as unavailable inference;
the ordered provider chain is the active workforce authority.

## Next bounded packages

### Package 1: checkpoint AR-227

Outcome: six new specialists are packaged without changing selection authority.

1. Format the one touched enrichment test if needed.
2. Run the focused AR-227 tests and named fast production spine once.
3. Run dashboard tests, routing and decision-conformance evals, documentation
   validation, and `git diff --check`.
4. If green, mark AR-227 done, create the substantive and required
   `docs(worklog):` ledger commits, push, and open one follow-up PR.
5. Stop AR-227. Do not repair AR-228 inside that PR.

### Package 2: freeze the inference-only contract

Outcome: one superseding ADR makes the owner contract executable and resolves
ADR-0087/0088/0118 contradictions.

1. Inventory every production call to deterministic staffing, role anchors,
   request-based recall, social bypass, semantic risk rules, and preflight
   blocking text.
2. Classify each as remove, inference-owned replacement, objective verifier, or
   historical-compatibility parser.
3. Add failing architectural tests before changing behavior.
4. Stop after the decision, inventory, and failing tests are reviewable.

### Package 3: remove deterministic staffing authority

Outcome: configured inference is the only source of semantic plans, selections,
gaps, hires, and no-specialist decisions.

1. Repair the first failing production boundary only.
2. Rerun focused tests and the named fast spine.
3. Continue boundary by boundary; do not tune prompt cases or add keyword rules.
4. Persist exact failure reasons so no generic unavailable message hides a
   staffing, validation, or risk defect.

### Package 4: live proof and corrected report

Outcome: Codex and ZCode prove the target contract on varied real prompts.

Use a fixed matrix containing at least:

- social greeting;
- substantive technical question;
- repository implementation;
- independent code review;
- external documentation comparison;
- local hardware diagnosis;
- genuine roster gap that hires a contractor;
- no-provider configuration;
- configured provider returning invalid output.

For every case record prompt, provider/model, plan, complete candidate access,
selected or hired specialists, delegation, worker outcome, header, correction
count, latency, and exact failure reason. Require zero header corrections. Only
after the full matrix passes may the local evidence page restore a product-wide
`EUREKA` verdict.

## Stop conditions

- Stop at the first failed boundary; repair it and rerun the same gate.
- Do not broaden into header simplification, dashboard redesign, release work,
  or exhaustive matrices.
- Use at most two independent review passes unless a Critical/High issue remains.
- Do not weaken a test or threshold merely because new specialists change an
  old deterministic ranking; remove the unauthorized deterministic authority.
- Do not claim inference unavailable unless provider attempts prove it.
- Do not claim a specialist, model, hire, delegation, or completion without the
  persisted current-turn receipt.
- Do not say `EUREKA` until the complete AR-228 acceptance matrix passes.

## Immediate verification commands

~~~text
python scripts/context_handoff_status.py --json --threshold 50
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest \
  tests/test_workforce_hiring_contract.py \
  tests/test_known_contractor_install.py \
  tests/test_roster_enrichment_overlay.py \
  tests/test_workforce_selection_safety.py \
  tests/test_workforce_dynamic_hiring.py \
  tests/test_workforce_cli.py \
  tests/test_full_roster_eval.py \
  -q -W error
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

Run the repository's named fast Python spine from `AGENTS.md` before the AR-227
demo checkpoint. Do not run the exhaustive corpus or manual hosted workflows.
