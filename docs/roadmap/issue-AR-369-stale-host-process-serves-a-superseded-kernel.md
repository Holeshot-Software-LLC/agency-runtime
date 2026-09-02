---
title: "AR-369: A stale host process keeps serving a superseded kernel after deploy"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [deploy, hermes, resident-managers, kernel, operations]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-366-openclaw-fail-open-withhold.md
  - docs/roadmap/issue-AR-357-canonical-response-contract-statement.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-369
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/504
depends_on: []
blocks: []
---

# AR-369: A stale host process keeps serving a superseded kernel after deploy

## Problem

The operator reported that the hermes mentor bot replaced every reply with
`Agency Runtime blocked an unverified draft because turn-scoped finalization
did not accept it`, and that the TUI header read
`Agency/Agencies loaded: none` even though a resident steward is always
bound. Both symptoms had one cause, and it was a deploy defect, not a model
or contract defect.

The failure chain, measured on this box 2026-09-02:

1. The hermes gateway process had been running since 2026-09-01 14:29, so it
   still held the Agency plugin as it existed then, pointing at a launcher
   tree whose kernel is **v4** (`113bc675…`). The plugin file on disk had
   been rewritten by the deploy and points at the **v5** tree
   (`62c94d87…`), which the running process never re-imported.
2. Every hermes turn therefore wrote a resident-manager binding carrying the
   v4 kernel. `validate_resident_manager_binding` raises
   `resident-manager kernel reference is not current`.
3. `_project_preflight_recipe` returns `None`, so
   `get_completion_evidence_snapshot` raises
   `RuntimeError: ready preflight recipe failed integrity validation`.
4. With no readable snapshot the header cannot be filled, so it renders
   `Agency/Agencies loaded: none`, and `validate_completion_policy` reports
   every one of the five header fields missing.
5. `transform_llm_output` treats that as an evaluated negative and replaces
   the operator's answer with the block message.

Claude and openclaw wrote `62c94d87…` (v5) on the same runtime at the same
time, which is what isolated the fault to the hermes process rather than the
code.

## Current state

Fixed operationally: `systemctl --user restart hermes-gateway-nexus.service`
made the next hermes turn write the v5 kernel, the snapshot read cleanly with
`resident_managers=['agency-steward']`, and the hermes battery passed.

The deploy procedure is what allowed it. AR-337 records the hermes step as a
"single-process restart", but this host runs **two** systemd user services --
`hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service` -- and
only the gateway loads the Agency plugin. Restarting the dashboard, which is
the obvious-looking process, changes nothing and looks like a successful
deploy.

## Approach

Two layers, matching AR-358's shape:

1. Detect it instead of relying on the operator noticing: a turn whose
   binding carries a superseded kernel should say so with a distinct reason
   code, not fail deep in recipe projection with an integrity error that
   reads like corruption. `agency doctor` should report a host whose live
   binding kernel differs from the installed one.
2. Correct the deploy contract: AR-337's hermes step must name the gateway
   service explicitly, and `agency install --agent hermes` should report that
   a restart of that service is required (it already returns
   `restart_required`, but nothing checks it against the running process).

## Dependencies

- None; the trust-chain and rule-8 work is independent.

## Acceptance

- [ ] A binding whose kernel reference is superseded produces a distinct,
      named reason code rather than a recipe integrity error.
- [ ] `agency doctor` names any host whose most recent binding kernel does
      not match the installed kernel.
- [ ] The AR-337 deploy steps name `hermes-gateway-nexus.service` as the
      process that must restart, and say why the dashboard is not it.
