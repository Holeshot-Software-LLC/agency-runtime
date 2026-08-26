---
title: "AR-289 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [handoff, workforce, reranking, inference, providers]
related:
  - docs/roadmap/issue-AR-289-native-reranker-transports.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
  - docs/worklog/README.md
  - README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-289
branch: codex/ar289-native-reranker-transports
evidence_commit: 95402d56ee1a7c908b89d9eeeb45c858f6769446
minimum_ledger_commit: 01ba3b9f97bd2c835ecc6156a08f660514703edd
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/327
---

# AR-289 active recovery capsule

## checkpoint

- Isolated worktree
  `C:/Users/lucas/.codex/visualizations/2026/08/25/01a039fe-b601-7710-828e-6dc4f32dc4bb/agency-runtime-ar289-native-reranker`
  is on `codex/ar289-native-reranker-transports`, based on `origin/main`
  `04057072`.
- The clean planning checkpoint is `95402d56`; its required worklog ledger is
  `01ba3b9f`. The implementation, tests, operating docs, canonical issue, and
  this capsule form the next substantive checkpoint slice.
- The implementation is integrated into draft PR #326. Tracker #327 is linked
  and closed; PR #326 merge is authorized after its required checks pass.
- Telemetry reported 23.6 percent remaining before implementation. The clean
  planning pair was created before code work, and same-task execution continued
  under the fixed 50-percent protocol. Package-closeout telemetry reported 9.9
  percent remaining and again required this clean substantive/ledger pair.

## completed-evidence

- Persisted profiles now distinguish the existing structured `text` reranker
  from a stage-scoped native `rerank` capability. `adapter: jina` cannot become
  a default, declare thinking, or route a generative stage.
- The native transport accepts Jina root, `/v1`, or exact `/v1/rerank` base
  URLs; resolves environment-backed bearer credentials; blocks redirects and
  unsafe credential URLs; bounds all content; and accepts only a complete
  finite scored permutation with a text actual-model receipt.
- Inference sends one positive-only query and complete candidate-document
  batch, reconstructs per-unit relative order, and preserves typed-only recall
  on every provider, identity, or contract failure. Scores remain absent from
  staffing evidence and authority.
- Focused verification passed `174` tests. The named fast spine plus the new
  provider file passed `856` with `20` expected skips. Dashboard tests passed
  `134`; whole-repository Ruff checks passed for `691` files; docs validation
  passed for `807` files; routing evaluation passed every gate.
- Decision conformance passed its baseline, killed `160/160` curated mutations,
  reported zero survivors, and confirmed the source tree stayed unchanged. An
  initial system-Python launch correctly failed before mutation because that
  interpreter lacked pytest; the repository-virtualenv run supplied the valid
  result.
- Both supplied Jina endpoints answered a separate bounded live probe before
  this code slice. The clean stacked implementation was later installed under
  explicit owner authorization and its native reranker file hash matched
  source. No credential or route was persisted, so there is still no live
  post-implementation Agency/Jina result.

## exact-blocker

- The implementation has no known code blocker. Required PR #326 hosted checks
  are green and its merge is authorized.
- A post-merge live Jina smoke requires a rotated/environment-backed key and an
  installed merged build. Do not reuse or record the credential pasted into
  conversation history.

## same-task-continuity

Continue in this task through normal compaction. Before any additional work,
verify the exact worktree, branch, status, and latest substantive/ledger pair.
The 50-percent threshold requires clean checkpoints but does not authorize a
new task, tracker write, publication, or runtime mutation.

## next-bounded-work-package

1. Merge PR #326 after scoped tracker parity and the required gates pass.
2. After merge, install the merged build, place a rotated key in `JINA_API_KEY`,
   configure the two explicit Jina recall profiles, validate config, and run a
   fresh additive smoke without persisting the credential.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_reranker_provider.py tests/test_inference_profiles.py tests/test_workforce_inference.py -q -W error
python -m pytest <named fast spine from AGENTS.md plus native provider test> -q -W error
node --test tests/dashboard_ui.test.mjs
python -m agency_runtime.cli eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Do not mutate, switch, clean, stage, or commit the shared checkout.
- Do not make native scores staffing confidence, eligibility, hiring evidence,
  or execution authority; preserve recruiter and verifier ownership.
- Do not send raw transcript, prior messages, negative suitability fields,
  credentials, or stored outcomes through native reranking.
- Preserve the structured text path for local chat models, LiteLLM, direct API
  keys, and Codex or Claude subscription CLIs.
- Do not persist the supplied credential or install/publish an unmerged branch.
- This turn authorizes tracker #327 and PR #326 merge only. It does not
  authorize publishing, tagging, signing, or unrelated machine mutation.
