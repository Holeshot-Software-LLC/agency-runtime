---
title: "AR-414: Restore reliable staffing and truthful failed-turn headers"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [staffing, headers, codex, reliability]
related:
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/worklog/2026-09-08-negated-request-scope.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
  - docs/worklog/README.md
  - docs/worklog/2026-09-08-failed-headers-and-planner.md
  - docs/roadmap/handoffs/issue-AR-414.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-414
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/773
depends_on: []
blocks: []
---

# AR-414: Restore reliable staffing and truthful failed-turn headers

## Problem

Trusted Codex hooks and a reachable MCP do not ensure staffing works. Ordinary
turns time out at the planner, then report every header field unverified even
though the exact failure receipt is readable. Earlier calls also confused a
hashed resident-manager turn reference with the actual trace/session IDs.

## Current state

Initial baseline before the repair: the header reader requires an active turn and rejects the
persisted preflight_failed state before rendering its receipt. Even historical
validation rejects the valid failure binding because no ready recipe exists.
The planner's configured alias has two gateway deployments; recent actual
responses identify GLM-5.3-flash. One classification took19.8seconds followed by
a60.1second planner timeout. No hook approval or new credential is needed.

The diagnostic renderer and finalizer are implemented. Request-scoped failed
turns also lacked persisted steward-binding evidence; the close now retains the
validated claim atomically. Focused header/store/preflight checks:117passed,
1skipped before final formatting/helper extraction. Live verification pending.

Checkpoint ae2220bb/ef29fc6b: new regression12pass; production spine1151pass,
3skip; dashboard224pass. The hook now supplies the real session/trace IDs next
to the initial header so the model need not guess from the hashed manager ID.
No accepted finalization is claimed for diagnostic failure output.

A bounded existing-deployment probe forwarding low via extra_body returns a
valid five-unit plan after one semantic repair (17.1seconds); earlier low at
the top level was filtered by the installed gateway OpenAI adapter. Current
GLM5.3 documentation supports low/high/max, not medium. A reversible experiment
sets only this planner deployment's order2to0 and extra_body.reasoning_effort
to low; unchanged fields are checked exactly. End-to-end validation is pending;
the experiment must be restored unless it proves useful in ordinary staffing.

The corrected instruction probe now accepts staffing in25.078seconds with
planner, recall, recruiter and critic all applied; see the linked worklog for
warm-cache limitations. The gateway correction is retained. Native verification
is waiting_for_operator: the newly installed bundle's eight hook hashes are
actually modified, unlike the prior trusted bundle. No trust bypass or repeated
native activation attempt is authorized by that state.

PR775/975ce7b4 merges the explicit planner instructions. Final6786aaa2 wheel
is installed, all614package files match, and final installed MCP failure
diagnostics pass. The final plugin is0.1.0+codex.6c3ad021798c. Canonical build,
independent artifact verification, focused176 and final fast spine1151/3skip
pass. The bounded package is waiting_for_operator for fresh native hook trust;
this issue remains in_progress and is not acceptance-closed.

Final stock installed fresh-input call: planner accepted10925ms without repair;
whole staffing failed48.626seconds at two recruiter validations, the repair
reporting recruiter_response_shape_invalid. No native or overall staffing
success is claimed. Trust approval and recruiter reliability remain separate
unfinished gates; the earlier25.078second accepted probe is not a general guarantee.

Resumed checkpoint: all eight hooks are now trusted. A normal native run on the
installed artifact delivered all five truthful failure-header fields, proving
that the restart/trust blocker is resolved. It revealed a deterministic plan
scope bug, now tracked separately as AR-415: `not a request to change` incorrectly
triggered mutation and release requirements. Two instrumented installed staffing
calls accepted (32.141s and18.118s); one fresh input failed HTTP transport. The
recruiter shape failure was not reproduced and is not declared repaired. Phase
implementing; AR-415 owns the next bounded scope repair and installed test.

AR-415 is now merged and installed, with deterministic installed checks passing.
Its new bundle changes the eight hook hashes again; the next native run is
waiting_for_operator for approval of plugin0.1.0+codex.07ad50ea4f52. No claim that
the earlier native diagnostic proves this new artifact. Staffing reliability
and current-artifact native scope verification remain unfinished.

## Approach

Render validated failure diagnostics separately from accepted finalization.
Preserve terminal immutability, exact session/trace binding and all staffing
acceptance checks. Identify the actual planner transport/model boundary with
bounded existing-provider probes before retaining any configuration change.
Run focused and fast checks, then installed/native demonstrations. Keep AR-404
and this issue open until their respective live gates are actually met.

## Dependencies

AR-408/AR-413 provide immutable, content-free failure receipts. Existing native
trust is approved; no credential replacement or trust bypass is in scope.

## Acceptance

- [ ] Failed-turn snapshots and finalizer output show the exact bounded cause,
      without claiming staffing success or reopening/accepting a failed run.
- [ ] Missing, malformed, cross-session and other-terminal evidence retain
      their rejection boundaries; ordinary accepted finalization is unchanged.
- [ ] Real planner/staffing calls demonstrate a repair with the original
      acceptance contract intact; record timings and limitations.
- [ ] An installed native turn shows the corresponding truthful header and
      staffing outcome; repository, tracker and worklog evidence agree.
