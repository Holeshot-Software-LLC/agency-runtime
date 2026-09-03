---
title: "AR-382: A predecessor package projects today's prose case, so no installed contractor can ever advance"
status: done
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, install, contract-schema, defect]
related:
  - docs/roadmap/issue-AR-381-contract-prose-outside-the-execution-profile-is-casefolded.md
  - docs/roadmap/issue-AR-379-hire-schema-has-no-home-for-domain-procedure.md
  - docs/decisions/0196-carry-governed-method-and-an-output-exemplar-in-the-contractor-card.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-382
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/573
depends_on: []
blocks: []
---

# AR-382: A predecessor package projects today's prose case, so no installed contractor can ever advance

## Problem

`install_known_contractors` advances an already-installed contractor only when
its stored identity byte-matches a known predecessor package. The comparison
(`known_installer.py:580-599`) checks seven things, and the last one is the
projected **recruitment contract**.

Every predecessor builder — `_legacy_known_contractor_package`,
`_v2_known_contractor_package`, `_v3_known_contractor_package` — reconstructed
its contract with `replace(current, schema_version=N)`, which only *relabels*
the version. `compile_contractor` re-parses internally, so the predecessor
**prompt** was always correct. `_known_contractor_agent` reads the dataclass
directly, so the predecessor **projection** kept the current version's prose.

After AR-381 made contract prose case-preserving at v4, that divergence became
load-bearing: the reconstructed v2 predecessor carried v4-cased `not_for` and
`scope_qualifiers` into a document that is supposed to reproduce a v2 install.

## Current state

Measured live on 2026-09-03 against the real Store, runtime installed from
`b1f030f2`:

```
agency install --all
  Governed contractors: 0 installed, 0 upgraded, 0 already current, 15 preserved
```

All fifteen packaged contractors were `preserved`. The v2 predecessor matches
six of the seven clauses and fails only on the projection:

```
worker.current_hash          True
worker.current_version       True
prompt.hash                  True
prompt.version               True
prompt.prompt_body           True
prompt.prompt_truncated      True
detail.recruitment_contract  False   <-- the only mismatch

not_for          stored  ["train and evaluate a specialized machine-learning model", ...]
                 rebuilt ["Train and evaluate a specialized machine-learning model", ...]
scope_qualifiers stored  ["build a typed async python cli with packaging and failure-path tests"]
                 rebuilt ["Build a typed async Python CLI with packaging and failure-path tests"]
```

So AR-379's and AR-381's card-quality work reaches only fresh installs. Every
existing worker stays on its v2 card: `agency route` still returns
`audit_revision: package-v2-cf4f7eeac1ffc395` with lowercased prose.

The v1 predecessor had the same latent defect; it was invisible only because
nothing compared its projection until v4 introduced a case difference.

## Approach

Re-parse each predecessor at its own schema version instead of relabelling it,
so the dataclass the projection reads folds exactly as that version folded.

## Acceptance

- [x] Every predecessor package below the case-preserving version projects
      casefolded `not_for` and `scope_qualifiers`, proven by test over all
      fifteen packaged contractors and every predecessor version.
- [x] An installed contractor at the previous packaged version advances rather
      than being preserved, proven against a real Store.
- [x] The predecessor prompt identities are unchanged, so no already-registered
      worker becomes unresolvable.
